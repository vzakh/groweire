"""Pipeline steps that assemble the real data products (PLAN_10 tasks 11-12).

labels    AppEEARS NDVI NetCDFs -> data/processed/ndvi_cell_month.parquet + labels summary
features  power_monthly + ndvi + grid -> data/processed/cell_month_features.parquet + manifest
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from agrolens_ml.contract import CONTRACT_VERSION, MONTHLY_INPUT_COLUMNS
from agrolens_ml.features.build import FEATURE_NAMES, build_feature_table
from agrolens_ml.schemas import CELL_MONTH_SCHEMA, feature_names_sha256

REPORTS = Path("ml/artifacts/reports")


def _landcover(raw: Path) -> np.ndarray:
    from pyhdf.SD import SD, SDC  # pylint: disable=import-outside-toplevel

    path = sorted((raw / "direct" / "mcd12q1").glob("*.hdf"))[-1]
    return SD(str(path), SDC.READ).select("LC_Type1").get()


def ndvi_files(raw: Path) -> list[Path]:
    """Completed AppEEARS NDVI bundles (Terra + Aqua), any year chunks."""
    out = []
    for task in sorted((raw / "appeears").glob("agrolens_M?D13Q1_*")):
        if (task / ".complete").exists():
            out += sorted(task.glob("*.nc"))
    return out


def run_labels(data: Path, log=print) -> Path:
    from agrolens_ml.labels import ndvi as L  # pylint: disable=import-outside-toplevel

    files = ndvi_files(data / "raw")
    if not files:
        raise SystemExit("no completed AppEEARS NDVI bundles yet (data/raw/appeears/*/.complete)")
    grid = pd.read_parquet(data / "processed" / "grid_cells.parquet")
    df = L.build_ndvi_table_appeears(files, grid, _landcover(data / "raw"), log=log)
    out = data / "processed" / "ndvi_cell_month.parquet"
    df.to_parquet(out, index=False)
    REPORTS.mkdir(parents=True, exist_ok=True)
    if df["stress_label"].notna().any():
        (REPORTS / "labels_summary.md").write_text(L.summary_markdown(df))
    years = sorted(df["month"].str[:4].unique())
    log(
        f"labels: {len(df):,} cell-months, years {years[0]}-{years[-1]}, "
        f"{int(df['stress_label'].notna().sum()):,} labelled"
    )
    return out


def cell_monthly_history(data: Path, ndvi: pd.DataFrame | None) -> pd.DataFrame:
    """Per-cell monthly history = its POWER node's monthly weather (+ leak-free NDVI anomaly)."""
    proc = data / "processed"
    power = pd.read_parquet(proc / "power_monthly.parquet")
    c2n = pd.read_csv(proc / "cell_to_power_node.csv", dtype=str)
    grid = pd.read_parquet(proc / "grid_cells.parquet", columns=["cell_id"])
    c2n = c2n[c2n["cell_id"].isin(grid["cell_id"])]
    hist = c2n.merge(power, on="node_id").drop(columns="node_id")
    hist = hist.drop(columns=["ndvi_z"])
    if ndvi is not None:
        hist = hist.merge(
            ndvi[["cell_id", "month", "ndvi_z_feat"]].rename(columns={"ndvi_z_feat": "ndvi_z"}),
            on=["cell_id", "month"],
            how="left",
        )
    else:
        hist["ndvi_z"] = np.nan
    hist["month"] = pd.PeriodIndex(hist["month"], freq="M")
    return hist[["cell_id", *MONTHLY_INPUT_COLUMNS]]


def run_features(data: Path, log=print) -> Path:
    proc = data / "processed"
    ndvi_path = proc / "ndvi_cell_month.parquet"
    ndvi = pd.read_parquet(ndvi_path) if ndvi_path.exists() else None
    hist = cell_monthly_history(data, ndvi)
    grid = pd.read_parquet(proc / "grid_cells.parquet").set_index("cell_id")
    feats = build_feature_table(hist, grid)
    feats["month"] = feats["month"].astype(str)

    fixed = hist.assign(month=hist["month"].astype(str))[
        ["cell_id", "month", "precip", "et0", "p_minus_et0", "t2m", "sm_rootzone"]
    ]
    out = feats.merge(fixed, on=["cell_id", "month"], how="left")
    if ndvi is not None:
        out = out.merge(
            ndvi[["cell_id", "month", "ndvi", "ndvi_z", "stress_label", "valid_frac"]],
            on=["cell_id", "month"],
            how="left",
        )
    else:
        out[["ndvi", "ndvi_z", "valid_frac"]] = np.nan
        out["stress_label"] = pd.array([pd.NA] * len(out), dtype="boolean")
    out["stress_label"] = out["stress_label"].astype("boolean")
    for field in CELL_MONTH_SCHEMA:
        if pa.types.is_float32(field.type):
            out[field.name] = out[field.name].astype("float32")
    path = proc / "cell_month_features.parquet"
    pq.write_table(
        pa.Table.from_pandas(
            out[CELL_MONTH_SCHEMA.names], schema=CELL_MONTH_SCHEMA, preserve_index=False
        ),
        path,
    )
    manifest = {
        "source": "real",
        "contract_version": CONTRACT_VERSION,
        "feature_names_sha256": feature_names_sha256(FEATURE_NAMES),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "ml_version": f"agrolens-ml {version('agrolens-ml')}",
        "rows": {"grid_cells": len(grid), "cell_month_features": len(out)},
        "ndvi_years": sorted(ndvi["month"].str[:4].unique().tolist()) if ndvi is not None else [],
    }
    (proc / "_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    log(
        f"features: {len(out):,} rows x {len(FEATURE_NAMES)} features, "
        f"{int(out['stress_label'].notna().sum()):,} labelled"
    )
    return path
