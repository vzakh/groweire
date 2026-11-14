"""OSM Nominatim place search, inside its usage policy (brief D20, plan 20 task 22b).

- one request per second for the WHOLE app (shared Redis token), never retried;
- an identifying User-Agent (set on the shared httpx client in main.py);
- search on submit only: no autocomplete, no batches.
"""

from __future__ import annotations

import asyncio
import time

import httpx
from loguru import logger
from pydantic import BaseModel, ValidationError

from core.errors import UpstreamError
from core.metrics import EXTERNAL_ERRORS

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIMEOUT = httpx.Timeout(5, connect=3)
VIEWBOX = "-10.7,55.5,-5.4,51.3"  # island of Ireland (brief D1)
BUCKET_KEY = "places:bucket"
BUCKET_MS = 1000  # 1 token per second, capacity 1
TOKEN_WAIT_S = 0.3
_POLL_S = 0.05
_local_last_call = 0.0  # fallback limiter when Redis is down (per process)


class _Item(BaseModel):
    display_name: str
    lat: float
    lon: float
    boundingbox: list[float] | None = None
    name: str | None = None
    type: str | None = None
    addresstype: str | None = None
    address: dict[str, str] | None = None


async def _try_token(redis) -> bool:
    global _local_last_call  # pylint: disable=global-statement
    try:
        return bool(await redis.set(BUCKET_KEY, "1", nx=True, px=BUCKET_MS))
    except Exception:  # pylint: disable=broad-except
        now = time.monotonic()
        if now - _local_last_call >= BUCKET_MS / 1000:
            _local_last_call = now
            return True
        return False


async def acquire_token(redis) -> bool:
    """True if we may call Nominatim now; waits at most 300 ms for the shared token."""
    deadline = time.monotonic() + TOKEN_WAIT_S
    while True:
        if await _try_token(redis):
            return True
        if time.monotonic() + _POLL_S > deadline:
            return False
        await asyncio.sleep(_POLL_S)


def _to_result(item: _Item) -> dict:
    address = item.address or {}
    name = item.name or item.display_name.split(",")[0].strip()
    county = address.get("county") or address.get("state_district")
    label = f"{name}, {county}" if county and county != name else name
    out = {
        "name": label,
        "lon": round(item.lon, 5),
        "lat": round(item.lat, 5),
        "kind": item.addresstype or item.type or "place",
        "bbox": None,
    }
    if item.boundingbox and len(item.boundingbox) == 4:
        south, north, west, east = item.boundingbox
        out["bbox"] = [round(west, 5), round(south, 5), round(east, 5), round(north, 5)]
    return out


async def search(http: httpx.AsyncClient, q: str) -> list[dict]:
    """Up to 5 places for `q`. The caller must hold a token. Raises UpstreamError."""
    try:
        response = await http.get(
            NOMINATIM_URL,
            params={
                "q": q,
                "format": "jsonv2",
                "countrycodes": "ie,gb",
                "viewbox": VIEWBOX,
                "bounded": 1,
                "limit": 5,
                "addressdetails": 1,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        items = [_Item.model_validate(raw) for raw in response.json()]
    except (httpx.HTTPError, ValidationError, ValueError, TypeError) as exc:
        logger.warning("external_api_error source=nominatim error={}", type(exc).__name__)
        EXTERNAL_ERRORS.labels(source="nominatim").inc()
        raise UpstreamError("nominatim_unavailable", str(exc)) from exc
    return [_to_result(item) for item in items[:5]]
