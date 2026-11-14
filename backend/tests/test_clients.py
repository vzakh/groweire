"""POWER / SoilGrids clients and the cache (plan 20 task 22). All HTTP is mocked with respx."""

from __future__ import annotations

import math
from datetime import date

import httpx
import pytest
import respx
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from agrolens_ml import MONTHLY_INPUT_COLUMNS, POWER_DAILY_PARAMETERS, power_daily_to_monthly
from clients import power, soilgrids
from clients.cache import Cache
from core.errors import UpstreamError
from testing import BrokenRedis, FakeRedis, power_payload, soil_payload

START, END = date(2024, 1, 1), date(2024, 3, 31)


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(power, "RETRY_WAIT_S", 0)
    monkeypatch.setattr(soilgrids, "RETRY_WAIT_S", 0)


@pytest.fixture
def cache():
    return Cache(FakeRedis())


@pytest.fixture
async def http():
    async with httpx.AsyncClient() as client:
        yield client


def test_snap_to_power_grid():
    assert power.snap(52.705, -6.955) == (52.5, -6.875)
    assert power.snap(52.76, -7.2) == (53.0, -7.5)


@respx.mock
async def test_power_happy_path_and_cache_hit(http, cache):
    route = respx.get(power.POWER_URL).respond(json=power_payload(START, END))
    first = await power.fetch_daily(http, cache, 52.705, -6.955, START, END)
    second = await power.fetch_daily(http, cache, 52.71, -6.96, START, END)  # same grid node
    assert route.call_count == 1
    assert first == second
    sent = route.calls[0].request.url.params
    assert sent["parameters"] == ",".join(POWER_DAILY_PARAMETERS)
    assert sent["community"] == "AG"
    assert (sent["latitude"], sent["longitude"]) == ("52.5", "-6.875")
    assert first["elevation_m"] == 60.0

    monthly = power_daily_to_monthly(power.daily_frame(first), elev_m=60.0, lat=52.7)
    assert tuple(monthly.columns) == MONTHLY_INPUT_COLUMNS
    assert len(monthly) == 3


@respx.mock
async def test_power_fill_value_becomes_none(http, cache):
    respx.get(power.POWER_URL).respond(json=power_payload(START, END, fill_days=("20240102",)))
    got = await power.fetch_daily(http, cache, 52.7, -6.9, START, END)
    assert got["parameter"]["T2M"]["20240102"] is None
    assert got["parameter"]["T2M"]["20240103"] is not None
    assert math.isnan(power.daily_frame(got).loc[1, "T2M"])


@respx.mock
async def test_power_timeout_is_an_upstream_error_and_not_cached(http, cache):
    route = respx.get(power.POWER_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(UpstreamError) as err:
        await power.fetch_daily(http, cache, 52.7, -6.9, START, END)
    assert err.value.code == "power_unavailable"
    assert route.call_count == power.ATTEMPTS
    assert not cache.redis.store


@respx.mock
async def test_power_429_is_retried(http, cache):
    route = respx.get(power.POWER_URL).mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json=power_payload(START, END))]
    )
    got = await power.fetch_daily(http, cache, 52.7, -6.9, START, END)
    assert route.call_count == 2
    assert "T2M" in got["parameter"]


@respx.mock
async def test_power_400_is_not_retried(http, cache):
    route = respx.get(power.POWER_URL).respond(400)
    with pytest.raises(UpstreamError):
        await power.fetch_daily(http, cache, 52.7, -6.9, START, END)
    assert route.call_count == 1


@respx.mock
async def test_power_bad_payload_is_an_upstream_error(http, cache):
    respx.get(power.POWER_URL).respond(json={"properties": {"parameter": {"T2M": {}}}})
    with pytest.raises(UpstreamError):
        await power.fetch_daily(http, cache, 52.7, -6.9, START, END)


@respx.mock
async def test_soilgrids_units_and_cache(http, cache):
    route = respx.get(soilgrids.SOILGRIDS_URL).respond(json=soil_payload())
    soil = await soilgrids.fetch_soil(http, cache, 52.7051, -6.9552)
    again = await soilgrids.fetch_soil(http, cache, 52.7051, -6.9552)
    assert route.call_count == 1 and soil == again
    assert soil["clay"] == pytest.approx(22.0)  # 220 g/kg -> 22 %
    assert soil["phh2o"] == pytest.approx(6.4)  # 64 -> pH 6.4
    assert soil["bdod"] == pytest.approx(1.2)  # 120 cg/cm3 -> 1.2 g/cm3
    assert soil["soc"] == pytest.approx(35.0)  # 350 dg/kg -> 35 g/kg
    assert soil["uncertainty"]["clay"] > 0


@respx.mock
async def test_soilgrids_null_layers_are_gaps(http, cache):
    respx.get(soilgrids.SOILGRIDS_URL).respond(json=soil_payload(null=True))
    soil = await soilgrids.fetch_soil(http, cache, 53.35, -6.26)
    assert all(soil[k] is None for k in soilgrids.DIVISORS)


@respx.mock
async def test_soilgrids_down_is_an_upstream_error(http, cache):
    respx.get(soilgrids.SOILGRIDS_URL).respond(503)
    with pytest.raises(UpstreamError) as err:
        await soilgrids.fetch_soil(http, cache, 52.7, -6.9)
    assert err.value.code == "soilgrids_unavailable"


@pytest.mark.db
@respx.mock
async def test_redis_down_falls_back_to_postgres(http, pg_engine):
    cache = Cache(BrokenRedis(), sessionmaker(bind=pg_engine))
    route = respx.get(power.POWER_URL).respond(json=power_payload(START, END))
    first = await power.fetch_daily(http, cache, 52.7, -6.9, START, END)
    second = await power.fetch_daily(http, cache, 52.7, -6.9, START, END)
    assert route.call_count == 1 and first == second
    with pg_engine.begin() as c:
        assert c.execute(text("SELECT count(*) FROM api_cache")).scalar_one() == 1
        c.execute(text("TRUNCATE api_cache"))


@pytest.mark.db
async def test_postgres_cache_respects_ttl(pg_engine):
    cache = Cache(BrokenRedis(), sessionmaker(bind=pg_engine))
    await cache.set("k:ttl", {"a": 1}, 3600)
    assert await cache.get("k:ttl") == {"a": 1}
    with pg_engine.begin() as c:
        c.execute(text("UPDATE api_cache SET fetched_at = now() - interval '2 hours'"))
    assert await cache.get("k:ttl") is None
    with pg_engine.begin() as c:
        c.execute(text("TRUNCATE api_cache"))
