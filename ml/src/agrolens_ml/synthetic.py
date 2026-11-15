"""Seeded, schema-exact synthetic tables for parallel development (brief §13.2, task 05).

Uses the REAL 0.05° grid geometry (grid_005deg.csv) and the exact schemas.py schemas, with seeded
random values in plausible Irish ranges. NOT data: every value is invented, and the manifest says
`source: "synthetic"`. risk_grid is produced by running the stub over the synthetic feature rows,
so the two always agree.

    python -m agrolens_ml.synthetic [--grid ml/config/grid_005deg.csv] [--out data/synthetic]
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from agrolens_ml.config import (
    MIN_VALID_FRAC,
    MONTHS,
    RISK_EXAMPLE_YEARS,
    RISK_RECENT_YEARS,
    STRESS_Z,
)
from agrolens_ml.contract import CONTRACT_VERSION, RISK_TYPES
from agrolens_ml.features.build import FEATURE_NAMES, STATIC_FROM_CELL, month_angle
from agrolens_ml.model.stub import STUB_VERSION, StubModel, stub_stress_types
from agrolens_ml.schemas import (
    CELL_MONTH_SCHEMA,
    GRID_CELLS_SCHEMA,
    RISK_COUNTS_SCHEMA,
    RISK_GRID_SCHEMA,
    feature_names_sha256,
)

YEARS = (2022, 2023, 2024, 2025)
HALF_CELL_DEG = 0.025
DAYS_PER_MONTH = 30.4

# Rough monthly means for Irish lowlands, ONLY to make synthetic values look plausible (index 1..12).
_T2M = np.array([np.nan, 5.5, 6, 6.5, 8.5, 11, 13.5, 15.5, 15, 13, 10.5, 7.5, 6])[0:13]
_PRECIP = np.array([np.nan, 100, 75, 75, 65, 65, 70, 70, 85, 85, 110, 105, 110])
_ET0 = np.array([np.nan, 8, 15, 28, 48, 75, 85, 85, 70, 45, 22, 10, 6])


def _write(df: pd.DataFrame, schema: pa.Schema, path: Path) -> None:
    for field in schema:
        if pa.types.is_float32(field.type):
            df[field.name] = df[field.name].astype("float32")
    table = pa.Table.from_pandas(df[schema.names], schema=schema, preserve_index=False)
    pq.write_table(table, path)


def _grid_cells(grid: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = len(grid)
    lon, lat = grid["lon"].to_numpy(), grid["lat"].to_numpy()
    x0, x1, y0, y1 = (
        lon - HALF_CELL_DEG,
        lon + HALF_CELL_DEG,
        lat - HALF_CELL_DEG,
        lat + HALF_CELL_DEG,
    )
    geom = [
        f"POLYGON (({a:.3f} {c:.3f}, {b:.3f} {c:.3f}, {b:.3f} {d:.3f}, {a:.3f} {d:.3f}, {a:.3f} {c:.3f}))"
        for a, b, c, d in zip(x0, x1, y0, y1)
    ]
    ag = rng.uniform(0.3, 1.0, n)
    drainage = pd.array(rng.integers(1, 6, n), dtype="Int8")
    drainage[rng.random(n) < 0.15] = pd.NA  # e.g. Northern Ireland: no Irish SIS class
    return pd.DataFrame(
        {
            "cell_id": grid["cell_id"].astype(str),
            "geom": geom,
            "lat": lat,
            "lon": lon,
            "elev_m": np.clip(rng.gamma(2.0, 50.0, n), 0, 600),
            "slope_deg": np.clip(rng.gamma(1.5, 1.5, n), 0, 20),
            "clay": rng.uniform(12, 35, n),
            "sand": rng.uniform(25, 60, n),
            "soc": rng.uniform(20, 90, n),
            "phh2o": rng.uniform(5.0, 7.3, n),
            "bdod": rng.uniform(0.9, 1.4, n),
            "drainage_class": drainage,
            "ag_fraction": ag,
            "crop_fraction": ag * rng.uniform(0.0, 0.6, n),
            "arable_fraction": np.full(n, np.nan),
        }
    )


def _cell_month(cells: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Monthly series Jan(YEARS[0]-1) .. Dec(YEARS[-1]) per cell, then rows for Mar-Oct of YEARS."""
    n = len(cells)
    periods = pd.period_range(f"{YEARS[0] - 1}-01", f"{YEARS[-1]}-12", freq="M")
    t_n = len(periods)
    cal = periods.month.to_numpy()  # (T,)

    wet = 1.0 + 0.35 * ((-cells["lon"].to_numpy() - 6.0) / 4.7)  # west is wetter
    a_p, a_t, a_e, a_n = (rng.standard_normal((n, t_n)) for _ in range(4))  # anomalies (z)
    precip = np.clip(_PRECIP[cal] * wet[:, None] * (1 + 0.35 * a_p), 0, None)
    t2m = _T2M[cal][None, :] + 1.0 * a_t - 0.006 * cells["elev_m"].to_numpy()[:, None]
    tmax = t2m + 4.5 + 0.5 * rng.standard_normal((n, t_n))
    tmin = t2m - 4.0 + 0.5 * rng.standard_normal((n, t_n))
    et0 = np.clip(_ET0[cal][None, :] * (1 + 0.12 * a_e), 0, None)
    pme = precip - et0
    pme_sd = np.sqrt((0.35 * _PRECIP[cal] * wet[:, None]) ** 2 + (0.12 * _ET0[cal]) ** 2)
    pme_z = (pme - (_PRECIP[cal] * wet[:, None] - _ET0[cal])) / pme_sd
    gwetroot = np.clip(0.78 + 0.08 * np.tanh(pme_z) - 0.004 * (t2m - 10), 0.3, 1.0)
    gwettop = np.clip(gwetroot - 0.05 + 0.05 * rng.standard_normal((n, t_n)), 0.2, 1.0)
    sm_root = np.clip(0.32 + 0.06 * np.tanh(pme_z), 0.1, 0.5)
    smap_pct = np.clip(50 + 30 * np.tanh(pme_z), 0, 100)
    ndvi_z = 0.6 * a_n + 0.4 * np.tanh(pme_z)
    ndvi = np.clip(0.72 + 0.06 * ndvi_z, 0.2, 0.95)
    valid = rng.uniform(0.1, 1.0, (n, t_n))
    heavy = rng.poisson(np.clip(precip / 60.0, 0, None)).astype(float)
    dry = np.clip(np.round(14 - precip / 8 + 2 * rng.standard_normal((n, t_n))), 0, 31)
    hot = rng.poisson(np.clip(tmax - 19.0, 0, None) * 0.5).astype(float)
    frost = rng.poisson(np.clip(4.0 - tmin, 0, None) * 1.5).astype(float)
    gdd5 = np.clip(t2m - 5.0, 0, None) * DAYS_PER_MONTH

    # target rows: Mar-Oct of YEARS
    t_idx = np.array([i for i, p in enumerate(periods) if p.year in YEARS and p.month in MONTHS])
    ci = np.repeat(np.arange(n), len(t_idx))
    ti = np.tile(t_idx, n)
    l1, l2, l3 = ti - 1, ti - 2, ti - 3
    m = cal[ti]
    ang = month_angle(m)

    feat = {
        "month_sin": np.sin(ang),
        "month_cos": np.cos(ang),
        "p_minus_et0_l1": pme[ci, l1],
        "p_minus_et0_3m_l1": pme[ci, l1] + pme[ci, l2] + pme[ci, l3],
        "p_minus_et0_l1_z": pme_z[ci, l1],
        "p_minus_et0_3m_l1_z": (pme_z[ci, l1] + pme_z[ci, l2] + pme_z[ci, l3]) / np.sqrt(3),
        "precip_l1": precip[ci, l1],
        "imerg_l1": precip[ci, l1] * rng.uniform(0.85, 1.15, len(ci)),
        "heavy_rain_days_l1": heavy[ci, l1],
        "dry_spell_max_l1": dry[ci, l1],
        "t2m_l1": t2m[ci, l1],
        "tmax_l1": tmax[ci, l1],
        "tmin_l1": tmin[ci, l1],
        "t2m_l1_z": a_t[ci, l1],
        "tmax_l1_z": a_t[ci, l1] + 0.3 * rng.standard_normal(len(ci)),
        "tmin_l1_z": a_t[ci, l1] + 0.3 * rng.standard_normal(len(ci)),
        "gdd5_l1": gdd5[ci, l1],
        "hot_days_l1": hot[ci, l1],
        "frost_days_l1": frost[ci, l1],
        "gwetroot_l1": gwetroot[ci, l1],
        "gwettop_l1": gwettop[ci, l1],
        "smap_rzsm_l1": sm_root[ci, l1],
        "smap_pct_l1": smap_pct[ci, l1],
        "ndvi_z_l1": ndvi_z[ci, l1],
        "ndvi_z_l2": ndvi_z[ci, l2],
        "clim_precip_m": _PRECIP[m] * wet[ci],
        "clim_tmax_m": _T2M[m] + 4.5,
        "clim_et0_m": _ET0[m],
    }
    for feature, key in STATIC_FROM_CELL.items():
        feat[feature] = cells[key].to_numpy(dtype=float, na_value=np.nan)[ci]

    label = pd.array(ndvi_z[ci, ti] <= STRESS_Z, dtype="boolean")
    label[valid[ci, ti] < MIN_VALID_FRAC] = pd.NA
    fixed = {
        "cell_id": cells["cell_id"].to_numpy()[ci],
        "month": periods[ti].strftime("%Y-%m"),
        "ndvi": ndvi[ci, ti],
        "ndvi_z": ndvi_z[ci, ti],
        "stress_label": label,
        "valid_frac": valid[ci, ti],
        "precip": precip[ci, ti],
        "et0": et0[ci, ti],
        "p_minus_et0": pme[ci, ti],
        "t2m": t2m[ci, ti],
        "sm_rootzone": sm_root[ci, ti],
    }
    assert set(feat) == set(FEATURE_NAMES), set(FEATURE_NAMES) ^ set(feat)
    return pd.DataFrame({**fixed, **{f: feat[f] for f in FEATURE_NAMES}})


def _sen_slope_per_year(p: np.ndarray, years: np.ndarray) -> np.ndarray:
    """Median of pairwise slopes along the last axis (Sen's slope), per year."""
    i, j = np.triu_indices(len(years), k=1)
    slopes = (p[..., j] - p[..., i]) / (years[j] - years[i])
    return np.median(slopes, axis=-1)


def _risk_grid(cm: pd.DataFrame, model: StubModel) -> pd.DataFrame:
    X = cm[list(FEATURE_NAMES)].astype(float)
    core = model.predict_frame(X)
    df = pd.DataFrame(
        {
            "cell_id": cm["cell_id"].to_numpy(),
            "calendar_month": cm["month"].str[5:7].astype(int).to_numpy(),
            "year": cm["month"].str[:4].astype(int).to_numpy(),
            "p": core["probability"].to_numpy(),
            "lo": core["lo"].to_numpy(),
            "hi": core["hi"].to_numpy(),
        }
    )
    agg = df.groupby(["cell_id", "calendar_month"], sort=True).agg(
        p_mean_10y=("p", "mean"), p_lo=("lo", "mean"), p_hi=("hi", "mean")
    )
    yearly = df.pivot_table(index=["cell_id", "calendar_month"], columns="year", values="p")
    years = yearly.columns.to_numpy(dtype=float)
    agg["trend_per_decade"] = (
        _sen_slope_per_year(yearly.to_numpy(), years)[yearly.index.get_indexer(agg.index)] * 10.0
    )
    agg = agg.reset_index()
    agg["dominant_type"] = [stub_stress_types(int(mo))[0] for mo in agg["calendar_month"]]
    agg["calendar_month"] = agg["calendar_month"].astype("int8")
    return agg


# Invented years-hit out of 25 per stress type and month, ONLY to drive layouts and tests.
_COUNT_YEARS = np.arange(2001, 2026)
_COUNT_BASE = {
    "drought": {6: 3, 7: 6, 8: 3},
    "waterlogging": {3: 5, 9: 2, 10: 7},
    "heat": {7: 2},
    "frost": {3: 15, 4: 8, 5: 2},
}


def _risk_counts(cells: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    total = len(_COUNT_YEARS)
    for cell_id in cells["cell_id"]:
        for month in MONTHS:
            for stress_type in RISK_TYPES:
                base = _COUNT_BASE[stress_type].get(month, 0)
                hit = int(np.clip(base + rng.integers(-1, 2), 0, total)) if base else 0
                years = np.sort(rng.choice(_COUNT_YEARS, size=hit, replace=False))[::-1]
                recent = int((years > _COUNT_YEARS[-1] - RISK_RECENT_YEARS).sum())
                rows.append(
                    {
                        "cell_id": cell_id,
                        "calendar_month": month,
                        "stress_type": stress_type,
                        "years_hit": hit,
                        "years_total": total,
                        "frequency": hit / total,
                        "recent_frequency": recent / RISK_RECENT_YEARS,
                        "example_years": [int(y) for y in years[:RISK_EXAMPLE_YEARS]],
                    }
                )
    return pd.DataFrame(rows)


def make_synthetic_tables(grid_csv: str | Path, out_dir: str | Path, seed: int = 7) -> Path:
    """Write grid_cells, cell_month_features, risk_grid, risk_counts + _MANIFEST.json to out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    grid = pd.read_csv(grid_csv, dtype={"cell_id": str})

    cells = _grid_cells(grid, rng)
    cm = _cell_month(cells, rng)
    risk = _risk_grid(cm, StubModel())

    _write(cells, GRID_CELLS_SCHEMA, out / "grid_cells.parquet")
    _write(cm, CELL_MONTH_SCHEMA, out / "cell_month_features.parquet")
    _write(risk, RISK_GRID_SCHEMA, out / "risk_grid.parquet")
    counts = _risk_counts(cells, np.random.default_rng(seed + 1))
    _write(counts, RISK_COUNTS_SCHEMA, out / "risk_counts.parquet")

    manifest = {
        "source": "synthetic",
        "contract_version": CONTRACT_VERSION,
        "feature_names_sha256": feature_names_sha256(FEATURE_NAMES),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "ml_version": STUB_VERSION,
        "seed": seed,
        "years": list(YEARS),
        "rows": {
            "grid_cells": len(cells),
            "cell_month_features": len(cm),
            "risk_grid": len(risk),
            "risk_counts": len(counts),
        },
    }
    (out / "_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--grid", default="ml/config/grid_005deg.csv")
    ap.add_argument("--out", default="data/synthetic")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    t0 = time.perf_counter()
    out = make_synthetic_tables(args.grid, args.out, args.seed)
    rows = json.loads((out / "_MANIFEST.json").read_text())["rows"]
    print(f"wrote {out}/ {rows} in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
