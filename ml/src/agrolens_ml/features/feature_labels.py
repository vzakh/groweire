"""Feature -> plain-language driver text (brief §8.7, PRD DD-13). Reading age ~9-11.

Farmer words only: never 'NDVI', 'ET0', '_z' or '%'. Describes the driver; gives no advice.
- Anomaly features ("than usual"): the text follows the SIGN OF THE VALUE.
- Other features: the text says which way the driver pushes the risk, i.e. the SIGN OF ITS
  CONTRIBUTION to the prediction (pred_contrib). Without a contribution, a neutral text.
"""

from __future__ import annotations

import math

# anomaly feature -> (value < 0, value > 0)
ANOMALY_TEXTS: dict[str, tuple[str, str]] = {
    "p_minus_et0_l1_z": ("Last month was drier than usual for this place",
                         "Last month was wetter than usual for this place"),
    "p_minus_et0_3m_l1_z": ("The last 3 months were drier than usual for this place",
                            "The last 3 months were wetter than usual for this place"),
    "t2m_l1_z": ("Last month was colder than usual", "Last month was warmer than usual"),
    "tmax_l1_z": ("Last month's days were cooler than usual",
                  "Last month's days were warmer than usual"),
    "tmin_l1_z": ("Last month's nights were colder than usual",
                  "Last month's nights were milder than usual"),
    "ndvi_z_l1": ("Crops here were less green than normal last month (seen from space)",
                  "Crops here were greener than normal last month (seen from space)"),
    "ndvi_z_l2": ("Crops here were less green than normal two months ago (seen from space)",
                  "Crops here were greener than normal two months ago (seen from space)"),
}  # fmt: skip

# other feature -> what it is, in farmer words (subject of "... makes crop stress more likely")
SUBJECTS: dict[str, str] = {
    "month_sin": "The time of year",
    "month_cos": "The time of year",
    "p_minus_et0_l1": "Last month's balance of rain against drying",
    "p_minus_et0_3m_l1": "The balance of rain against drying over the last 3 months",
    "precip_l1": "Last month's rain",
    "imerg_l1": "Last month's rain (measured from space)",
    "heavy_rain_days_l1": "The number of very wet days last month",
    "dry_spell_max_l1": "The longest dry spell last month",
    "t2m_l1": "Last month's temperature",
    "tmax_l1": "Last month's day-time temperature",
    "tmin_l1": "Last month's night-time temperature",
    "gdd5_l1": "The warmth crops had for growing last month",
    "hot_days_l1": "The number of hot days last month",
    "frost_days_l1": "The number of frosty nights last month",
    "gwetroot_l1": "How wet the soil was deep down last month",
    "gwettop_l1": "How wet the top of the soil was last month",
    "smap_rzsm_l1": "Soil wetness last month (measured from space)",
    "smap_pct_l1": "How wet the soil was last month compared with other years",
    "clim_precip_m": "How much rain this month usually brings here",
    "clim_tmax_m": "How warm this month usually is here",
    "clim_et0_m": "How fast fields usually dry out this month here",
    "elev_m": "How high this land is",
    "slope_deg": "How steep this land is",
    "clay": "How much clay is in this soil",
    "sand": "How much sand is in this soil",
    "soc": "How much organic matter is in this soil",
    "ph": "How acid or limey this soil is",
    "drainage_class": "How well this soil drains",
    "ag_fraction": "How much of the area around is farmland",
}

BANNED_TERMS: tuple[str, ...] = ("NDVI", "ET0", "_z", "%")

_NEUTRAL_ANOMALY = "Recent weather at this place"


def _missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def text(feature: str, value: float | None, contribution: float | None = None) -> str:
    """Plain-language text for a driver (feature, its value, its contribution to the risk)."""
    if feature in ANOMALY_TEXTS:
        if _missing(value) or value == 0:
            return _NEUTRAL_ANOMALY
        lower, higher = ANOMALY_TEXTS[feature]
        return lower if value < 0 else higher
    subject = SUBJECTS.get(feature, "Recent conditions at this place")
    if _missing(contribution) or contribution == 0:
        return subject
    effect = "more" if contribution > 0 else "less"
    return f"{subject} makes crop stress {effect} likely this month"
