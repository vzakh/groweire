"""Training-side POWER processing: power_daily.parquet -> monthly history per POWER node.

Calls the SAME power_daily_to_monthly the backend uses on its live path (no train/serve skew).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from agrolens_ml.features.monthly import power_daily_to_monthly
from agrolens_ml.io.power import node_metadata


def build_power_monthly(daily: pd.DataFrame, nodes: pd.DataFrame) -> pd.DataFrame:
    """daily: power_daily.parquet rows; nodes: index node_id, columns lat, elev_m."""
    parts = []
    for node_id, frame in daily.groupby("node_id", sort=True):
        meta = nodes.loc[node_id]
        monthly = power_daily_to_monthly(frame, elev_m=meta["elev_m"], lat=meta["lat"])
        parts.append(monthly.assign(node_id=node_id))
    out = pd.concat(parts, ignore_index=True)
    return out[["node_id", *[c for c in out.columns if c != "node_id"]]]


def run(processed: Path, raw: Path) -> Path:
    daily = pd.read_parquet(processed / "power_daily.parquet")
    nodes = node_metadata(raw / "power")
    monthly = build_power_monthly(daily, nodes)
    out = processed / "power_monthly.parquet"
    monthly.assign(month=monthly["month"].astype(str)).to_parquet(out, index=False)
    nodes.to_csv(processed / "power_nodes.csv")
    return out
