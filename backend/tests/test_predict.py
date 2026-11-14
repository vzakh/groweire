"""POST /predict/stress-risk (plan 20 task 24). Stub bundle + synthetic pilot + mocked POWER."""

from __future__ import annotations

import time

import pytest
import respx

from clients import power, soilgrids
from testing import power_responder, soil_payload

pytestmark = pytest.mark.db
URL = "/api/v1/predict/stress-risk"

# Keys of the response example in brief §9.1.
BRIEF_TOP_KEYS = {
    "model_version",
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
    "stress_types",
    "drivers",
    "crop_sensitivity",
    "crop_weighted_risk",
    "level",
    "label",
    "frequency_text",
    "aria_label",
}


def test_pilot_seasonal_profile(db_client, pilot_field):
    r = db_client.post(URL, json={"field_id": pilot_field, "mode": "seasonal_profile"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert BRIEF_TOP_KEYS <= set(body)
    assert [m["month"] for m in body["months"]] == list(range(3, 11))
    for m in body["months"]:
        assert BRIEF_MONTH_KEYS <= set(m)
        assert 0 <= m["interval"][0] <= m["probability"] <= m["interval"][1] <= 1
        assert m["crop_sensitivity"] is None and m["crop_weighted_risk"] is None
        assert {"feature", "value", "contribution", "text"} == set(m["drivers"][0])
        assert "%" not in m["frequency_text"]
    assert body["model_version"] == "stub-0"
    assert body["calibrated_region"] == "IE"
    assert body["riskiest_month"] == 7  # the stub's seasonal curve peaks in July
    assert body["headline"].startswith("July is the riskiest month for crops here.")
    assert body["trend"]["direction"] in ("increasing", "decreasing", "stable")
    assert "synthetic_data" in body["data_quality"]  # stub model + synthetic tables (brief §8.8)
    assert body["disclaimer"].startswith("This tool supports, not replaces")
    assert {p["dataset_id"] for p in body["provenance"]} >= {"modis_ndvi", "power"}


def test_crop_weighting(db_client, pilot_field):
    body = db_client.post(URL, json={"field_id": pilot_field, "crop_id": "spring_barley"}).json()
    july = next(m for m in body["months"] if m["month"] == 7)
    assert july["stress_types"] == ["drought"]
    assert july["crop_sensitivity"] == 0.8
    assert july["crop_weighted_risk"] == pytest.approx(july["probability"] * 0.8, abs=1e-3)
    assert july["label"] == "Dry"
    assert july["aria_label"].startswith("July, spring barley: dry.")
    assert "spring barley" in body["headline"]
    codes = {g["code"] for g in body["information_gaps"]}
    assert "crop_sensitivity_unverified" in codes
    march = next(m for m in body["months"] if m["month"] == 3)  # stub: type "other"
    assert march["crop_sensitivity"] is None and "crop_sensitivity_unknown" in codes


def test_unknown_crop_and_field(db_client, pilot_field):
    r = db_client.post(URL, json={"field_id": pilot_field, "crop_id": "bananas"})
    assert r.status_code == 422 and r.json()["code"] == "unknown_crop"
    r = db_client.post(URL, json={"field_id": "f_00000000"})
    assert r.status_code == 404 and r.json()["code"] == "field_not_found"
    r = db_client.post(URL, json={"mode": "seasonal_profile"})
    assert r.status_code == 422 and r.json()["code"] == "field_input_ambiguous"


@respx.mock
def test_next_month_rebuilds_from_live_power_when_stored_features_are_old(db_client, pilot_field):
    route = respx.get(power.POWER_URL).mock(side_effect=power_responder)
    r = db_client.post(URL, json={"field_id": pilot_field, "mode": "next_month"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert route.call_count == 1
    assert len(body["months"]) == 1 and body["months"][0]["year"] is not None
    assert "live_weather_only" in body["data_quality"]
    assert body["trend"] is None


@respx.mock
def test_non_pilot_field_is_flagged_not_calibrated(db_client, kenya_field):
    respx.get(power.POWER_URL).mock(side_effect=power_responder)
    respx.get(soilgrids.SOILGRIDS_URL).respond(json=soil_payload())
    r = db_client.post(URL, json={"field_id": kenya_field, "mode": "seasonal_profile"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pilot_coverage"] is False
    assert body["calibrated_region"] == "IE"
    assert "outside_pilot" in body["data_quality"]
    assert body["needs_local_review"] is True
    assert [m["month"] for m in body["months"]] == list(range(3, 11))
    assert "outside_pilot" in {g["code"] for g in body["information_gaps"]}


@respx.mock
def test_non_pilot_without_weather_is_503(db_client, kenya_field, monkeypatch):
    monkeypatch.setattr(power, "RETRY_WAIT_S", 0)
    respx.get(power.POWER_URL).respond(503)
    respx.get(soilgrids.SOILGRIDS_URL).respond(json=soil_payload())
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
