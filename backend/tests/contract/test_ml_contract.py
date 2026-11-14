"""Consumer side of the ML -> Backend contract (brief §13.2).

The shared suite lives in ml/tests/contract and runs with `make contract`. These checks pin
what the BACKEND relies on, so a contract change fails here too, not only in ML.
"""

from __future__ import annotations

import ast
import inspect
import json
import math

import agrolens_ml
from core.config import APP_DIR, get_settings

USED_BY_BACKEND = {
    "CONTRACT_VERSION",
    "FEATURE_NAMES",
    "STRESS_TYPES",
    "POWER_DAILY_PARAMETERS",
    "CELL_STATIC_KEYS",
    "MONTHLY_INPUT_COLUMNS",
    "power_daily_to_monthly",
    "build_feature_row",
    "StressModel",
    "load_bundle",
    "make_synthetic_tables",
    "schemas",
}


def test_contract_version_the_backend_was_built_for():
    assert agrolens_ml.CONTRACT_VERSION == "1.0"


def test_everything_the_backend_uses_is_public():
    assert USED_BY_BACKEND <= set(agrolens_ml.__all__)


def test_backend_imports_only_the_public_surface():
    """No `agrolens_ml.<submodule>` imports and no names outside __all__ anywhere in app/."""
    public = set(agrolens_ml.__all__)
    for path in APP_DIR.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("agrolens_ml."), f"{path}: import {alias.name}"
            elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("agrolens_ml"):
                assert node.module == "agrolens_ml", f"{path}: from {node.module} import ..."
                used = {alias.name for alias in node.names}
                assert used <= public, f"{path}: {used - public}"


def test_signatures_the_backend_calls():
    assert list(inspect.signature(agrolens_ml.power_daily_to_monthly).parameters) == [
        "daily",
        "elev_m",
        "lat",
    ]
    assert list(inspect.signature(agrolens_ml.build_feature_row).parameters) == [
        "cell_static",
        "monthly_history",
        "target_month",
    ]
    assert set(agrolens_ml.STRESS_TYPES) == {"drought", "waterlogging", "heat", "frost", "other"}
    assert {"lat", "lon", "elev_m", "slope_deg", "drainage_class"} <= set(
        agrolens_ml.CELL_STATIC_KEYS
    )
    assert {
        "month",
        "precip",
        "tmax",
        "tmin",
        "et0",
        "p_minus_et0",
        "frost_days",
        "hot_days",
        "heavy_rain_days",
    } <= set(agrolens_ml.MONTHLY_INPUT_COLUMNS)


def test_current_bundle_loads_and_reproduces_its_example():
    model_dir = get_settings().resolved_model_dir()
    model = agrolens_ml.load_bundle(model_dir)
    example = json.loads((model_dir / "example.json").read_text())
    row = {k: (math.nan if v is None else v) for k, v in example["features"].items()}
    prediction = model.predict([row])[0]
    assert abs(prediction["probability"] - example["expected"]["probability"]) < 1e-9
    assert set(prediction) == {
        "probability",
        "interval",
        "drivers",
        "stress_types",
        "needs_local_review",
    }
    assert {"feature", "value", "contribution", "text"} <= set(prediction["drivers"][0])
