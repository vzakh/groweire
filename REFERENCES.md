# References

Every dataset, method, guideline and software package GrowÉire uses, with its licence and how to cite it. The NASA Space Apps Challenge requires every source to be cited, so this list can be copied into the project's *Resources* section.

**Contents**

1. [NASA data](#1-nasa-data)
2. [Other data](#2-other-data)
3. [Methods and science](#3-methods-and-science)
4. [Agronomic guidance and rules](#4-agronomic-guidance-and-rules)
5. [Software](#5-software)
6. [Images and branding](#6-images-and-branding)
7. [Required acknowledgements](#7-required-acknowledgements)

---

## 1. NASA data

### Used in the calculations

| Dataset | Provider | What GrowÉire uses it for | Access | Citation / DOI |
|---|---|---|---|---|
| **NASA POWER**, daily, Agroclimatology (AG) community: `T2M`, `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `PRECTOTCORR`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN`, `GWETROOT`, `GWETTOP` | NASA Langley Research Center (MERRA-2 / CERES) | Daily weather for ET0, the soil moisture deficit model and the counted monthly risks; climate summary and trends | REST API `power.larc.nasa.gov/api/temporal/daily/point` (live in the API and offline for the pilot) | <https://power.larc.nasa.gov/> |
| **GPM IMERG Final Precipitation L3 1 month 0.1° V07** (`GPM_3IMERGM`) | NASA GES DISC | Rescales POWER rain per pilot cell and month (about 10 km instead of 50 km) | NASA Earthdata | Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. (2023). GES DISC. <https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07> |
| **MOD13Q1 v6.1**, MODIS/Terra Vegetation Indices 16-Day L3 Global 250 m | NASA LP DAAC | NDVI history (summer greenness under *More detail*); NDVI labels for the earlier stress model | AppEEARS | Didan, K. (2021). <https://doi.org/10.5067/MODIS/MOD13Q1.061> |
| **MYD13Q1 v6.1**, MODIS/Aqua Vegetation Indices 16-Day L3 Global 250 m | NASA LP DAAC | Terra + Aqua composite, so fewer cloud gaps over Ireland | AppEEARS | Didan, K. (2021). <https://doi.org/10.5067/MODIS/MYD13Q1.061> |
| **MCD12Q1 v6.1**, MODIS/Terra+Aqua Land Cover Type Yearly L3 Global 500 m (IGBP) | NASA LP DAAC | Agricultural mask for the pilot grid (grassland, cropland, mosaic ≥ 30%) | NASA Earthdata | Friedl, M., Sulla-Menashe, D. (2022). <https://doi.org/10.5067/MODIS/MCD12Q1.061> |
| **SRTMGL1 v003**, NASA Shuttle Radar Topography Mission Global 1 arc second | NASA LP DAAC | Elevation and slope per cell (erosion index, ET0 elevation) | NASA Earthdata | NASA JPL (2013). <https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL1.003> |
| **SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture, v8** (`SPL4SMGP`) | NASA NSIDC DAAC | Root-zone soil moisture series under *More detail* | AppEEARS (points) | Reichle, R., De Lannoy, G., Koster, R.D., Crow, W.T., Kimball, J.S., Liu, Q., Bechtold, M. (2025). <https://doi.org/10.5067/T5RUATAQREF8> |
| **GIBS** WMTS imagery: `MODIS_Terra_CorrectedReflectance_TrueColor`, `MODIS_Terra_L3_NDVI_16Day`, `SMAP_L4_Analyzed_Root_Zone_Soil_Moisture` | NASA ESDIS | Map layers under *More maps* | Browser tiles from `gibs.earthdata.nasa.gov` | <https://nasa-gibs.github.io/gibs-api-docs/> |

All NASA data above is open, with no restrictions on use.

### Named on the website, not yet used in the calculations

The landing page names these missions as context for future versions. GrowÉire does not read their data yet.

| Mission | Link |
|---|---|
| GRACE-FO (groundwater and stored water) | <https://gracefo.jpl.nasa.gov/> |
| Landsat (30 m field imagery) | <https://landsat.gsfc.nasa.gov/> |
| ECOSTRESS (plant water use) | <https://ecostress.jpl.nasa.gov/> |

### NASA tools

- **AppEEARS** (Application for Extracting and Exploring Analysis Ready Samples), NASA LP DAAC: <https://appeears.earthdatacloud.nasa.gov/>
- **earthaccess** (Python): <https://earthaccess.readthedocs.io/>
- **Earthdata Login**: <https://urs.earthdata.nasa.gov/>

## 2. Other data

| Dataset | Provider | What GrowÉire uses it for | Citation / link | Licence |
|---|---|---|---|---|
| **SoilGrids 2.0** (clay, sand, silt, soil organic carbon, pH, bulk density; 0–30 cm; 250 m) | ISRIC – World Soil Information | Soil description for every field; live outside the pilot, pre-computed per cell inside it | Poggio, L. et al. (2021). *SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty.* SOIL 7, 217–240. <https://doi.org/10.5194/soil-7-217-2021> | CC BY 4.0 |
| **Irish Soil Information System**, national soil map with indicative drainage | Teagasc / EPA | Drainage class per pilot cell, which sets the soil moisture deficit model parameters | Creamer, R. et al. (2014). *Irish Soil Information System Synthesis Report* (2007-S-CD-1-S1). EPA. Data: <https://gis.epa.ie/GetData/Download>, <https://gis.teagasc.ie/soils/> | EPA data policy |
| **Met Éireann** daily station data | Met Éireann | Ground truth for checking POWER weather and our ET0 | <https://www.met.ie/climate/available-data/historical-data> | CC BY 4.0 |
| **OpenStreetMap / Nominatim** | OpenStreetMap Foundation | Place-name search (server-side, ≤ 1 request/s, identifying User-Agent, no autocomplete) | <https://nominatim.org/>, usage policy <https://operations.osmfoundation.org/policies/nominatim/> | ODbL |
| **GeoNames** (IE and GB dumps) | GeoNames | Offline fallback for place search | <https://www.geonames.org/> | CC BY 4.0 |
| **OpenFreeMap** "liberty" vector style | OpenFreeMap (OpenStreetMap data) | Basemap in the field app | <https://openfreemap.org/> | OSM data ODbL |
| **Natural Earth** 1:10m Admin-0 map units | Natural Earth | Ireland outline and the analysis grid | <https://www.naturalearthdata.com/> | Public domain |

## 3. Methods and science

| Method | Where it is used | Reference |
|---|---|---|
| FAO-56 Penman–Monteith reference evapotranspiration (ET0) and single crop coefficients (Kc) | `ml/src/agrolens_ml/features/et0.py`; crop water demand in the rotation engine | Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56. <https://www.fao.org/4/x0490e/x0490e00.htm> |
| Hybrid soil moisture deficit (SMD) model for Irish soils (well, moderately and poorly drained) | `ml/src/agrolens_ml/risk_counts.py`: drought and waterlogging days | Schulte, R.P.O., Diamond, J., Finkele, K., Holden, N.M., Brereton, A.J. (2005). *Predicting the soil moisture conditions of Irish grasslands.* Irish Journal of Agricultural and Food Research 44, 95–110. Met Éireann implementation: <https://www.met.ie/climate/services/agri-meteorological-data> |
| Dry day threshold: SMD > 50 mm, the upper limit of optimum grass growth | `ml/src/agrolens_ml/config.py` | Teagasc (2021), as cited in Basu, Fenton, Daly & Tuohy (2024). Frontiers in Environmental Science 12, 1331659. <https://doi.org/10.3389/fenvs.2024.1331659>; consistent with FAO-56 chapter 8 |
| Wilson score interval for "N years out of M" | `backend/app/services/risk.py` | Wilson, E.B. (1927). *Probable inference, the law of succession, and statistical inference.* Journal of the American Statistical Association 22(158), 209–212. |
| Sen's slope (robust trend per decade) | `backend/app/services/conditions.py` | Sen, P.K. (1968). *Estimates of the regression coefficient based on Kendall's tau.* Journal of the American Statistical Association 63(324), 1379–1389. |
| Gradient-boosted trees (the earlier stress model, kept in `ml/artifacts/`) | `ml/src/agrolens_ml/model/` | Ke, G. et al. (2017). *LightGBM: A highly efficient gradient boosting decision tree.* NeurIPS 2017. Grinsztajn, L., Oyallon, E., Varoquaux, G. (2022). *Why do tree-based models still outperform deep learning on typical tabular data?* NeurIPS 2022. |

## 4. Agronomic guidance and rules

These are the sources behind the crop catalogue ([`backend/app/data/crops_ie.json`](backend/app/data/crops_ie.json)) and the rotation templates ([`rotations_ie.json`](backend/app/data/rotations_ie.json)). Every number in the catalogue names its source by the id below; the ids are defined in [`sources.json`](backend/app/data/sources.json).

| Id | Source | Link |
|---|---|---|
| `fao56_table11` | FAO-56, Table 11: lengths of crop development stages | <https://www.fao.org/4/x0490e/x0490e0b.htm> |
| `fao56_table12` | FAO-56, Table 12: single crop coefficients (Kc) | <https://www.fao.org/4/x0490e/x0490e0b.htm> |
| `teagasc_crops` | Teagasc crops advice: sowing and harvest windows, husbandry of Irish tillage crops | <https://www.teagasc.ie/crops/crops/> |
| `teagasc_rotation` | Teagasc: break crops and crop rotation in Irish tillage (take-all breaks; rotation trials at Oak Park and Knockbeg) | <https://www.teagasc.ie/crops/crops/break-crops/> |
| `teagasc_cover_crops` | Teagasc: cover (catch) crop guidance | <https://www.teagasc.ie/crops/crops/cover-crops/> |
| `teagasc_grassland` | Teagasc: grass-clover and multispecies swards | <https://www.teagasc.ie/crops/grassland/> |
| `dafm_conditionality` | Department of Agriculture, Food and the Marine: CAP conditionality, GAEC 7 crop rotation and diversification | <https://www.gov.ie/en/department-of-agriculture-food-and-the-marine/> |

Further reading used in planning:

- Teagasc (2016). *Crop Production Systems* (rotation trials, Knockbeg). <https://teagasc.ie/wp-content/uploads/media/website/publications/2016/5616-Crop-Production-systems.pdf>
- Central Statistics Office Ireland. *Farm Structure Survey 2023* and *Area, Yield and Production of Crops*. <https://www.cso.ie>

## 5. Software

Main open-source packages, each under its own licence.

| Area | Packages (licence) |
|---|---|
| API | FastAPI (MIT), Pydantic (MIT), Uvicorn (BSD-3-Clause), SQLAlchemy (MIT), GeoAlchemy2 (MIT), Alembic (MIT), psycopg2 (LGPL-3.0), httpx (BSD-3-Clause), tenacity (Apache-2.0), Shapely (BSD-3-Clause), pyproj (MIT), redis-py (MIT), loguru (MIT), prometheus-fastapi-instrumentator (ISC) |
| Data and ML | pandas (BSD-3-Clause), NumPy (BSD-3-Clause), pyarrow (Apache-2.0), scikit-learn (BSD-3-Clause), LightGBM (MIT), joblib (BSD-3-Clause), xarray (Apache-2.0), rasterio (BSD-3-Clause), GeoPandas (BSD-3-Clause), earthaccess (MIT) |
| Database and cache | PostgreSQL (PostgreSQL Licence), PostGIS (GPL-2.0), Redis 7 |
| Frontend | Vue (MIT), Vite (MIT), Tailwind CSS (MIT), shadcn-vue (MIT), Reka UI (MIT), Pinia (MIT), Vue Router (MIT), MapLibre GL JS (BSD-3-Clause), openapi-fetch (MIT), Mock Service Worker (MIT), Lucide icons (ISC), flag-icons (MIT) |
| Fonts | Manrope (SIL OFL 1.1), Atkinson Hyperlegible (SIL OFL 1.1), via Fontsource |
| Tooling | uv (MIT / Apache-2.0), pytest (MIT), Vitest (MIT), Black (MIT) |

## 6. Images and branding

| Item | Source | Licence / use |
|---|---|---|
| NASA Space Apps Challenge 2026 logo (footer) | Official logo, <https://www.spaceappschallenge.org/> | Used as allowed by the Hack Athlone organisers; not covered by this project's MIT Licence |
| Landing-page photographs (`frontend/public/img/`) | From the GrowÉire design prototype | Source and licence to be confirmed |

No other organisation's logo is used. NASA missions, Met Éireann and Teagasc are named in text only. GrowÉire is not endorsed by NASA or by any data provider.

## 7. Required acknowledgements

Copy these wherever the data is shown or presented (app, slides, submission).

- **NASA POWER:** "These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program."
- **NASA GIBS:** "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)."
- **MODIS, SRTM (NASA LP DAAC), SMAP (NASA NSIDC DAAC), GPM IMERG (NASA GES DISC):** cite each dataset with its DOI, as listed in section 1.
- **Met Éireann:** "Copyright Met Éireann. Source www.met.ie. This data is published under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence. Data modified (aggregated) from the original."
- **SoilGrids:** "SoilGrids 2.0, ISRIC – World Soil Information (Poggio et al., 2021), CC BY 4.0."
- **OpenStreetMap:** "© OpenStreetMap contributors" (place search and basemap).
- **GeoNames:** "GeoNames (www.geonames.org), CC BY 4.0."
