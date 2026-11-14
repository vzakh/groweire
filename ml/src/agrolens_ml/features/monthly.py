"""POWER daily -> monthly aggregates (brief §8.3, §13.2).

Task-05 SHELL: every aggregate is real EXCEPT et0 / p_minus_et0 (NaN until task 12 adds FAO-56
Penman-Monteith). sm_rootzone (SMAP) and ndvi_z (MODIS) are not in POWER, so they are NaN here
and filled from the pilot tables by the training pipeline.
The SAME function builds the training table, so the backend's live path has no train/serve skew.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from agrolens_ml.config import DRY_DAY_MM, FROST_C, GDD_BASE_C, HEAVY_RAIN_MM, HOT_DAY_C
from agrolens_ml.contract import MONTHLY_INPUT_COLUMNS, POWER_DAILY_PARAMETERS

POWER_FILL = -999.0


def _daily_frame(daily: pd.DataFrame) -> pd.DataFrame:
    df = daily.copy()
    if "date" in df.columns:
        df = df.set_index(pd.to_datetime(df["date"])).drop(columns="date")
    df.index = pd.DatetimeIndex(df.index)
    missing = [p for p in POWER_DAILY_PARAMETERS if p not in df.columns]
    if missing:
        raise ValueError(f"POWER daily frame is missing parameters: {missing}")
    out = df[list(POWER_DAILY_PARAMETERS)].apply(pd.to_numeric, errors="coerce").astype(float)
    return out.mask(out <= POWER_FILL + 1e-9).sort_index()


def _longest_dry_run(precip: pd.Series, month: pd.PeriodIndex) -> pd.Series:
    dry = (precip < DRY_DAY_MM).to_numpy()  # NaN -> not dry (breaks the run)
    run_id = np.cumsum(~dry)
    runs = pd.Series(dry.astype(float)).groupby([np.asarray(month), run_id]).sum()
    return runs.groupby(level=0).max()


def power_daily_to_monthly(daily: pd.DataFrame, elev_m: float, lat: float) -> pd.DataFrame:
    """POWER daily (POWER_DAILY_PARAMETERS, `date` column or DatetimeIndex) -> monthly_history.

    Returns one row per calendar month with exactly MONTHLY_INPUT_COLUMNS (`month` = Period[M]).
    `elev_m` and `lat` feed FAO-56 ET0 (task 12); unused by the shell.
    """
    del elev_m, lat  # used from task 12 (ET0)
    df = _daily_frame(daily)
    month = df.index.to_period("M")
    g = df.groupby(month)

    p = df["PRECTOTCORR"]
    out = pd.DataFrame(
        {
            "precip": g["PRECTOTCORR"].sum(min_count=1),
            "heavy_rain_days": (p > HEAVY_RAIN_MM).groupby(month).sum().astype(float),
            "dry_spell_max": _longest_dry_run(p, month),
            "t2m": g["T2M"].mean(),
            "tmax": g["T2M_MAX"].mean(),
            "tmin": g["T2M_MIN"].mean(),
            "hot_days": (df["T2M_MAX"] >= HOT_DAY_C).groupby(month).sum().astype(float),
            "frost_days": (df["T2M_MIN"] <= FROST_C).groupby(month).sum().astype(float),
            "gdd5": (df["T2M"] - GDD_BASE_C).clip(lower=0).groupby(month).sum(min_count=1),
            "gwetroot": g["GWETROOT"].mean(),
            "gwettop": g["GWETTOP"].mean(),
        }
    )
    out["et0"] = np.nan  # TODO(task 12): FAO-56 Penman-Monteith
    out["p_minus_et0"] = np.nan  # TODO(task 12): precip - et0
    out["sm_rootzone"] = np.nan  # SMAP, pilot tables only
    out["ndvi_z"] = np.nan  # MODIS, pilot tables only
    out.index = pd.PeriodIndex(out.index, freq="M")
    out = out.rename_axis("month").reset_index()
    return out[list(MONTHLY_INPUT_COLUMNS)]
