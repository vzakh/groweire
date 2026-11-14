"""NASA POWER daily point data, validated and cached (plan 20 task 22)."""

from __future__ import annotations

import hashlib
from datetime import date

import httpx
import pandas as pd
from loguru import logger
from pydantic import BaseModel, ValidationError
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from agrolens_ml import POWER_DAILY_PARAMETERS
from clients.cache import Cache
from core.errors import UpstreamError
from core.metrics import EXTERNAL_ERRORS

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
TIMEOUT = httpx.Timeout(20, connect=5)
TTL_S = 30 * 86_400
FILL_VALUE = -999.0
ATTEMPTS = 3
RETRY_WAIT_S = 0.5  # tests set this to 0
GRID_LAT, GRID_LON = 0.5, 0.625  # POWER meteorology grid (MERRA-2)


class _Retryable(Exception):
    pass


class _Geometry(BaseModel):
    coordinates: list[float]


class _Properties(BaseModel):
    parameter: dict[str, dict[str, float | None]]


class _PowerResponse(BaseModel):
    geometry: _Geometry | None = None
    properties: _Properties


def snap(lat: float, lon: float) -> tuple[float, float]:
    """Nearest POWER grid node. Points in one grid box share one cached response."""
    return round(round(lat / GRID_LAT) * GRID_LAT, 3), round(round(lon / GRID_LON) * GRID_LON, 4)


def cache_key(lat: float, lon: float, start: date, end: date) -> str:
    params_hash = hashlib.sha256(",".join(POWER_DAILY_PARAMETERS).encode()).hexdigest()[:8]
    return f"power:v1:{lat:.3f}:{lon:.4f}:{start:%Y%m%d}:{end:%Y%m%d}:{params_hash}"


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (_Retryable, httpx.TimeoutException, httpx.TransportError))


async def _request(http: httpx.AsyncClient, lat: float, lon: float, start: date, end: date) -> dict:
    response = await http.get(
        POWER_URL,
        params={
            "parameters": ",".join(POWER_DAILY_PARAMETERS),  # never a local copy
            "community": "AG",
            "latitude": lat,
            "longitude": lon,
            "start": f"{start:%Y%m%d}",
            "end": f"{end:%Y%m%d}",
            "format": "JSON",
        },
        timeout=TIMEOUT,
    )
    if response.status_code == 429 or response.status_code >= 500:
        raise _Retryable(f"status {response.status_code}")
    response.raise_for_status()
    parsed = _PowerResponse.model_validate(response.json())
    missing = [p for p in POWER_DAILY_PARAMETERS if p not in parsed.properties.parameter]
    if missing:
        raise ValueError(f"POWER response lacks {missing}")
    coords = parsed.geometry.coordinates if parsed.geometry else []
    return {
        "lat": lat,
        "lon": lon,
        "elevation_m": coords[2] if len(coords) > 2 and coords[2] != FILL_VALUE else None,
        "parameter": {
            name: {day: (None if v is None or v == FILL_VALUE else v) for day, v in series.items()}
            for name, series in parsed.properties.parameter.items()
            if name in POWER_DAILY_PARAMETERS
        },
    }


async def fetch_daily(
    http: httpx.AsyncClient, cache: Cache, lat: float, lon: float, start: date, end: date
) -> dict:
    """{lat, lon, elevation_m, parameter: {NAME: {YYYYMMDD: float | None}}} for the grid node.

    Raises UpstreamError("power_unavailable"); services turn that into an information gap.
    """
    node_lat, node_lon = snap(lat, lon)

    async def load() -> dict:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(ATTEMPTS),
                wait=wait_exponential(multiplier=RETRY_WAIT_S, max=4),
                retry=retry_if_exception(_is_retryable),
                reraise=True,
            ):
                with attempt:
                    return await _request(http, node_lat, node_lon, start, end)
        except (_Retryable, httpx.HTTPError, ValidationError, ValueError) as exc:
            logger.warning("external_api_error source=power error={}", type(exc).__name__)
            EXTERNAL_ERRORS.labels(source="power").inc()
            raise UpstreamError("power_unavailable", str(exc)) from exc
        raise UpstreamError("power_unavailable")

    return await cache.get_or_set(cache_key(node_lat, node_lon, start, end), TTL_S, load)


def daily_frame(payload: dict) -> pd.DataFrame:
    """fetch_daily payload -> DataFrame[date, *POWER_DAILY_PARAMETERS] (None -> NaN).

    This is the `daily` input of agrolens_ml.power_daily_to_monthly.
    """
    df = pd.DataFrame({p: payload["parameter"][p] for p in POWER_DAILY_PARAMETERS}, dtype="float64")
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    return df.sort_index().rename_axis("date").reset_index()
