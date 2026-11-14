ML := uv run --package agrolens-ml
BUNDLE ?= ml/artifacts/stub_v0
DATA ?= data/synthetic

.PHONY: sync synthetic stub contract test-ml check

sync:            ## install the workspace (all members) into .venv
	uv sync --all-packages

synthetic:       ## seeded, schema-exact synthetic tables -> data/synthetic/ (task 05)
	$(ML) python -m agrolens_ml.synthetic

stub:            ## (re)write the committed stub bundle ml/artifacts/stub_v0/ (task 05)
	$(ML) python -m agrolens_ml.model.stub

contract:        ## ML -> Backend contract tests: make contract BUNDLE=... DATA=...
	$(ML) pytest ml/tests/contract -m contract --bundle $(BUNDLE) --data $(DATA)

test-ml:         ## ML unit tests (offline)
	$(ML) pytest ml/tests -q -m "not contract"

check: test-ml synthetic contract test-backend compose-config

# --- backend (PLAN_20) ---
BE := PYTHONPATH=backend/app uv run --package agrolens-backend
COMPOSE := docker compose -f compose.yaml

.PHONY: db-up db-down migrate load-pilot api test-backend openapi fixtures

db-up:           ## start local PostGIS (:55432) + Redis (:56379) and wait until healthy
	$(COMPOSE) up -d --wait db redis

db-down:         ## stop them (data volume is kept)
	$(COMPOSE) down

migrate:         ## alembic upgrade head
	cd backend && PYTHONPATH=app uv run --package agrolens-backend alembic upgrade head

load-pilot:      ## parquet -> PostGIS: make load-pilot DATA=data/synthetic
	$(BE) python -m jobs.load_pilot $(DATA)

api:             ## run the API with reload on :8080
	$(BE) uvicorn main:app --reload --port 8080

test-backend:    ## backend tests (DB tests are skipped when PostGIS is not running)
	$(BE) pytest backend/tests -q

openapi:         ## write backend/openapi.json (Backend -> Frontend contract)
	$(BE) python -m jobs.export_openapi

GEONAMES_DIR := data/raw/geonames
GEONAMES_URL := https://download.geonames.org/export/dump

.PHONY: geonames load-gazetteer build up compose-config load-pilot-docker

geonames:        ## download the GeoNames IE + GB dumps (CC BY 4.0) for the place-search fallback
	mkdir -p $(GEONAMES_DIR)
	for f in IE.zip GB.zip admin2Codes.txt; do curl -sSfL -o $(GEONAMES_DIR)/$$f $(GEONAMES_URL)/$$f; done
	unzip -o -q $(GEONAMES_DIR)/IE.zip IE.txt -d $(GEONAMES_DIR)
	unzip -o -q $(GEONAMES_DIR)/GB.zip GB.txt -d $(GEONAMES_DIR)

load-gazetteer:  ## GeoNames dumps -> gazetteer table only (pilot tables are left alone)
	$(BE) python -m jobs.load_pilot --gazetteer-only

build:           ## build the API image with the promoted model bundle baked in
	MODEL_VERSION=$$(cat ml/artifacts/CURRENT) $(COMPOSE) build api

up:              ## db + redis + migrate + api in containers (API_PORT=8081 to move the host port)
	MODEL_VERSION=$$(cat ml/artifacts/CURRENT) $(COMPOSE) up -d --build --wait api

load-pilot-docker: ## same as load-pilot, inside the API image: make load-pilot-docker PILOT_DATA=synthetic
	$(COMPOSE) --profile ops run --rm load-pilot

compose-config:  ## validate compose.yaml
	$(COMPOSE) config -q

fixtures:        ## write backend/tests/fixtures/api/*.json (Backend -> Frontend contract)
	$(BE) python -m jobs.export_fixtures

# Rebuild real ML outputs end to end once NDVI chunks have landed (PLAN_10 tasks 11-15)
ml-real:
	uv run python -m agrolens_ml.cli labels
	uv run python -m agrolens_ml.cli features
	uv run python -m agrolens_ml.cli train --out ml/artifacts/stress_lgbm_v1
	uv run python -m agrolens_ml.cli risk-grid --out ml/artifacts/stress_lgbm_v1
	uv run pytest ml/tests/contract -m contract -q --bundle ml/artifacts/stress_lgbm_v1 --data data/processed
