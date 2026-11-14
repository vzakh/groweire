"""Place search schemas (brief §9.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

OSM_ATTRIBUTION = "© OpenStreetMap contributors"
GEONAMES_ATTRIBUTION = "GeoNames (CC BY 4.0)"


class Place(BaseModel):
    name: str = Field(examples=["Bagenalstown, County Carlow"])
    lon: float
    lat: float
    bbox: list[float] | None = Field(default=None, description="[west, south, east, north]")
    kind: str = Field(examples=["town"])


class PlacesOut(BaseModel):
    results: list[Place]
    attribution: str = Field(examples=[OSM_ATTRIBUTION])
    source: Literal["osm", "geonames"]
