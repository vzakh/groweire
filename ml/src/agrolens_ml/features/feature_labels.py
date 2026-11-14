"""Feature -> plain-language driver text (brief §8.7, PRD DD-13).

Farmer words only: never 'NDVI', 'ET0', '_z' or '%'. Describes the driver; gives no advice.
Task-05 draft: one (lower, higher, neutral) text per feature used as a driver.
"""

from __future__ import annotations

import math

# feature -> (text when value < 0 / lower than usual, text when > 0 / higher, neutral text)
_TEXTS: dict[str, tuple[str, str, str]] = {
    "p_minus_et0_3m_l1_z": (
        "The last 3 months were drier than usual for this place",
        "The last 3 months were wetter than usual for this place",
        "Rain and drying over the last 3 months",
    ),
    "p_minus_et0_l1_z": (
        "Last month was drier than usual for this place",
        "Last month was wetter than usual for this place",
        "Rain and drying last month",
    ),
    "tmax_l1_z": (
        "Last month's days were cooler than usual",
        "Last month's days were warmer than usual",
        "Day-time temperature last month",
    ),
    "tmax_l1": (
        "Last month's days were cool",
        "Last month's days were warm",
        "Day-time temperature last month",
    ),
    "ndvi_z_l1": (
        "Crops here were less green than normal last month (seen from space)",
        "Crops here were greener than normal last month (seen from space)",
        "How green crops were last month (seen from space)",
    ),
    "precip_l1": (
        "Little rain fell last month",
        "A lot of rain fell last month",
        "Rain last month",
    ),
    "hot_days_l1": (
        "Few hot days last month",
        "Several hot days last month",
        "Hot days last month",
    ),
    "frost_days_l1": ("Few frosty nights", "Several frosty nights last month", "Frosty nights"),
}

_DEFAULT = (
    "Weather here was a little below usual",
    "Weather here was a little above usual",
    "Recent weather at this place",
)


def text(feature: str, value: float | None) -> str:
    """Plain-language text for a driver feature and its (signed) value."""
    lower, higher, neutral = _TEXTS.get(feature, _DEFAULT)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return neutral
    return lower if value < 0 else higher


BANNED_TERMS: tuple[str, ...] = ("NDVI", "ET0", "_z", "%")
