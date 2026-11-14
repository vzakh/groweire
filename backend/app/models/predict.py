"""POST /predict/stress-risk schemas (brief §9.1, contract 2.0: counted risk)."""

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
    mode: Literal["seasonal_profile"] = Field(
        default="seasonal_profile",
        description="Kept for older clients. The only mode: `next_month` was removed in 2.0.",
    )
    crop_id: str | None = Field(default=None, description="Adds crop sensitivity weighting")

    @model_validator(mode="after")
    def one_target(self) -> "PredictIn":
        if (self.field_id is None) == (self.geometry is None):
            raise ValueError("code=field_input_ambiguous: Send either field_id or geometry.")
        return self


class Driver(BaseModel):
    """One counted fact behind a month (2.0: evidence, no longer a model feature)."""

    feature: str = Field(description="Stress type: drought | waterlogging | heat | frost")
    value: float | None = Field(description="Years in which it happened (years_hit)")
    contribution: float | None = Field(description="Its counted frequency, 0..1")
    text: str = Field(
        examples=["July was too dry here in 3 of the last 25 years: 2018, 2006 and 2022."],
        description="Farmer words: a sentence that can be checked against memory",
    )


class TypeCountOut(BaseModel):
    stress_type: str = Field(description="drought | waterlogging | heat | frost")
    years_hit: int
    years_total: int
    frequency: float = Field(description="years_hit / years_total")
    recent_frequency: float | None = Field(description="The same over the last 10 years")
    example_years: list[int] = Field(description="Years it happened, worst first (max 5)")


class MonthRiskOut(BaseModel):
    month: int = Field(ge=1, le=12)
    probability: float = Field(
        description="Counted frequency of the most frequent stress type in this month"
    )
    interval: tuple[float, float] = Field(
        description="90% range for that frequency, given the number of years counted"
    )
    years_hit: int = Field(description="Years the most frequent stress type happened")
    years_total: int = Field(description="Years of weather history counted")
    stress_types: list[str] = Field(
        description="The most frequent stress type; empty when nothing was counted in any year"
    )
    counts: list[TypeCountOut] = Field(description="Every stress type, most frequent first")
    drivers: list[Driver]
    crop_sensitivity: float | None
    crop_weighted_risk: float | None
    level: Literal["low", "medium", "high"]
    label: str = Field(examples=["Dry"], description="OK | Dry | Wet | Heat | Frost | Unclear")
    frequency_text: str = Field(
        examples=["about 2 years in 10"],
        description="How often the weather was like this (the counted frequency, never "
        "crop-weighted)",
    )
    aria_label: str


class Trend(BaseModel):
    per_decade: float
    direction: Literal["increasing", "decreasing", "stable"]
    months_affected: list[int]


class PredictOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    field_id: str
    mode: Literal["seasonal_profile"] = "seasonal_profile"
    method: Literal["counted_history"] = "counted_history"
    crop_id: str | None
    model_version: str = Field(
        examples=["counted-1"], description="Version of the counting rules (no trained model)"
    )
    calibrated_region: str = "IE"
    pilot_coverage: bool
    headline: str
    months: list[MonthRiskOut]
    riskiest_month: int | None
    trend: Trend | None = Field(
        default=None, description="Always null in 2.0: 25 years of counts are too few for a trend"
    )
    data_quality: list[str]
    information_gaps: list[InformationGap]
    needs_local_review: bool
    disclaimer: str = DISCLAIMER
    provenance: list[Provenance]
