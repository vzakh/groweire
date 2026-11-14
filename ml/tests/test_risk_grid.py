import numpy as np

from agrolens_ml.risk_grid import _dominant, sens_slope


def test_sens_slope_linear_and_robust():
    years = np.arange(2002, 2026, dtype=float)
    P = np.vstack([0.1 + 0.01 * (years - 2002), np.full(len(years), 0.2)])
    P[0, 5] = 0.99  # one outlier barely moves Sen's slope
    np.testing.assert_allclose(sens_slope(years, P), [0.01, 0.0], atol=1e-3)


def test_dominant_type_prefers_named_stress():
    assert _dominant([["other"], ["drought"], ["drought", "heat"], ["other"]]) == "drought"
    assert _dominant([["other"], ["other"]]) == "other"
