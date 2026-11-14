"""FEATURE_NAMES and build_feature_row (brief §8.3).

Task-05 SHELL: real signature and the no-leakage rule, simple lag-1 internals. Task 12 replaces the
internals (z-anomalies, climatology, IMERG, SMAP percentile) behind the same signature.
Hard rule 2: a feature for target month m only uses rows with month < m.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

# Owned by ML; may change without a contract bump (D22). Draft from brief §8.3.
FEATURE_NAMES: tuple[str, ...] = (
    # calendar
    "month_sin",
    "month_cos",
    # water balance
    "p_minus_et0_l1",
    "p_minus_et0_3m_l1",
    "p_minus_et0_l1_z",
    "p_minus_et0_3m_l1_z",
    # precipitation
    "precip_l1",
    "imerg_l1",
    "heavy_rain_days_l1",
    "dry_spell_max_l1",
    # temperature
    "t2m_l1",
    "tmax_l1",
    "tmin_l1",
    "t2m_l1_z",
    "tmax_l1_z",
    "tmin_l1_z",
    "gdd5_l1",
    "hot_days_l1",
    "frost_days_l1",
    # soil moisture
    "gwetroot_l1",
    "gwettop_l1",
    "smap_rzsm_l1",
    "smap_pct_l1",
    # vegetation memory
    "ndvi_z_l1",
    "ndvi_z_l2",
    # climatology of the target month
    "clim_precip_m",
    "clim_tmax_m",
    "clim_et0_m",
    # static
    "elev_m",
    "slope_deg",
    "clay",
    "sand",
    "soc",
    "ph",
    "drainage_class",
    "ag_fraction",
)

# feature <- monthly_history column, taken from month m-1
LAG1_FROM_MONTHLY: dict[str, str] = {
    "p_minus_et0_l1": "p_minus_et0",
    "precip_l1": "precip",
    "heavy_rain_days_l1": "heavy_rain_days",
    "dry_spell_max_l1": "dry_spell_max",
    "t2m_l1": "t2m",
    "tmax_l1": "tmax",
    "tmin_l1": "tmin",
    "gdd5_l1": "gdd5",
    "hot_days_l1": "hot_days",
    "frost_days_l1": "frost_days",
    "gwetroot_l1": "gwetroot",
    "gwettop_l1": "gwettop",
    "smap_rzsm_l1": "sm_rootzone",
    "ndvi_z_l1": "ndvi_z",
}

# feature <- cell_static key
STATIC_FROM_CELL: dict[str, str] = {
    "elev_m": "elev_m",
    "slope_deg": "slope_deg",
    "clay": "clay",
    "sand": "sand",
    "soc": "soc",
    "ph": "phh2o",
    "drainage_class": "drainage_class",
    "ag_fraction": "ag_fraction",
}


def month_angle(month: int | np.ndarray) -> float | np.ndarray:
    """Calendar month (1..12) -> angle on the unit circle; month_sin/cos = sin/cos of this."""
    return 2.0 * np.pi * (np.asarray(month) - 1) / 12.0


def month_from_sin_cos(s: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Inverse of month_angle (vectorised). NaN in -> NaN out."""
    ang = np.arctan2(np.asarray(s, dtype=float), np.asarray(c, dtype=float))
    return np.mod(np.round(ang * 12.0 / (2.0 * np.pi)), 12) + 1


def _to_float(value) -> float:
    if value is None:
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _month_index(monthly_history: pd.DataFrame) -> pd.PeriodIndex:
    months = monthly_history["month"]
    if isinstance(months.dtype, pd.PeriodDtype):
        return pd.PeriodIndex(months)
    return pd.PeriodIndex(pd.to_datetime(months.astype(str)), freq="M")


def build_feature_row(
    cell_static: dict, monthly_history: pd.DataFrame, target_month: pd.Period
) -> dict:
    """Feature row for one cell and one target month; keys == FEATURE_NAMES, values float.

    Only rows with month < target_month are read (hard rule 2).
    """
    target = pd.Period(target_month, freq="M")
    row = dict.fromkeys(FEATURE_NAMES, math.nan)

    ang = month_angle(target.month)
    row["month_sin"], row["month_cos"] = float(np.sin(ang)), float(np.cos(ang))

    if monthly_history is not None and len(monthly_history):
        idx = _month_index(monthly_history)
        past = monthly_history.loc[np.asarray(idx < target)]  # <- the leakage guard
        past_idx = idx[np.asarray(idx < target)]
        by_month = {p: i for i, p in enumerate(past_idx)}

        def value_at(lag: int, col: str) -> float:
            pos = by_month.get(target - lag)
            if pos is None or col not in past.columns:
                return math.nan
            return _to_float(past.iloc[pos][col])

        for feat, col in LAG1_FROM_MONTHLY.items():
            row[feat] = value_at(1, col)
        row["ndvi_z_l2"] = value_at(2, "ndvi_z")
        pme = [value_at(k, "p_minus_et0") for k in (1, 2, 3)]
        row["p_minus_et0_3m_l1"] = math.nan if any(map(math.isnan, pme)) else float(sum(pme))

    for feat, key in STATIC_FROM_CELL.items():
        row[feat] = _to_float((cell_static or {}).get(key))

    return row
