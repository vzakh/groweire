"""Rotation engine + POST /rotations/compare (plan 20 task 26)."""

from __future__ import annotations

import pytest
import respx

from clients import power
from models.rotations import Constraints
from services import rotation
from services.rotation import explain, generate, score
from services.rotation.catalog import load_catalog
from testing import power_responder

URL = "/api/v1/rotations/compare"
BARLEY = ["spring_barley"] * 4
PRIORITIES = [
    "income_stability",
    "simplicity",
    "soil_cover",
    "water_use",
    "forage_value",
    "nitrogen_fixing",
    "pest_break",
    "market_suitability",
]


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture
def env():
    """A stub-like seasonal profile: dry-risk summer, wet-risk October."""
    kinds = {6: "drought", 7: "drought", 8: "drought", 10: "waterlogging"}
    base = {3: 0.06, 4: 0.08, 5: 0.12, 6: 0.18, 7: 0.24, 8: 0.17, 9: 0.10, 10: 0.14}
    et0 = dict(zip(range(1, 13), [8, 15, 28, 48, 75, 85, 85, 70, 45, 22, 10, 6], strict=True))
    return score.Env(
        risk={m: (p, kinds.get(m, "other")) for m, p in base.items()},
        et0=et0,
        heavy_rain_days={m: 0.5 for m in range(1, 13)},
        slope_deg=2.0,
    )


# ---------- pure engine ----------


def test_every_emitted_code_has_an_advisor_question(catalog):
    rotation.check_codes(catalog)
    assert set(explain.CODES) <= set(catalog.advisor_questions)


def test_bare_months_for_continuous_spring_barley(catalog, env):
    current = generate.Candidate("current", "x", BARLEY, is_current=True)
    result = score.evaluate(current, catalog, env)
    assert result.metrics["bare_months_per_year"] == 7.0  # covered April..August only
    assert result.metrics["pest_break_score"] == 0.0
    assert result.metrics["n_fixing_years"] == 0
    assert result.metrics["rule_compliance"]["ie_crop_rotation_2_of_4"] is False
    assert result.metrics["water_demand_mm"] > 0


def test_cover_crop_fills_the_winter_gap(catalog, env):
    cover = generate.fill_cover(BARLEY, catalog, Constraints())
    assert cover == {
        0: "cover_oats_vetch",
        1: "cover_oats_vetch",
        2: "cover_oats_vetch",
        3: "cover_oats_vetch",
    }
    with_cover = generate.Candidate("c", "x", BARLEY, cover=cover)
    result = score.evaluate(with_cover, catalog, env)
    assert result.metrics["bare_months_per_year"] == 1.0  # only March is bare


def test_no_brassica_cover_crop_with_oilseed_rape(catalog):
    only_mustard = Constraints(excluded_crops=["cover_oats_vetch", "cover_phacelia"])
    sequence = ["winter_oilseed_rape", "spring_barley"]
    assert generate.fill_cover(sequence, catalog, only_mustard) == {}


def test_winter_crop_cover_wraps_into_the_previous_year(catalog):
    cand = generate.Candidate("c", "x", ["spring_barley", "winter_wheat"])
    covered = score.cover_matrix(cand, catalog)
    assert covered[0][10] and covered[0][11]  # wheat sown in the autumn of the barley year
    assert covered[1][0] and not covered[1][10]


def test_kc_curve_and_two_of_four(catalog):
    barley = catalog.crop("spring_barley")
    assert score.kc_at(barley, 0.0) == pytest.approx(0.3)
    assert score.kc_at(barley, 0.6) == pytest.approx(1.15)
    assert score.kc_at(barley, 1.0) == pytest.approx(0.25)
    assert score.two_of_four(["a", "a", "a", "b"]) is True
    assert score.two_of_four(["a"]) is False
    assert score.two_of_four(["a", "a", "a", "a", "b"]) is False  # one 4-year window is all "a"


def test_scores_are_between_0_and_1_and_ties_are_half(catalog, env):
    cands = generate.candidates(BARLEY, Constraints(), catalog)
    results = [score.evaluate(c, catalog, env) for c in cands]
    for scores in score.criteria(results):
        assert all(0 <= v <= 1 for v in scores.values())
    assert score.normalise([2.0, 2.0, None]) == [0.5, 0.5, 0.5]


@pytest.mark.parametrize("priority", PRIORITIES)
def test_picking_a_priority_never_lowers_the_best_strategy_on_it(catalog, env, priority):
    cands = generate.candidates(BARLEY, Constraints(), catalog)
    all_scores = score.criteria([score.evaluate(c, catalog, env) for c in cands])
    best = max(range(len(cands)), key=lambda i: all_scores[i][priority])

    def rank(priorities):
        w = score.weights(priorities)
        totals = [score.total_score(s, w) for s in all_scores]
        return sum(1 for t in totals if t > totals[best] + 1e-12)

    assert rank([priority]) <= rank([])


def test_weights(catalog):
    assert score.weights(["income_stability", "simplicity", "soil_cover"]) == {
        "climate_risk": 1,
        "income_stability": 3,
        "simplicity": 2,
        "soil_cover": 1,
    }
    assert score.weights([]) == {"climate_risk": 1}


# ---------- API ----------


def _body(field_id, **overrides):
    body = {
        "field_id": field_id,
        "current_rotation": BARLEY,
        "priorities": ["income_stability", "simplicity", "soil_cover"],
        "constraints": {"has_livestock": False, "market_contracts": ["malting_barley"]},
        "n_alternatives": 3,
    }
    body.update(overrides)
    return body


@pytest.mark.db
@respx.mock
def test_compare(db_client, pilot_field):
    respx.get(power.POWER_URL).mock(side_effect=power_responder)
    r = db_client.post(URL, json=_body(pilot_field))
    assert r.status_code == 200, r.text
    body = r.json()
    strategies = body["strategies"]
    assert len(strategies) == 4  # current + 3 (J1: at least 3 strategies incl. the current one)
    current = strategies[0]
    assert current["id"] == "current" and current["is_current"] and current["vs_current"] is None
    assert current["headline"] == "Your rotation: spring barley every year"
    assert current["explanation"]["why_suggested"] == "Baseline for comparison."
    assert "Fits your malting barley contract" in current["explanation"]["benefits"]
    assert any("wild oats" in risk for risk in current["explanation"]["risks_needing_local_review"])
    alternatives = strategies[1:]
    assert [s["score"] for s in alternatives] == sorted(
        (s["score"] for s in alternatives), reverse=True
    )
    for s in strategies:
        assert 0 <= s["score"] <= 1
        assert s["headline"] and s["one_line_why"]
        assert "%" not in s["headline"] + s["one_line_why"]
        assert 2 <= len(s["advisor_questions"]) <= 4
        blocks = s["explanation"]
        assert blocks["why_suggested"] and blocks["evidence"] and blocks["benefits"]
        assert blocks["information_gaps"] and blocks["risks_needing_local_review"]
        assert all(e["claim"] and e["source"] for e in blocks["evidence"])
        assert not {"grass_clover_ley", "maize_silage", "multispecies_sward"} & set(s["sequence"])
    for s in alternatives:
        assert set(s["vs_current"]) == {"risk", "bare_soil", "workload"}
    assert body["weights_used"] == {
        "climate_risk": 1,
        "income_stability": 3,
        "simplicity": 2,
        "soil_cover": 1,
    }
    assert body["disclaimer"].startswith("This tool supports, not replaces")
    assert "synthetic_data" in body["data_quality"]

    # Deterministic: the same request gives the same answer (golden behaviour).
    assert db_client.post(URL, json=_body(pilot_field)).json() == body


@pytest.mark.db
@respx.mock
def test_constraints_are_respected(db_client, pilot_field):
    respx.get(power.POWER_URL).mock(side_effect=power_responder)
    constraints = {
        "has_livestock": True,
        "excluded_crops": ["spring_beans", "winter_oilseed_rape"],
        "must_include": ["spring_oats"],
    }
    body = db_client.post(
        URL, json=_body(pilot_field, constraints=constraints, n_alternatives=5)
    ).json()
    for s in body["strategies"][1:]:
        used = set(s["sequence"]) | {c["crop_id"] for c in s["cover_crops"]}
        assert not used & {"spring_beans", "winter_oilseed_rape"}
        assert "spring_oats" in s["sequence"]
    assert len(body["strategies"]) >= 2


@pytest.mark.db
@pytest.mark.parametrize(
    "overrides, code",
    [
        (
            {"priorities": ["simplicity", "soil_cover", "water_use", "pest_break"]},
            "validation_error",
        ),
        ({"priorities": ["simplicity", "simplicity"]}, "duplicate_priorities"),
        ({"priorities": ["profit"]}, "validation_error"),
        ({"current_rotation": ["bananas"]}, "unknown_crop"),
        ({"current_rotation": ["cover_mustard"]}, "unknown_crop"),
        ({"current_rotation": []}, "validation_error"),
        ({"n_alternatives": 9}, "validation_error"),
    ],
)
def test_bad_requests(db_client, pilot_field, overrides, code):
    r = db_client.post(URL, json=_body(pilot_field, **overrides))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == code


@pytest.mark.db
@respx.mock
def test_compare_still_answers_when_weather_is_down(db_client, pilot_field, monkeypatch):
    monkeypatch.setattr(power, "RETRY_WAIT_S", 0)
    respx.get(power.POWER_URL).respond(503)
    r = db_client.post(URL, json=_body(pilot_field))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "climate_unavailable" in {g["code"] for g in body["information_gaps"]}
    assert all(s["metrics"]["water_demand_mm"] is None for s in body["strategies"])


@pytest.mark.db
def test_unknown_field(db_client):
    r = db_client.post(URL, json=_body("f_00000000"))
    assert r.status_code == 404 and r.json()["code"] == "field_not_found"
