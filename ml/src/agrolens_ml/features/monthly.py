"""POWER daily -> monthly aggregates (brief §8.3, §13.2).

et0 is the monthly sum of daily FAO-56 Penman-Monteith ET0 (features/et0.py) and
p_minus_et0 = precip - et0 (climatic water balance). sm_rootzone (SMAP) and ndvi_z (MODIS) are
not in POWER, so they are NaN here and filled from the pilot tables by the training pipeline.
The SAME function builds the training table, so the backend's live path has no train/serve skew.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from agrolens_ml.config import DRY_DAY_MM, FROST_C, GDD_BASE_C, HEAVY_RAIN_MM, HOT_DAY_C
from agrolens_ml.contract import MONTHLY_INPUT_COLUMNS, POWER_DAILY_PARAMETERS
from agrolens_ml.features.et0 import actual_vapour_pressure_from_dew, et0_penman_monteith

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
    return out.mask(out <= POWER_FILL + 1e-9).sort_index().copy()


def _longest_dry_run(precip: pd.Series, month: pd.PeriodIndex) -> pd.Series:
    dry = (precip < DRY_DAY_MM).to_numpy()  # NaN -> not dry (breaks the run)
    run_id = np.cumsum(~dry)
    runs = pd.Series(dry.astype(float)).groupby([np.asarray(month), run_id]).sum()
    return runs.groupby(level=0).max()


def power_daily_to_monthly(daily: pd.DataFrame, elev_m: float, lat: float) -> pd.DataFrame:
    """POWER daily (POWER_DAILY_PARAMETERS, `date` column or DatetimeIndex) -> monthly_history.

    Returns one row per calendar month with exactly MONTHLY_INPUT_COLUMNS (`month` = Period[M]).
    `elev_m` [m] and `lat` [deg] feed FAO-56 ET0 (pressure and extraterrestrial radiation).
    """
    df = power_daily_with_et0(daily, elev_m, lat)
    return _monthly_aggregates(df)


def power_daily_with_et0(daily: pd.DataFrame, elev_m: float, lat: float) -> pd.DataFrame:
    """Cleaned POWER daily frame (DatetimeIndex, fill values -> NaN) plus an `ET0` column [mm/day].

    The one place daily ET0 is computed: the monthly aggregates and the counted risks both use it.
    """
    df = _daily_frame(daily)
    df["ET0"] = et0_penman_monteith(
        df["T2M_MAX"],
        df["T2M_MIN"],
        df["ALLSKY_SFC_SW_DWN"],
        df["WS2M"],
        actual_vapour_pressure_from_dew(df["T2MDEW"]),
        elev_m,
        lat,
        df.index.day_of_year,
    )
    return df


def _monthly_aggregates(df: pd.DataFrame) -> pd.DataFrame:
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
    out["et0"] = df["ET0"].groupby(month).sum(min_count=1)
    out["p_minus_et0"] = out["precip"] - out["et0"]
    out["sm_rootzone"] = np.nan  # SMAP, pilot tables only
    out["ndvi_z"] = np.nan  # MODIS, pilot tables only
    out.index = pd.PeriodIndex(out.index, freq="M")
    out = out.rename_axis("month").reset_index()
    return out[list(MONTHLY_INPUT_COLUMNS)]
