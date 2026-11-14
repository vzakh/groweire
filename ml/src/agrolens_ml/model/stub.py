"""Deterministic stub model + stub bundle writer (brief §13.2, task 05).

The numbers here are NOT agronomic facts (hard rule 1). They only drive layouts and tests, and
every stub response is flagged `synthetic_data` by the backend. Never shipped to prod
(ALLOW_STUB_MODEL=false there).

Stub formula: p = clip(base[month] + 0.03*h, 0, 1), interval = p ± 0.05, with h a stable hash in
[-1, 1]. Feature rows carry no cell_id, so h hashes the row's static features (elev, soil, ...),
which are constant per cell: same determinism, no extra key in the rows.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from agrolens_ml.contract import CONTRACT_VERSION, Prediction, StressModel
from agrolens_ml.features import feature_labels
from agrolens_ml.features.build import (
    FEATURE_NAMES,
    STATIC_FROM_CELL,
    build_feature_row,
    month_from_sin_cos,
)
from agrolens_ml.features.monthly import power_daily_to_monthly

STUB_VERSION = "stub-0"
STUB_BASE: dict[int, float] = {
    3: 0.06,
    4: 0.08,
    5: 0.12,
    6: 0.18,
    7: 0.24,
    8: 0.17,
    9: 0.10,
    10: 0.14,
}
STUB_BASE_OUTSIDE_SEASON = 0.05
STUB_HALF_WIDTH = 0.05
STUB_DRIVERS: tuple[tuple[str, float], ...] = (  # (feature, fixed contribution)
    ("p_minus_et0_3m_l1_z", 0.04),
    ("tmax_l1_z", 0.02),
    ("ndvi_z_l1", 0.01),
)
STATIC_HASH_FEATURES: tuple[str, ...] = tuple(STATIC_FROM_CELL)


def stub_stress_types(month: int) -> list[str]:
    """Jun-Aug drought, Oct waterlogging, otherwise other (brief §13.2)."""
    if month in (6, 7, 8):
        return ["drought"]
    if month == 10:
        return ["waterlogging"]
    return ["other"]


def stable_hash_unit(keys: pd.DataFrame) -> np.ndarray:
    """Per-row stable hash of the given columns -> float in [-1, 1]."""
    rounded = keys.astype(float).round(3)
    out = np.empty(len(rounded))
    for i, vals in enumerate(rounded.itertuples(index=False, name=None)):
        digest = hashlib.sha256(repr(vals).encode()).digest()
        out[i] = int.from_bytes(digest[:8], "big") / 2**64 * 2.0 - 1.0
    return out


def rows_to_frame(rows: list[dict], feature_names: tuple[str, ...] = FEATURE_NAMES) -> pd.DataFrame:
    """Feature rows -> float frame in FEATURE_NAMES order. Missing -> NaN; unknown -> ValueError."""
    known = set(feature_names)
    for i, r in enumerate(rows):
        extra = set(r) - known
        if extra:
            raise ValueError(f"row {i} has unknown feature keys: {sorted(extra)}")
    frame = pd.DataFrame.from_records(rows, columns=list(feature_names))
    return frame.apply(pd.to_numeric, errors="coerce").astype(float)


class StubModel(StressModel):
    """Deterministic seasonal curve; satisfies the StressModel contract."""

    def __init__(self, base: dict[int, float] | None = None, version: str = STUB_VERSION):
        self.base = {int(k): float(v) for k, v in (base or STUB_BASE).items()}
        self.version = version

    def predict_frame(self, X: pd.DataFrame) -> pd.DataFrame:
        """Vectorised core: probability, lo, hi, month for a FEATURE_NAMES frame."""
        month = month_from_sin_cos(X["month_sin"].to_numpy(), X["month_cos"].to_numpy())
        base = np.array(
            [
                (
                    self.base.get(int(m), STUB_BASE_OUTSIDE_SEASON)
                    if not math.isnan(m)
                    else STUB_BASE_OUTSIDE_SEASON
                )
                for m in month
            ]
        )
        p = np.clip(base + 0.03 * stable_hash_unit(X[list(STATIC_HASH_FEATURES)]), 0.0, 1.0)
        return pd.DataFrame(
            {
                "probability": p,
                "lo": np.clip(p - STUB_HALF_WIDTH, 0.0, 1.0),
                "hi": np.clip(p + STUB_HALF_WIDTH, 0.0, 1.0),
                "month": month,
            },
            index=X.index,
        )

    def predict(self, rows: list[dict]) -> list[Prediction]:
        X = rows_to_frame(rows)
        core = self.predict_frame(X)
        driver_vals = X[[f for f, _ in STUB_DRIVERS]].to_numpy()
        out: list[Prediction] = []
        for i, (p, lo, hi, month) in enumerate(core.itertuples(index=False, name=None)):
            m = 0 if math.isnan(month) else int(month)
            types = stub_stress_types(m)
            drivers = []
            for j, (feat, contrib) in enumerate(STUB_DRIVERS):
                v = driver_vals[i, j]
                value = None if math.isnan(v) else float(v)
                drivers.append(
                    {
                        "feature": feat,
                        "value": value,
                        "contribution": contrib,
                        "text": feature_labels.text(feat, value),
                    }
                )
            out.append(
                Prediction(
                    probability=float(p),
                    interval=(float(lo), float(hi)),
                    drivers=drivers,
                    stress_types=types,
                    needs_local_review="other" in types,
                )
            )
        return out


# ---------------------------------------------------------------- bundle writer


def _example_history() -> tuple[dict, pd.DataFrame, pd.Period]:
    """A small seeded POWER-like daily series near Carlow -> monthly history (live path)."""
    rng = np.random.default_rng(7)
    dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
    doy = dates.day_of_year.to_numpy()
    seas = np.cos(2 * np.pi * (doy - 200) / 365.25)
    t2m = 10 + 5 * seas + rng.normal(0, 2, len(dates))
    daily = pd.DataFrame(
        {
            "date": dates,
            "T2M": t2m,
            "T2M_MAX": t2m + 4 + rng.normal(0, 1, len(dates)),
            "T2M_MIN": t2m - 4 + rng.normal(0, 1, len(dates)),
            "PRECTOTCORR": rng.gamma(0.6, 4.0, len(dates)),
            "RH2M": np.clip(85 - 8 * seas + rng.normal(0, 4, len(dates)), 30, 100),
            "WS2M": np.abs(rng.normal(4, 1.5, len(dates))),
            "ALLSKY_SFC_SW_DWN": np.clip(9 + 8 * seas + rng.normal(0, 2, len(dates)), 0.3, None),
            "GWETROOT": np.clip(0.75 - 0.1 * seas + rng.normal(0, 0.03, len(dates)), 0, 1),
            "GWETTOP": np.clip(0.7 - 0.15 * seas + rng.normal(0, 0.05, len(dates)), 0, 1),
            "T2MDEW": t2m - 2.5 + rng.normal(0, 1, len(dates)),
        }
    )
    static = {
        "lat": 52.70,
        "lon": -6.90,
        "elev_m": 60.0,
        "slope_deg": 2.0,
        "clay": 22.0,
        "sand": 40.0,
        "soc": 35.0,
        "phh2o": 6.4,
        "bdod": 1.2,
        "drainage_class": 2,
        "ag_fraction": 0.85,
        "crop_fraction": 0.4,
    }
    monthly = power_daily_to_monthly(daily, elev_m=static["elev_m"], lat=static["lat"])
    return static, monthly, pd.Period("2024-07", freq="M")


def _json_safe(row: dict) -> dict:
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}


def write_sha256sums(out: Path, names: list[str]) -> None:
    lines = [f"{hashlib.sha256((out / n).read_bytes()).hexdigest()}  {n}" for n in names]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def make_stub_bundle(out_dir: str | Path) -> Path:
    """Write the stub bundle (bundle.joblib, model_card.json, example.json, SHA256SUMS)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    bundle = {
        "kind": "stub",
        "version": STUB_VERSION,
        "feature_names": FEATURE_NAMES,
        "base": dict(STUB_BASE),
        "contract_version": CONTRACT_VERSION,
    }
    joblib.dump(bundle, out / "bundle.joblib")

    card = {
        "model_details": {
            "name": "AgroLens stress-risk stub",
            "version": STUB_VERSION,
            "kind": "stub",
            "contract_version": CONTRACT_VERSION,
        },
        "intended_use": "development only",
        "out_of_scope": ["any real decision", "production serving (ALLOW_STUB_MODEL=false)"],
        "caveats": [
            "Deterministic seasonal curve; numbers are not agronomic facts (rule 1).",
            "Every response built on it must carry data_quality ['synthetic_data'].",
        ],
    }
    (out / "model_card.json").write_text(json.dumps(card, indent=2) + "\n")

    static, monthly, target = _example_history()
    row = build_feature_row(static, monthly, target)
    pred = StubModel(bundle["base"]).predict([row])[0]
    example = {
        "cell_static": static,
        "target_month": str(target),
        "features": _json_safe(row),
        "expected": {"probability": pred["probability"], "interval": list(pred["interval"])},
    }
    (out / "example.json").write_text(json.dumps(example, indent=2) + "\n")

    write_sha256sums(out, ["bundle.joblib", "model_card.json", "example.json"])
    return out


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "ml/artifacts/stub_v0"
    print(make_stub_bundle(target_dir))
