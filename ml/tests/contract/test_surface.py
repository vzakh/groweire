"""The public surface equals brief §13.2 exactly (names + signatures)."""

from __future__ import annotations

import inspect
import typing

import pytest

import agrolens_ml

pytestmark = pytest.mark.contract

EXPECTED_ALL = {
    "CONTRACT_VERSION",
    "FEATURE_NAMES",
    "STRESS_TYPES",
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
}

EXPECTED_SIGNATURES = {
    "power_daily_to_monthly": ["daily", "elev_m", "lat"],
    "build_feature_row": ["cell_static", "monthly_history", "target_month"],
    "attribute_stress": ["row"],
    "load_bundle": ["model_dir"],
    "make_stub_bundle": ["out_dir"],
    "make_synthetic_tables": ["grid_csv", "out_dir", "seed"],
}


def test_contract_version():
    assert agrolens_ml.CONTRACT_VERSION == "1.0"


def test_all_is_exactly_the_surface():
    assert set(agrolens_ml.__all__) == EXPECTED_ALL
    for name in EXPECTED_ALL:
        assert hasattr(agrolens_ml, name), name


@pytest.mark.parametrize("name, params", EXPECTED_SIGNATURES.items())
def test_signatures(name, params):
    sig = inspect.signature(getattr(agrolens_ml, name))
    assert list(sig.parameters) == params


def test_synthetic_seed_default():
    sig = inspect.signature(agrolens_ml.make_synthetic_tables)
    assert sig.parameters["seed"].default == 7


def test_constants():
    assert agrolens_ml.STRESS_TYPES == ("drought", "waterlogging", "heat", "frost", "other")
    assert agrolens_ml.POWER_DAILY_PARAMETERS == (
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
    assert agrolens_ml.CELL_STATIC_KEYS == (
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
    assert agrolens_ml.MONTHLY_INPUT_COLUMNS == (
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
    names = agrolens_ml.FEATURE_NAMES
    assert isinstance(names, tuple) and len(names) == len(set(names)) > 0
    assert all(isinstance(n, str) for n in names)


def test_prediction_typeddict():
    hints = typing.get_type_hints(agrolens_ml.Prediction)
    assert set(hints) == {
        "probability",
        "interval",
        "drivers",
        "stress_types",
        "needs_local_review",
    }


def test_stress_model_interface():
    assert inspect.isabstract(agrolens_ml.StressModel)
    assert list(inspect.signature(agrolens_ml.StressModel.predict).parameters) == ["self", "rows"]


def test_schemas_module():
    for name in ("GRID_CELLS_SCHEMA", "CELL_MONTH_SCHEMA", "RISK_GRID_SCHEMA", "MANIFEST_KEYS"):
        assert hasattr(agrolens_ml.schemas, name), name
