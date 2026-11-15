# Pilot data downloads

Scripts that fetch the raw pilot inputs into the repo-root `data/` folder (gitignored). They read
the analysis grid and the Ireland outline from [`ml/config/`](../../config/). Dataset citations,
licences and acknowledgement wording are in the root [`REFERENCES.md`](../../../REFERENCES.md).

```bash
cd ml/pipelines/download
make install                 # requests, pandas, ... (Python 3.10+)
cp .env.example .env         # Earthdata Login, only for the NASA AppEEARS / IMERG / direct steps
make all-fast                # POWER, SoilGrids, Met Éireann, GeoNames + check (no login needed)
make submit && make wait     # AppEEARS jobs (MODIS NDVI etc.): submit first, they take hours
make imerg                   # optional: GPM IMERG monthly rain
make check                   # what is present and what is missing
```

| Script | Writes |
| --- | --- |
| `01_power.py` | `data/raw/power/*.json`, `data/processed/power_daily.parquet`, `data/processed/cell_to_power_node.csv` |
| `02_soilgrids.py` | SoilGrids values at the 0.05° cell centroids |
| `03_met_eireann.py` | Met Éireann station CSVs |
| `04_geonames.py` | GeoNames IE + GB dumps (place-search fallback) |
| `10_appeears_submit.py`, `11_appeears_download.py` | AppEEARS requests and downloads |
| `12_direct_landcover_srtm.py` | MCD12Q1 land cover and SRTM elevation tiles |
| `20_imerg.py` | GPM IMERG monthly totals |
| `99_check.py` | A report of the expected files |

Re-runs skip files that already exist. Override the folders with `AGROLENS_RAW` /
`AGROLENS_PROCESSED` and the years with `AGROLENS_YEAR_START` / `AGROLENS_YEAR_END`.
The Irish Soil Information System drainage map has no API and is still downloaded by hand.
