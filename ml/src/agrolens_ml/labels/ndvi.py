"""NDVI labels: QA filter -> monthly max-value composite (Terra + Aqua) -> cell mean -> z -> label.

Source: MOD13Q1 / MYD13Q1 v6.1 tiles (h17v03 covers all of Ireland), downloaded directly
from NASA Earthdata or via AppEEARS. The core works on per-pixel arrays,
so either source can feed it.

  QA         keep pixel reliability 0 (good) and 1 (marginal); drop 2 (snow/ice), 3 (cloudy), fill
  month      from each pixel's own "composite day of the year" (the day the value was observed)
  composite  per pixel and calendar month: MAX NDVI over all Terra+Aqua composites in that month
  cell       mean over the cell's valid agricultural pixels; valid_frac = valid / ag pixels
  label      stress_label = ndvi_z <= -1 for months 3-10 with valid_frac >= 0.3, else null
  z          vs the FIXED 2001-2020 climatology of (cell, calendar month), >= 8 valid years
             (the target definition). ndvi_z_feat is the leak-free anomaly used as a FEATURE
             (baseline years strictly before the month, as in features/build.py).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from agrolens_ml.config import BASELINE, MIN_CLIM_YEARS, MIN_VALID_FRAC, MONTHS, STRESS_Z
from agrolens_ml.grid import AG_CLASSES, cell_index, sinusoidal_to_lonlat

NDVI_SDS = "250m 16 days NDVI"
REL_SDS = "250m 16 days pixel reliability"
DOY_SDS = "250m 16 days composite day of the year"
NDVI_FILL, NDVI_SCALE, NDVI_VALID = -3000, 10000.0, (-2000, 10000)
KEEP_RELIABILITY = (0, 1)
MIN_LABEL_YEARS = 8
LABEL_MONTHS = range(2, 11)  # Feb..Oct; Feb only feeds lag features
_NAME = re.compile(r"^(MOD|MYD)13Q1\.A(\d{4})(\d{3})\.(h\d\dv\d\d)\.")


class PixelIndex:
    """Agricultural pixels of the retained cells inside one 250 m MODIS tile."""

    def __init__(self, flat: np.ndarray, cell_codes: np.ndarray, cell_ids: np.ndarray):
        self.flat = flat  # flat pixel indices into the tile
        self.cell_codes = cell_codes  # 0..n_cells-1 per selected pixel
        self.cell_ids = cell_ids  # cell_id per code
        self.n_ag = np.bincount(cell_codes, minlength=len(cell_ids)).astype(float)

    @classmethod
    def build(
        cls, grid_cells: pd.DataFrame, landcover: np.ndarray, h: int, v: int, n: int = 4800
    ) -> "PixelIndex":
        lon, lat = sinusoidal_to_lonlat(h, v, n)
        keys = cell_index(lon, lat).ravel()
        del lon, lat
        lut = pd.Series(
            np.arange(len(grid_cells)),
            index=cell_index(grid_cells["lon"].to_numpy(), grid_cells["lat"].to_numpy()),
        )
        codes = lut.reindex(keys).to_numpy()
        factor = n // landcover.shape[0]  # 250 m pixel -> 500 m land-cover pixel
        lc = np.repeat(np.repeat(landcover, factor, axis=0), factor, axis=1).ravel()
        sel = ~np.isnan(codes) & np.isin(lc, AG_CLASSES)
        flat = np.flatnonzero(sel)
        return cls(flat, codes[sel].astype(np.int64), grid_cells["cell_id"].to_numpy())


def parse_name(path: Path) -> tuple[str, int, int, str]:
    m = _NAME.match(path.name)
    if not m:
        raise ValueError(f"not a MOD13Q1/MYD13Q1 granule: {path.name}")
    return m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)


def qa_ndvi(ndvi_raw: np.ndarray, reliability: np.ndarray) -> np.ndarray:
    """Scaled NDVI with NaN where QA rejects the pixel."""
    ok = (
        np.isin(reliability, KEEP_RELIABILITY)
        & (ndvi_raw != NDVI_FILL)
        & (ndvi_raw >= NDVI_VALID[0])
        & (ndvi_raw <= NDVI_VALID[1])
    )
    return np.where(ok, ndvi_raw / NDVI_SCALE, np.nan).astype(np.float32)


def pixel_months(year: int, doy: np.ndarray) -> np.ndarray:
    """Calendar month (1..12) of each pixel's composite day of year; 0 where DOY is missing."""
    doy = np.asarray(doy)
    ok = (doy >= 1) & (doy <= 366)
    dates = np.datetime64(f"{year}-01-01") + (np.where(ok, doy, 1) - 1).astype("timedelta64[D]")
    month = dates.astype("datetime64[M]").astype(np.int64) % 12 + 1
    return np.where(ok, month, 0)


def read_granule(path: Path, pix: PixelIndex) -> tuple[np.ndarray, np.ndarray]:
    """(QA'd NDVI, calendar month) for the selected pixels of one HDF4 granule."""
    from pyhdf.SD import SD, SDC  # pylint: disable=import-outside-toplevel

    _, year, _, _ = parse_name(path)
    sd = SD(str(path), SDC.READ)
    try:
        ndvi = sd.select(NDVI_SDS).get().ravel()[pix.flat]
        rel = sd.select(REL_SDS).get().ravel()[pix.flat]
        doy = sd.select(DOY_SDS).get().ravel()[pix.flat]
    finally:
        sd.end()
    return qa_ndvi(ndvi, rel), pixel_months(year, doy)


def year_cell_months(
    composites: list[tuple[np.ndarray, np.ndarray]], pix: PixelIndex, year: int
) -> pd.DataFrame:
    """Max-value monthly composite per pixel, then cell mean + valid_frac, for one year."""
    if not composites:
        return pd.DataFrame()
    ndvi = np.stack([c[0] for c in composites])  # (K, P)
    month = np.stack([c[1] for c in composites])
    n_cells = len(pix.cell_ids)
    out = []
    for m in LABEL_MONTHS:
        vals = np.where(month == m, ndvi, np.nan)
        with np.errstate(all="ignore"):
            import warnings  # pylint: disable=import-outside-toplevel

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                mx = np.nanmax(vals, axis=0)
        valid = ~np.isnan(mx)
        cnt = np.bincount(pix.cell_codes[valid], minlength=n_cells).astype(float)
        tot = np.bincount(pix.cell_codes[valid], weights=mx[valid], minlength=n_cells)
        with np.errstate(invalid="ignore", divide="ignore"):
            mean = tot / cnt
        out.append(
            pd.DataFrame(
                {
                    "cell_id": pix.cell_ids,
                    "month": f"{year}-{m:02d}",
                    "ndvi": mean,
                    "valid_frac": cnt / pix.n_ag,
                }
            )
        )
    return pd.concat(out, ignore_index=True)


def add_anomalies_and_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Fixed-baseline ndvi_z + stress_label (target) and leak-free ndvi_z_feat (feature)."""
    df = df.copy()
    per = pd.PeriodIndex(df["month"], freq="M")
    df["_year"], df["_cal"] = per.year, per.month
    good = df["valid_frac"] >= MIN_VALID_FRAC
    in_base = df["_year"].between(*BASELINE)

    base = df[good & in_base].groupby(["cell_id", "_cal"])["ndvi"].agg(["mean", "std", "count"])
    base = base[base["count"] >= MIN_LABEL_YEARS]
    clim = base.reindex(pd.MultiIndex.from_arrays([df["cell_id"], df["_cal"]])).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (df["ndvi"].to_numpy() - clim[:, 0]) / np.where(clim[:, 1] > 0, clim[:, 1], np.nan)
    df["ndvi_z"] = np.where(good, z, np.nan)
    label = pd.array(df["ndvi_z"] <= STRESS_Z, dtype="boolean")
    label[~(good & df["_cal"].isin(list(MONTHS)) & df["ndvi_z"].notna()).to_numpy()] = pd.NA
    df["stress_label"] = label

    # leak-free feature anomaly: baseline values strictly before the row (same as build.py)
    df = df.sort_values(["cell_id", "month"]).reset_index(drop=True)
    v = df["ndvi"].where(good & in_base)
    pres, fill = v.notna().astype(float), v.fillna(0.0)
    grp = [df["cell_id"], df["_cal"]]
    n = pres.groupby(grp).cumsum() - pres
    s = fill.groupby(grp).cumsum() - fill
    ss = (fill**2).groupby(grp).cumsum() - fill**2
    ok = n >= MIN_CLIM_YEARS
    mean = (s / n).where(ok)
    std = np.sqrt(((ss - n * mean**2) / (n - 1)).where(ok).clip(lower=0))
    df["ndvi_z_feat"] = ((df["ndvi"] - mean) / std.where(std > 0)).where(good)
    return df.drop(columns=["_year", "_cal"])


def discover(dirs: list[Path]) -> dict[int, list[Path]]:
    """Granules (Terra + Aqua) grouped by year, Feb-Oct only."""
    by_year: dict[int, list[Path]] = defaultdict(list)
    for d in dirs:
        for p in sorted(d.glob("M?D13Q1.A*.hdf")):
            _, year, doy, _ = parse_name(p)
            if 32 <= doy <= 304:
                by_year[year].append(p)
    return dict(sorted(by_year.items()))


def build_ndvi_table(
    dirs: list[Path],
    grid_cells: pd.DataFrame,
    landcover: np.ndarray,
    h: int = 17,
    v: int = 3,
    log=print,
) -> pd.DataFrame:
    pix = PixelIndex.build(grid_cells, landcover, h, v)
    log(f"{len(pix.flat):,} agricultural pixels in {len(grid_cells)} cells")
    frames = []
    for year, paths in discover(dirs).items():
        comps = [read_granule(p, pix) for p in paths]
        frames.append(year_cell_months(comps, pix, year))
        log(f"{year}: {len(paths)} composites")
    return add_anomalies_and_labels(pd.concat(frames, ignore_index=True))


def summary_markdown(df: pd.DataFrame) -> str:
    lab = df.dropna(subset=["stress_label"]).copy()
    lab["cal"] = lab["month"].str[5:7].astype(int)
    lab["year"] = lab["month"].str[:4].astype(int)
    lab["y"] = lab["stress_label"].astype(float)
    by_month = lab.groupby("cal")["y"].agg(["mean", "count"])
    summer = lab[lab["cal"].isin([6, 7])].groupby("year")["y"].mean().sort_values(ascending=False)
    lines = [
        "# NDVI stress labels: summary",
        "",
        f"Overall positive rate: **{lab['y'].mean():.3f}** "
        f"({int(lab['y'].sum()):,} of {len(lab):,} labelled cell-months; target 0.10-0.18)",
        "",
        "| Month | Positive rate | Labelled rows |",
        "|---|---|---|",
    ]
    lines += [f"| {m} | {r['mean']:.3f} | {int(r['count']):,} |" for m, r in by_month.iterrows()]
    lines += [
        "",
        "Share of stressed cells in Jun-Jul, by year (highest first):",
        "",
        "| Rank | Year | Share |",
        "|---|---|---|",
    ]
    lines += [f"| {i} | {y} | {s:.3f} |" for i, (y, s) in enumerate(summer.items(), 1)]
    rank = list(summer.index).index(2018) + 1 if 2018 in summer.index else None
    lines += ["", f"2018 (known national drought) ranks **{rank}** of {len(summer)}."]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ AppEEARS NetCDF source
# AppEEARS area outputs (geographic projection): one NetCDF per task, dims (time, lat, lon),
# variables _250m_16_days_NDVI (int16, scale 1e-4, fill -3000) and
# _250m_16_days_pixel_reliability (int32, fill -1); time = composite START, seconds since 2000-01-01.
NC_NDVI = "_250m_16_days_NDVI"
NC_REL = "_250m_16_days_pixel_reliability"


def geographic_pixel_index(
    grid_cells: pd.DataFrame,
    landcover: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    lc_h: int = 17,
    lc_v: int = 3,
) -> PixelIndex:
    """PixelIndex for a regular lon/lat grid; ag mask looked up in the sinusoidal LC tile."""
    from agrolens_ml.grid import (
        R_EARTH,
        TILE_M,
        X_MIN,
        Y_MAX,
    )  # pylint: disable=import-outside-toplevel

    lon2, lat2 = np.meshgrid(lon, lat)
    keys = cell_index(lon2, lat2).ravel()
    lut = pd.Series(
        np.arange(len(grid_cells)),
        index=cell_index(grid_cells["lon"].to_numpy(), grid_cells["lat"].to_numpy()),
    )
    codes = lut.reindex(keys).to_numpy()
    n = landcover.shape[0]
    size = TILE_M / n
    phi = np.deg2rad(lat2).ravel()
    x = R_EARTH * np.deg2rad(lon2).ravel() * np.cos(phi)
    y = R_EARTH * phi
    col = np.floor((x - (X_MIN + lc_h * TILE_M)) / size).astype(np.int64)
    row = np.floor(((Y_MAX - lc_v * TILE_M) - y) / size).astype(np.int64)
    inside = (row >= 0) & (row < n) & (col >= 0) & (col < n)
    lc = np.full(keys.shape, 255, dtype=landcover.dtype)
    lc[inside] = landcover[row[inside], col[inside]]
    sel = ~np.isnan(codes) & np.isin(lc, AG_CLASSES)
    return PixelIndex(
        np.flatnonzero(sel), codes[sel].astype(np.int64), grid_cells["cell_id"].to_numpy()
    )


def read_appeears_nc(
    path: Path, grid_cells: pd.DataFrame, landcover: np.ndarray, cache: dict
) -> dict[int, list[tuple[np.ndarray, np.ndarray]]]:
    """{year: [(QA'd NDVI, month per pixel), ...]} for one AppEEARS NetCDF (Feb-Oct composites)."""
    import xarray as xr  # pylint: disable=import-outside-toplevel

    out: dict[int, list] = defaultdict(list)
    with xr.open_dataset(path, decode_cf=False, decode_times=False) as ds:
        lon, lat = ds["lon"].values, ds["lat"].values
        key = (len(lon), len(lat), float(lon[0]), float(lat[0]))
        if key not in cache:
            cache[key] = geographic_pixel_index(grid_cells, landcover, lon, lat)
        pix = cache[key]
        starts = np.datetime64("2000-01-01") + ds["time"].values.astype("timedelta64[s]")
        for t, start in enumerate(starts):
            day = start.astype("datetime64[D]")
            year = int(str(day)[:4])
            month = int(str(day)[5:7])
            if month not in LABEL_MONTHS:
                continue
            ndvi = ds[NC_NDVI][t].values.ravel()[pix.flat]
            rel = ds[NC_REL][t].values.ravel()[pix.flat]
            out[year].append((qa_ndvi(ndvi, rel), np.full(len(pix.flat), month)))
    return dict(out), pix


def build_ndvi_table_appeears(
    nc_files: list[Path], grid_cells: pd.DataFrame, landcover: np.ndarray, log=print
) -> pd.DataFrame:
    """Cell-month NDVI + labels from AppEEARS NetCDFs (Terra and/or Aqua, any year chunks)."""
    cache: dict = {}
    by_year: dict[int, list] = defaultdict(list)
    pix = None
    for path in nc_files:
        comps, pix = read_appeears_nc(path, grid_cells, landcover, cache)
        for year, lst in comps.items():
            by_year[year].extend(lst)
        log(
            f"{path.parent.name}: {sum(len(v) for v in comps.values())} Feb-Oct composites, "
            f"{len(pix.flat):,} ag pixels"
        )
    if len(cache) > 1:
        raise ValueError("AppEEARS outputs are on different grids; build one table per grid")
    frames = [year_cell_months(by_year[y], pix, y) for y in sorted(by_year)]
    return add_anomalies_and_labels(pd.concat(frames, ignore_index=True))
