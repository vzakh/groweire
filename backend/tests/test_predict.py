"""POST /predict/stress-risk on counted risks (PLAN_40). Synthetic pilot + mocked POWER."""

from __future__ import annotations

import time

import pytest
import respx

from agrolens_ml import RISK_RULES_VERSION
from clients import power
from services import risk
from testing import power_responder

pytestmark = pytest.mark.db
URL = "/api/v1/predict/stress-risk"

# Keys of the response example in brief §9.1.
BRIEF_TOP_KEYS = {
    "model_version",
    "method",
    "calibrated_region",
    "headline",
    "months",
    "riskiest_month",
    "trend",
    "data_quality",
    "needs_local_review",
    "disclaimer",
    "provenance",
}
BRIEF_MONTH_KEYS = {
    "month",
    "probability",
    "interval",
    "years_hit",
    "years_total",
    "stress_types",
    "counts",
    "drivers",
    "crop_sensitivity",
    "crop_weighted_risk",
    "level",
    "label",
    "frequency_text",
    "aria_label",
}
TYPES = {"drought", "waterlogging", "heat", "frost"}


def month(body: dict, number: int) -> dict:
    return next(m for m in body["months"] if m["month"] == number)


def test_pilot_profile_is_counted_from_history(db_client, pilot_field):
    r = db_client.post(URL, json={"field_id": pilot_field, "mode": "seasonal_profile"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert BRIEF_TOP_KEYS <= set(body)
    assert [m["month"] for m in body["months"]] == list(range(3, 11))
    for m in body["months"]:
        assert BRIEF_MONTH_KEYS <= set(m)
        assert "year" not in m
        assert 0 <= m["interval"][0] <= m["probability"] <= m["interval"][1] <= 1
        assert m["probability"] == pytest.approx(m["years_hit"] / m["years_total"], abs=1e-4)
        assert m["crop_sensitivity"] is None and m["crop_weighted_risk"] is None
        assert {c["stress_type"] for c in m["counts"]} == TYPES
        frequencies = [c["frequency"] for c in m["counts"]]
        assert frequencies == sorted(frequencies, reverse=True)  # most frequent first
        top = m["counts"][0]
        assert (m["years_hit"], m["years_total"]) == (top["years_hit"], top["years_total"])
        assert m["stress_types"] == ([top["stress_type"]] if top["years_hit"] else [])
        # one counted fact per type that ever happened, as a checkable sentence
        happened = [c for c in m["counts"] if c["years_hit"] > 0]
        assert [d["feature"] for d in m["drivers"]] == [c["stress_type"] for c in happened]
        for d, c in zip(m["drivers"], happened, strict=True):
            assert {"feature", "value", "contribution", "text"} == set(d)
            assert d["value"] == c["years_hit"]
            assert f"in {c['years_hit']} of the last {c['years_total']} years" in d["text"]
            assert str(c["example_years"][0]) in d["text"]
        assert "%" not in m["frequency_text"]
    assert body["model_version"] == RISK_RULES_VERSION
    assert body["method"] == "counted_history" and body["mode"] == "seasonal_profile"
    assert body["calibrated_region"] == "IE"
    assert body["trend"] is None
    assert body["needs_local_review"] is True
    assert "synthetic_data" in body["data_quality"]  # synthetic tables (brief §8.8)
    assert body["disclaimer"].startswith("This tool supports, not replaces")
    assert {p["dataset_id"] for p in body["provenance"]} >= {"power", "met_eireann_smd"}
    codes = {g["code"] for g in body["information_gaps"]}
    assert {"risk_rules_unverified", "weather_is_area_average"} <= codes

    # synthetic counts: frost in most Marches; the headline says how often in checkable words
    march = month(body, 3)
    assert march["stress_types"] == ["frost"] and march["label"] == "Frost"
    assert body["riskiest_month"] == 3
    assert body["headline"] == (
        f"March is the riskiest month for crops here. In {march['frequency_text']} it is too "
        "frosty."
    )
    assert march["drivers"][0]["text"].startswith("March had frost here in ")


def test_crop_weighting_ranks_months_but_words_stay_counted(db_client, pilot_field):
    body = db_client.post(URL, json={"field_id": pilot_field, "crop_id": "spring_barley"}).json()
    july = month(body, 7)
    assert july["stress_types"] == ["drought"]
    assert july["crop_sensitivity"] == 0.8
    assert july["crop_weighted_risk"] == pytest.approx(july["probability"] * 0.8, abs=1e-3)
    assert july["label"] in ("Dry", "OK")
    assert july["aria_label"].startswith("July, spring barley: ")
    # the frequency words describe the counted weather, not the crop-weighted number
    assert july["frequency_text"] == _frequency_text(july["probability"])
    assert "spring barley" in body["headline"]
    shown = {m["month"]: m["crop_weighted_risk"] for m in body["months"]}
    assert all(v is not None for m, v in shown.items() if month(body, m)["stress_types"])
    best = max(shown.items(), key=lambda kv: ((kv[1] or 0), -kv[0]))[0]
    assert body["riskiest_month"] == best
    top = month(body, best)
    assert top["frequency_text"] in body["headline"]
    codes = {g["code"] for g in body["information_gaps"]}
    assert "crop_sensitivity_unverified" in codes


def _frequency_text(p: float) -> str:
    from services import plain  # pylint: disable=import-outside-toplevel

    return plain.frequency_text(p)


def test_unknown_crop_field_and_removed_mode(db_client, pilot_field):
    r = db_client.post(URL, json={"field_id": pilot_field, "crop_id": "bananas"})
    assert r.status_code == 422 and r.json()["code"] == "unknown_crop"
    r = db_client.post(URL, json={"field_id": "f_00000000"})
    assert r.status_code == 404 and r.json()["code"] == "field_not_found"
    r = db_client.post(URL, json={"mode": "seasonal_profile"})
    assert r.status_code == 422 and r.json()["code"] == "field_input_ambiguous"
    r = db_client.post(URL, json={"field_id": pilot_field, "mode": "next_month"})
    assert r.status_code == 422  # removed in contract 2.0


@respx.mock
def test_pilot_field_never_calls_the_weather_service(db_client, pilot_field):
    route = respx.get(power.POWER_URL).mock(side_effect=power_responder)
    assert db_client.post(URL, json={"field_id": pilot_field}).status_code == 200
    assert route.call_count == 0


@respx.mock
def test_non_pilot_field_counts_live_weather_and_is_flagged(db_client, kenya_field):
    route = respx.get(power.POWER_URL).mock(side_effect=power_responder)
    r = db_client.post(URL, json={"field_id": kenya_field, "mode": "seasonal_profile"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert route.call_count == 1
    assert body["pilot_coverage"] is False
    assert body["calibrated_region"] == "IE"
    assert {"outside_pilot", "drainage_unknown"} <= set(body["data_quality"])
    assert body["needs_local_review"] is True
    assert [m["month"] for m in body["months"]] == list(range(3, 11))
    assert all(m["years_total"] >= 29 for m in body["months"])  # 30 years of live history
    codes = {g["code"] for g in body["information_gaps"]}
    assert {"outside_pilot", "drainage_unknown", "risk_rules_unverified"} <= codes
    # the second request is answered from the cache
    assert db_client.post(URL, json={"field_id": kenya_field}).json()["months"] == body["months"]
    assert route.call_count == 1


@respx.mock
def test_non_pilot_without_weather_is_503(db_client, kenya_field, monkeypatch):
    monkeypatch.setattr(power, "RETRY_WAIT_S", 0)
    respx.get(power.POWER_URL).respond(503)
    r = db_client.post(URL, json={"field_id": kenya_field})
    assert r.status_code == 503 and r.json()["code"] == "climate_unavailable"


def test_geometry_instead_of_field_id(db_client):
    ring = [[-7.25, 52.65], [-7.24, 52.65], [-7.24, 52.66], [-7.25, 52.66], [-7.25, 52.65]]
    r = db_client.post(URL, json={"geometry": {"type": "Polygon", "coordinates": [ring]}})
    assert r.status_code == 200, r.text
    assert r.json()["field_id"].startswith("f_")


def test_pilot_predict_is_fast(db_client, pilot_field):
    body = {"field_id": pilot_field, "crop_id": "spring_barley"}
    db_client.post(URL, json=body)  # warm up
    timings = []
    for _ in range(20):
        started = time.perf_counter()
        assert db_client.post(URL, json=body).status_code == 200
        timings.append(time.perf_counter() - started)
    assert sorted(timings)[18] < 0.3  # p95 < 300 ms (brief §9.2)


# ---------- pure functions (no DB) ----------


@pytest.mark.parametrize(
    "hit, total, low, high",
    [
        (0, 25, 0.0, 0.098),  # never seen in 25 years still allows about 1 year in 10
        (1, 25, 0.009, 0.161),
        (5, 25, 0.101, 0.358),
        (25, 25, 0.902, 1.0),
    ],
)
def test_wilson_interval(hit, total, low, high):
    got = risk.wilson_interval(hit, total)
    assert got == pytest.approx((low, high), abs=2e-3)
    assert got[0] <= hit / total <= got[1]


def _row(month_no, kind, hit, years=()):
    return {
        "calendar_month": month_no,
        "stress_type": kind,
        "years_hit": hit,
        "years_total": 25,
        "frequency": hit / 25,
        "recent_frequency": None,
        "example_years": list(years),
    }


def test_months_from_counts_picks_the_most_frequent_type():
    rows = [
        _row(7, "drought", 2, [2018, 2006]),
        _row(7, "heat", 8, [2013, 2021]),
        _row(7, "waterlogging", 0),
        _row(7, "frost", 0),
        _row(8, "drought", 3, [2022]),
        _row(8, "heat", 3, [2003]),  # a tie goes to the first type in plain.yaml type_priority
        _row(9, "drought", 0),
        _row(9, "heat", 0),
    ]
    months = {m.month: m for m in risk.months_from_counts(rows)}
    assert set(months) == {7, 8, 9}
    assert months[7].stress_types == ["heat"] and months[7].probability == pytest.approx(0.32)
    assert [c.stress_type for c in months[7].counts][:2] == ["heat", "drought"]
    assert months[8].stress_types == ["drought"]
    assert months[9].stress_types == [] and months[9].probability == 0.0
