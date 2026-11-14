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

check: test-ml synthetic contract

# Rebuild real ML outputs end to end once NDVI chunks have landed (PLAN_10 tasks 11-15)
ml-real:
	uv run python -m agrolens_ml.cli labels
	uv run python -m agrolens_ml.cli features
	uv run python -m agrolens_ml.cli train --out ml/artifacts/stress_lgbm_v1
	uv run python -m agrolens_ml.cli risk-grid --out ml/artifacts/stress_lgbm_v1
	uv run pytest ml/tests/contract -m contract -q --bundle ml/artifacts/stress_lgbm_v1 --data data/processed
