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

# --- Counted risk (PLAN_40 task 41): absolute rules, counted per calendar month over the years ---
# Daily soil water balance = Met Éireann / Teagasc hybrid soil moisture deficit (SMD) model:
#   SMD_t = SMD_{t-1} - Rain + ETa + Drain            (mm; 0 = field capacity, -10 = saturated)
#   ETa = ET0                                          when SMD_{t-1} <= SMDc
#   ETa = ET0 * (SMDmax - SMD_{t-1}) / (SMDmax - SMDc) when SMD_{t-1} >  SMDc
# Source: https://www.met.ie/climate/services/agri-meteorological-data, after Schulte et al. 2005,
# Irish Journal of Agricultural and Food Research 44: 95-110. ET0 is FAO-56 Penman-Monteith for the
# grass reference (Kc = 1), which is also what the model was calibrated on.
SMD_MAX_MM = 110.0  # theoretical maximum deficit, all classes (Met Éireann)
SMD_SATURATED_MM = -10.0  # saturation = a 10 mm surplus (Met Éireann)
# Per drainage class: smd_min (well drained soils never saturate), smd_c (deficit above which
# actual ET falls below ET0), drain_max (mm/day drained at saturation, falling linearly to 0 at
# field capacity). "moderate" returns to field capacity on the first dry day (max drainage
# > 10 mm/day); "poor" drains 0.5 mm/day at -10 (Met Éireann). "well" never holds a surplus.
SMD_CLASSES: dict[str, dict[str, float]] = {
    "well": {"smd_min": 0.0, "smd_c": 0.0, "drain_max": 0.0},
    "moderate": {"smd_min": SMD_SATURATED_MM, "smd_c": 0.0, "drain_max": 10.0},
    "poor": {"smd_min": SMD_SATURATED_MM, "smd_c": 10.0, "drain_max": 0.5},
}
# Our drainage_class ordinal (1 excessive .. 5 very poor, Irish SIS) -> Met Éireann class.
# draft_unverified: this mapping is ours, not from a source.
SMD_CLASS_OF_DRAINAGE: dict[int, str] = {1: "well", 2: "well", 3: "moderate", 4: "poor", 5: "poor"}
SMD_CLASS_UNKNOWN = "moderate"  # no drainage class (e.g. Northern Ireland) -> information gap

# Dry day: SMD > 50 mm, the upper limit of optimum grass growth (Teagasc 2021, as cited in Basu,
# Fenton, Daly & Tuohy 2024, Front. Environ. Sci. 12:1331659). FAO-56 ch. 8 agrees: stress starts
# at p x TAW with p = 0.50-0.55, i.e. 55-60 mm of a 110 mm maximum. Sourced second-hand.
DRY_DAY_SMD_MM = 50.0
# Wet day: SMD < 0, water above field capacity (Met Éireann: negative SMD = surplus, -10 =
# saturated). Using "< 0" rather than exactly -10 is our choice (owner decision 2026-11-14).
WET_DAY_SMD_MM = 0.0
# A month is "too dry" / "too wet" when at least this many of its days are dry / wet days.
# draft_unverified: no source gives a day count; "most of the month" is the simplest rule
# (owner decision 2026-11-14). Surfaced to the farmer as an information gap.
RISK_MIN_DAYS = 15
# Heat (HOT_DAY_C, HEAT_MIN_HOT_DAYS) and frost (FROST_C, FROST_MIN_DAYS, FROST_MONTHS) reuse the
# constants above. draft_unverified: they carry no citation.
RISK_UNVERIFIED: tuple[str, ...] = ("min_days_per_month", "drainage_class_mapping", "heat", "frost")
# Rain: POWER daily rain is scaled per cell and month to the GPM IMERG monthly total (owner
# decision 2026-11-14, PLAN_40 Log). Guards against silly ratios; numerical safety, not agronomy.
RAIN_SCALE_MIN = 0.25
RAIN_SCALE_MAX = 4.0
RAIN_SCALE_MIN_MONTH_MM = 1.0  # a POWER month drier than this is left unscaled
RISK_RECENT_YEARS = 10  # recent_frequency window
RISK_EXAMPLE_YEARS = 5  # example_years kept per row, worst first
RISK_MAX_MISSING_DAYS = 3  # a month with more missing days is not counted

# Labels (brief §8.1)
STRESS_Z = -1.0
MIN_VALID_FRAC = 0.3

# z-anomalies need at least this many earlier baseline years of the same calendar month
MIN_CLIM_YEARS = 5
