"""Seasonal risk profile per cell x calendar month -> risk_grid.parquet (PLAN_10 task 15).

p_mean_10y / p_lo / p_hi: means over the last 10 complete years of the model probability and
interval bounds. dominant_type: most frequent non-"other" stress type in those years (else
"other"). trend_per_decade: Sen's slope of the yearly probability over all years >= 2002, x 10.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from agrolens_ml.features.build import FEATURE_NAMES
from agrolens_ml.features.stress_rules import attribute_stress
from agrolens_ml.model.bundle import load_bundle
from agrolens_ml.schemas import RISK_GRID_SCHEMA

PROFILE_YEARS = 10
TREND_START = 2002


def sens_slope(years: np.ndarray, P: np.ndarray) -> np.ndarray:
    """Median pairwise slope per row of P (rows = series over `years`), NaN-aware."""
    i, j = np.triu_indices(len(years), k=1)
    slopes = (P[:, j] - P[:, i]) / (years[j] - years[i])[None, :]
    with np.errstate(all="ignore"):
        return np.nanmedian(slopes, axis=1)


def _dominant(types: pd.Series) -> str:
    flat = [t for ts in types for t in ts if t != "other"]
    return pd.Series(flat).mode().iloc[0] if flat else "other"


def build_risk_grid(processed: Path, bundle_dir: Path) -> pd.DataFrame:
    model = load_bundle(bundle_dir)
    df = pd.read_parquet(processed / "cell_month_features.parquet",
                         columns=["cell_id", "month", *FEATURE_NAMES])
    df["year"] = df["month"].str[:4].astype(int)
    df["calendar_month"] = df["month"].str[5:7].astype(int)
    df = df[df["year"] >= TREND_START].reset_index(drop=True)
    X = df[list(FEATURE_NAMES)].astype(float)
    core = model.predict_frame(X)
    df[["p", "lo", "hi"]] = core[["probability", "lo", "hi"]].to_numpy()

    last = sorted(df["year"].unique())[-PROFILE_YEARS:]
    recent = df[df["year"].isin(last)].copy()
    recent["types"] = [attribute_stress(r) for r in recent[list(FEATURE_NAMES)].to_dict("records")]
    g = recent.groupby(["cell_id", "calendar_month"])
    out = g.agg(p_mean_10y=("p", "mean"), p_lo=("lo", "mean"), p_hi=("hi", "mean")).reset_index()
    out["dominant_type"] = g["types"].agg(_dominant).to_numpy()

    wide = df.pivot_table(index=["cell_id", "calendar_month"], columns="year", values="p")
    trend = pd.Series(sens_slope(wide.columns.to_numpy(float), wide.to_numpy()) * 10,
                      index=wide.index, name="trend_per_decade").reset_index()
    out = out.merge(trend, on=["cell_id", "calendar_month"], how="left")
    return out[[f.name for f in RISK_GRID_SCHEMA]]


def write_risk_grid(processed: Path, bundle_dir: Path) -> Path:
    out = build_risk_grid(processed, bundle_dir)
    path = processed / "risk_grid.parquet"
    pq.write_table(pa.Table.from_pandas(out, schema=RISK_GRID_SCHEMA, preserve_index=False), path)
    return path
