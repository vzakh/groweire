"""Pilot grid & masks -> grid_cells.parquet (PLAN_10 task 10, brief §7.1).

Inputs (all offline):
  ml/config/grid_005deg.csv             0.05° cell centroids (cell_id, lon, lat)
  data/raw/direct/mcd12q1/MCD12Q1.A<y>*.hdf       IGBP land cover (LC_Type1), MODIS sinusoidal 500 m
  data/raw/direct/srtmgl1/*.SRTMGL1.hgt.zip       1-arcsec elevation tiles
  data/processed/soil_cell.parquet                SoilGrids 0-5/5-15/15-30 cm at centroids

Cell values:
  ag_fraction    share of the cell's 500 m pixels in IGBP 10 (grassland), 12 (cropland), 14 (mosaic)
  crop_fraction  share in 12 + 14 only (Irish tillage is a minority; reported as a slice)
  elev_m         mean SRTM over the cell's land pixels
  slope_deg      mean slope [deg] from the 1-arcsec DEM with metric pixel spacing at each latitude
  soil           0-30 cm depth-weighted means (weights 5/10/15 cm)
  drainage_class majority class of 100 sample points per cell on the EPA/Teagasc national soil map
                 (data/raw/irish_sis/.../soils_ie_f1.shp, IFS codes -> IFS_DRAINAGE below);
                 null outside the Republic of Ireland. arable_fraction -> null (EUCROPMAP not used)
Cells with ag_fraction >= AG_MIN are retained.
"""

from __future__ import annotations

import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from agrolens_ml.contract import CELL_STATIC_KEYS
from agrolens_ml.schemas import GRID_CELLS_SCHEMA

CELL_DEG = 0.05
HALF = CELL_DEG / 2
AG_MIN = 0.3
AG_CLASSES = (10, 12, 14)
CROP_CLASSES = (12, 14)
LC_FILL = 255

# MODIS sinusoidal grid (MODLAND)
R_EARTH = 6371007.181
TILE_M = 1111950.5197665
X_MIN, Y_MAX = -20015109.354, 10007554.677

SRTM_N = 3600  # 1 arcsec, tiles are 3601 x 3601 with shared edges; drop the last row/col
SRTM_NODATA = -32768
SOIL_PROPS = ("clay", "sand", "soc", "phh2o", "bdod")

# Teagasc/EPA indicative soil map (IFS_CODE) -> drainage ordinal 1 (excessive) .. 5 (very poor).
# Descriptions from the map legend (Soils/Legend/LEGEND.DOC); the 1-5 ordinal is AgroLens' mapping.
IFS_DRAINAGE: dict[int, int | None] = {
    11: 2, 12: 2,  # deep well drained mineral (acid / basic)
    21: 2, 22: 2,  # shallow well drained mineral
    31: 4, 32: 4,  # deep poorly drained mineral
    33: 4, 34: 4,  # shallow poorly drained mineral
    43: 4, 46: 4,  # shallow rocky, peaty topsoil
    41: 5, 42: 5,  # poorly drained mineral with peaty topsoil
    44: 5, 45: 5,  # shallow poorly drained, peaty topsoil
    51: 3, 53: 3, 56: 3,  # alluvium (mineral, marl), lacustrine: variable
    61: 5, 63: 5, 64: 5, 65: 5, 66: 5, 75: 5,  # raised/blanket/cutaway/fen peat, swamp
    70: 1, 71: 1, 72: 1,  # scree, aeolian sands, marine sands
    73: None, 74: None, 76: None,  # marine sediment, made ground, water
}  # fmt: skip
SIS_SAMPLES_PER_SIDE = 10
SOIL_DEPTHS = (("0_5cm", 5.0), ("5_15cm", 10.0), ("15_30cm", 15.0))


def sinusoidal_to_lonlat(h: int, v: int, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Pixel-centre lon/lat [deg] of a MODIS sinusoidal tile (h, v) with n x n pixels."""
    size = TILE_M / n
    x = X_MIN + h * TILE_M + (np.arange(n) + 0.5) * size
    y = Y_MAX - v * TILE_M - (np.arange(n) + 0.5) * size
    lat = y / R_EARTH  # radians
    lon = x[None, :] / (R_EARTH * np.cos(lat)[:, None])
    return np.rad2deg(lon), np.repeat(np.rad2deg(lat)[:, None], n, axis=1)


def cell_index(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Integer key of the 0.05° cell containing (lon, lat); centroids sit at k*0.05 + 0.025."""
    ix = np.floor(np.asarray(lon) / CELL_DEG).astype(np.int64)
    iy = np.floor(np.asarray(lat) / CELL_DEG).astype(np.int64)
    return ix * 100_000 + iy


def landcover_fractions(hdf_files: list[Path], grid: pd.DataFrame) -> pd.DataFrame:
    """ag_fraction / crop_fraction per cell from MCD12Q1 LC_Type1 tiles."""
    from pyhdf.SD import SD, SDC  # pylint: disable=import-outside-toplevel

    keys, ag, crop = [], [], []
    for path in hdf_files:
        hv = path.name.split(".")[2]  # e.g. h17v03
        h, v = int(hv[1:3]), int(hv[4:6])
        lc = SD(str(path), SDC.READ).select("LC_Type1").get()
        lon, lat = sinusoidal_to_lonlat(h, v, lc.shape[0])
        valid = lc != LC_FILL
        keys.append(cell_index(lon[valid], lat[valid]))
        ag.append(np.isin(lc[valid], AG_CLASSES))
        crop.append(np.isin(lc[valid], CROP_CLASSES))
    frame = pd.DataFrame(
        {"key": np.concatenate(keys), "ag": np.concatenate(ag), "crop": np.concatenate(crop)}
    )
    stats = frame.groupby("key")[["ag", "crop"]].mean()
    gkey = cell_index(grid["lon"].to_numpy(), grid["lat"].to_numpy())
    return pd.DataFrame(
        {
            "ag_fraction": stats["ag"].reindex(gkey).to_numpy(),
            "crop_fraction": stats["crop"].reindex(gkey).to_numpy(),
        },
        index=grid.index,
    )


def _read_hgt(path: Path) -> tuple[np.ndarray, int, int]:
    """SRTM .hgt.zip -> (3600x3600 float array with NaN for nodata/sea, lat0, lon0 of SW corner)."""
    name = path.name.split(".")[0]  # N51W009
    lat0 = int(name[1:3]) * (1 if name[0] == "N" else -1)
    lon0 = int(name[4:7]) * (1 if name[3] == "E" else -1)
    with zipfile.ZipFile(path) as zf:
        member = next(m for m in zf.namelist() if m.endswith(".hgt"))
        raw = np.frombuffer(zf.read(member), dtype=">i2")
    n = int(np.sqrt(raw.size))
    dem = raw.reshape(n, n)[:SRTM_N, :SRTM_N].astype(float)  # row 0 = north edge
    dem[(dem == SRTM_NODATA) | (dem == 0)] = np.nan  # 0 = sea in SRTMGL1
    return dem, lat0, lon0


def _slope_deg(dem: np.ndarray, lat0: int) -> np.ndarray:
    lats = lat0 + 1 - (np.arange(SRTM_N) + 0.5) / SRTM_N
    dy = np.deg2rad(1 / 3600) * 6371000.0
    dx = dy * np.cos(np.deg2rad(lats))[:, None]
    gy, gx = np.gradient(dem)
    return np.rad2deg(np.arctan(np.hypot(gx / dx, gy / dy)))


def terrain(hgt_files: list[Path], grid: pd.DataFrame) -> pd.DataFrame:
    """Mean elevation and slope per cell (1° tile = 20 x 20 cells of 180 x 180 pixels)."""
    per = int(SRTM_N * CELL_DEG)  # 180
    n_cells = SRTM_N // per  # 20
    records = []
    for path in hgt_files:
        dem, lat0, lon0 = _read_hgt(path)
        slope = _slope_deg(dem, lat0)
        with warnings.catch_warnings():  # all-sea blocks -> NaN, expected
            warnings.simplefilter("ignore", category=RuntimeWarning)
            elev_b = np.nanmean(dem.reshape(n_cells, per, n_cells, per), axis=(1, 3))
            slope_b = np.nanmean(slope.reshape(n_cells, per, n_cells, per), axis=(1, 3))
        rows, cols = np.mgrid[0:n_cells, 0:n_cells]
        clat = lat0 + 1 - (rows + 0.5) * CELL_DEG
        clon = lon0 + (cols + 0.5) * CELL_DEG
        records.append(
            pd.DataFrame(
                {
                    "key": cell_index(clon.ravel(), clat.ravel()),
                    "elev_m": elev_b.ravel(),
                    "slope_deg": slope_b.ravel(),
                }
            )
        )
    stats = pd.concat(records).groupby("key").mean()
    gkey = cell_index(grid["lon"].to_numpy(), grid["lat"].to_numpy())
    return stats.reindex(gkey).set_index(grid.index)


def soil_0_30(soil: pd.DataFrame) -> pd.DataFrame:
    """Depth-weighted 0-30 cm means of the SoilGrids layers (NaN-aware)."""
    out = pd.DataFrame(index=soil.index)
    for prop in SOIL_PROPS:
        vals = np.stack([soil[f"{prop}_{d}"].to_numpy(dtype=float) for d, _ in SOIL_DEPTHS])
        w = np.array([wt for _, wt in SOIL_DEPTHS])[:, None] * ~np.isnan(vals)
        with np.errstate(invalid="ignore"):
            out[prop] = np.nansum(vals * w, axis=0) / w.sum(axis=0)
    return out


def drainage_from_soil_map(shp: Path, grid: pd.DataFrame) -> pd.Series:
    """Majority IFS drainage class per cell from a 10 x 10 point sample (null where no soil map)."""
    import geopandas as gpd  # pylint: disable=import-outside-toplevel

    soils = gpd.read_file(shp, columns=["IFS_CODE"])
    soils["drain"] = soils["IFS_CODE"].astype(int).map(IFS_DRAINAGE)
    soils = soils.dropna(subset=["drain"])
    k = SIS_SAMPLES_PER_SIDE
    offs = (np.arange(k) + 0.5) / k * CELL_DEG - HALF
    dx, dy = np.meshgrid(offs, offs)
    lon = (grid["lon"].to_numpy()[:, None] + dx.ravel()[None, :]).ravel()
    lat = (grid["lat"].to_numpy()[:, None] + dy.ravel()[None, :]).ravel()
    pts = gpd.GeoDataFrame({"row": np.repeat(np.arange(len(grid)), k * k)},
                           geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326").to_crs(soils.crs)
    hit = gpd.sjoin(pts, soils[["drain", "geometry"]], how="inner", predicate="within")
    hit = hit.drop_duplicates("index_left") if "index_left" in hit else hit
    mode = hit.groupby("row")["drain"].agg(lambda s: s.value_counts().idxmax())
    out = pd.Series(pd.array([pd.NA] * len(grid), dtype="Int8"), index=grid.index)
    out.iloc[mode.index.to_numpy()] = mode.to_numpy().astype(int)
    return out


def _wkt_box(lon: np.ndarray, lat: np.ndarray) -> list[str]:
    return [
        f"POLYGON (({x - HALF:.3f} {y - HALF:.3f}, {x + HALF:.3f} {y - HALF:.3f}, "
        f"{x + HALF:.3f} {y + HALF:.3f}, {x - HALF:.3f} {y + HALF:.3f}, "
        f"{x - HALF:.3f} {y - HALF:.3f}))"
        for x, y in zip(lon, lat)
    ]


def build_grid(config_dir: Path, raw: Path, processed: Path) -> pd.DataFrame:
    grid = pd.read_csv(config_dir / "grid_005deg.csv", dtype={"cell_id": str})
    lc = landcover_fractions(sorted((raw / "direct" / "mcd12q1").glob("*.hdf")), grid)
    ter = terrain(sorted((raw / "direct" / "srtmgl1").glob("*.hgt.zip")), grid)
    soil = pd.read_parquet(processed / "soil_cell.parquet").set_index("cell_id")
    soil = soil_0_30(soil).reindex(grid["cell_id"]).set_index(grid.index)
    cells = pd.concat([grid, lc, ter, soil], axis=1)
    sis = sorted((raw / "irish_sis").glob("**/soils_ie_f1.shp"))
    cells["drainage_class"] = (drainage_from_soil_map(sis[0], grid) if sis
                               else pd.array([pd.NA] * len(cells), dtype="Int8"))
    cells["arable_fraction"] = np.nan
    cells["geom"] = _wkt_box(cells["lon"].to_numpy(), cells["lat"].to_numpy())
    return cells


def write_grid(cells: pd.DataFrame, out: Path, ag_min: float = AG_MIN) -> pd.DataFrame:
    kept = cells[cells["ag_fraction"] >= ag_min].copy()
    for field in GRID_CELLS_SCHEMA:
        if pa.types.is_float32(field.type):
            kept[field.name] = kept[field.name].astype("float32")
    cols = ["cell_id", "geom", *CELL_STATIC_KEYS, "arable_fraction"]
    pq.write_table(
        pa.Table.from_pandas(kept[cols], schema=GRID_CELLS_SCHEMA, preserve_index=False), out
    )
    return kept


def preview_png(cells: pd.DataFrame, kept: pd.DataFrame, path: Path) -> None:
    import matplotlib  # pylint: disable=import-outside-toplevel

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel

    fig, ax = plt.subplots(figsize=(6, 7))
    ax.scatter(cells["lon"], cells["lat"], s=2, c="#cccccc", label="all cells")
    sc = ax.scatter(
        kept["lon"], kept["lat"], s=2, c=kept["ag_fraction"], cmap="YlGn", vmin=AG_MIN, vmax=1
    )
    fig.colorbar(sc, ax=ax, label="farmland share")
    ax.set_title(f"AgroLens pilot grid: {len(kept)} farmland cells (≥ {AG_MIN:.0%} farmland)")
    ax.set_aspect(1 / np.cos(np.deg2rad(53.4)))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
