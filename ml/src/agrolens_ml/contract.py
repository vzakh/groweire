"""ML -> Backend contract constants and types (brief §13.2, CONTRACT_VERSION 2.0).

2.0 (PLAN_40): the risk shown to the farmer is COUNTED from weather history (count_risks,
risk_counts table). The model types below stay for the optional ML add-on; the backend's main
path no longer loads a bundle.

Changing anything in this module is a contract change (brief rule 4): bump CONTRACT_VERSION,
update brief §13.2, the stub and ml/tests/contract/ in one commit.
FEATURE_NAMES is deliberately NOT here: it is owned by ML and may change behind the contract (D22).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypedDict

CONTRACT_VERSION: str = "2.0"

# Counted risk (PLAN_40). RISK_RULES_VERSION names the rule set in config.py; bump it when a
# threshold changes, so a response can always be traced to the rules that produced it.
RISK_TYPES: tuple[str, ...] = ("drought", "waterlogging", "heat", "frost")
RISK_RULES_VERSION: str = "counted-1"

STRESS_TYPES: tuple[str, ...] = ("drought", "waterlogging", "heat", "frost", "other")

# Exact NASA POWER daily parameter names (AG community) the backend must request for a live point.
# The pilot POWER download used this same set, so the pilot tables and a live point use one input.
POWER_DAILY_PARAMETERS: tuple[str, ...] = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "WS2M",
    "ALLSKY_SFC_SW_DWN",
    "GWETROOT",
    "GWETTOP",
    "T2MDEW",
)

# Static description of a cell / field the backend can build for ANY point (live path).
# Units: elev_m m, slope_deg degrees, clay/sand %, soc g/kg, phh2o pH, bdod g/cm3,
# drainage_class ordinal 1 (excessive) .. 5 (very poor) or None, ag/crop_fraction 0..1.
CELL_STATIC_KEYS: tuple[str, ...] = (
    "lat",
    "lon",
    "elev_m",
    "slope_deg",
    "clay",
    "sand",
    "soc",
    "phh2o",
    "bdod",
    "drainage_class",
    "ag_fraction",
    "crop_fraction",
)

# Columns of `monthly_history` (output of power_daily_to_monthly, input of build_feature_row).
# `month` is a pandas Period[M]; the rest are floats (NaN when unavailable).
MONTHLY_INPUT_COLUMNS: tuple[str, ...] = (
    "month",
    "precip",
    "heavy_rain_days",
    "dry_spell_max",
    "t2m",
    "tmax",
    "tmin",
    "hot_days",
    "frost_days",
    "gdd5",
    "et0",
    "p_minus_et0",
    "gwetroot",
    "gwettop",
    "sm_rootzone",
    "ndvi_z",
)


class Prediction(TypedDict):
    """One prediction for one feature row."""

    probability: float  # calibrated P(stress) in [0, 1]
    interval: tuple[float, float]  # fold-ensemble (min, max)
    drivers: list[dict]  # top-3 [{feature, value, contribution, text}], text in farmer words
    stress_types: list[str]  # subset of STRESS_TYPES
    needs_local_review: bool


class StressModel(ABC):
    """Interface every bundle kind (stub | lgbm | b1) implements."""

    version: str

    @abstractmethod
    def predict(self, rows: list[dict]) -> list[Prediction]:
        """Predict for feature rows (keys ⊆ FEATURE_NAMES; missing -> NaN; unknown -> ValueError)."""
