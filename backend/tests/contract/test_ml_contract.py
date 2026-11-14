"""Consumer side of the ML -> Backend contract (brief §13.2).

The shared suite lives in ml/tests/contract and runs with `make contract`. These checks pin
what the BACKEND relies on, so a contract change fails here too, not only in ML.
"""

from __future__ import annotations

import ast
import inspect

import agrolens_ml
from core.config import APP_DIR

# Since contract 2.0 the backend's main path counts risks; it loads no model bundle.
USED_BY_BACKEND = {
    "CONTRACT_VERSION",
    "FEATURE_NAMES",
    "RISK_TYPES",
    "RISK_RULES_VERSION",
    "POWER_DAILY_PARAMETERS",
    "CELL_STATIC_KEYS",
    "MONTHLY_INPUT_COLUMNS",
    "power_daily_to_monthly",
    "count_risks",
    "make_synthetic_tables",
    "schemas",
}
NOT_ON_THE_MAIN_PATH = {"load_bundle", "StressModel", "build_feature_row", "attribute_stress"}


def test_contract_version_the_backend_was_built_for():
    assert agrolens_ml.CONTRACT_VERSION == "2.0"


def test_everything_the_backend_uses_is_public():
    assert USED_BY_BACKEND <= set(agrolens_ml.__all__)


def test_backend_imports_only_the_public_surface_and_no_model():
    """No `agrolens_ml.<submodule>` imports, no names outside __all__, no model on the main path."""
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
                assert not used & NOT_ON_THE_MAIN_PATH, f"{path}: {used & NOT_ON_THE_MAIN_PATH}"


def test_signatures_the_backend_calls():
    assert list(inspect.signature(agrolens_ml.power_daily_to_monthly).parameters) == [
        "daily",
        "elev_m",
        "lat",
    ]
    assert list(inspect.signature(agrolens_ml.count_risks).parameters) == [
        "daily",
        "elev_m",
        "lat",
        "drainage_class",
        "monthly_rain_mm",
    ]
    assert agrolens_ml.RISK_TYPES == ("drought", "waterlogging", "heat", "frost")
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


def test_risk_counts_columns_the_backend_reads():
    assert agrolens_ml.schemas.RISK_COUNTS_SCHEMA.names == [
        "cell_id",
        "calendar_month",
        "stress_type",
        "years_hit",
        "years_total",
        "frequency",
        "recent_frequency",
        "example_years",
    ]
