"""POST /predict/stress-risk schemas (brief §9.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.common import DISCLAIMER, InformationGap, Provenance
from models.fields import PolygonIn


class PredictIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"field_id": "f_8c1e02ab", "mode": "seasonal_profile", "crop_id": "spring_barley"}
            ]
        },
    )

    field_id: str | None = None
    geometry: PolygonIn | None = Field(
        default=None, description="Instead of field_id: a polygon, stored as a new field"
    )
    mode: Literal["next_month", "seasonal_profile"] = "seasonal_profile"
    crop_id: str | None = Field(default=None, description="Adds crop sensitivity weighting")

    @model_validator(mode="after")
    def one_target(self) -> "PredictIn":
        if (self.field_id is None) == (self.geometry is None):
            raise ValueError("code=field_input_ambiguous: Send either field_id or geometry.")
        return self


class Driver(BaseModel):
    feature: str
    value: float | None
    contribution: float | None
    text: str = Field(description="Farmer words, written by the ML package")


class MonthRiskOut(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int | None = Field(default=None, description="Only for mode=next_month")
    probability: float
    interval: tuple[float, float]
    stress_types: list[str]
    drivers: list[Driver]
    crop_sensitivity: float | None
    crop_weighted_risk: float | None
    level: Literal["low", "medium", "high"]
    label: str = Field(examples=["Dry"], description="OK | Dry | Wet | Heat | Frost | Unclear")
    frequency_text: str = Field(examples=["about 2 years in 10"])
    aria_label: str


class Trend(BaseModel):
    per_decade: float
    direction: Literal["increasing", "decreasing", "stable"]
    months_affected: list[int]


class PredictOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    field_id: str
    mode: Literal["next_month", "seasonal_profile"]
    crop_id: str | None
    model_version: str
    calibrated_region: str = "IE"
    pilot_coverage: bool
    headline: str
    months: list[MonthRiskOut]
    riskiest_month: int | None
    trend: Trend | None
    data_quality: list[str]
    information_gaps: list[InformationGap]
    needs_local_review: bool
    disclaimer: str = DISCLAIMER
    provenance: list[Provenance]
