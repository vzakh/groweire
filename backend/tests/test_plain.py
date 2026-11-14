"""Plain-language layer (plan 20 task 24b, brief §10.5). Wording is frozen on purpose."""

from __future__ import annotations

import pytest

from agrolens_ml import FEATURE_NAMES
from services import plain


@pytest.mark.parametrize(
    "p, text",
    [
        (0.0, "less than 1 year in 20"),
        (0.049, "less than 1 year in 20"),
        (0.05, "about 1 year in 20"),
        (0.095, "about 1 year in 20"),
        (0.10, "about 1 year in 10"),
        (0.149, "about 1 year in 10"),
        (0.15, "about 2 years in 10"),
        (0.21, "about 2 years in 10"),
        (0.25, "about 3 years in 10"),
        (0.5, "about 5 years in 10"),
        (0.949, "about 9 years in 10"),
        (0.95, "almost every year"),
        (1.0, "almost every year"),
    ],
)
def test_frequency_text(p, text):
    assert plain.frequency_text(p) == text


@pytest.mark.parametrize(
    "p, expected",
    [
        (0.0, "low"),
        (0.099, "low"),
        (0.10, "medium"),
        (0.249, "medium"),
        (0.25, "high"),
        (1, "high"),
    ],
)
def test_level(p, expected):
    assert plain.level(p) == expected


@pytest.mark.parametrize(
    "risk_level, types, expected",
    [
        ("low", ["drought"], "OK"),
        ("medium", ["drought"], "Dry"),
        ("high", ["waterlogging"], "Wet"),
        ("medium", ["heat"], "Heat"),
        ("medium", ["frost"], "Frost"),
        ("high", ["other"], "Unclear"),
        ("high", [], "Unclear"),
        ("high", ["heat", "drought"], "Dry"),  # drought names the month when both apply
    ],
)
def test_label(risk_level, types, expected):
    assert plain.label(risk_level, types) == expected


def _m(month, risk, *types):
    return {"month": month, "risk": risk, "stress_types": list(types)}


def test_headline_dry_july():
    months = [_m(6, 0.15, "drought"), _m(7, 0.21, "drought"), _m(8, 0.12, "drought")]
    assert plain.headline(months, "Spring barley") == (
        "July is the riskiest month for spring barley here. In about 2 years in 10 it is too dry."
    )
    assert plain.riskiest_month(months) == 7


def test_headline_wet_october():
    months = [_m(7, 0.11, "drought"), _m(10, 0.31, "waterlogging")]
    assert plain.headline(months, "Winter wheat") == (
        "October is the riskiest month for winter wheat here. "
        "In about 3 years in 10 it is too wet."
    )


def test_headline_all_low():
    months = [_m(m, 0.04, "other") for m in range(3, 11)]
    assert plain.headline(months, "Spring oats") == (
        "No month stands out as risky for spring oats here."
    )


def test_headline_cause_unclear_and_no_crop():
    months = [_m(5, 0.18, "other"), _m(6, 0.12, "drought")]
    assert plain.headline(months, None) == (
        "May is the riskiest month for crops here. "
        "In about 2 years in 10 crops here do worse than normal, cause unclear."
    )


def test_riskiest_month_tie_goes_to_the_earlier_month():
    assert plain.riskiest_month([_m(8, 0.2), _m(6, 0.2), _m(7, 0.1)]) == 6
    assert plain.riskiest_month([]) is None


def test_aria_label():
    assert plain.aria_label(
        7, "Spring barley", "Dry", "about 2 years in 10", (0.15, 0.27), "drought"
    ) == (
        "July, spring barley: dry. In about 2 years in 10 it is too dry here. "
        "Uncertainty 15 to 27 percent."
    )
    # frost is counted often, but this crop is not sensitive then: the label says OK
    assert plain.aria_label(3, "Maize", "OK", "about 9 years in 10", (0.7, 0.96), "frost") == (
        "March, maize: OK. In about 9 years in 10 it is too frosty here. "
        "Uncertainty 70 to 96 percent."
    )
    assert plain.aria_label(9, None, "OK", "less than 1 year in 20", (0.0, 0.1)) == (
        "September, crops: OK. No risky weather was counted here."
    )


@pytest.mark.parametrize(
    "kind, hit, years, text",
    [
        ("drought", 1, [2018], "July was too dry here in 1 of the last 25 years: 2018."),
        (
            "drought",
            3,
            [2018, 2006, 2022],
            "July was too dry here in 3 of the last 25 years: 2018, 2006 and 2022.",
        ),
        (
            "frost",
            22,
            [2013, 2018, 2010, 2020, 2016],
            "July had frost here in 22 of the last 25 years, for example 2013, 2018 and 2010.",
        ),
        (
            "waterlogging",
            2,
            [2012, 2007],
            "July was too wet here in 2 of the last 25 years: 2012 and 2007.",
        ),
        ("heat", 0, [], "July was too hot here in 0 of the last 25 years."),
    ],
)
def test_evidence_text(kind, hit, years, text):
    assert plain.evidence_text(7, kind, hit, 25, years) == text


def test_headline_words_describe_the_counted_weather_not_the_crop_weighting():
    months = [
        {"month": 6, "risk": 0.05, "frequency": 0.12, "stress_types": ["drought"]},
        {"month": 7, "risk": 0.19, "frequency": 0.24, "stress_types": ["drought"]},
    ]
    assert plain.headline(months, "Spring barley") == (
        "July is the riskiest month for spring barley here. In about 2 years in 10 it is too dry."
    )


@pytest.mark.parametrize(
    "text",
    [
        "NDVI was low last month",
        "ET0 is above normal",
        "Rain was 30% below normal",
        "p_minus_et0_3m_l1_z is negative",
        "The z-score is low",
        "tmax_l1 was high",
        "",
    ],
)
def test_technical_driver_texts_are_rejected(text):
    assert not plain.driver_text_ok(text, FEATURE_NAMES)


def test_farmer_word_driver_text_is_accepted():
    text = "The 3 months before are often drier than usual here"
    assert plain.driver_text_ok(text, FEATURE_NAMES)


def test_no_generated_string_has_a_percent_sign_or_jargon():
    months = [
        _m(m, p, t) for m, p, t in [(3, 0.03, "frost"), (7, 0.4, "heat"), (10, 0.97, "other")]
    ]
    strings = [plain.frequency_text(p / 100) for p in range(0, 101)]
    strings += [plain.headline(months[:i], "Potatoes") for i in range(1, 4)]
    strings += [plain.aria_label(7, "Potatoes", "Heat", s, (0.1, 0.2)) for s in strings[:5]]
    for s in strings:
        assert "%" not in s and "NDVI" not in s and "ET0" not in s and "z-score" not in s


def test_greenness_text():
    start = "How green the land around your field was each summer, seen by NASA satellites."
    assert plain.greenness_text([]) == start
    assert plain.greenness_text([2018]) == f"{start} The least green summer was 2018."
    assert plain.greenness_text([2018, 2006, 2013]) == (
        f"{start} The least green summers were 2018, 2006 and 2013."
    )
