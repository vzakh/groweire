PY ?= python3

.PHONY: install submit status wait power soil met geonames imerg check all-fast

install:            ## create venv deps
	$(PY) -m pip install -r requirements.txt

submit:             ## 1) submit AppEEARS jobs (do this FIRST, they take hours)
	$(PY) scripts/10_appeears_submit.py

status:             ## check AppEEARS jobs once, download finished ones
	$(PY) scripts/11_appeears_download.py

wait:               ## poll AppEEARS every 10 min until everything is downloaded
	$(PY) scripts/11_appeears_download.py --wait

power:              ## NASA POWER daily, all nodes over Ireland (~5-15 min)
	$(PY) scripts/01_power.py

soil:               ## SoilGrids at 4.5k cell centroids (~10-30 min)
	$(PY) scripts/02_soilgrids.py

met:                ## Met Eireann station CSVs (~1 min)
	$(PY) scripts/03_met_eireann.py

geonames:           ## GeoNames gazetteer, fallback place search (~1 min)
	$(PY) scripts/04_geonames.py

imerg:              ## optional GPM IMERG monthly
	$(PY) scripts/20_imerg.py

check:
	$(PY) scripts/99_check.py

all-fast: power soil met geonames check   ## everything that needs no Earthdata login
