# AgroLens: загрузка данных (пилот: остров Ирландия)

Скрипты скачивают все датасеты из `docs/TECHNICAL_BRIEF.md` §6. Запускаются на твоём компьютере
(нужен Python 3.10+). Сетка анализа и контур Ирландии уже лежат в `config/`.

## Порядок (важно: AppEEARS первым)

```bash
python3 -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env          # впиши логин/пароль Earthdata (https://urs.earthdata.nasa.gov)

python scripts/10_appeears_submit.py --dry-run   # посмотреть, что уйдёт в AppEEARS
make submit                   # 1. отправить задания: MODIS NDVI, land cover, SRTM, SMAP
make all-fast                 # 2. пока ждём: POWER + SoilGrids + Met Éireann (без логина)
make wait                     # 3. дождаться AppEEARS и скачать (часы; можно оставить на ночь)
make check                    # что скачано и сколько весит
```

## Что скачивается

| Скрипт | Датасет | Логин | Время | Размер (оценка) | Куда |
|---|---|---|---|---|---|
| `01_power.py` | NASA POWER daily (AG): T2M, Tmax/Tmin, осадки, RH, ветер, радиация, GWETROOT/GWETTOP, 2001–2025 | нет | 5–15 мин | ~50 MB | `data/processed/power_daily.parquet` |
| `02_soilgrids.py` | ISRIC SoilGrids v2: clay, sand, silt, SOC, pH, bulk density, 0–30 см | нет | 10–30 мин | <5 MB | `data/processed/soil_cell.parquet` |
| `03_met_eireann.py` | Met Éireann: суточные данные 15 станций (наземная правда) | нет | 1 мин | ~30 MB | `data/raw/met_eireann/` |
| `04_geonames.py` | GeoNames: справочник мест Ирландии (резервный поиск по названию) | нет | 1 мин | ~5 MB | `data/raw/geonames/` |
| `10/11_appeears_*` | MOD13Q1 + MYD13Q1 NDVI (фев–окт), MCD12Q1, SRTM, SMAP L4 v8 | Earthdata | часы (очередь NASA) | NDVI: несколько GB; остальное <1 GB | `data/raw/appeears/<task>/` |
| `20_imerg.py` | GPM IMERG monthly (опционально) | Earthdata | 20–60 мин | <20 MB | `data/processed/imerg_cell_month.parquet` |

`config/`:
- `ireland.geojson` — контур острова (Natural Earth, public domain)
- `grid_005deg.csv` — 4 533 ячейки 0,05° (основная сетка)
- `grid_010deg.csv` — 1 147 ячеек 0,1°
- `grid_025deg.csv` — 183 ячейки 0,25° (точки для SMAP, у которого разрешение 9 км)

## Если что-то пошло не так
- **AppEEARS отклонил задание.** Скрипт пишет текст ошибки. Частые причины: неверное имя слоя (скрипт сверяет имена с каталогом и выводит доступные) или формат повторяющихся дат (`recurring`). В последнем случае поставь даты `MM-DD-YYYY` без `recurring` и сократи диапазон лет.
- **NDVI слишком тяжёлый.** Задай `AGROLENS_YEAR_START=2010` в `.env`. Тогда будет 3 чанка вместо 5 на каждый сенсор.
- **SoilGrids падает.** Перезапусти, сервис у ISRIC в бете. Для теста: `python scripts/02_soilgrids.py --limit 20`.
- **Met Éireann: файл станции не найден.** Сверь ID с `data/raw/met_eireann/StationDetails.csv`.

## Не скачивается скриптами (вручную, если нужно)
- **JRC EUCROPMAP 2018/2022** (маска пашни, 10 м): Google Earth Engine `JRC/D5/EUCROPMAP/V1` или каталог данных JRC.
- **CSO урожайность по годам**: https://www.cso.ie, раздел «Area, Yield and Production of Crops» (таблицы PxStat).
- **Irish Soil Information System** (класс дренажа): https://gis.epa.ie/GetData/Download (раздел Soils).

## Источники
Полный список с DOI, лицензиями и готовыми текстами атрибуции: **`REFERENCES.md`**.

## Атрибуция (обязательна в сабмите)
NASA POWER (NASA LaRC); MODIS MOD13Q1/MYD13Q1, MCD12Q1, SRTMGL1 (NASA LP DAAC); SMAP SPL4SMGP v8 (NASA NSIDC DAAC); GPM IMERG (NASA GES DISC); SoilGrids (ISRIC, CC BY 4.0); Met Éireann (CC BY 4.0: «Copyright Met Éireann, Source www.met.ie»); GeoNames (CC BY 4.0); OpenStreetMap contributors; Natural Earth.
