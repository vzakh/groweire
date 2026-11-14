"""ISRIC SoilGrids point query, unit-converted and cached forever (plan 20 task 22)."""

from __future__ import annotations

import httpx
from loguru import logger
from pydantic import BaseModel, ValidationError
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from clients.cache import Cache
from core.errors import UpstreamError
from core.metrics import EXTERNAL_ERRORS

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
TIMEOUT = httpx.Timeout(15, connect=5)
ATTEMPTS = 3  # 1 try + 2 retries (the beta API can be slow)
RETRY_WAIT_S = 0.5  # tests set this to 0
DEPTHS = {"0-5cm": 5.0, "5-15cm": 10.0, "15-30cm": 15.0}  # label -> thickness (weight)
# Same divisors as the ML download script: mapped units -> clay/sand/silt %, soc g/kg, pH, g/cm3.
DIVISORS = {"clay": 10, "sand": 10, "silt": 10, "soc": 10, "phh2o": 10, "bdod": 100}


class _Retryable(Exception):
    pass


class _Values(BaseModel):
    mean: float | None = None
    uncertainty: float | None = None


class _Depth(BaseModel):
    label: str
    values: _Values


class _Layer(BaseModel):
    name: str
    depths: list[_Depth]


class _Properties(BaseModel):
    layers: list[_Layer]


class _SoilResponse(BaseModel):
    properties: _Properties


def cache_key(lat: float, lon: float) -> str:
    return f"soil:v1:{lat:.3f}:{lon:.3f}"


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (_Retryable, httpx.TimeoutException, httpx.TransportError))


def _weighted(layer: _Layer, attr: str) -> float | None:
    pairs = [
        (getattr(d.values, attr), DEPTHS[d.label])
        for d in layer.depths
        if d.label in DEPTHS and getattr(d.values, attr) is not None
    ]
    if not pairs:
        return None
    return sum(v * w for v, w in pairs) / sum(w for _, w in pairs)


async def _request(http: httpx.AsyncClient, lat: float, lon: float) -> dict:
    params = [("lon", lon), ("lat", lat)]
    params += [("property", p) for p in DIVISORS]
    params += [("depth", d) for d in DEPTHS]
    params += [("value", "mean"), ("value", "uncertainty")]
    response = await http.get(SOILGRIDS_URL, params=params, timeout=TIMEOUT)
    if response.status_code == 429 or response.status_code >= 500:
        raise _Retryable(f"status {response.status_code}")
    response.raise_for_status()
    parsed = _SoilResponse.model_validate(response.json())
    out: dict = {name: None for name in DIVISORS}
    uncertainty: dict = {}
    for layer in parsed.properties.layers:
        if layer.name not in DIVISORS:
            continue
        mean = _weighted(layer, "mean")
        if mean is not None:
            out[layer.name] = round(mean / DIVISORS[layer.name], 3)
        unc = _weighted(layer, "uncertainty")
        if unc is not None:
            uncertainty[layer.name] = round(unc / DIVISORS[layer.name], 3)
    out["uncertainty"] = uncertainty
    return out


async def fetch_soil(http: httpx.AsyncClient, cache: Cache, lat: float, lon: float) -> dict:
    """{clay, sand, silt [%], soc [g/kg], phh2o, bdod [g/cm3], uncertainty{}} for 0-30 cm.

    A value is None where SoilGrids has no data (urban, water): an information gap.
    Raises UpstreamError("soilgrids_unavailable").
    """
    lat, lon = round(lat, 3), round(lon, 3)

    async def load() -> dict:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(ATTEMPTS),
                wait=wait_exponential(multiplier=RETRY_WAIT_S, max=4),
                retry=retry_if_exception(_is_retryable),
                reraise=True,
            ):
                with attempt:
                    return await _request(http, lat, lon)
        except (_Retryable, httpx.HTTPError, ValidationError, ValueError) as exc:
            logger.warning("external_api_error source=soilgrids error={}", type(exc).__name__)
            EXTERNAL_ERRORS.labels(source="soilgrids").inc()
            raise UpstreamError("soilgrids_unavailable", str(exc)) from exc
        raise UpstreamError("soilgrids_unavailable")

    return await cache.get_or_set(cache_key(lat, lon), None, load)
