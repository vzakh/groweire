"""Train, calibrate, evaluate and bundle the stress model (PLAN_10 tasks 13-14, brief §8.5-8.6).

Splits: GroupKFold by year on the training years, a future-years holdout (2022-2025) and a
spatial block-family check. If the final holdout years are not labelled yet (NDVI still
downloading), the last two labelled years become a *dev* holdout: the run is reported but
ml/artifacts/CURRENT is not switched (holdout_kind = "dev").
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import sklearn
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import GroupKFold

from agrolens_ml.contract import CONTRACT_VERSION
from agrolens_ml.features.build import FEATURE_NAMES
from agrolens_ml.model import evaluate as ev
from agrolens_ml.model.baselines import B1_FEATURES, b0_fit, b0_predict, b1_pipeline
from agrolens_ml.model.ensemble import EnsembleModel
from agrolens_ml.model.stub import write_sha256sums
from agrolens_ml.schemas import feature_names_sha256

TRAIN_START = 2002  # 2001 has no lag history
HOLDOUT_YEARS = (2022, 2025)
CASE_YEAR = 2018
BLOCK_M = 50_000
SPATIAL_FAMILY_MOD = 5
LGBM_PARAMS = dict(
    objective="binary", learning_rate=0.05, num_leaves=31, min_child_samples=50,
    feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
    metric=["average_precision", "binary_logloss"], verbosity=-1, seed=42,
    deterministic=True, force_col_wise=True, num_threads=0,
)  # fmt: skip


# ---------------------------------------------------------------- data
def load_training_table(processed: Path) -> pd.DataFrame:
    df = pd.read_parquet(processed / "cell_month_features.parquet")
    df = df[df["stress_label"].notna()].copy()
    grid = pd.read_parquet(processed / "grid_cells.parquet",
                           columns=["cell_id", "lon", "lat", "crop_fraction"])
    df = df.merge(grid, on="cell_id", how="left")
    df["year"] = df["month"].str[:4].astype(int)
    df["mon"] = df["month"].str[5:7].astype(int)
    df["y"] = df["stress_label"].astype(bool).astype(int)
    df["block_family"] = spatial_families(df["lon"].to_numpy(), df["lat"].to_numpy())
    return df.reset_index(drop=True)


def spatial_families(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """0 = held-out family (every 5th 50-km block in Irish Transverse Mercator), 1 = rest."""
    from pyproj import Transformer  # pylint: disable=import-outside-toplevel

    x, y = Transformer.from_crs("EPSG:4326", "EPSG:2157", always_xy=True).transform(lon, lat)
    bx, by = np.floor(np.asarray(x) / BLOCK_M), np.floor(np.asarray(y) / BLOCK_M)
    block = pd.Series(bx * 1000 + by)
    rank = block.rank(method="dense").astype(int).to_numpy()
    return np.where(rank % SPATIAL_FAMILY_MOD == 0, 0, 1)


def split_years(df: pd.DataFrame) -> tuple[list[int], list[int], str]:
    years = sorted(df["year"].unique())
    final = [y for y in years if HOLDOUT_YEARS[0] <= y <= HOLDOUT_YEARS[1]]
    if final:
        hold, kind = final, "final"
    else:
        hold, kind = years[-2:], "dev"
    train = [y for y in years if TRAIN_START <= y < min(hold)]
    return train, hold, kind


def xy(df: pd.DataFrame, cols=FEATURE_NAMES) -> tuple[np.ndarray, np.ndarray]:
    return df[list(cols)].to_numpy(dtype=float), df["y"].to_numpy()


# ---------------------------------------------------------------- fitting
def fit_lgbm_cv(X, y, groups, n_splits=5, rounds=2000, es=100, log=print):
    oof = np.full(len(y), np.nan)
    members = []
    for k, (tr, va) in enumerate(GroupKFold(n_splits=n_splits).split(X, y, groups)):
        dtr = lgb.Dataset(X[tr], y[tr], feature_name=list(FEATURE_NAMES), free_raw_data=False)
        dva = lgb.Dataset(X[va], y[va], reference=dtr)
        booster = lgb.train(LGBM_PARAMS, dtr, num_boost_round=rounds, valid_sets=[dva],
                            callbacks=[lgb.early_stopping(es, first_metric_only=True, verbose=False)])
        it = booster.best_iteration or rounds
        oof[va] = booster.predict(X[va], num_iteration=it)
        members.append((booster, it))
        log(f"  fold {k}: {it} trees, val years {sorted(set(groups[va]))}")
    return members, oof


def fit_lgbm_fixed(X, y, rounds: int):
    booster = lgb.train(LGBM_PARAMS, lgb.Dataset(X, y, feature_name=list(FEATURE_NAMES)),
                        num_boost_round=rounds)
    return booster, rounds


def fit_b1_cv(df, groups, n_splits=5):
    X = df[list(B1_FEATURES)]
    y = df["y"].to_numpy()
    oof = np.full(len(y), np.nan)
    members = []
    for tr, va in GroupKFold(n_splits=n_splits).split(X, y, groups):
        m = b1_pipeline().fit(X.iloc[tr], y[tr])
        oof[va] = m.predict_proba(X.iloc[va])[:, 1]
        members.append(m)
    return members, oof


def lgbm_bundle(members, calibrator, version: str) -> dict:
    return {"kind": "lgbm", "members": members, "calibrator": calibrator, "version": version,
            "feature_names": FEATURE_NAMES, "inputs": None}


def b1_bundle(members, version: str) -> dict:
    return {"kind": "b1", "members": members, "calibrator": None, "version": version,
            "feature_names": FEATURE_NAMES, "inputs": B1_FEATURES}


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _json_safe(v):
    if isinstance(v, float) and np.isnan(v):
        return None
    return v


# ---------------------------------------------------------------- main
def run_train(data: Path, out: Path, n_splits: int = 5, artifacts: Path = Path("ml/artifacts"),
              log=print) -> dict:
    processed = data / "processed"
    df = load_training_table(processed)
    train_years, hold_years, hold_kind = split_years(df)
    n_splits = min(n_splits, len(train_years))
    tr = df[df["year"].isin(train_years)].reset_index(drop=True)
    ho = df[df["year"].isin(hold_years)].reset_index(drop=True)
    log(f"train years {train_years[0]}-{train_years[-1]} ({len(tr):,} rows), "
        f"holdout {hold_kind} {hold_years} ({len(ho):,} rows), base rate {tr['y'].mean():.3f}")

    X, y = xy(tr)
    groups = tr["year"].to_numpy()
    members, oof = fit_lgbm_cv(X, y, groups, n_splits, log=log)
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(oof, y)
    b1_members, b1_oof = fit_b1_cv(tr, groups, n_splits)
    version = f"stress-lgbm-1-{hold_kind}"
    lgbm = EnsembleModel(lgbm_bundle(members, calibrator, version))
    b1 = EnsembleModel(b1_bundle(b1_members, version.replace("lgbm", "b1")))

    # ---- holdout evaluation
    yh = ho["y"].to_numpy()
    p = {
        "B0 climatology": b0_predict(b0_fit(tr), ho),
        "B1 logistic": b1.predict_frame(ho)["probability"].to_numpy(),
        "LGBM raw": lgbm.raw_members(ho).mean(axis=0),
        "LGBM calibrated": lgbm.predict_frame(ho)["probability"].to_numpy(),
    }
    table = {k: ev.metrics(yh, v) for k, v in p.items()}
    cv = {"LGBM calibrated (OOF)": ev.metrics(y, calibrator.predict(oof)),
          "B1 logistic (OOF)": ev.metrics(y, b1_oof)}
    cal, b0m, b1m = table["LGBM calibrated"], table["B0 climatology"], table["B1 logistic"]
    ship_lgbm = (cal["pr_auc"] or 0) > max(b0m["pr_auc"] or 0, b1m["pr_auc"] or 0) and \
        cal["brier"] < min(b0m["brier"], b1m["brier"])
    shipped = lgbm if ship_lgbm else b1
    log(f"holdout PR-AUC  B0 {b0m['pr_auc']:.3f}  B1 {b1m['pr_auc']:.3f}  "
        f"LGBM-cal {cal['pr_auc']:.3f} -> ship {'lgbm' if ship_lgbm else 'b1'}")

    # ---- spatial check: retrain without the held-out block family, score its holdout cells
    fixed = int(np.median([it for _, it in members]))
    keep = tr["block_family"].to_numpy() == 1
    sp_booster = fit_lgbm_fixed(X[keep], y[keep], fixed)
    sp_model = EnsembleModel(lgbm_bundle([sp_booster], calibrator, "spatial"))
    fam = (ho["block_family"] == 0).to_numpy()
    spatial = {"held_out_family_unseen_cells": ev.metrics(
                   yh[fam], sp_model.predict_frame(ho[fam])["probability"].to_numpy()),
               "same_rows_full_model": ev.metrics(yh[fam], p["LGBM calibrated"][fam])}

    # ---- case study: leave the case year out of training
    case_year = CASE_YEAR if CASE_YEAR in train_years else int(
        tr[tr["mon"].isin([6, 7])].groupby("year")["y"].mean().idxmax())
    cy = tr["year"].to_numpy() == case_year
    case_booster = fit_lgbm_fixed(X[~cy], y[~cy], fixed)
    case_model = EnsembleModel(lgbm_bundle([case_booster], calibrator, "case"))
    case_df = tr[cy].assign(predicted=case_model.predict_frame(tr[cy])["probability"].to_numpy())
    clim = tr[~cy].groupby("mon")["y"].mean()
    case_monthly = pd.DataFrame({
        "observed": case_df.groupby("mon")["y"].mean(),
        "predicted": case_df.groupby("mon")["predicted"].mean(),
        "climatology": clim,
    }).dropna()

    # ---- write bundle + reports
    out.mkdir(parents=True, exist_ok=True)
    reports = out / "reports"
    reports.mkdir(exist_ok=True)
    bundle = (lgbm_bundle(members, calibrator, version) if ship_lgbm
              else b1_bundle(b1_members, b1.version))
    bundle |= {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(), "contract_version": CONTRACT_VERSION,
        "lib_versions": {"lightgbm": lgb.__version__, "sklearn": sklearn.__version__},
        "train_years": train_years, "holdout_years": hold_years, "holdout_kind": hold_kind,
    }
    joblib.dump(bundle, out / "bundle.joblib", compress=3)

    ex_row = ho[ho["ndvi_z_l1"].notna()].iloc[[0]]
    expected = shipped.predict_frame(ex_row).iloc[0]
    example = {
        "cell_id": str(ex_row["cell_id"].iloc[0]), "target_month": str(ex_row["month"].iloc[0]),
        "features": {f: _json_safe(float(ex_row[f].iloc[0])) for f in FEATURE_NAMES},
        "expected": {"probability": float(expected["probability"]),
                     "interval": [float(expected["lo"]), float(expected["hi"])]},
    }
    (out / "example.json").write_text(json.dumps(example, indent=2) + "\n")

    p_ship = p["LGBM calibrated"] if ship_lgbm else p["B1 logistic"]
    curves = {k: ev.reliability(yh, v) for k, v in p.items()}
    ev.plot_reliability({k: curves[k] for k in ("B0 climatology", "B1 logistic", "LGBM calibrated")},
                        reports / "reliability.png")
    ev.plot_case(case_monthly, case_year, reports / f"case_{case_year}.png")
    sl = ev.slices(ho, yh, p_ship)
    shares = ev.band_shares(p_ship)
    gain = pd.Series(np.mean([b.feature_importance("gain") for b, _ in members], axis=0),
                     index=FEATURE_NAMES).sort_values(ascending=False)
    extra = [
        f"Holdout: **{hold_kind}** years {hold_years}; training years {train_years[0]}-{train_years[-1]}.",
        f"Shipped: **{'LightGBM (calibrated)' if ship_lgbm else 'B1 logistic regression'}** "
        "(rule: LGBM-calibrated must beat B0 and B1 on PR-AUC and Brier).",
        "", "## Cross-validation (out-of-fold, training years)", "",
        *[f"- {k}: PR-AUC {m['pr_auc']:.4f}, Brier {m['brier']:.4f}" for k, m in cv.items()],
        "", "## Spatial check (every 5th 50-km block held out)", "",
        *[f"- {k}: PR-AUC {m['pr_auc'] or float('nan'):.4f}, Brier {m['brier']:.4f}, n {m['n']:,}"
          for k, m in spatial.items()],
        "", "## By month (shipped model)", "", "| Month | PR-AUC | Brier | base rate |", "|---|---|---|---|",
        *[f"| {k} | {m['pr_auc'] or float('nan'):.3f} | {m['brier']:.3f} | {m['base_rate']:.3f} |"
          for k, m in sl["by_month"].items()],
        "", "## By crop share (tercile)", "",
        *[f"- {k}: PR-AUC {m['pr_auc'] or float('nan'):.3f}, base rate {m['base_rate']:.3f}"
          for k, m in sl["by_crop_fraction_tercile"].items()],
        "", f"## Case study {case_year} (year left out of training)", "",
        "| Month | observed | predicted | usual year |", "|---|---|---|---|",
        *[f"| {m} | {r.observed:.3f} | {r.predicted:.3f} | {r.climatology:.3f} |"
          for m, r in case_monthly.iterrows()],
        "", "## Plain-language bands at 0.10 / 0.25 (holdout share)", "",
        *[f"- {k}: {v:.3f}" for k, v in shares.items()],
        "", "## Top features (mean gain)", "",
        *[f"- {k}: {v:,.0f}" for k, v in gain.head(12).items()],
    ]
    (reports / "metrics.md").write_text(ev.metrics_markdown(table, extra))

    card = {
        "model_details": {"name": "AgroLens crop-stress risk", "version": bundle["version"],
                          "kind": bundle["kind"], "contract_version": CONTRACT_VERSION,
                          "trained_at": bundle["trained_at"], "git_sha": bundle["git_sha"],
                          "algorithm": "LightGBM binary, 5 year-grouped CV members, isotonic calibration"
                          if ship_lgbm else "logistic regression on 5 standardised features"},
        "intended_use": "Decision support for crop-rotation planning on Irish farmland: how often a "
                        "month shows vegetation stress at this place. Not a field measurement.",
        "out_of_scope": ["regions outside the Republic of Ireland / Northern Ireland pilot",
                         "single-field yield prediction", "insurance or credit decisions"],
        "factors": ["calendar month", "land-cover mix (crop_fraction)", "region (50-km blocks)"],
        "metrics": {"holdout": table, "cv_oof": cv, "acceptance": {
            "rule": "LGBM-calibrated beats B0 and B1 on holdout PR-AUC and Brier",
            "lgbm_passed": bool(ship_lgbm), "shipped_kind": bundle["kind"]}},
        "evaluation_data": {"holdout_years": hold_years, "holdout_kind": hold_kind, "rows": len(ho)},
        "training_data": {
            "years": train_years, "rows": len(tr), "cells": int(tr["cell_id"].nunique()),
            "label": "MODIS MOD13Q1 NDVI monthly max composite, cell mean over farmed pixels; "
                     "stress = NDVI anomaly z <= -1 vs the 2001-2020 same-month baseline",
            "features": "NASA POWER daily weather (lag 1-3 months), FAO-56 ET0 water balance, "
                        "SoilGrids 0-30 cm, SRTM terrain, EPA/Teagasc soil drainage, MCD12Q1 land cover"},
        "quantitative_analyses": {"slices": sl, "spatial": spatial,
                                  "case_study": {"year": case_year,
                                                 "monthly": case_monthly.round(4).to_dict("index")},
                                  "reliability": curves},
        "ethical_considerations": [
            "Over-reliance: the tool supports, not replaces, the farmer's and adviser's judgement.",
            "Coarse 5 km cells cannot see a single field."],
        "caveats": [
            "Cloud gaps reduce NDVI quality (only good/marginal MODIS pixels used).",
            "Grass cutting and grazing lower NDVI without real stress (see crop_fraction slices).",
            "NASA POWER weather is coarse (~50 km).",
            "MODIS Terra/Aqua are near end of mission; a VIIRS hand-over is future work.",
            "SMAP soil-moisture features are empty in this version.",
            *([] if hold_kind == "final" else
              ["DEV RUN: final holdout years were not labelled yet; do not ship."])],
        "plain_thresholds": {"low_lt": ev.PLAIN_LOW_LT, "high_ge": ev.PLAIN_HIGH_GE,
                             "base_rate": float(tr["y"].mean()), "band_shares": shares},
        "plain_language_note": (
            "This shows how often, in past years, crops and grass at places like yours looked "
            "stressed from space in each month, and what the weather was doing before. It is a "
            "guide for planning, not a measurement of your field."),
    }
    (out / "model_card.json").write_text(json.dumps(card, indent=2, default=float) + "\n")
    write_sha256sums(out, ["bundle.joblib", "model_card.json", "example.json"])

    manifest_path = processed / "_MANIFEST.json"
    if manifest_path.exists():
        man = json.loads(manifest_path.read_text())
        man |= {"ml_version": bundle["version"], "feature_names_sha256": feature_names_sha256()}
        manifest_path.write_text(json.dumps(man, indent=2) + "\n")
    if hold_kind == "final":
        (artifacts / "CURRENT").write_text(out.name + "\n")
    return {"table": table, "shipped": bundle["kind"], "holdout_kind": hold_kind, "out": out}
