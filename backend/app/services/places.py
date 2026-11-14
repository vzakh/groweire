"""Place search: cache -> Nominatim (under the shared token) -> local gazetteer (task 22b)."""

from __future__ import annotations

import re

import httpx
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from clients import nominatim
from clients.cache import Cache
from core.errors import AppError, UpstreamError
from models.places import GEONAMES_ATTRIBUTION, OSM_ATTRIBUTION, PlacesOut

TTL_S = 30 * 86_400
_SPACES = re.compile(r"\s+")

_GAZETTEER = text("""
    SELECT name, county, kind, ST_X(geom) AS lon, ST_Y(geom) AS lat
    FROM gazetteer
    WHERE lower(ascii_name) % :q
    ORDER BY similarity(lower(ascii_name), :q) DESC, population DESC
    LIMIT 5
    """)


def normalise(q: str) -> str:
    return _SPACES.sub(" ", q).strip().lower()


def _gazetteer(session_factory, q: str) -> list[dict]:
    with session_factory() as session:
        rows = session.execute(_GAZETTEER, {"q": q}).mappings().all()
    return [
        {
            "name": f"{r['name']}, {r['county']}" if r["county"] else r["name"],
            "lon": round(r["lon"], 5),
            "lat": round(r["lat"], 5),
            "bbox": None,
            "kind": r["kind"],
        }
        for r in rows
    ]


async def search(q: str, http: httpx.AsyncClient, cache: Cache, session_factory) -> PlacesOut:
    key = f"places:v1:{normalise(q)}"
    cached = await cache.get(key)
    if cached is not None:
        return PlacesOut(results=cached, attribution=OSM_ATTRIBUTION, source="osm")

    asked_osm = False
    if await nominatim.acquire_token(cache.redis):
        try:
            results = await nominatim.search(http, normalise(q))
            asked_osm = True
            if results:
                await cache.set(key, results, TTL_S)
                return PlacesOut(results=results, attribution=OSM_ATTRIBUTION, source="osm")
        except UpstreamError:
            pass

    local = await run_in_threadpool(_gazetteer, session_factory, normalise(q))
    if local:
        return PlacesOut(results=local, attribution=GEONAMES_ATTRIBUTION, source="geonames")
    if asked_osm:  # OSM answered "nothing": the UI says "Tap the map instead"
        return PlacesOut(results=[], attribution=OSM_ATTRIBUTION, source="osm")
    raise AppError(
        "place_search_busy",
        "Place search is busy right now. Tap the map instead, or try again in a moment.",
        status=503,
    )
