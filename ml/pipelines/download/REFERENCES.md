# References & data sources

> Где взяли каждый датасет, лицензия, DOI и как цитировать. Этот список можно копировать в раздел
> «Resources / Data used» на странице проекта Space Apps.
> ✔ означает, что DOI или текст я сверил по официальной странице датасета. ○ означает, что DOI
> построен по стандартной схеме DAAC: перед сабмитом открой ссылку один раз и проверь.

## 1. NASA data

| Dataset | Used for | Provider | Access (script) | DOI / landing page | License |
|---|---|---|---|---|---|
| **NASA POWER**, Daily, Agroclimatology (AG) community: T2M, T2M_MAX, T2M_MIN, T2MDEW, PRECTOTCORR, RH2M, WS2M, ALLSKY_SFC_SW_DWN, GWETROOT, GWETTOP | Climate features, ET0, frost/heat/rain indicators | NASA Langley Research Center (LaRC) | REST API `power.larc.nasa.gov/api/temporal/daily/point` (`01_power.py`) | https://power.larc.nasa.gov/ ✔ | NASA open data, no restrictions |
| **MOD13Q1 v6.1**: MODIS/Terra Vegetation Indices 16-Day L3 Global 250 m (NDVI, pixel reliability) | ML label (NDVI anomaly), NDVI history | NASA LP DAAC (USGS EROS) | AppEEARS area (`10_appeears_submit.py`) | https://doi.org/10.5067/MODIS/MOD13Q1.061 ✔ | No restrictions on use, sale, redistribution ✔ |
| **MYD13Q1 v6.1**: MODIS/Aqua Vegetation Indices 16-Day L3 Global 250 m | Terra+Aqua composite (fewer cloud gaps) | NASA LP DAAC | AppEEARS area | https://doi.org/10.5067/MODIS/MYD13Q1.061 ○ | No restrictions |
| **MCD12Q1 v6.1**: MODIS Land Cover Type Yearly L3 Global 500 m (LC_Type1, IGBP) | Agricultural mask for the grid | NASA LP DAAC | AppEEARS area | https://doi.org/10.5067/MODIS/MCD12Q1.061 ○ | No restrictions |
| **SRTMGL1 v003**: NASA SRTM Global 1 arc second (NetCDF) | Elevation, slope (erosion index) | NASA LP DAAC | AppEEARS area | https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL1_NC.003 ○ | No restrictions |
| **SPL4SMGP v8**: SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture | Root-zone soil moisture and percentile | NASA NSIDC DAAC | AppEEARS point (183 pts, 0.25°) | https://doi.org/10.5067/T5RUATAQREF8 ✔ | NASA open data |
| **GPM IMERG Final Precipitation L3 Monthly V07** (GPM_3IMERGM), optional | Satellite precipitation | NASA GES DISC | `earthaccess` (`20_imerg.py`) | https://doi.org/10.5067/GPM/IMERG/3B-MONTH/07 ○ | NASA open data |
| **GIBS** WMTS imagery (true colour, NDVI, soil moisture) | Map layers in the web app | NASA ESDIS | Browser tiles `gibs.earthdata.nasa.gov` | https://nasa-gibs.github.io/gibs-api-docs/ | NASA open data |

**NASA tools:**
- **AppEEARS** (Application for Extracting and Exploring Analysis Ready Samples), NASA EOSDIS LP DAAC: https://appeears.earthdatacloud.nasa.gov/
- **earthaccess** (Python, NSIDC/community): https://earthaccess.readthedocs.io/
- **Earthdata Login**: https://urs.earthdata.nasa.gov/

## 2. Non-NASA data

| Dataset | Used for | Provider | Access | Reference | License |
|---|---|---|---|---|---|
| **SoilGrids v2.0** (clay, sand, silt, SOC, pH, bulk density; 0–30 cm; 250 m) | Soil properties | ISRIC – World Soil Information | Cloud VRT/COG `files.isric.org/soilgrids/latest/data` (`02_soilgrids.py`) | Poggio, L. et al. (2021) *SoilGrids 2.0*. SOIL 7, 217–240. https://doi.org/10.5194/soil-7-217-2021 | CC BY 4.0 |
| **Met Éireann** daily station data (rain, Tmax/Tmin; PET and soil moisture deficits at synoptic stations) | Ground truth: validating POWER and ET0 | Met Éireann (Irish Meteorological Service) | `cli.fusio.net/cli/climate_data/webdata/dly<ID>.csv` (`03_met_eireann.py`) | https://www.met.ie/climate/available-data/historical-data ✔ | CC BY 4.0 ✔ |
| **GeoNames** gazetteer (IE + Northern Ireland part of GB; populated places, localities) | Fallback place-name search (brief D20) | GeoNames | `download.geonames.org/export/dump/{IE,GB}.zip` (`04_geonames.py`) | https://www.geonames.org/ | CC BY 4.0 |
| **OpenStreetMap / Nominatim** (live, not downloaded) | Primary place-name search via the backend proxy | OpenStreetMap Foundation | `nominatim.openstreetmap.org/search` (≤ 1 req/s per app, custom User-Agent, no autocomplete or bulk) | https://operations.osmfoundation.org/policies/nominatim/ | ODbL; attribution "© OpenStreetMap contributors" |
| **Natural Earth** 1:10m Admin-0 map units | Ireland outline, analysis grid | Natural Earth | GitHub `nvkelso/natural-earth-vector` | https://www.naturalearthdata.com/ | Public domain |
| **EUCROPMAP** 2018 / 2022 (10 m crop types), manual | Arable vs grassland mask | European Commission JRC | GEE `JRC/D5/EUCROPMAP/V1` | d'Andrimont, R. et al. (2021) RSE 266, 112708. https://doi.org/10.1016/j.rse.2021.112708 ✔; Ghassemi, B. et al. (2024) Sci. Data 11, 1048. https://doi.org/10.1038/s41597-024-03884-y ✔ | CC BY 4.0 ✔ |
| **CSO Area, Yield and Production of Crops**, manual | Year-level sanity check (e.g. 2018 drought) | Central Statistics Office Ireland | https://www.cso.ie (releases "aypc") | e.g. https://cso.ie/en/releasesandpublications/er/aypc/areayieldandproductionofcrops2019 ✔ | CSO open data (check terms on site) |
| **Irish Soil Information System**, national soil map and indicative drainage, manual | Waterlogging modifier | Teagasc / EPA | https://gis.epa.ie/GetData/Download ; https://gis.teagasc.ie/soils/ | Creamer, R. et al. (2014) *Irish Soil Information System Synthesis Report* (2007-S-CD-1-S1), EPA | See EPA data policy |

## 3. Methods & agronomy

- Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56. https://www.fao.org/3/X0490E/x0490e00.htm (ET0 Penman–Monteith, crop coefficients Kc)
- Teagasc (2016). *Crop Production Systems* (rotation trials, Knockbeg). https://teagasc.ie/wp-content/uploads/media/website/publications/2016/5616-Crop-Production-systems.pdf
- Teagasc (2024). *Planning for 2024 on tillage farms* (crop rotation conditionality: ≥2 crops over 4 years). https://teagasc.ie/news--events/daily/crops/planning-for-2024-on-tillage-farms.php
- Grinsztajn, L., Oyallon, E., Varoquaux, G. (2022). *Why do tree-based models still outperform deep learning on typical tabular data?* NeurIPS 2022. https://neurips.cc/virtual/2022/poster/55627
- Ke, G. et al. (2017). *LightGBM: A Highly Efficient Gradient Boosting Decision Tree*. NeurIPS 2017.

## 4. Required acknowledgement text (paste into the app's footer, slides and README)

- **NASA POWER:** "These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program."
- **MODIS / SRTM (LP DAAC):** follow the citation format on each DOI landing page (LP DAAC "Citing Our Data").
- **SMAP:** Reichle, R., De Lannoy, G., Koster, R. D., Crow, W. T., Kimball, J. S., Liu, Q., & Bechtold, M. (2025). *SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data* (SPL4SMGP, Version 8). NASA NSIDC DAAC. https://doi.org/10.5067/T5RUATAQREF8 ✔
- **GIBS:** "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)."
- **Met Éireann:** "Copyright Met Éireann. Source www.met.ie. This data is published under a Creative Commons Attribution 4.0 International (CC BY 4.0) licence. Data modified (aggregated) from the original." ✔
- **SoilGrids:** "SoilGrids 2.0, ISRIC – World Soil Information (Poggio et al., 2021), CC BY 4.0."
- **OpenStreetMap:** "© OpenStreetMap contributors" (place search and basemap).
- **GeoNames:** "GeoNames (www.geonames.org), CC BY 4.0."
- **EUCROPMAP (if used):** "EUCROPMAP © European Union, Joint Research Centre, CC BY 4.0."

## 5. Disclaimer for the app

This tool supports, not replaces, your judgment and local agronomic advice. Satellite and
reanalysis data are coarse (250 m – 50 km) and indirect. Field-level outputs are risk indicators,
not measurements.
