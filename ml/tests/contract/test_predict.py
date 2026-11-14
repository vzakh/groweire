"""Prediction invariants for any bundle kind (brief §8.7, §13.2)."""

from __future__ import annotations

import math
import time

import pytest

from agrolens_ml import FEATURE_NAMES, STRESS_TYPES
from agrolens_ml.contract import StressModel

pytestmark = pytest.mark.contract

BANNED = ("NDVI", "ET0", "_z", "%")
LATENCY_BUDGET_S = 0.100


def _check(pred) -> None:
    p = pred["probability"]
    lo, hi = pred["interval"]
    assert 0.0 <= p <= 1.0
    assert 0.0 <= lo <= p <= hi <= 1.0
    assert len(pred["drivers"]) <= 3
    for d in pred["drivers"]:
        assert set(d) >= {"feature", "value", "contribution", "text"}
        assert d["feature"] in FEATURE_NAMES
        assert d["text"].strip()
        assert not any(term in d["text"] for term in BANNED), d["text"]
    assert pred["stress_types"] and set(pred["stress_types"]) <= set(STRESS_TYPES)
    assert isinstance(pred["needs_local_review"], bool)


def test_model_is_a_stress_model(model):
    assert isinstance(model, StressModel)
    assert isinstance(model.version, str) and model.version


def test_example_row_has_feature_names(example):
    assert set(example["features"]) == set(FEATURE_NAMES)


def test_predict_example(model, example):
    [pred] = model.predict([example["features"]])
    _check(pred)
    assert math.isclose(pred["probability"], example["expected"]["probability"], abs_tol=1e-9)


def test_missing_keys_are_allowed(model, example):
    row = dict(example["features"])
    for key in list(row)[2:10]:
        row.pop(key)
    _check(model.predict([row])[0])


def test_unknown_keys_raise(model, example):
    with pytest.raises(ValueError):
        model.predict([{**example["features"], "not_a_feature": 1.0}])


def test_batch_latency(model, example):
    rows = [example["features"]] * 1000
    model.predict(rows[:10])  # warm-up
    t0 = time.perf_counter()
    preds = model.predict(rows)
    elapsed = time.perf_counter() - t0
    assert len(preds) == 1000
    assert elapsed < LATENCY_BUDGET_S, f"{elapsed * 1000:.0f} ms for 1,000 rows"
