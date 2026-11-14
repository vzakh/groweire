"""Real bundle kinds: round trip, training/serving parity, schema + version guards, latency."""

from __future__ import annotations

import time

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.isotonic import IsotonicRegression

from agrolens_ml import FEATURE_NAMES, load_bundle
from agrolens_ml.model.baselines import B1_FEATURES, b1_pipeline
from agrolens_ml.model.train import b1_bundle, fit_lgbm_fixed, lgbm_bundle


@pytest.fixture(scope="module")
def data():
    rng = np.random.default_rng(0)
    n = 4000
    X = pd.DataFrame(rng.normal(size=(n, len(FEATURE_NAMES))), columns=list(FEATURE_NAMES))
    X.loc[rng.random(n) < 0.1, "ndvi_z_l1"] = np.nan
    logit = -1.8 - 1.2 * X["p_minus_et0_3m_l1_z"] + 0.8 * X["tmax_l1_z"]
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int).to_numpy()
    return X, y


@pytest.fixture(scope="module")
def lgbm_dir(data, tmp_path_factory):
    X, y = data
    A = X.to_numpy()
    members = [fit_lgbm_fixed(A[k::5], y[k::5], 300) for k in range(5)]
    raw = np.mean([b.predict(A, num_iteration=it) for b, it in members], axis=0)
    cal = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(raw, y)
    out = tmp_path_factory.mktemp("lgbm")
    joblib.dump(lgbm_bundle(members, cal, "test-lgbm"), out / "bundle.joblib")
    return out


def test_lgbm_round_trip_parity(data, lgbm_dir):
    X, _ = data
    model = load_bundle(lgbm_dir)
    rows = [{k: (None if np.isnan(v) else v) for k, v in r.items()} for r in X.head(200).to_dict("records")]
    served = np.array([p["probability"] for p in model.predict(rows)])
    trained = model.predict_frame(X.head(200))["probability"].to_numpy()
    np.testing.assert_allclose(served, trained, atol=1e-9)
    for p in model.predict(rows[:20]):
        lo, hi = p["interval"]
        assert 0 <= lo <= p["probability"] <= hi <= 1
        assert len(p["drivers"]) == 3


def test_lgbm_drivers_find_the_signal(data, lgbm_dir):
    X, _ = data
    preds = load_bundle(lgbm_dir).predict(X.head(300).to_dict("records"))
    top = pd.Series([p["drivers"][0]["feature"] for p in preds]).value_counts()
    assert top.index[0] in ("p_minus_et0_3m_l1_z", "tmax_l1_z")


def test_lgbm_latency(data, lgbm_dir):
    X, _ = data
    model = load_bundle(lgbm_dir)
    rows = X.head(1000).to_dict("records")
    model.predict(rows[:10])
    t0 = time.perf_counter()
    model.predict(rows)
    assert time.perf_counter() - t0 < 0.100 * 3  # contract budget is 100 ms; loose in CI


def test_b1_round_trip(data, tmp_path):
    X, y = data
    members = [b1_pipeline().fit(X[list(B1_FEATURES)].iloc[k::3], y[k::3]) for k in range(3)]
    joblib.dump(b1_bundle(members, "test-b1"), tmp_path / "bundle.joblib")
    model = load_bundle(tmp_path)
    [p] = model.predict([X.iloc[0].to_dict()])
    assert {d["feature"] for d in p["drivers"]} <= set(B1_FEATURES)
    assert np.isclose(p["probability"], model.predict_frame(X.iloc[[0]])["probability"].iloc[0])


def test_schema_and_version_guards(lgbm_dir, tmp_path):
    b = joblib.load(lgbm_dir / "bundle.joblib")
    joblib.dump({**b, "feature_names": FEATURE_NAMES[:-1]}, tmp_path / "bundle.joblib")
    with pytest.raises(ValueError, match="feature_names"):
        load_bundle(tmp_path)
    joblib.dump({**b, "lib_versions": {"lightgbm": "1.0.0"}}, tmp_path / "bundle.joblib")
    with pytest.raises(ValueError, match="lightgbm"):
        load_bundle(tmp_path)
