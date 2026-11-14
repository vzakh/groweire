"""Sample ISRIC SoilGrids v2.0 at every grid-cell centroid, straight from ISRIC's cloud rasters.

Why not the REST API: it is beta and rate-limited (fair use is a few calls per minute), so ~4.5k
points would take many hours. Instead we read only the needed pixels from the official VRT/COG
files over HTTPS (GDAL /vsicurl/), which takes minutes.

Output: data/processed/soil_cell.parquet with conventional units:
  clay/sand/silt %, soc g/kg, phh2o pH, bdod g/cm3, for depths 0-5, 5-15, 15-30 cm (mean).
No login needed.
"""
from __future__ import annotations

import argparse

import pandas as pd
import rasterio
from pyproj import Transformer

from common import PROCESSED, ensure, log, read_grid

BASE = "/vsicurl/https://files.isric.org/soilgrids/latest/data"
PROPS = {  # property: divisor to convert stored integers to conventional units
    "clay": 10, "sand": 10, "silt": 10,  # g/kg -> %
    "soc": 10,                            # dg/kg -> g/kg
    "phh2o": 10,                          # pH*10 -> pH
    "bdod": 100,                          # cg/cm3 -> g/cm3
}
DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="grid_005deg.csv")
    ap.add_argument("--limit", type=int, default=0, help="sample only first N cells (testing)")
    args = ap.parse_args()

    cells = read_grid(args.grid)
    if args.limit:
        cells = cells[: args.limit]
    df = pd.DataFrame(cells)

    env = rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4",
                       GDAL_HTTP_RETRY_DELAY="5", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".vrt,.tif")
    with env:
        for prop, div in PROPS.items():
            for depth in DEPTHS:
                url = f"{BASE}/{prop}/{prop}_{depth}_mean.vrt"
                log.info("sampling %s", url)
                with rasterio.open(url) as src:
                    tr = Transformer.from_crs("EPSG:4326", src.crs.to_wkt(), always_xy=True)
                    xy = [tr.transform(lo, la) for lo, la in zip(df.lon, df.lat)]
                    vals = [v[0] for v in src.sample(xy)]
                    nod = src.nodata
                col = f"{prop}_{depth.replace('-', '_')}"
                df[col] = [None if (nod is not None and v == nod) else v / div for v in vals]

    ensure(PROCESSED)
    df.to_parquet(PROCESSED / "soil_cell.parquet", index=False)
    log.info("wrote soil_cell.parquet: %d cells, %d columns", len(df), df.shape[1])
    log.info("null share per column:\n%s", df.isna().mean().round(3).to_string())


if __name__ == "__main__":
    main()
