"""Real StressModel: k cross-validation fold members + one shared calibrator (PLAN_10 task 14).

    p_k         = calibrator(member_k(X))          (b1: no calibrator, logistic output is used)
    probability = mean_k p_k,  interval = (min_k p_k, max_k p_k)
    drivers     = top-3 |mean_k contribution| (lgbm: pred_contrib = SHAP, log-odds; b1: coef * z)

`predict_frame` is the vectorised core shared by training/evaluation, the risk grid and `predict`,
so the score in training equals the score in serving (Google Rules of ML #37).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from agrolens_ml.contract import Prediction, StressModel
from agrolens_ml.features import feature_labels
from agrolens_ml.features.build import FEATURE_NAMES
from agrolens_ml.features.stress_rules import attribute_stress
from agrolens_ml.model.stub import rows_to_frame

REVIEW_INTERVAL_WIDTH = 0.3
N_DRIVERS = 3
_NAN_KEY = -9.87654321e300


class EnsembleModel(StressModel):
    """kind 'lgbm' (members = [(Booster, best_iteration)]) or 'b1' (members = sklearn Pipelines)."""

    def __init__(self, bundle: dict):
        self.kind = bundle["kind"]
        self.members = bundle["members"]
        self.calibrator = bundle.get("calibrator")
        self.version = bundle["version"]
        self.feature_names = tuple(bundle["feature_names"])
        self.inputs = tuple(bundle.get("inputs") or self.feature_names)  # b1 uses a subset
        self._input_idx = [self.feature_names.index(f) for f in self.inputs]

    # ------------------------------------------------------------ vectorised core
    def _array(self, X: pd.DataFrame) -> np.ndarray:
        return X[list(self.inputs)].to_numpy(dtype=float)

    def raw_members(self, X: pd.DataFrame) -> np.ndarray:
        """(k, n) uncalibrated member scores in [0, 1]."""
        A = self._array(X)
        if self.kind == "lgbm":
            return np.stack([b.predict(A, num_iteration=it) for b, it in self.members])
        F = pd.DataFrame(A, columns=list(self.inputs))
        return np.stack([m.predict_proba(F)[:, 1] for m in self.members])

    def member_probs(self, X: pd.DataFrame) -> np.ndarray:
        raw = self.raw_members(X)
        if self.calibrator is None:
            return raw
        return np.clip(self.calibrator.predict(raw.ravel()).reshape(raw.shape), 0.0, 1.0)

    def predict_frame(self, X: pd.DataFrame) -> pd.DataFrame:
        P = self.member_probs(X)
        p = P.mean(axis=0)
        return pd.DataFrame(
            {"probability": p, "lo": np.minimum(P.min(axis=0), p), "hi": np.maximum(P.max(axis=0), p)},
            index=X.index,
        )

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        """(n, n_features) mean member contribution (positive = raises the risk)."""
        A = self._array(X)
        # SHAP is the expensive part (~75 ms per 1,000 rows per member): identical rows (e.g. the
        # same cell's static part with repeated months) have identical contributions, so dedupe.
        key = np.nan_to_num(A, nan=_NAN_KEY)
        _, first, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
        A = A[first]
        if self.kind == "lgbm":
            sub = np.mean(
                [b.predict(A, num_iteration=it, pred_contrib=True)[:, :-1] for b, it in self.members],
                axis=0,
            )
        else:
            F = pd.DataFrame(A, columns=list(self.inputs))
            sub = np.mean([m[:-1].transform(F) * m[-1].coef_[0][None, :] for m in self.members], axis=0)
        full = np.zeros((len(A), len(self.feature_names)))
        full[:, self._input_idx] = sub
        return full[np.asarray(inverse).ravel()]

    # ------------------------------------------------------------ contract
    def predict(self, rows: list[dict]) -> list[Prediction]:
        X = rows_to_frame(rows, FEATURE_NAMES)
        core = self.predict_frame(X)
        C = self.contributions(X)
        vals = X[list(self.feature_names)].to_numpy(dtype=float)
        top = np.argsort(-np.abs(C), axis=1)[:, :N_DRIVERS]
        ndvi_col = self.feature_names.index("ndvi_z_l1")
        records = X.to_dict("records")
        out: list[Prediction] = []
        for i, (p, lo, hi) in enumerate(core.itertuples(index=False, name=None)):
            drivers = []
            for j in top[i]:
                feat, v, c = self.feature_names[j], vals[i, j], float(C[i, j])
                value = None if math.isnan(v) else float(v)
                drivers.append(
                    {"feature": feat, "value": value, "contribution": c,
                     "text": feature_labels.text(feat, value, c)}
                )
            types = attribute_stress(records[i])
            review = bool(
                (hi - lo) > REVIEW_INTERVAL_WIDTH or "other" in types or math.isnan(vals[i, ndvi_col])
            )
            out.append(
                Prediction(probability=float(p), interval=(float(lo), float(hi)), drivers=drivers,
                           stress_types=types, needs_local_review=review)
            )
        return out
