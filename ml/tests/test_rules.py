"""Each stress rule fires at its threshold and not just past it (brief §8.2)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from agrolens_ml import FEATURE_NAMES, STRESS_TYPES, attribute_stress
from agrolens_ml.features.build import month_angle

EPS = 1e-6


def row(month: int = 7, **values) -> dict:
    r = dict.fromkeys(FEATURE_NAMES, math.nan)
    ang = month_angle(month)
    r["month_sin"], r["month_cos"] = float(np.sin(ang)), float(np.cos(ang))
    r.update(values)
    return r


def test_nothing_known_is_other():
    assert attribute_stress(row()) == ["other"]


@pytest.mark.parametrize("value, fires", [(-1.0, True), (-1.0 + EPS, False), (-2.5, True)])
def test_drought_water_balance(value, fires):
    assert ("drought" in attribute_stress(row(p_minus_et0_3m_l1_z=value))) is fires


@pytest.mark.parametrize("value, fires", [(20.0, True), (20.0 + EPS, False)])
def test_drought_smap(value, fires):
    assert ("drought" in attribute_stress(row(smap_pct_l1=value))) is fires


@pytest.mark.parametrize(
    "z, drainage, gwet, fires",
    [
        (1.0, 4, math.nan, True),
        (1.0 - EPS, 5, math.nan, False),
        (1.5, 3, math.nan, False),
        (1.5, 3, 0.9, True),
        (1.5, math.nan, 0.9 - EPS, False),
        (1.5, None, 0.95, True),
    ],
)
def test_waterlogging(z, drainage, gwet, fires):
    r = row(p_minus_et0_l1_z=z, drainage_class=drainage, gwetroot_l1=gwet)
    assert ("waterlogging" in attribute_stress(r)) is fires


@pytest.mark.parametrize("days, fires", [(3, True), (2, False)])
def test_heat(days, fires):
    assert ("heat" in attribute_stress(row(hot_days_l1=days))) is fires


@pytest.mark.parametrize(
    "month, days, fires", [(3, 1, True), (5, 2, True), (6, 3, False), (4, 0, False)]
)
def test_frost_only_in_spring(month, days, fires):
    assert ("frost" in attribute_stress(row(month=month, frost_days_l1=days))) is fires


def test_several_types_and_order():
    types = attribute_stress(row(month=4, p_minus_et0_3m_l1_z=-1.5, hot_days_l1=4, frost_days_l1=2))
    assert types == ["drought", "heat", "frost"]
    assert set(types) <= set(STRESS_TYPES)
