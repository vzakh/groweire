"""OPTIONAL: GPM IMERG Final monthly precipitation (GPM_3IMERGM, V07) sampled at grid cells.

POWER already provides precipitation, so skip this if short on time. It needs an Earthdata Login
(.env or ~/.netrc) and the `earthaccess` package. It streams each monthly file and keeps only the
Ireland window, without downloading the global files.

Output: data/processed/imerg_cell_month.parquet (cell_id, month, precip_mm)
"""
from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

from common import IE_BBOX, PROCESSED, YEAR_END, YEAR_START, ensure, load_env, log, read_grid


def main() -> None:
    load_env()
    import earthaccess
    import xarray as xr

    earthaccess.login(strategy="environment")
    results = earthaccess.search_data(short_name="GPM_3IMERGM", version="07",
                                      temporal=(f"{YEAR_START}-01-01", f"{YEAR_END}-12-31"),
                                      bounding_box=IE_BBOX)
    log.info("%d IMERG monthly granules", len(results))
    cells = pd.DataFrame(read_grid())
    x0, y0, x1, y1 = IE_BBOX
    rows = []
    for fobj in earthaccess.open(results):
        ds = xr.open_dataset(fobj, group="Grid", engine="h5netcdf")
        sub = ds["precipitation"].sel(lon=slice(x0, x1), lat=slice(y0, y1)).load()
        t = pd.Timestamp(np.asarray(ds["time"].values)[0])
        hours = calendar.monthrange(t.year, t.month)[1] * 24
        vals = sub.isel(time=0).sel(lon=xr.DataArray(cells.lon), lat=xr.DataArray(cells.lat),
                                    method="nearest").values * hours  # mm/hr -> mm/month
        rows.append(pd.DataFrame({"cell_id": cells.cell_id, "month": t.strftime("%Y-%m"),
                                  "precip_mm": vals}))
        log.info("IMERG %s", t.strftime("%Y-%m"))
    ensure(PROCESSED)
    pd.concat(rows).to_parquet(PROCESSED / "imerg_cell_month.parquet", index=False)


if __name__ == "__main__":
    main()
