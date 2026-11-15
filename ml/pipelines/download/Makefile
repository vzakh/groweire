PY ?= python3

.PHONY: install submit status wait power soil met geonames imerg check all-fast

install:            ## create venv deps
	$(PY) -m pip install -r requirements.txt

submit:             ## 1) submit AppEEARS jobs (do this FIRST, they take hours)
	$(PY) 10_appeears_submit.py

status:             ## check AppEEARS jobs once, download finished ones
	$(PY) 11_appeears_download.py

wait:               ## poll AppEEARS every 10 min until everything is downloaded
	$(PY) 11_appeears_download.py --wait

power:              ## NASA POWER daily, all nodes over Ireland (~5-15 min)
	$(PY) 01_power.py

soil:               ## SoilGrids at 4.5k cell centroids (~10-30 min)
	$(PY) 02_soilgrids.py

met:                ## Met Eireann station CSVs (~1 min)
	$(PY) 03_met_eireann.py

geonames:           ## GeoNames gazetteer, fallback place search (~1 min)
	$(PY) 04_geonames.py

imerg:              ## optional GPM IMERG monthly
	$(PY) 20_imerg.py

check:
	$(PY) 99_check.py

all-fast: power soil met geonames check   ## everything that needs no Earthdata login
