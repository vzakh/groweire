"""FAO-56 ET0 against the worked examples in FAO-56 (Allen et al., 1998)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agrolens_ml import power_daily_to_monthly
from agrolens_ml.features import et0 as fao

# FAO-56 Example 18 (Brussels, 6 July, lat 50°48'N, 100 m): ET0 = 3.9 mm/day.
# Rs = 22.07 MJ m-2 d-1 (from sunshine in the example), u2 = 2.078 m/s, ea = 1.409 kPa.
EX18 = dict(
    tmax_c=21.5,
    tmin_c=12.3,
    rs=22.07,
    u2=2.078,
    ea=1.409,
    elev_m=100.0,
    lat_deg=50.0 + 48.0 / 60.0,
    doy=187,
)


def test_example18_intermediates():
    assert fao.atmospheric_pressure(100.0) == pytest.approx(100.1, abs=0.05)
    assert fao.psychrometric_constant(100.0) == pytest.approx(0.0666, abs=0.0002)
    es = (fao.sat_vapour_pressure(21.5) + fao.sat_vapour_pressure(12.3)) / 2
    assert es == pytest.approx(1.997, abs=0.005)
    assert fao.slope_vapour_curve(16.9) == pytest.approx(0.122, abs=0.001)
    ra = fao.extraterrestrial_radiation(EX18["lat_deg"], 187)
    assert ra == pytest.approx(41.09, abs=0.05)
    rso = fao.clear_sky_radiation(ra, 100.0)
    assert rso == pytest.approx(30.90, abs=0.05)
    rnl = fao.net_longwave_radiation(21.5, 12.3, 1.409, 22.07, rso)
    assert rnl == pytest.approx(3.71, abs=0.03)


def test_example18_et0():
    assert fao.et0_penman_monteith(**EX18) == pytest.approx(3.9, abs=0.1)


def test_example8_extraterrestrial_radiation():
    # FAO-56 Example 8: 20°S on 3 September (J = 246) -> Ra = 32.2 MJ m-2 d-1
    assert fao.extraterrestrial_radiation(-20.0, 246) == pytest.approx(32.2, abs=0.1)


def test_dew_point_vapour_pressure():
    # e°(Tdew) at 12.0 °C ≈ 1.40 kPa (FAO-56 Table 2.3: 1.402)
    assert fao.actual_vapour_pressure_from_dew(12.0) == pytest.approx(1.402, abs=0.002)


def test_vectorised_and_polar_safe():
    out = fao.et0_penman_monteith(
        np.array([21.5, 5.0]),
        np.array([12.3, -2.0]),
        np.array([22.07, 0.5]),
        np.array([2.078, 3.0]),
        np.array([1.409, 0.5]),
        100.0,
        np.array([50.8, 78.0]),
        np.array([187, 355]),
    )
    assert out.shape == (2,)
    assert np.all(np.isfinite(out)) and np.all(out >= 0)


def test_monthly_et0_and_water_balance():
    dates = pd.date_range("2024-07-01", "2024-07-31", freq="D")
    n = len(dates)
    daily = pd.DataFrame(
        {
            "date": dates,
            "T2M": 16.9,
            "T2M_MAX": 21.5,
            "T2M_MIN": 12.3,
            "PRECTOTCORR": 1.0,
            "RH2M": 75.0,
            "WS2M": 2.078,
            "ALLSKY_SFC_SW_DWN": 22.07,
            "GWETROOT": 0.7,
            "GWETTOP": 0.6,
            "T2MDEW": 12.0,
        }
    )
    monthly = power_daily_to_monthly(daily, elev_m=100.0, lat=50.8)
    row = monthly.iloc[0]
    expected = fao.et0_penman_monteith(
        21.5,
        12.3,
        22.07,
        2.078,
        fao.actual_vapour_pressure_from_dew(12.0),
        100.0,
        50.8,
        dates.day_of_year.to_numpy(),
    ).sum()
    assert row["et0"] == pytest.approx(expected, rel=1e-9)
    assert 100 < row["et0"] < 130  # ~3.9 mm/day x 31 days
    assert row["p_minus_et0"] == pytest.approx(n * 1.0 - row["et0"], rel=1e-9)
