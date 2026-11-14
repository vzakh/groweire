"""GET /crops schemas (brief §9): what the crop picker needs, not the whole catalogue."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.common import DISCLAIMER, Provenance


class CropOut(BaseModel):
    id: str = Field(examples=["spring_barley"])
    name: str = Field(examples=["Spring barley"])
    family: str
    season: str = Field(description="spring | winter | perennial | cover")
    role: str = Field(description="main | cover")
    sow_months: list[int]
    harvest_months: list[int]
    n_fixing: bool
    forage_value: str
    requires_livestock: bool
    market: list[str]
    sources: list[str]


class CropsOut(BaseModel):
    region: str = "IE"
    crops: list[CropOut]
    disclaimer: str = DISCLAIMER
    provenance: list[Provenance]
