"""NDVI labels: QA, monthly max compositing, cell mean/valid_frac, z and label (PLAN_10 task 11)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agrolens_ml.labels import ndvi as L


def test_qa_keeps_good_and_marginal_only():
    raw = np.array([5000, 6000, 7000, 8000, -3000, 12000], dtype=np.int16)
    rel = np.array([0, 1, 2, 3, 0, 0], dtype=np.int8)
    out = L.qa_ndvi(raw, rel)
    assert out[0] == pytest.approx(0.5) and out[1] == pytest.approx(0.6)
    assert np.isnan(out[2:]).all()  # snow/ice, cloudy, fill, out of range


def test_pixel_months_from_doy():
    assert L.pixel_months(2018, np.array([1, 31, 32, 182, 366, -1])).tolist() == [1, 1, 2, 7, 1, 0]
    assert L.pixel_months(2020, np.array([60, 61])).tolist() == [2, 3]  # leap year


class _Pix(L.PixelIndex):
    def __init__(self, codes, ids):
        super().__init__(np.arange(len(codes)), np.asarray(codes), np.asarray(ids))


def test_year_cell_months_max_composite_and_valid_frac():
    pix = _Pix([0, 0, 1, 1], ["a", "b"])  # 2 ag pixels per cell
    # two July composites: per-pixel max wins; pixel 3 never valid
    c1 = (np.array([0.5, 0.6, 0.7, np.nan], dtype=np.float32), np.array([7, 7, 7, 7]))
    c2 = (np.array([0.8, 0.4, np.nan, np.nan], dtype=np.float32), np.array([7, 7, 7, 7]))
    df = L.year_cell_months([c1, c2], pix, 2018).set_index(["cell_id", "month"])
    assert df.loc[("a", "2018-07"), "ndvi"] == pytest.approx((0.8 + 0.6) / 2)
    assert df.loc[("a", "2018-07"), "valid_frac"] == pytest.approx(1.0)
    assert df.loc[("b", "2018-07"), "ndvi"] == pytest.approx(0.7)
    assert df.loc[("b", "2018-07"), "valid_frac"] == pytest.approx(0.5)
    assert np.isnan(df.loc[("a", "2018-06"), "ndvi"])  # no June composite


def _series(values, valid=1.0, cal=7, start=2001):
    years = range(start, start + len(values))
    return pd.DataFrame(
        {
            "cell_id": "a",
            "month": [f"{y}-{cal:02d}" for y in years],
            "ndvi": values,
            "valid_frac": valid,
        }
    )


def test_z_and_label_on_toy_series():
    vals = [0.80, 0.82, 0.78, 0.81, 0.79, 0.80, 0.83, 0.77, 0.80, 0.81] + [0.60]  # 2011 dip
    df = L.add_anomalies_and_labels(_series(vals)).set_index("month")
    assert df.loc["2011-07", "stress_label"] == True  # noqa: E712
    assert df.loc["2003-07", "stress_label"] == False  # noqa: E712
    base = np.array(vals)  # 2001-2011 all in the baseline
    assert df.loc["2011-07", "ndvi_z"] == pytest.approx((0.60 - base.mean()) / base.std(ddof=1))


def test_low_valid_frac_and_short_baseline_give_null_label():
    df = L.add_anomalies_and_labels(_series([0.8] * 6 + [0.5], valid=1.0))  # 7 years
    assert df["stress_label"].isna().all()  # < 8 baseline years -> no climatology
    vals = [0.80, 0.82, 0.78, 0.81, 0.79, 0.80, 0.83, 0.77, 0.80, 0.60]
    s = _series(vals)
    s.loc[9, "valid_frac"] = 0.2
    out = L.add_anomalies_and_labels(s)
    assert pd.isna(out.loc[9, "stress_label"]) and np.isnan(out.loc[9, "ndvi_z"])


def test_feature_anomaly_ignores_later_years():
    vals = [0.80, 0.82, 0.78, 0.81, 0.79, 0.80, 0.83, 0.77, 0.80, 0.81]
    a = L.add_anomalies_and_labels(_series(vals)).set_index("month")
    vals2 = vals[:6] + [0.1, 0.1, 0.1, 0.1]  # change 2007+ only
    b = L.add_anomalies_and_labels(_series(vals2)).set_index("month")
    assert a.loc["2006-07", "ndvi_z_feat"] == pytest.approx(b.loc["2006-07", "ndvi_z_feat"])
    assert np.isnan(a.loc["2004-07", "ndvi_z_feat"])  # < MIN_CLIM_YEARS earlier years
