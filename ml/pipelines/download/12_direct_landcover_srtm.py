"""Download MCD12Q1 land cover + SRTMGL1 elevation for Ireland DIRECTLY from NASA (earthaccess).

Faster alternative to the AppEEARS area jobs agrolens_MCD12Q1 / agrolens_SRTM, which queue behind
the large NDVI jobs. The files are small (one MODIS tile h17v03 ~6 MB/year; 27 SRTM tiles ~75 MB).
Needs the Earthdata Login in .env (EARTHDATA_USERNAME / EARTHDATA_PASSWORD).

Outputs:
  data/raw/direct/mcd12q1/MCD12Q1.A<year>001.h17v03.061.*.hdf   (HDF4; read with pyhdf)
  data/raw/direct/srtmgl1/<tile>.SRTMGL1.hgt.zip                (GDAL SRTMHGT driver)

  python ml/pipelines/download/12_direct_landcover_srtm.py [--landcover-year 2025]
"""
from __future__ import annotations

import argparse

from common import IE_BBOX, RAW, ensure, load_env, log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--landcover-year", type=int, default=0, help="default: latest available")
    args = ap.parse_args()
    load_env()
    import earthaccess  # pylint: disable=import-outside-toplevel

    earthaccess.login(strategy="environment")

    lc = earthaccess.search_data(short_name="MCD12Q1", version="061", bounding_box=IE_BBOX,
                                 temporal=("2001-01-01", "2030-12-31"))
    years = sorted({int(g.data_links()[0].rsplit("/", 1)[-1].split(".")[1][1:5]) for g in lc})
    year = args.landcover_year or years[-1]
    lc = [g for g in lc if f".A{year}001." in g.data_links()[0]]
    log.info("MCD12Q1 %d: %d granule(s) (available years %s)", year, len(lc), years)
    earthaccess.download(lc, str(ensure(RAW / "direct" / "mcd12q1")))

    dem = earthaccess.search_data(short_name="SRTMGL1", version="003", bounding_box=IE_BBOX)
    log.info("SRTMGL1: %d tiles", len(dem))
    earthaccess.download(dem, str(ensure(RAW / "direct" / "srtmgl1")))
    log.info("done -> %s", RAW / "direct")


if __name__ == "__main__":
    main()
