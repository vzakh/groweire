"""Rule-based stress-type attribution (brief §8.2, D4). Thresholds live in config.py.

Rules read the feature row for target month m, so they describe the conditions LEADING INTO m
(lag-1 / 3-month features), which is what the model can know when it issues the risk:
  drought      p_minus_et0_3m_l1_z <= -1   or  smap_pct_l1 <= 20
  waterlogging p_minus_et0_l1_z >= +1      and (drainage_class >= 4 (poor/very poor)
                                                 or gwetroot_l1 >= 0.9)
  heat         hot_days_l1 >= 3
  frost        frost_days_l1 >= 1          and target month in March-May
  other        none of the above ("cause unclear, e.g. grass cutting")
Missing values (NaN/None) never trigger a rule.
"""

from __future__ import annotations

import math

from agrolens_ml import config
from agrolens_ml.features.build import month_from_sin_cos


def _v(row: dict, key: str) -> float:
    x = row.get(key)
    try:
        x = float(x)
    except (TypeError, ValueError):
        return math.nan
    return x


def _le(x: float, t: float) -> bool:
    return not math.isnan(x) and x <= t


def _ge(x: float, t: float) -> bool:
    return not math.isnan(x) and x >= t


def attribute_stress(row: dict) -> list[str]:
    """Stress types (subset of STRESS_TYPES, in that order) suggested by a feature row."""
    types: list[str] = []
    if _le(_v(row, "p_minus_et0_3m_l1_z"), config.DROUGHT_PME_3M_Z) or _le(
        _v(row, "smap_pct_l1"), config.DROUGHT_SMAP_PCT
    ):
        types.append("drought")
    if _ge(_v(row, "p_minus_et0_l1_z"), config.WATERLOG_PME_1M_Z) and (
        _ge(_v(row, "drainage_class"), config.WATERLOG_DRAINAGE_MIN)
        or _ge(_v(row, "gwetroot_l1"), config.WATERLOG_GWETROOT)
    ):
        types.append("waterlogging")
    if _ge(_v(row, "hot_days_l1"), config.HEAT_MIN_HOT_DAYS):
        types.append("heat")
    s, c = _v(row, "month_sin"), _v(row, "month_cos")
    month = math.nan if math.isnan(s) or math.isnan(c) else float(month_from_sin_cos(s, c))
    if _ge(_v(row, "frost_days_l1"), config.FROST_MIN_DAYS) and month in config.FROST_MONTHS:
        types.append("frost")
    return types or ["other"]
