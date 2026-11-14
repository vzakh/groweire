"""agrolens_ml: the ML -> Backend contract surface (brief §13.2, CONTRACT_VERSION 2.0).

The backend may rely on exactly the names in __all__ (plus agrolens_ml.schemas) and nothing else.
Everything behind them (feature engineering, FEATURE_NAMES, model internals) is ML-owned.
"""

from agrolens_ml import schemas
from agrolens_ml.contract import (
    CELL_STATIC_KEYS,
    CONTRACT_VERSION,
    MONTHLY_INPUT_COLUMNS,
    POWER_DAILY_PARAMETERS,
    RISK_RULES_VERSION,
    RISK_TYPES,
    STRESS_TYPES,
    Prediction,
    StressModel,
)
from agrolens_ml.features.build import FEATURE_NAMES, build_feature_row
from agrolens_ml.features.monthly import power_daily_to_monthly
from agrolens_ml.features.stress_rules import attribute_stress
from agrolens_ml.model.bundle import load_bundle
from agrolens_ml.model.stub import make_stub_bundle
from agrolens_ml.risk_counts import count_risks
from agrolens_ml.synthetic import make_synthetic_tables

__all__ = [
    "CONTRACT_VERSION",
    "FEATURE_NAMES",
    "STRESS_TYPES",
    "RISK_TYPES",
    "RISK_RULES_VERSION",
    "count_risks",
    "POWER_DAILY_PARAMETERS",
    "CELL_STATIC_KEYS",
    "MONTHLY_INPUT_COLUMNS",
    "power_daily_to_monthly",
    "build_feature_row",
    "attribute_stress",
    "Prediction",
    "StressModel",
    "load_bundle",
    "make_stub_bundle",
    "make_synthetic_tables",
    "schemas",
]
