"""Layers, glossary, metrics, OpenAPI and the unhandled-error shape (plan 20 task 27)."""

from __future__ import annotations

import json

import pytest

from core.config import REPO_ROOT

EXPECTED_PATHS = {
    "/api/v1/health/live",
    "/api/v1/health/ready",
    "/api/v1/places",
    "/api/v1/fields",
    "/api/v1/fields/{field_id}",
    "/api/v1/fields/{field_id}/conditions",
    "/api/v1/predict/stress-risk",
    "/api/v1/crops",
    "/api/v1/rotations/compare",
    "/api/v1/layers",
    "/api/v1/layers/stress-risk",
    "/api/v1/glossary",
}


def test_openapi_lists_every_endpoint_of_the_brief(client):
    schema = client.get("/api/v1/openapi.json").json()
    assert set(schema["paths"]) == EXPECTED_PATHS  # one versioned prefix, no hidden routes


def test_committed_openapi_is_up_to_date(app):
    committed = REPO_ROOT / "backend" / "openapi.json"
    if not committed.exists():
        pytest.skip("backend/openapi.json not exported yet (make openapi)")
    assert json.loads(committed.read_text(encoding="utf-8")) == app.openapi(), "run `make openapi`"


def test_layers(client):
    body = client.get("/api/v1/layers").json()
    ids = [layer["id"] for layer in body["layers"]]
    assert ids == ["true_colour", "ndvi", "soil_moisture", "stress_risk"]
    for layer in body["layers"][:3]:
        assert layer["url_template"].startswith(
            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
        )
        assert layer["gibs_identifier"] in layer["url_template"]
        assert layer["tile_matrix_set"] in layer["url_template"]


def test_glossary_covers_the_challenge_terms(client):
    terms = client.get("/api/v1/glossary").json()["terms"]
    technical = " ".join(t["term"] for t in terms)
    for needed in ("NDVI", "Evapotranspiration", "Soil-moisture", "Frost", "Water balance"):
        assert needed in technical
    assert all(t["title"] and t["text"] for t in terms)


@pytest.mark.db
def test_stress_risk_layer(db_client):
    r = db_client.get("/api/v1/layers/stress-risk", params={"month": 7})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "FeatureCollection" and len(body["features"]) > 100
    feature = body["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert {"cell_id", "p", "level", "dominant_type"} <= set(feature["properties"])
    assert body["data_quality"] == ["synthetic_data"]
    assert db_client.get("/api/v1/layers/stress-risk", params={"month": 12}).status_code == 422


def test_big_responses_are_gzipped(client):
    r = client.get("/api/v1/crops", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"


def test_metrics_endpoint(client):
    client.get("/api/v1/crops")
    text = client.get("/metrics").text
    assert "http_request" in text
    assert "stress_model_predictions_total" in text
    assert "external_api_errors_total" in text or "cache_hits_total" in text


def test_unhandled_error_hides_the_traceback(app):
    from fastapi.testclient import TestClient  # pylint: disable=import-outside-toplevel

    @app.get("/api/v1/_boom", include_in_schema=False)
    def boom():
        raise RuntimeError("secret detail")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/v1/_boom")
    assert r.status_code == 500
    assert r.json() == {"detail": "Something went wrong on our side.", "code": "internal_error"}
    assert "secret" not in r.text
