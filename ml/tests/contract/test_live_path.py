"""Backend live path for any point: POWER daily JSON -> power_daily_to_monthly -> build_feature_row."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from agrolens_ml import (
    FEATURE_NAMES,
    MONTHLY_INPUT_COLUMNS,
    build_feature_row,
    power_daily_to_monthly,
)
from agrolens_ml.io.power import power_json_to_daily

pytestmark = pytest.mark.contract

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

POINTS = {
    # Irish pilot point (near Oak Park, Co. Carlow) with full static info
    "power_node_ie.json": {
        "lat": 52.7,
        "lon": -6.9,
        "elev_m": 60.0,
        "slope_deg": 2.0,
        "clay": 22.0,
        "sand": 40.0,
        "soc": 35.0,
        "phh2o": 6.4,
        "bdod": 1.2,
        "drainage_class": 2,
        "ag_fraction": 0.85,
        "crop_fraction": 0.4,
    },
    # Non-Irish point (Kenya highlands): soil only, no Irish drainage/land-cover info
    "power_node_ke.json": {
        "lat": -0.4,
        "lon": 36.9,
        "elev_m": 1900.0,
        "slope_deg": None,
        "clay": 40.0,
        "sand": 30.0,
        "soc": 25.0,
        "phh2o": 5.8,
        "bdod": 1.1,
        "drainage_class": None,
        "ag_fraction": None,
        "crop_fraction": None,
    },
}


@pytest.mark.parametrize("fixture, static", POINTS.items())
def test_live_path(fixture, static):
    daily = power_json_to_daily(json.loads((FIXTURES / fixture).read_text()))
    monthly = power_daily_to_monthly(daily, elev_m=static["elev_m"], lat=static["lat"])
    assert tuple(monthly.columns) == MONTHLY_INPUT_COLUMNS
    assert isinstance(monthly["month"].dtype, pd.PeriodDtype)
    assert len(monthly) >= 24

    last = monthly["month"].max()
    for target in (last + 1, last - 5):
        row = build_feature_row(static, monthly, target)
        assert tuple(row) == FEATURE_NAMES
        assert all(isinstance(v, float) for v in row.values())
        assert row["precip_l1"] == pytest.approx(
            monthly.loc[monthly["month"] == target - 1, "precip"].item()
        )
