"""Constants for the pilot (Ireland) and the documented thresholds (brief §7, §8)."""

from __future__ import annotations

# Island of Ireland bounding box (lon_min, lat_min, lon_max, lat_max), brief D1.
BBOX: tuple[float, float, float, float] = (-10.7, 51.3, -5.4, 55.5)

MONTHS = range(3, 11)  # March..October, the modelled season (brief §8.1)
BASELINE: tuple[int, int] = (2001, 2020)  # climatology reference period (labels and z-anomalies)

# Monthly aggregate thresholds (brief §8.3)
HEAVY_RAIN_MM = 20.0  # heavy_rain_days: daily precip > 20 mm
DRY_DAY_MM = 1.0  # dry_spell_max: longest run of days with precip < 1 mm
HOT_DAY_C = 25.0  # hot_days: T2M_MAX >= 25 °C (Irish context)
FROST_C = 0.0  # frost_days: T2M_MIN <= 0 °C
GDD_BASE_C = 5.0  # gdd5: sum of max(T2M - 5, 0)

# Stress-type attribution rules (brief §8.2); used by features/stress_rules.py from task 12.
DROUGHT_PME_3M_Z = -1.0  # 3-month P-ET0 anomaly <= -1 sd
DROUGHT_SMAP_PCT = 20.0  # or SMAP root-zone percentile <= 20
WATERLOG_PME_1M_Z = 1.0  # 1-month P-ET0 anomaly >= +1 sd
WATERLOG_GWETROOT = 0.9  # and (drainage poor/very poor or GWETROOT >= 0.9)
WATERLOG_DRAINAGE_MIN = 4  # drainage_class ordinal: 4 = poor, 5 = very poor
HEAT_MIN_HOT_DAYS = 3  # >= 3 hot days in the month
FROST_MIN_DAYS = 1  # >= 1 frost day ...
FROST_MONTHS = (3, 4, 5)  # ... in March-May

# Labels (brief §8.1)
STRESS_Z = -1.0
MIN_VALID_FRAC = 0.3

# z-anomalies need at least this many earlier baseline years of the same calendar month
MIN_CLIM_YEARS = 5
