"""Load a model bundle directory into a StressModel (brief §8.8, §13.2)."""

from __future__ import annotations

from pathlib import Path

import joblib

from agrolens_ml.contract import StressModel
from agrolens_ml.features.build import FEATURE_NAMES
from agrolens_ml.model.stub import StubModel

BUNDLE_FILE = "bundle.joblib"


def load_bundle(model_dir: str | Path) -> StressModel:
    """Load `<model_dir>/bundle.joblib`; raises ValueError if its feature_names != FEATURE_NAMES."""
    path = Path(model_dir) / BUNDLE_FILE
    bundle = joblib.load(path)
    names = tuple(bundle.get("feature_names", ()))
    if names != FEATURE_NAMES:
        raise ValueError(
            f"{path}: bundle feature_names do not match the installed agrolens_ml FEATURE_NAMES "
            f"({len(names)} vs {len(FEATURE_NAMES)}); retrain or install the matching version"
        )
    kind = bundle.get("kind")
    if kind == "stub":
        return StubModel(bundle["base"], bundle["version"])
    if kind in ("lgbm", "b1"):
        raise NotImplementedError(f"bundle kind {kind!r} is implemented in PLAN_10 task 14")
    raise ValueError(f"{path}: unknown bundle kind {kind!r}")
