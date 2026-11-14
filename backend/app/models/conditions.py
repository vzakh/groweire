"""GET /fields/{id}/conditions schemas (brief §9, plan 20 task 23)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from models.common import DISCLAIMER, InformationGap, Provenance


class ClimateMonth(BaseModel):
    month: int = Field(ge=1, le=12)
    precip_mm: float | None
    tmax_c: float | None
    tmin_c: float | None
    et0_mm: float | None = Field(description="Reference evapotranspiration (FAO-56)")
    p_minus_et0_mm: float | None = Field(description="Water balance: rain minus ET0")
    frost_days: float | None
    hot_days: float | None
    heavy_rain_days: float | None


class Climate(BaseModel):
    period: str = Field(examples=["1996–2025"])
    months: list[ClimateMonth]


class Trends(BaseModel):
    """Sen's slope per decade over complete calendar years."""

    precip_mm_per_decade: float | None
    tmax_c_per_decade: float | None
    frost_days_per_decade: float | None
    n_years: int


class SoilFact(BaseModel):
    label: str = Field(examples=["Drainage"])
    text: str = Field(examples=["Drains well"])


class Soil(BaseModel):
    source: Literal["pilot_grid", "soilgrids"]
    clay: float | None = Field(description="%")
    sand: float | None = Field(description="%")
    soc: float | None = Field(description="Soil organic carbon, g/kg")
    phh2o: float | None
    bdod: float | None = Field(description="Bulk density, g/cm3")
    drainage_class: int | None = Field(description="1 (excessive) .. 5 (very poor); pilot only")
    elev_m: float | None
    slope_deg: float | None
    uncertainty: dict[str, float] | None = None
    plain: list[SoilFact] = Field(
        default_factory=list,
        description='The "Your soil" card: the values above in farmer words, no judgement',
    )


class Series(BaseModel):
    """Monthly satellite history for the field's cells (pilot only), area-weighted."""

    months: list[str] = Field(examples=[["2024-03", "2024-04"]])
    ndvi: list[float | None]
    ndvi_z: list[float | None]
    sm_rootzone: list[float | None]


class GreennessHistory(BaseModel):
    """How green the land around the field was each summer (June-August mean NDVI), pilot only."""

    years: list[int]
    summer_ndvi: list[float | None] = Field(description="null = too few clear satellite views")
    lowest_years: list[int] = Field(description="The least green summers, lowest first (max 3)")
    text: str


class ConditionsOut(BaseModel):
    field_id: str
    pilot_coverage: bool
    climate: Climate | None
    trends: Trends | None
    soil: Soil | None
    series: Series | None
    greenness_history: GreennessHistory | None = None
    data_quality: list[str]
    information_gaps: list[InformationGap]
    provenance: list[Provenance]
    disclaimer: str = DISCLAIMER
