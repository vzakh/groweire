"""Baselines the model must beat (brief §8.5): B0 climatology, B1 logistic regression."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

B1_FEATURES = ("p_minus_et0_3m_l1_z", "tmax_l1_z", "smap_pct_l1", "ndvi_z_l1", "drainage_class")


def b0_fit(train: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Training stress frequency per (cell_id, calendar month), with a per-month fallback."""
    y = train["stress_label"].astype(float)
    by_cell = y.groupby([train["cell_id"], train["mon"]]).mean()
    by_month = y.groupby(train["mon"]).mean()
    return by_cell, by_month


def b0_predict(model: tuple[pd.Series, pd.Series], df: pd.DataFrame) -> np.ndarray:
    by_cell, by_month = model
    idx = pd.MultiIndex.from_arrays([df["cell_id"], df["mon"]])
    p = by_cell.reindex(idx).to_numpy()
    fb = by_month.reindex(df["mon"]).to_numpy()
    return np.where(np.isnan(p), fb, p)


def b1_pipeline() -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scale", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000)),
    ])
