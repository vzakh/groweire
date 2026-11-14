"""FAO-56 Penman-Monteith reference evapotranspiration, daily step (Allen et al., 1998).

Equation numbers refer to FAO Irrigation and Drainage Paper 56, chapters 2-4:
https://www.fao.org/3/X0490E/x0490e00.htm

Inputs map to NASA POWER (AG community) daily parameters:
    tmax, tmin  <- T2M_MAX, T2M_MIN   [°C]
    rs          <- ALLSKY_SFC_SW_DWN  [MJ m-2 day-1]
    u2          <- WS2M               [m s-1, already at 2 m]
    ea          <- e°(T2MDEW)         [kPa]  (eq. 14)
G (soil heat flux) is 0 for daily steps (eq. 42). All functions are vectorised (numpy).
"""

from __future__ import annotations

import numpy as np

GSC = 0.0820  # solar constant [MJ m-2 min-1]
SIGMA = 4.903e-9  # Stefan-Boltzmann constant [MJ K-4 m-2 day-1]
ALBEDO = 0.23  # hypothetical grass reference crop


def atmospheric_pressure(elev_m):
    """Eq. 7: P [kPa] from elevation [m]."""
    return 101.3 * ((293.0 - 0.0065 * np.asarray(elev_m, dtype=float)) / 293.0) ** 5.26


def psychrometric_constant(elev_m):
    """Eq. 8: γ [kPa °C-1]."""
    return 0.665e-3 * atmospheric_pressure(elev_m)


def sat_vapour_pressure(t_c):
    """Eq. 11: e°(T) [kPa]."""
    t = np.asarray(t_c, dtype=float)
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def actual_vapour_pressure_from_dew(tdew_c):
    """Eq. 14: ea = e°(Tdew) [kPa]."""
    return sat_vapour_pressure(tdew_c)


def slope_vapour_curve(t_c):
    """Eq. 13: Δ [kPa °C-1] at air temperature T."""
    t = np.asarray(t_c, dtype=float)
    return 4098.0 * sat_vapour_pressure(t) / (t + 237.3) ** 2


def extraterrestrial_radiation(lat_deg, doy):
    """Eqs. 21-25: Ra [MJ m-2 day-1] for latitude [deg] and day of year (1..366)."""
    phi = np.deg2rad(np.asarray(lat_deg, dtype=float))
    j = np.asarray(doy, dtype=float)
    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi * j / 365.0)  # eq. 23
    delta = 0.409 * np.sin(2.0 * np.pi * j / 365.0 - 1.39)  # eq. 24
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))  # eq. 25 (polar-safe)
    return (
        (24.0 * 60.0 / np.pi)
        * GSC
        * dr
        * (ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))
    )


def clear_sky_radiation(ra, elev_m):
    """Eq. 37: Rso [MJ m-2 day-1]."""
    return (0.75 + 2e-5 * np.asarray(elev_m, dtype=float)) * np.asarray(ra, dtype=float)


def net_longwave_radiation(tmax_c, tmin_c, ea, rs, rso):
    """Eq. 39: Rnl [MJ m-2 day-1]. Rs/Rso is limited to <= 1.0 as FAO-56 requires."""
    tmax_k4 = (np.asarray(tmax_c, dtype=float) + 273.16) ** 4
    tmin_k4 = (np.asarray(tmin_c, dtype=float) + 273.16) ** 4
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.clip(np.asarray(rs, dtype=float) / np.asarray(rso, dtype=float), 0.0, 1.0)
    return (
        SIGMA
        * (tmax_k4 + tmin_k4)
        / 2.0
        * (0.34 - 0.14 * np.sqrt(np.asarray(ea, dtype=float)))
        * (1.35 * ratio - 0.35)
    )


def et0_penman_monteith(tmax_c, tmin_c, rs, u2, ea, elev_m, lat_deg, doy):
    """Eq. 6, daily: ET0 [mm day-1], clipped at 0 (tiny negatives occur on dark winter days)."""
    tmax = np.asarray(tmax_c, dtype=float)
    tmin = np.asarray(tmin_c, dtype=float)
    t = (tmax + tmin) / 2.0  # eq. 9
    es = (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2.0  # eq. 12
    delta = slope_vapour_curve(t)
    gamma = psychrometric_constant(elev_m)
    ra = extraterrestrial_radiation(lat_deg, doy)
    rso = clear_sky_radiation(ra, elev_m)
    rns = (1.0 - ALBEDO) * np.asarray(rs, dtype=float)  # eq. 38
    rn = rns - net_longwave_radiation(tmax, tmin, ea, rs, rso)  # eq. 40
    u2 = np.asarray(u2, dtype=float)
    ea = np.asarray(ea, dtype=float)
    et0 = (0.408 * delta * rn + gamma * (900.0 / (t + 273.0)) * u2 * (es - ea)) / (
        delta + gamma * (1.0 + 0.34 * u2)
    )
    return np.clip(et0, 0.0, None)
