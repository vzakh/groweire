"""Health endpoints, the error shape and the request-id / body-size middleware."""

from __future__ import annotations

import pytest

from agrolens_ml import CONTRACT_VERSION, RISK_RULES_VERSION
from api.routes import health
from core.config import Settings, get_settings


def test_live(client):
    r = client.get("/api/v1/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["x-request-id"]


def test_request_id_is_echoed(client):
    r = client.get("/api/v1/health/live", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"


def test_unsafe_request_id_is_replaced(client):
    r = client.get("/api/v1/health/live", headers={"X-Request-ID": "bad id with spaces"})
    assert r.headers["x-request-id"] != "bad id with spaces"


def test_unknown_route_uses_error_shape(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"
    assert "detail" in r.json()


def test_body_over_1mb_is_rejected(client):
    r = client.post("/api/v1/health/live", content=b"x" * 1_000_001)
    assert r.status_code == 413
    assert r.json()["code"] == "payload_too_large"


@pytest.fixture
def with_source(monkeypatch):
    def _set(source, has_counts=True):
        monkeypatch.setattr(health, "_data_source", lambda _factory: source)
        monkeypatch.setattr(health, "_has_counts", lambda _factory: has_counts)

    return _set


def test_ready_needs_no_model_bundle(client, with_source):
    with_source("synthetic")
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_version"] == RISK_RULES_VERSION
    assert body["model_kind"] == "counted_history"
    assert body["data_source"] == "synthetic"
    assert body["contract_version"] == CONTRACT_VERSION
    assert body["cache"] in ("redis", "degraded")
    assert not hasattr(client.app.state, "stress_model")


def test_ready_without_counted_risks(client, with_source):
    with_source("real", has_counts=False)
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 503
    assert r.json()["code"] == "dataset_not_loaded"


def test_ready_refuses_stub_when_not_allowed(app, client, with_source):
    with_source("synthetic")
    app.dependency_overrides[get_settings] = lambda: Settings(allow_stub_model=False)
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 503
    assert r.json()["code"] == "stub_model_in_prod"


def test_ready_without_loaded_data(client, with_source):
    with_source(None)
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 503
    assert r.json()["code"] == "dataset_not_loaded"


def test_ready_when_db_is_down(client, monkeypatch):
    def boom(_factory):
        raise ConnectionError("db down")

    monkeypatch.setattr(health, "_data_source", boom)
    r = client.get("/api/v1/health/ready")
    assert r.status_code == 503
    assert r.json()["code"] == "db_unavailable"
