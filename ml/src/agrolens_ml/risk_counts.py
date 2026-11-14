"""Counted monthly risks from NASA POWER daily weather (PLAN_40 tasks 41-42).

"In N of the last 25 years, July was too dry here": for every calendar month and stress type we
count the years in which an ABSOLUTE rule fired. Rules and their sources live in config.py:

  drought       >= RISK_MIN_DAYS days with soil moisture deficit (SMD) > DRY_DAY_SMD_MM
  waterlogging  >= RISK_MIN_DAYS days with SMD < WET_DAY_SMD_MM (water above field capacity)
  heat          >= HEAT_MIN_HOT_DAYS days with T2M_MAX >= HOT_DAY_C
  frost         >= FROST_MIN_DAYS days with T2M_MIN <= FROST_C, in FROST_MONTHS only

SMD is the Met Éireann hybrid model (Schulte et al. 2005), run daily on rain and our FAO-56 ET0
for the grass reference. Weather comes from the POWER node (about 50 km). In the pilot, each
cell's daily rain is scaled to its NASA GPM IMERG monthly total (about 10 km), because POWER rain
flattens Ireland's wet west / drier east. The soil drainage class also differs per cell.

One code path serves the pilot table (build_risk_counts) and a live point (count_risks).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from agrolens_ml import config
from agrolens_ml.contract import CONTRACT_VERSION, RISK_RULES_VERSION, RISK_TYPES
from agrolens_ml.features.monthly import power_daily_with_et0
from agrolens_ml.schemas import RISK_COUNTS_SCHEMA

DAY_COLUMNS = {
    "drought": "dry_days",
    "waterlogging": "wet_days",
    "heat": "hot_days",
    "frost": "frost_days",
}
IMERG_FILE = "imerg_cell_month.parquet"  # cell_id, month "YYYY-MM", precip_mm (20_imerg.py)
COUNT_COLUMNS = [f.name for f in RISK_COUNTS_SCHEMA if f.name != "cell_id"]


def smd_class(drainage_class) -> str:
    """Met Éireann drainage class for our 1..5 ordinal; unknown -> SMD_CLASS_UNKNOWN."""
    try:
        if drainage_class is None or pd.isna(drainage_class):
            return config.SMD_CLASS_UNKNOWN
        return config.SMD_CLASS_OF_DRAINAGE.get(int(drainage_class), config.SMD_CLASS_UNKNOWN)
    except (TypeError, ValueError):
        return config.SMD_CLASS_UNKNOWN


def simulate_smd(rain, et0, klass: str, smd0: float = 0.0) -> np.ndarray:
    """Daily soil moisture deficit [mm] for one drainage class (Met Éireann hybrid model).

    rain, et0: daily mm (NaN counts as 0). Starts at field capacity (smd0 = 0), which holds for
    a series that starts in an Irish winter.
    """
    p = config.SMD_CLASSES[klass]
    smd_min, smd_c, drain_max = p["smd_min"], p["smd_c"], p["drain_max"]
    rain = np.nan_to_num(np.asarray(rain, dtype=float))
    et0 = np.nan_to_num(np.asarray(et0, dtype=float))
    out = np.empty(len(rain))
    prev = float(smd0)
    for i, (r, pe) in enumerate(zip(rain, et0)):
        eta = pe if prev <= smd_c else pe * (config.SMD_MAX_MM - prev) / (config.SMD_MAX_MM - smd_c)
        drain = drain_max * (prev / config.SMD_SATURATED_MM) if prev < 0 else 0.0
        prev = min(max(prev - r + eta + drain, smd_min), config.SMD_MAX_MM)
        out[i] = prev
    return out


def monthly_day_counts(daily_et0: pd.DataFrame, klass: str) -> pd.DataFrame:
    """Per (year, month): dry / wet / hot / frost day counts, for months with enough data.

    daily_et0: output of power_daily_with_et0 (DatetimeIndex, POWER columns + ET0).
    """
    df = daily_et0
    smd = simulate_smd(df["PRECTOTCORR"], df["ET0"], klass)
    needed = df[["PRECTOTCORR", "ET0", "T2M_MAX", "T2M_MIN"]]
    days = pd.DataFrame(
        {
            "year": df.index.year,
            "month": df.index.month,
            "dry_days": smd > config.DRY_DAY_SMD_MM,
            "wet_days": smd < config.WET_DAY_SMD_MM,
            "hot_days": (df["T2M_MAX"] >= config.HOT_DAY_C).to_numpy(),
            "frost_days": (df["T2M_MIN"] <= config.FROST_C).to_numpy(),
            "present": needed.notna().all(axis=1).to_numpy(),
        }
    )
    out = days.groupby(["year", "month"], as_index=False).sum()
    in_month = pd.PeriodIndex.from_fields(year=out["year"], month=out["month"], freq="M")
    complete = out["present"] >= in_month.days_in_month - config.RISK_MAX_MISSING_DAYS
    return out[complete.to_numpy()].drop(columns="present").reset_index(drop=True)


def monthly_hits(day_counts: pd.DataFrame, min_days: int = config.RISK_MIN_DAYS) -> pd.DataFrame:
    """Long table (year, month, stress_type, days, hit): did the rule fire in that month?"""
    parts = []
    for stress_type in RISK_TYPES:
        days = day_counts[DAY_COLUMNS[stress_type]].astype(int)
        if stress_type == "heat":
            hit = days >= config.HEAT_MIN_HOT_DAYS
        elif stress_type == "frost":
            hit = (days >= config.FROST_MIN_DAYS) & day_counts["month"].isin(config.FROST_MONTHS)
        else:
            hit = days >= min_days
        parts.append(
            pd.DataFrame(
                {
                    "year": day_counts["year"],
                    "month": day_counts["month"],
                    "stress_type": stress_type,
                    "days": days,
                    "hit": hit,
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def count_hits(hits: pd.DataFrame) -> pd.DataFrame:
    """Hits -> one row per (calendar_month in MONTHS, stress_type) with COUNT_COLUMNS."""
    rows = []
    hits = hits[hits["month"].isin(config.MONTHS)]
    for (month, stress_type), g in hits.groupby(["month", "stress_type"], sort=True):
        g = g.sort_values("year")
        recent = g.tail(config.RISK_RECENT_YEARS)
        worst = g[g["hit"]].sort_values(["days", "year"], ascending=False)
        total = len(g)
        rows.append(
            {
                "calendar_month": int(month),
                "stress_type": stress_type,
                "years_hit": int(g["hit"].sum()),
                "years_total": total,
                "frequency": float(g["hit"].mean()) if total else np.nan,
                "recent_frequency": float(recent["hit"].mean()) if total else np.nan,
                "example_years": [int(y) for y in worst["year"].head(config.RISK_EXAMPLE_YEARS)],
            }
        )
    return pd.DataFrame(rows, columns=COUNT_COLUMNS)


def scale_rain_to_monthly(daily_et0: pd.DataFrame, monthly_rain_mm: pd.Series) -> pd.DataFrame:
    """Scale daily rain so each month's total matches `monthly_rain_mm` (index "YYYY-MM", mm).

    POWER rain is a model average over about 50 km: it keeps the day-to-day pattern but flattens
    Ireland's wet west / drier east. GPM IMERG monthly totals (about 10 km, gauge-adjusted) put
    the amounts right. Months without a total, or with almost no POWER rain, keep POWER as it is.
    """
    df = daily_et0.copy()
    month = df.index.strftime("%Y-%m")
    power = df["PRECTOTCORR"].groupby(month).sum()
    target = pd.to_numeric(monthly_rain_mm.reindex(power.index), errors="coerce")
    ratio = (target / power.where(power >= config.RAIN_SCALE_MIN_MONTH_MM)).clip(
        config.RAIN_SCALE_MIN, config.RAIN_SCALE_MAX
    )
    df["PRECTOTCORR"] = df["PRECTOTCORR"].to_numpy() * ratio.fillna(1.0).reindex(month).to_numpy()
    return df


def count_risks(
    daily: pd.DataFrame,
    elev_m: float,
    lat: float,
    drainage_class,
    monthly_rain_mm: pd.Series | None = None,
) -> pd.DataFrame:
    """Counted risks for one point from POWER daily data (the live path uses exactly this).

    `monthly_rain_mm` (optional, index "YYYY-MM"): monthly rain totals the daily rain is scaled
    to, as the pilot table does with GPM IMERG. A live point outside the pilot has none.
    """
    df = power_daily_with_et0(daily, elev_m, lat)
    if monthly_rain_mm is not None:
        df = scale_rain_to_monthly(df, monthly_rain_mm)
    return count_hits(monthly_hits(monthly_day_counts(df, smd_class(drainage_class))))


def imerg_monthly(processed: Path) -> pd.DataFrame | None:
    """IMERG monthly rain, months x cells (mm), or None when the file is not there."""
    path = processed / IMERG_FILE
    if not path.exists():
        return None
    table = pd.read_parquet(path, columns=["cell_id", "month", "precip_mm"])
    return table.pivot(index="month", columns="cell_id", values="precip_mm")


def build_cell_hits(processed: Path, min_days: int = config.RISK_MIN_DAYS) -> pd.DataFrame:
    """Hits per cell (cell_id, year, month, stress_type, days, hit).

    Weather is the cell's POWER node; with imerg_cell_month.parquet present, the rain of every
    cell is scaled to its own IMERG monthly totals. Without it, cells that share a node and a
    drainage class share one series.
    """
    daily = pd.read_parquet(processed / "power_daily.parquet")
    nodes = pd.read_csv(processed / "power_nodes.csv").set_index("node_id")
    imerg = imerg_monthly(processed)
    with_et0 = {
        node_id: power_daily_with_et0(
            frame, elev_m=nodes.loc[node_id, "elev_m"], lat=nodes.loc[node_id, "lat"]
        )
        for node_id, frame in daily.groupby("node_id", sort=True)
    }
    shared: dict[tuple[str, str], pd.DataFrame] = {}
    parts = []
    for cell in cell_series(processed).itertuples():
        df = with_et0[cell.node_id]
        if imerg is not None and cell.cell_id in imerg.columns:
            df = scale_rain_to_monthly(df, imerg[cell.cell_id])
            hits = monthly_hits(monthly_day_counts(df, cell.smd_class), min_days)
        else:
            key = (cell.node_id, cell.smd_class)
            if key not in shared:
                shared[key] = monthly_hits(monthly_day_counts(df, cell.smd_class), min_days)
            hits = shared[key]
        parts.append(hits.assign(cell_id=cell.cell_id))
    return pd.concat(parts, ignore_index=True)


def cell_series(processed: Path) -> pd.DataFrame:
    """cell_id -> (node_id, smd_class): which weather series a cell reads."""
    cells = pd.read_parquet(processed / "grid_cells.parquet", columns=["cell_id", "drainage_class"])
    link = pd.read_csv(processed / "cell_to_power_node.csv")
    cells = cells.merge(link, on="cell_id", how="left", validate="one_to_one")
    if cells["node_id"].isna().any():
        raise ValueError("grid cells without a POWER node in cell_to_power_node.csv")
    cells["smd_class"] = cells["drainage_class"].map(smd_class)
    return cells[["cell_id", "node_id", "smd_class"]]


def build_risk_counts(processed: Path) -> pd.DataFrame:
    """risk_counts table: one row per cell x calendar month x stress type."""
    hits = build_cell_hits(processed)
    out = pd.concat(
        [
            count_hits(g).assign(cell_id=cell_id)
            for cell_id, g in hits.groupby("cell_id", sort=True)
        ],
        ignore_index=True,
    )
    out = out.sort_values(["cell_id", "calendar_month", "stress_type"]).reset_index(drop=True)
    return out[[f.name for f in RISK_COUNTS_SCHEMA]]


def write_risk_counts(processed: Path) -> Path:
    out = build_risk_counts(processed)
    path = processed / "risk_counts.parquet"
    pq.write_table(pa.Table.from_pandas(out, schema=RISK_COUNTS_SCHEMA, preserve_index=False), path)
    _stamp_manifest(processed, len(out))
    return path


def _stamp_manifest(processed: Path, rows: int) -> None:
    """The folder now holds a contract-2.0 table set: say so in its manifest."""
    path = processed / "_MANIFEST.json"
    if not path.exists():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["contract_version"] = CONTRACT_VERSION
    manifest["risk_rules_version"] = RISK_RULES_VERSION
    has_imerg = (processed / IMERG_FILE).exists()
    manifest["rain_source"] = "power_scaled_to_imerg_monthly" if has_imerg else "power"
    manifest.setdefault("rows", {})["risk_counts"] = rows
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
