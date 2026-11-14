"""FEATURE_NAMES, build_feature_table (training) and build_feature_row (serving) (brief §8.3).

One code path (Google Rules of ML #32): build_feature_row runs build_feature_table on the history
truncated to months < target, so training and serving cannot drift apart.

Hard rule 2 (no leakage): the feature row for target month m only uses data from months < m.
Anomalies (z) compare a value with the same calendar month in the BASELINE years (2001-2020) that
lie strictly before it. For targets from 2021 on (holdout, live serving) that is exactly the fixed
2001-2020 climatology; earlier targets use the baseline years seen so far (>= MIN_CLIM_YEARS).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from agrolens_ml.config import BASELINE, MIN_CLIM_YEARS, MONTHS

# Owned by ML; may change without a contract bump (D22). Brief §8.3.
FEATURE_NAMES: tuple[str, ...] = (
    # calendar
    "month_sin", "month_cos",
    # water balance
    "p_minus_et0_l1", "p_minus_et0_3m_l1", "p_minus_et0_l1_z", "p_minus_et0_3m_l1_z",
    # precipitation
    "precip_l1", "imerg_l1", "heavy_rain_days_l1", "dry_spell_max_l1",
    # temperature
    "t2m_l1", "tmax_l1", "tmin_l1", "t2m_l1_z", "tmax_l1_z", "tmin_l1_z",
    "gdd5_l1", "hot_days_l1", "frost_days_l1",
    # soil moisture
    "gwetroot_l1", "gwettop_l1", "smap_rzsm_l1", "smap_pct_l1",
    # vegetation memory
    "ndvi_z_l1", "ndvi_z_l2",
    # climatology of the target month
    "clim_precip_m", "clim_tmax_m", "clim_et0_m",
    # static
    "elev_m", "slope_deg", "clay", "sand", "soc", "ph", "drainage_class", "ag_fraction",
)  # fmt: skip

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

# OPTIONAL monthly_history columns (not in the contract; NaN when absent). Adding an optional,
# NaN-allowed column is backward compatible (PLAN_10 risks table).
OPTIONAL_LAG1: dict[str, str] = {"imerg_l1": "imerg", "smap_pct_l1": "smap_pct"}

# z-anomaly of month m-1 for these columns
LAG1_Z: dict[str, str] = {
    "p_minus_et0_l1_z": "p_minus_et0",
    "t2m_l1_z": "t2m",
    "tmax_l1_z": "tmax",
    "tmin_l1_z": "tmin",
}

# climatological mean of the TARGET calendar month (baseline years before m)
CLIM_OF_TARGET: dict[str, str] = {
    "clim_precip_m": "precip",
    "clim_tmax_m": "tmax",
    "clim_et0_m": "et0",
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

_PME3 = "_pme_3m"  # internal: 3-month P-ET0 sum ending at the row's month


def month_angle(month: int | np.ndarray) -> float | np.ndarray:
    """Calendar month (1..12) -> angle on the unit circle; month_sin/cos = sin/cos of this."""
    return 2.0 * np.pi * (np.asarray(month) - 1) / 12.0


def month_from_sin_cos(s: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Inverse of month_angle (vectorised). NaN in -> NaN out."""
    ang = np.arctan2(np.asarray(s, dtype=float), np.asarray(c, dtype=float))
    return np.mod(np.round(ang * 12.0 / (2.0 * np.pi)), 12) + 1


def _to_period(months: pd.Series) -> pd.Series:
    if isinstance(months.dtype, pd.PeriodDtype):
        return months
    return pd.Series(
        pd.PeriodIndex(pd.to_datetime(months.astype(str)), freq="M"), index=months.index
    )


def _panel(monthly: pd.DataFrame, targets: pd.DataFrame, key: str) -> pd.DataFrame:
    """Contiguous monthly panel per key covering history and targets (so shift(1) == m-1)."""
    obs = monthly.assign(month=_to_period(monthly["month"]))
    if obs.duplicated([key, "month"]).any():
        raise ValueError("monthly history has duplicate (key, month) rows")
    tgt = targets[[key, "month"]].assign(month=_to_period(targets["month"]))
    spans = pd.concat([obs[[key, "month"]], tgt]).groupby(key)["month"].agg(["min", "max"])
    keys, months = [], []
    for k, lo, hi in zip(spans.index, spans["min"], spans["max"]):
        rng = pd.period_range(lo, hi, freq="M")
        keys.append(np.full(len(rng), k, dtype=object))
        months.append(rng)
    index = pd.MultiIndex.from_arrays(
        [
            np.concatenate(keys),
            pd.PeriodIndex.from_ordinals(np.concatenate([m.asi8 for m in months]), freq="M"),
        ],
        names=[key, "month"],
    )
    return obs.set_index([key, "month"]).reindex(index)


def _exclusive_baseline_stats(
    values: pd.Series, keys: np.ndarray, cal: np.ndarray, in_base: np.ndarray
) -> tuple[pd.Series, pd.Series]:
    """Mean/std of the same calendar month in baseline years strictly BEFORE each row."""
    v = values.where(in_base)
    present = v.notna().astype(float)
    filled = v.fillna(0.0)
    grp = [keys, cal]
    n = present.groupby(grp).cumsum() - present
    s = filled.groupby(grp).cumsum() - filled
    ss = (filled**2).groupby(grp).cumsum() - filled**2
    ok = n >= MIN_CLIM_YEARS
    mean = (s / n).where(ok)
    var = ((ss - n * mean**2) / (n - 1)).where(ok)
    return mean, np.sqrt(var.clip(lower=0.0))


def build_feature_table(
    monthly: pd.DataFrame,
    static: pd.DataFrame,
    targets: pd.DataFrame | None = None,
    key: str = "cell_id",
) -> pd.DataFrame:
    """Vectorised features for many (key, target month) pairs (training).

    monthly: rows [key, month, *MONTHLY_INPUT_COLUMNS[1:], optional imerg/smap_pct].
    static:  index = key, columns ⊇ CELL_STATIC_KEYS (missing -> NaN).
    targets: [key, month]; default = every monthly row in MONTHS (Mar-Oct).
    Returns [key, month (Period)] + FEATURE_NAMES, one row per target.
    """
    if targets is None:
        months = _to_period(monthly["month"])
        targets = monthly.loc[months.dt.month.isin(list(MONTHS)).to_numpy(), [key, "month"]]
    panel = _panel(monthly, targets, key)
    keys = panel.index.get_level_values(0).to_numpy()
    pidx = panel.index.get_level_values(1)
    cal = np.asarray(pidx.month)
    in_base = np.asarray((pidx.year >= BASELINE[0]) & (pidx.year <= BASELINE[1]))

    def col(name: str) -> pd.Series:
        return panel[name] if name in panel.columns else pd.Series(np.nan, index=panel.index)

    def lag(series: pd.Series, k: int) -> pd.Series:
        return series.groupby(level=0, sort=False).shift(k)

    def zscore(series: pd.Series) -> pd.Series:
        mean, std = _exclusive_baseline_stats(series, keys, cal, in_base)
        return ((series - mean) / std.where(std > 0)).astype(float)

    pme = col("p_minus_et0")
    pme3 = pme + lag(pme, 1) + lag(pme, 2)  # NaN if any month missing

    feats = pd.DataFrame(index=panel.index)
    ang = month_angle(cal)
    feats["month_sin"], feats["month_cos"] = np.sin(ang), np.cos(ang)
    for feat, src in {**LAG1_FROM_MONTHLY, **OPTIONAL_LAG1}.items():
        feats[feat] = lag(col(src), 1)
    feats["p_minus_et0_3m_l1"] = lag(pme3, 1)
    for feat, src in LAG1_Z.items():
        feats[feat] = lag(zscore(col(src)), 1)
    feats["p_minus_et0_3m_l1_z"] = lag(zscore(pme3), 1)
    feats["ndvi_z_l2"] = lag(col("ndvi_z"), 2)
    for feat, src in CLIM_OF_TARGET.items():
        feats[feat] = _exclusive_baseline_stats(col(src), keys, cal, in_base)[0]

    st = static.reindex(pd.Index(keys))
    for feat, src in STATIC_FROM_CELL.items():
        feats[feat] = (
            pd.to_numeric(st[src], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
            if src in st.columns
            else np.nan
        )

    want = pd.MultiIndex.from_arrays(
        [targets[key].to_numpy(dtype=object), pd.PeriodIndex(_to_period(targets["month"]))],
        names=[key, "month"],
    )
    out = feats.loc[want, list(FEATURE_NAMES)].astype(float)
    return out.reset_index()


def build_feature_row(
    cell_static: dict, monthly_history: pd.DataFrame, target_month: pd.Period
) -> dict:
    """Feature row for one cell and one target month; keys == FEATURE_NAMES, values float.

    Only rows with month < target_month are read (hard rule 2). Same code as training.
    """
    target = pd.Period(target_month, freq="M")
    hist = monthly_history if monthly_history is not None else pd.DataFrame(columns=["month"])
    if len(hist):
        months = _to_period(hist["month"])
        hist = hist.loc[(months < target).to_numpy()].assign(month=months[months < target])
    hist = hist.assign(_key="_")
    static = pd.DataFrame([dict(cell_static or {})], index=pd.Index(["_"], name="_key"))
    targets = pd.DataFrame({"_key": ["_"], "month": pd.PeriodIndex([target], freq="M")})
    out = build_feature_table(hist, static, targets, key="_key")
    return {f: float(out.iloc[0][f]) for f in FEATURE_NAMES}
