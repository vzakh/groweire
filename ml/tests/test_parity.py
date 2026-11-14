"""Training/serving parity (Google Rules of ML #37): build_feature_table == build_feature_row.

The table sees the FULL history (including months >= target); the row sees only months < target.
Equality on a random sample therefore also proves the vectorised table is leak-free.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from agrolens_ml import FEATURE_NAMES, MONTHLY_INPUT_COLUMNS, build_feature_row
from agrolens_ml.features.build import build_feature_table

N_SAMPLE = 500


def _data(seed: int = 3):
    rng = np.random.default_rng(seed)
    cells = [f"c{i:05d}" for i in range(6)]
    months = pd.period_range("2001-01", "2024-12", freq="M")
    rows = []
    for c in cells:
        frame = pd.DataFrame({"cell_id": c, "month": months})
        for col in MONTHLY_INPUT_COLUMNS[1:]:
            vals = rng.normal(size=len(months)) * 10 + 50
            vals[rng.random(len(months)) < 0.05] = np.nan  # gaps
            frame[col] = vals
        frame["smap_pct"] = rng.uniform(0, 100, len(months))
        rows.append(frame.iloc[rng.integers(0, 6) :])  # ragged starts per cell
    monthly = pd.concat(rows, ignore_index=True)
    static = pd.DataFrame(
        {
            "elev_m": rng.uniform(0, 300, 6),
            "slope_deg": rng.uniform(0, 5, 6),
            "clay": rng.uniform(10, 40, 6),
            "sand": rng.uniform(20, 60, 6),
            "soc": rng.uniform(20, 80, 6),
            "phh2o": rng.uniform(5, 7.5, 6),
            "drainage_class": [1, 2, 3, 4, 5, None],
            "ag_fraction": rng.uniform(0.3, 1, 6),
        },
        index=pd.Index(cells, name="cell_id"),
    )
    return monthly, static


def test_table_equals_row_on_random_sample():
    monthly, static = _data()
    table = build_feature_table(monthly, static)
    sample = table.sample(N_SAMPLE, random_state=0)
    for _, trow in sample.iterrows():
        cid, month = trow["cell_id"], trow["month"]
        hist = monthly[monthly["cell_id"] == cid].drop(columns="cell_id")
        srow = build_feature_row(static.loc[cid].to_dict(), hist, month)
        expected = trow[list(FEATURE_NAMES)].to_numpy(dtype=float)
        got = np.array([srow[f] for f in FEATURE_NAMES])
        np.testing.assert_allclose(
            got, expected, rtol=0, atol=1e-9, equal_nan=True, err_msg=f"{cid} {month}"
        )


def test_table_shape_and_targets():
    monthly, static = _data()
    table = build_feature_table(monthly, static)
    assert list(table.columns) == ["cell_id", "month", *FEATURE_NAMES]
    assert set(table["month"].dt.month) == set(range(3, 11))
    assert not table.duplicated(["cell_id", "month"]).any()


def test_future_target_beyond_history():
    monthly, static = _data()
    hist = monthly[monthly["cell_id"] == "c00000"].drop(columns="cell_id")
    row = build_feature_row(static.loc["c00000"].to_dict(), hist, pd.Period("2025-01", freq="M"))
    last = hist[hist["month"] == pd.Period("2024-12", freq="M")]
    assert row["precip_l1"] == last["precip"].item() or np.isnan(last["precip"].item())
