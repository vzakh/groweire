"""Fakes for tests and for the fixture export: no network, no real data (brief rule 3).

The payloads have the SHAPE of the real upstream responses; the numbers are invented.
"""

from __future__ import annotations

import math
import time
from datetime import date, datetime, timedelta

import httpx

from agrolens_ml import POWER_DAILY_PARAMETERS


class FakeRedis:
    """The few async Redis calls the app uses, in memory."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.expires: dict[str, float] = {}

    def _alive(self, key) -> bool:
        if key in self.expires and time.monotonic() >= self.expires[key]:
            self.store.pop(key, None)
            self.expires.pop(key, None)
        return key in self.store

    async def get(self, key):
        return self.store[key] if self._alive(key) else None

    async def set(self, key, value, ex=None, px=None, nx=False):
        if nx and self._alive(key):
            return None
        self.store[key] = value
        self.expires.pop(key, None)
        if px or ex:
            self.expires[key] = time.monotonic() + (px / 1000 if px else ex)
        return True

    async def delete(self, key):
        self.store.pop(key, None)

    async def ping(self):
        return True

    async def aclose(self):
        return None


class BrokenRedis:
    """Redis that is down: every call fails."""

    async def _fail(self, *_args, **_kwargs):
        raise ConnectionError("redis down")

    get = set = delete = ping = _fail

    async def aclose(self):
        return None


def _daily_values(day: date, lat: float) -> dict[str, float]:
    """A smooth, deterministic seasonal year. Invented numbers in plausible ranges."""
    doy = day.timetuple().tm_yday
    season = math.cos(2 * math.pi * (doy - 200) / 365.25) * (1 if lat >= 0 else -1)  # +1 midsummer
    wobble = math.sin(day.toordinal() * 0.9) * 0.5 + math.sin(day.toordinal() * 0.23) * 0.5
    t2m = 10 + 5.5 * season + 2 * wobble
    wet = (day.toordinal() * 7 + day.year) % 5 in (0, 1)
    return {
        "T2M": t2m,
        "T2M_MAX": t2m + 4 + season,
        "T2M_MIN": t2m - 4,
        "PRECTOTCORR": round((6.0 - 2 * season + 3 * wobble) if wet else 0.0, 2),
        "RH2M": 82 - 6 * season,
        "WS2M": 4.5 - season + 0.5 * wobble,
        "ALLSKY_SFC_SW_DWN": 9 + 8 * season,
        "GWETROOT": 0.7 - 0.12 * season,
        "GWETTOP": 0.68 - 0.15 * season,
        "T2MDEW": t2m - 2.5,
    }


def power_payload(
    start: date, end: date, lat: float = 52.5, lon: float = -6.875, fill_days: tuple = ()
) -> dict:
    """A POWER `/temporal/daily/point` JSON body for [start, end]."""
    parameter: dict[str, dict[str, float]] = {p: {} for p in POWER_DAILY_PARAMETERS}
    day = start
    while day <= end:
        key = f"{day:%Y%m%d}"
        values = _daily_values(day, lat)
        for name in POWER_DAILY_PARAMETERS:
            parameter[name][key] = -999.0 if key in fill_days else round(values[name], 2)
        day += timedelta(days=1)
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat, 60.0]},
        "properties": {"parameter": parameter},
    }


_SOIL_MAPPED = {"clay": 220, "sand": 400, "silt": 380, "soc": 350, "phh2o": 64, "bdod": 120}


def soil_payload(null: bool = False) -> dict:
    """A SoilGrids `properties/query` JSON body (mapped units, three depths)."""
    layers = []
    for name, value in _SOIL_MAPPED.items():
        depths = [
            {
                "label": label,
                "values": {
                    "mean": None if null else value,
                    "uncertainty": None if null else max(1, value // 10),
                },
            }
            for label in ("0-5cm", "5-15cm", "15-30cm")
        ]
        layers.append({"name": name, "depths": depths})
    return {"type": "Feature", "properties": {"layers": layers}}


def nominatim_payload() -> list[dict]:
    """A Nominatim `search?format=jsonv2&addressdetails=1` body for "Bagenalstown"."""
    return [
        {
            "place_id": 1,
            "name": "Bagenalstown",
            "display_name": "Bagenalstown, County Carlow, Leinster, Ireland",
            "lat": "52.7000",
            "lon": "-6.9620",
            "boundingbox": ["52.68", "52.72", "-6.99", "-6.94"],
            "category": "place",
            "type": "town",
            "addresstype": "town",
            "address": {"town": "Bagenalstown", "county": "County Carlow", "country": "Ireland"},
        }
    ]


def power_responder(request: httpx.Request) -> httpx.Response:
    """respx side effect: answer any POWER daily request with a payload for its own range."""
    params = request.url.params
    start = datetime.strptime(params["start"], "%Y%m%d").date()
    end = datetime.strptime(params["end"], "%Y%m%d").date()
    body = power_payload(start, end, float(params["latitude"]), float(params["longitude"]))
    return httpx.Response(200, json=body)
