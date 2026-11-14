"""GET /fields/{id}/conditions (plan 20 task 23)."""

from __future__ import annotations

import httpx
import pytest
import respx

from clients import power, soilgrids
from services.conditions import sens_slope
from testing import power_responder, soil_payload

pytestmark = pytest.mark.db


def test_sens_slope():
    assert sens_slope([1, 2, 3, 4]) == pytest.approx(1.0)
    assert sens_slope([1, 2, 30, 4, 5]) == pytest.approx(1.0)  # robust to one outlier
    assert sens_slope([5]) is None


@respx.mock
def test_pilot_field(db_client, pilot_field):
    route = respx.get(power.POWER_URL).mock(side_effect=power_responder)
    soil_route = respx.get(soilgrids.SOILGRIDS_URL).respond(json=soil_payload())
    r = db_client.get(f"/api/v1/fields/{pilot_field}/conditions")
    assert r.status_code == 200, r.text
    body = r.json()

    assert [m["month"] for m in body["climate"]["months"]] == list(range(1, 13))
    july = body["climate"]["months"][6]
    assert july["tmax_c"] > body["climate"]["months"][0]["tmax_c"]
    assert july["et0_mm"] > 0
    assert july["p_minus_et0_mm"] == pytest.approx(july["precip_mm"] - july["et0_mm"], abs=0.2)
    assert body["trends"]["n_years"] >= 29

    assert body["soil"]["source"] == "pilot_grid"
    assert soil_route.call_count == 0  # pilot fields use the grid's soil, no live call
    assert 0 < body["soil"]["clay"] < 100

    series = body["series"]
    assert len(series["months"]) == len(series["ndvi"]) == len(series["sm_rootzone"]) > 0
    assert body["data_quality"] == ["synthetic_data"]
    assert {p["dataset_id"] for p in body["provenance"]} >= {"power", "modis_ndvi", "smap"}
    assert body["disclaimer"].startswith("This tool supports, not replaces")
    assert "no_soil_test" in {g["code"] for g in body["information_gaps"]}

    # Warm call: served from the cache, no second POWER request.
    again = db_client.get(f"/api/v1/fields/{pilot_field}/conditions")
    assert again.json() == body
    assert route.call_count == 1


@respx.mock
def test_non_pilot_field_has_no_series_and_says_so(db_client, kenya_field):
    respx.get(power.POWER_URL).mock(side_effect=power_responder)
    soil_route = respx.get(soilgrids.SOILGRIDS_URL).respond(json=soil_payload())
    body = db_client.get(f"/api/v1/fields/{kenya_field}/conditions").json()
    assert body["pilot_coverage"] is False
    assert body["series"] is None
    assert "outside_pilot" in body["data_quality"]
    assert "outside_pilot" in {g["code"] for g in body["information_gaps"]}
    assert body["soil"]["source"] == "soilgrids"
    assert body["soil"]["uncertainty"]["clay"] > 0
    assert soil_route.call_count == 1
    assert body["climate"] is not None


@respx.mock
def test_upstreams_down_become_information_gaps(db_client, kenya_field, monkeypatch):
    monkeypatch.setattr(power, "RETRY_WAIT_S", 0)
    monkeypatch.setattr(soilgrids, "RETRY_WAIT_S", 0)
    respx.get(power.POWER_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    respx.get(soilgrids.SOILGRIDS_URL).respond(503)
    r = db_client.get(f"/api/v1/fields/{kenya_field}/conditions")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["climate"] is None and body["trends"] is None and body["soil"] is None
    codes = {g["code"] for g in body["information_gaps"]}
    assert {"climate_unavailable", "soil_unavailable"} <= codes


def test_unknown_field_and_bad_years(db_client, pilot_field):
    r = db_client.get("/api/v1/fields/f_00000000/conditions")
    assert r.status_code == 404 and r.json()["code"] == "field_not_found"
    r = db_client.get(f"/api/v1/fields/{pilot_field}/conditions", params={"years": 99})
    assert r.status_code == 422
