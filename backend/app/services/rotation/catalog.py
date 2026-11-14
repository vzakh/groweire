"""Crop catalogue + rotation templates: loaded and validated once at startup (plan 20 task 25).

Hard rule 1: a number without a source is refused here, so it can never reach a farmer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.config import APP_DIR

DATA_DIR = APP_DIR / "data"
STRESS_KINDS = ("drought", "waterlogging", "heat", "frost")
Month = int


class Calendar(BaseModel):
    sow_months: list[Month]
    harvest_months: list[Month]
    ground_cover_months: list[Month]
    source: str

    @model_validator(mode="after")
    def months_in_range(self) -> "Calendar":
        for m in (*self.sow_months, *self.harvest_months, *self.ground_cover_months):
            if not 1 <= m <= 12:
                raise ValueError(f"calendar month {m} is not in 1..12")
        return self


class Kc(BaseModel):
    """FAO-56 single crop coefficient. `stage_days` = [initial, development, mid, late]."""

    ini: float | None
    mid: float | None
    end: float | None
    stage_days: list[int] | None
    source: str | None
    stage_source: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def numbers_need_sources(self) -> "Kc":
        if any(v is not None for v in (self.ini, self.mid, self.end)) and not self.source:
            raise ValueError("kc has numbers but no source")
        if self.stage_days is not None:
            if not self.stage_source:
                raise ValueError("kc.stage_days has numbers but no stage_source")
            if len(self.stage_days) != 4 or min(self.stage_days) <= 0:
                raise ValueError("kc.stage_days must be 4 positive day counts")
        return self


class Crop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    family: str
    season: Literal["spring", "winter", "perennial", "cover"]
    role: Literal["main", "cover"]
    calendar: Calendar
    n_fixing: bool
    rooting: Literal["shallow", "medium", "deep"]
    kc: Kc
    stress_sensitivity: dict[str, list[float] | str | None] = Field(
        description="Per stress kind: 12 monthly values 0..1 (Jan..Dec) or null; plus `source`"
    )
    disease_groups: list[str]
    pest_break_for: list[str]
    forage_value: Literal["none", "low", "medium", "high"]
    market: list[str]
    residue_om: Literal["low", "medium", "high"]
    equipment: list[str]
    requires_livestock: bool
    source: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def sensitivities_are_sourced(self) -> "Crop":
        s = self.stress_sensitivity
        extra = set(s) - {*STRESS_KINDS, "source"}
        if extra or any(k not in s for k in STRESS_KINDS):
            raise ValueError(f"{self.id}: stress_sensitivity needs exactly {STRESS_KINDS} + source")
        has_numbers = False
        for kind in STRESS_KINDS:
            series = s[kind]
            if series is None:
                continue
            has_numbers = True
            if not isinstance(series, list) or len(series) != 12:
                raise ValueError(f"{self.id}: stress_sensitivity.{kind} must have 12 values")
            if any(not 0 <= v <= 1 for v in series):
                raise ValueError(f"{self.id}: stress_sensitivity.{kind} must be within 0..1")
        if has_numbers and not s.get("source"):
            raise ValueError(f"{self.id}: stress_sensitivity has numbers but no source")
        return self

    @property
    def sow_month(self) -> int | None:
        return self.calendar.sow_months[0] if self.calendar.sow_months else None

    @property
    def harvest_month(self) -> int | None:
        return self.calendar.harvest_months[-1] if self.calendar.harvest_months else None

    @property
    def autumn_sown(self) -> bool:
        return self.season == "winter"


class RotationTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    sequence: list[str] = Field(min_length=1, max_length=8)
    rationale: str
    source: str

    @property
    def years(self) -> int:
        return len(self.sequence)


@dataclass(frozen=True)
class Catalog:
    crops: dict[str, Crop]
    templates: list[RotationTemplate]
    sources: dict[str, dict]
    advisor_questions: dict[str, str]

    def crop(self, crop_id: str) -> Crop:
        return self.crops[crop_id]

    @property
    def cover_crops(self) -> list[Crop]:
        return [c for c in self.crops.values() if c.role == "cover"]


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalog(data_dir: Path = DATA_DIR) -> Catalog:
    """Raises ValueError on an unsourced number, an unknown source id or an unknown crop id."""
    sources = _read(data_dir / "sources.json")
    crops = {c["id"]: Crop.model_validate(c) for c in _read(data_dir / "crops_ie.json")["crops"]}
    templates = [
        RotationTemplate.model_validate(t)
        for t in _read(data_dir / "rotations_ie.json")["templates"]
    ]
    questions = _read(data_dir / "advisor_questions.json")

    def known(source_id: str | None, where: str) -> None:
        if source_id is not None and source_id not in sources:
            raise ValueError(f"{where}: unknown source id {source_id!r}")

    for crop in crops.values():
        known(crop.calendar.source, f"{crop.id}.calendar")
        known(crop.kc.source, f"{crop.id}.kc")
        known(crop.kc.stage_source, f"{crop.id}.kc.stage_days")
        known(crop.stress_sensitivity.get("source"), f"{crop.id}.stress_sensitivity")
        for source_id in crop.source:
            known(source_id, crop.id)
    for template in templates:
        known(template.source, template.id)
        for crop_id in template.sequence:
            if crop_id not in crops or crops[crop_id].role != "main":
                raise ValueError(f"{template.id}: {crop_id!r} is not a main crop in the catalogue")
    for code, question in questions.items():
        if any(ch.isdigit() for ch in question) or "%" in question:
            raise ValueError(f"advisor question {code!r} must not state a number")
    return Catalog(crops=crops, templates=templates, sources=sources, advisor_questions=questions)
