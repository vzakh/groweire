"""Hard rule 2 (brief §8.4): data at month >= m never changes the feature row for m."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from agrolens_ml import MONTHLY_INPUT_COLUMNS, build_feature_row

STATIC = {
    "lat": 53.0,
    "lon": -7.5,
    "elev_m": 80.0,
    "slope_deg": 3.0,
    "clay": 25.0,
    "sand": 35.0,
    "soc": 40.0,
    "phh2o": 6.2,
    "bdod": 1.2,
    "drainage_class": 3,
    "ag_fraction": 0.8,
    "crop_fraction": 0.3,
}


def _history(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = pd.period_range("2019-01", "2023-12", freq="M")  # 5 years
    data = {c: rng.normal(size=len(months)) for c in MONTHLY_INPUT_COLUMNS if c != "month"}
    return pd.DataFrame({"month": months, **data})[list(MONTHLY_INPUT_COLUMNS)]


def _same(a: dict, b: dict) -> bool:
    return a.keys() == b.keys() and all(
        (math.isnan(a[k]) and math.isnan(b[k])) or a[k] == b[k] for k in a
    )


@pytest.mark.parametrize("target", ["2020-03", "2021-07", "2022-10", "2023-06"])
def test_mutating_future_leaves_row_unchanged(target):
    target = pd.Period(target, freq="M")
    hist = _history()
    before = build_feature_row(STATIC, hist, target)

    mutated = hist.copy()
    future = mutated["month"] >= target
    cols = [c for c in MONTHLY_INPUT_COLUMNS if c != "month"]
    mutated.loc[future, cols] = mutated.loc[future, cols] * 100 + 999
    assert _same(before, build_feature_row(STATIC, mutated, target))

    truncated = hist.loc[~future]
    assert _same(before, build_feature_row(STATIC, truncated, target))


def test_past_data_does_change_row():
    target = pd.Period("2022-07", freq="M")
    hist = _history()
    before = build_feature_row(STATIC, hist, target)
    changed = hist.copy()
    changed.loc[changed["month"] == target - 1, "precip"] += 10
    after = build_feature_row(STATIC, changed, target)
    assert after["precip_l1"] == pytest.approx(before["precip_l1"] + 10)


def test_month_order_does_not_matter():
    target = pd.Period("2022-07", freq="M")
    hist = _history()
    shuffled = hist.sample(frac=1.0, random_state=1)
    assert _same(
        build_feature_row(STATIC, hist, target), build_feature_row(STATIC, shuffled, target)
    )
