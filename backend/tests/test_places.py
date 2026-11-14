"""GET /places (plan 20 task 22b). Nominatim is mocked; the gazetteer is the test PostGIS."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from clients import nominatim
from clients.cache import Cache
from core.errors import AppError
from services import places
from testing import FakeRedis, nominatim_payload

pytestmark = pytest.mark.db
URL = "/api/v1/places"


@pytest.fixture
def gazetteer(pg_engine):
    with pg_engine.begin() as c:
        c.execute(text("""
                INSERT INTO gazetteer (place_id, name, ascii_name, kind, county, geom, population)
                VALUES (1, 'Bagenalstown', 'Bagenalstown', 'village', 'Carlow',
                        ST_SetSRID(ST_MakePoint(-6.96, 52.70), 4326), 2950),
                       (2, 'Ballon', 'Ballon', 'village', 'Carlow',
                        ST_SetSRID(ST_MakePoint(-6.77, 52.74), 4326), 700)
                """))
    yield
    with pg_engine.begin() as c:
        c.execute(text("TRUNCATE gazetteer"))


@respx.mock
def test_happy_path_then_cache_hit(db_client):
    route = respx.get(nominatim.NOMINATIM_URL).respond(json=nominatim_payload())
    r = db_client.get(URL, params={"q": "Bagenalstown"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "osm"
    assert body["attribution"] == "© OpenStreetMap contributors"
    assert body["results"][0] == {
        "name": "Bagenalstown, County Carlow",
        "lon": -6.962,
        "lat": 52.7,
        "bbox": [-6.99, 52.68, -6.94, 52.72],
        "kind": "town",
    }
    again = db_client.get(URL, params={"q": "  bagenalstown "})  # same normalised query
    assert again.json() == body
    assert route.call_count == 1

    request = route.calls[0].request
    assert request.headers["user-agent"].startswith("AgroLens/")
    assert "python-httpx" not in request.headers["user-agent"]
    assert request.url.params["countrycodes"] == "ie,gb"
    assert request.url.params["bounded"] == "1"


@respx.mock
def test_nominatim_5xx_falls_back_to_gazetteer(db_client, gazetteer):
    route = respx.get(nominatim.NOMINATIM_URL).respond(503)
    r = db_client.get(URL, params={"q": "bagenalstown"})
    assert r.status_code == 200, r.text
    assert route.call_count == 1  # never retried
    body = r.json()
    assert body["source"] == "geonames"
    assert body["attribution"] == "GeoNames (CC BY 4.0)"
    assert body["results"][0]["name"] == "Bagenalstown, Carlow"


@respx.mock
def test_no_token_uses_gazetteer_without_http(db_client, app, gazetteer):
    route = respx.get(nominatim.NOMINATIM_URL).respond(json=nominatim_payload())
    app.state.redis.store[nominatim.BUCKET_KEY] = "1"  # the token is taken
    r = db_client.get(URL, params={"q": "bagenalstwn"})  # typo: trigram match
    assert r.status_code == 200, r.text
    assert route.call_count == 0
    assert r.json()["source"] == "geonames"


@respx.mock
def test_osm_says_nothing_and_gazetteer_is_empty(db_client):
    respx.get(nominatim.NOMINATIM_URL).respond(json=[])
    r = db_client.get(URL, params={"q": "zzzzqqq"})
    assert r.status_code == 200
    assert r.json()["results"] == []


@respx.mock
def test_busy_when_osm_skipped_and_gazetteer_empty(db_client, app):
    respx.get(nominatim.NOMINATIM_URL).respond(json=nominatim_payload())
    app.state.redis.store[nominatim.BUCKET_KEY] = "1"
    r = db_client.get(URL, params={"q": "zzzzqqq"})
    assert r.status_code == 503
    assert r.json()["code"] == "place_search_busy"


@pytest.mark.parametrize("q", ["a", "x" * 101])
def test_query_length_limits(db_client, q):
    r = db_client.get(URL, params={"q": q})
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


@respx.mock
async def test_twenty_parallel_searches_make_one_upstream_call(pg_engine):
    route = respx.get(nominatim.NOMINATIM_URL).respond(json=nominatim_payload())
    cache = Cache(FakeRedis())
    factory = sessionmaker(bind=pg_engine)

    async def one(i: int):
        try:
            return await places.search(f"place {i}", http, cache, factory)
        except AppError as exc:
            return exc.code

    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(*(one(i) for i in range(20)))
    assert route.call_count == 1  # 1 request per second for the whole app
    assert results.count("place_search_busy") == 19
