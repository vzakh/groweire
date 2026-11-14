"""POST /rotations/compare schemas (brief §9.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.common import DISCLAIMER, InformationGap, Provenance

Priority = Literal[
    "income_stability",
    "simplicity",
    "soil_cover",
    "water_use",
    "forage_value",
    "nitrogen_fixing",
    "pest_break",
    "market_suitability",
]
Change = Literal["lower", "same", "higher"]
Amount = Literal["less", "same", "more"]


class Constraints(BaseModel):
    """`null` means "not asked": it becomes an information gap, not a filter."""

    model_config = ConfigDict(extra="forbid")

    has_livestock: bool | None = None
    irrigation: bool | None = None
    equipment: list[str] | None = Field(default=None, max_length=30)
    excluded_crops: list[str] = Field(default_factory=list, max_length=20)
    must_include: list[str] = Field(default_factory=list, max_length=4)
    market_contracts: list[str] = Field(default_factory=list, max_length=10)


class CompareIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "field_id": "f_8c1e02ab",
                    "current_rotation": ["spring_barley"] * 4,
                    "priorities": ["income_stability", "simplicity", "soil_cover"],
                    "constraints": {
                        "has_livestock": True,
                        "irrigation": False,
                        "equipment": None,
                        "excluded_crops": ["potatoes"],
                        "must_include": [],
                        "market_contracts": ["malting_barley"],
                    },
                    "n_alternatives": 3,
                }
            ]
        },
    )

    field_id: str
    current_rotation: list[str] = Field(min_length=1, max_length=8)
    priorities: list[Priority] = Field(
        default_factory=list, max_length=3, description="Ordered top-3; weights 3, 2, 1 (D18)"
    )
    constraints: Constraints = Field(default_factory=Constraints)
    n_alternatives: int = Field(default=3, ge=1, le=5)

    @field_validator("priorities")
    @classmethod
    def unique_priorities(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("code=duplicate_priorities: Each priority can be picked only once.")
        return value


class CoverCropUse(BaseModel):
    after_year: int = Field(description="1-based year whose harvest the cover crop follows")
    crop_id: str


class RuleCompliance(BaseModel):
    ie_crop_rotation_2_of_4: bool
    two_crop_rule_10_30ha: bool | None = Field(
        default=None, description="null: the farm's tillage area is not known"
    )


class Metrics(BaseModel):
    bare_months_per_year: float
    crop_weighted_stress: float
    water_demand_mm: float | None
    workability_risk: float
    erosion_index: float | None
    n_fixing_years: int
    pest_break_score: float
    organic_matter_score: float
    forage_score: float
    market_score: float
    rule_compliance: RuleCompliance


class Evidence(BaseModel):
    claim: str
    source: str = Field(description="Source id (see GET /glossary sources) or a metric name")


class Explanation(BaseModel):
    """The five blocks the challenge asks for (J2)."""

    why_suggested: str
    evidence: list[Evidence]
    benefits: list[str]
    information_gaps: list[str]
    risks_needing_local_review: list[str]


class VsCurrent(BaseModel):
    risk: Change
    bare_soil: Amount
    workload: Amount


class Strategy(BaseModel):
    id: str
    label: str
    sequence: list[str]
    cover_crops: list[CoverCropUse]
    is_current: bool
    headline: str
    one_line_why: str
    vs_current: VsCurrent | None
    score: float
    criteria: dict[str, float] = Field(description="Per-criterion score 0..1, higher = better")
    metrics: Metrics
    explanation: Explanation
    advisor_questions: list[str] = Field(min_length=2, max_length=4)


class SameCropNote(BaseModel):
    """Shown first when the farmer grows one crop every year (the cost of no rotation)."""

    text: str
    source: str | None = Field(description="Source id for the claim, or null for a plain prompt")


class CompareOut(BaseModel):
    field_id: str
    same_crop_note: SameCropNote | None = Field(
        default=None, description="Only when the current rotation is one arable crop every year"
    )
    strategies: list[Strategy]
    weights_used: dict[str, int]
    data_quality: list[str]
    information_gaps: list[InformationGap]
    needs_local_review: bool = True
    disclaimer: str = DISCLAIMER
    provenance: list[Provenance]
