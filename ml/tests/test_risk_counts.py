"""Counted-risk rules on hand-built daily series (PLAN_40 task 41): one test per rule."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agrolens_ml import config
from agrolens_ml.risk_counts import (
    count_hits,
    monthly_day_counts,
    monthly_hits,
    scale_rain_to_monthly,
    simulate_smd,
    smd_class,
)


def daily(start="2001-01-01", end="2002-12-31", rain=5.0, et0=0.0, tmax=15.0, tmin=8.0):
    """A daily frame shaped like power_daily_with_et0 output, constant unless overridden."""
    idx = pd.date_range(start, end, freq="D")
    return pd.DataFrame(
        {"PRECTOTCORR": rain, "ET0": et0, "T2M_MAX": tmax, "T2M_MIN": tmin}, index=idx
    ).astype(float)


def hit(df, klass, year, month, stress_type, **kw):
    hits = monthly_hits(monthly_day_counts(df, klass), **kw)
    row = hits[
        (hits.year == year) & (hits.month == month) & (hits.stress_type == stress_type)
    ].iloc[0]
    return bool(row.hit), int(row.days)


# --- the soil water balance (Met Éireann hybrid SMD model) ---


def test_smd_actual_et_formula():
    # no rain, ET0 = 4: day 1 takes the full 4 mm; then ETa = 4 * (110 - SMD) / 110
    smd = simulate_smd([0, 0, 0], [4, 4, 4], "well")
    assert smd[0] == pytest.approx(4.0)
    assert smd[1] == pytest.approx(4.0 + 4.0 * (110 - 4) / 110)
    assert smd[2] == pytest.approx(smd[1] + 4.0 * (110 - smd[1]) / 110)


def test_smd_poor_soil_takes_full_et_up_to_10mm():
    smd = simulate_smd([0, 0, 0, 0], [4, 4, 4, 4], "poor")  # SMDc = 10
    assert smd[:3] == pytest.approx([4.0, 8.0, 12.0])
    assert smd[3] == pytest.approx(12.0 + 4.0 * (110 - 12) / (110 - 10))


def test_smd_never_exceeds_maximum():
    assert simulate_smd(np.zeros(2000), np.full(2000, 6.0), "well").max() <= config.SMD_MAX_MM


def test_well_drained_never_saturates():
    assert simulate_smd([30, 30, 0], [0, 0, 0], "well") == pytest.approx([0, 0, 0])


def test_moderate_saturates_then_returns_to_field_capacity_on_first_dry_day():
    assert simulate_smd([30, 0, 0], [0, 0, 0], "moderate") == pytest.approx([-10, 0, 0])


def test_poor_drains_half_a_mm_per_day_at_saturation():
    smd = simulate_smd([30, 0, 0], [0, 0, 0], "poor")
    assert smd[0] == pytest.approx(-10.0)
    assert smd[1] == pytest.approx(-9.5)  # 0.5 mm/day at -10
    assert smd[2] == pytest.approx(-9.5 + 0.5 * 9.5 / 10)  # falling linearly towards 0


@pytest.mark.parametrize(
    "drainage, klass",
    [(1, "well"), (2, "well"), (3, "moderate"), (4, "poor"), (5, "poor"), (None, "moderate")],
)
def test_drainage_class_mapping(drainage, klass):
    assert smd_class(drainage) == klass
    assert smd_class(float("nan")) == config.SMD_CLASS_UNKNOWN


# --- one test per rule ---


def dry_july(dry_days_wanted: int) -> pd.DataFrame:
    """Field capacity all year, then a rainless spell that ends on 31 July 2002.

    With ET0 = 5 mm/day and no rain, SMD = 110 * (1 - (105/110)^n) after n days: 49.9 mm on
    day 13 and 52.2 mm on day 14, so the first 13 days of the spell are not yet dry days.
    """
    df = daily()
    spell = pd.date_range(end="2002-07-31", periods=dry_days_wanted + 13, freq="D")
    df.loc[spell, ["PRECTOTCORR", "ET0"]] = [0.0, 5.0]
    return df


def test_drought_rule_fires_at_15_dry_days_not_14():
    assert hit(dry_july(15), "well", 2002, 7, "drought") == (True, 15)
    assert hit(dry_july(14), "well", 2002, 7, "drought") == (False, 14)
    assert hit(daily(), "well", 2002, 7, "drought") == (False, 0)


def test_drought_day_is_strictly_above_50mm():
    # one day takes the soil from field capacity to exactly 50 mm; it then stays there
    df = daily("2001-07-01", "2001-07-31", rain=0.0, et0=0.0)
    df.loc["2001-07-01", "ET0"] = 50.0
    assert monthly_day_counts(df, "well").dry_days.iloc[0] == 0
    df.loc["2001-07-01", "ET0"] = 50.01
    assert monthly_day_counts(df, "well").dry_days.iloc[0] == 31


def wet_march(wet_days: int) -> pd.DataFrame:
    """No rain or ET (soil rests at field capacity), then heavy rain on the first days of March."""
    df = daily(rain=0.0)
    df.loc[pd.date_range("2002-03-01", periods=wet_days, freq="D"), "PRECTOTCORR"] = 30.0
    return df


def test_waterlogging_rule_fires_at_15_wet_days_not_14():
    # moderately drained: wet only on the rain days themselves
    assert hit(wet_march(15), "moderate", 2002, 3, "waterlogging") == (True, 15)
    assert hit(wet_march(14), "moderate", 2002, 3, "waterlogging") == (False, 14)


def test_waterlogging_depends_on_drainage_class():
    df = wet_march(3)  # three very wet days, then dry
    assert hit(df, "well", 2002, 3, "waterlogging") == (False, 0)
    assert hit(df, "moderate", 2002, 3, "waterlogging") == (False, 3)
    assert hit(df, "poor", 2002, 3, "waterlogging") == (True, 31)  # stays above field capacity


def test_heat_rule_fires_at_3_hot_days_at_25c():
    df = daily()
    df.loc["2002-07-10":"2002-07-11", "T2M_MAX"] = 25.0
    assert hit(df, "well", 2002, 7, "heat") == (False, 2)
    df.loc["2002-07-12", "T2M_MAX"] = 25.0
    assert hit(df, "well", 2002, 7, "heat") == (True, 3)
    df.loc["2002-07-12", "T2M_MAX"] = 24.99
    assert hit(df, "well", 2002, 7, "heat") == (False, 2)


def test_frost_rule_one_day_at_zero_in_march_to_may_only():
    df = daily()
    df.loc["2002-04-20", "T2M_MIN"] = 0.0
    df.loc["2002-10-20", "T2M_MIN"] = -3.0
    assert hit(df, "well", 2002, 4, "frost") == (True, 1)
    assert hit(df, "well", 2002, 10, "frost") == (False, 1)  # outside March-May
    df.loc["2002-04-20", "T2M_MIN"] = 0.01
    assert hit(df, "well", 2002, 4, "frost") == (False, 0)


# --- counting years ---


def test_counts_years_and_keeps_worst_years_first():
    df = daily("2001-01-01", "2012-12-31")
    for year, hot in [(2003, 3), (2006, 9), (2012, 5)]:
        df.loc[pd.date_range(f"{year}-07-01", periods=hot, freq="D"), "T2M_MAX"] = 27.0
    counts = count_hits(monthly_hits(monthly_day_counts(df, "well")))
    assert set(counts.calendar_month) == set(config.MONTHS)
    row = counts[(counts.calendar_month == 7) & (counts.stress_type == "heat")].iloc[0]
    assert (row.years_hit, row.years_total) == (3, 12)
    assert row.frequency == pytest.approx(3 / 12)
    assert row.recent_frequency == pytest.approx(3 / 10)  # 2003..2012
    assert row.example_years == [2006, 2012, 2003]
    june = counts[(counts.calendar_month == 6) & (counts.stress_type == "heat")].iloc[0]
    assert (june.years_hit, june.example_years) == (0, [])


def test_months_with_missing_weather_are_not_counted():
    df = daily("2001-01-01", "2003-12-31")
    df.loc["2002-07-01":"2002-07-04", "T2M_MAX"] = np.nan  # 4 missing days > 3 allowed
    df.loc["2003-07-01":"2003-07-03", "T2M_MAX"] = np.nan  # 3 missing days: still counted
    counts = count_hits(monthly_hits(monthly_day_counts(df, "well")))
    row = counts[(counts.calendar_month == 7) & (counts.stress_type == "heat")].iloc[0]
    assert row.years_total == 2


# --- rain scaled to monthly totals (GPM IMERG in the pilot) ---


def test_rain_is_scaled_to_the_monthly_total_and_keeps_its_daily_pattern():
    df = daily("2002-06-01", "2002-08-31", rain=0.0)
    df.loc["2002-06-10", "PRECTOTCORR"] = 30.0
    df.loc["2002-06-20", "PRECTOTCORR"] = 10.0  # June: 40 mm on two days
    df.loc["2002-07-05", "PRECTOTCORR"] = 0.5  # July: almost dry in POWER -> left alone
    df.loc["2002-08-01":"2002-08-10", "PRECTOTCORR"] = 1.0  # August: 10 mm
    target = pd.Series({"2002-06": 20.0, "2002-07": 50.0, "2002-08": 400.0})
    out = scale_rain_to_monthly(df, target)
    assert out.loc["2002-06-10", "PRECTOTCORR"] == pytest.approx(15.0)
    assert out.loc["2002-06-20", "PRECTOTCORR"] == pytest.approx(5.0)
    assert out.loc["2002-06", "PRECTOTCORR"].sum() == pytest.approx(20.0)
    assert out.loc["2002-07", "PRECTOTCORR"].sum() == pytest.approx(0.5)  # under 1 mm: unscaled
    assert out.loc["2002-08", "PRECTOTCORR"].sum() == pytest.approx(40.0)  # ratio capped at 4
    assert df.loc["2002-06-10", "PRECTOTCORR"] == 30.0  # the input frame is not changed


def test_months_without_a_monthly_total_keep_power_rain():
    df = daily("2002-06-01", "2002-07-31", rain=2.0)
    out = scale_rain_to_monthly(df, pd.Series({"2002-06": 30.0}))
    assert out.loc["2002-06", "PRECTOTCORR"].sum() == pytest.approx(30.0)
    assert out.loc["2002-07", "PRECTOTCORR"].sum() == pytest.approx(62.0)
