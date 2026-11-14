"""Candidate rotations: the current one, sourced templates and small changes to the current one.

Deterministic (brief §10.2, D5): same inputs, same candidates, in the same order.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from models.rotations import Constraints
from services.rotation.catalog import Catalog, Crop, RotationTemplate

MIN_GAP_MONTHS = 3
LATEST_COVER_SOWING = 9  # a cover crop needs the main crop off the field by September
COVER_PREFERENCE = ("cover_oats_vetch", "cover_phacelia", "cover_mustard")
BREAK_CROPS = ("spring_beans", "spring_oats", "winter_oilseed_rape", "winter_oats")
MIN_JACCARD_DISTANCE = 0.25
EXPANDED_YEARS = 4


@dataclass
class Candidate:
    id: str
    label: str
    sequence: list[str]
    cover: dict[int, str] = field(default_factory=dict)  # year index -> cover crop after it
    is_current: bool = False
    template: RotationTemplate | None = None
    origin: str = "template"  # current | cover | step | template

    @property
    def key(self) -> tuple:
        return tuple(self.sequence), tuple(sorted(self.cover.items()))

    @property
    def crop_set(self) -> set[str]:
        return set(self.sequence) | set(self.cover.values())


def allowed(crop: Crop, constraints: Constraints) -> bool:
    if crop.id in constraints.excluded_crops:
        return False
    if crop.requires_livestock and constraints.has_livestock is False:
        return False
    if constraints.equipment is not None and not set(crop.equipment) <= set(constraints.equipment):
        return False
    return True


def fill_cover(sequence: list[str], catalog: Catalog, constraints: Constraints) -> dict[int, str]:
    """Winter gaps of >= 3 months before a spring-sown crop get the best allowed cover crop."""
    has_brassica = any(catalog.crop(c).family == "brassica" for c in sequence)
    choice = None
    for crop_id in COVER_PREFERENCE:
        crop = catalog.crops.get(crop_id)
        if crop is None or crop_id in constraints.excluded_crops:
            continue
        if has_brassica and "clubroot" in crop.disease_groups:
            continue  # do not put a brassica cover crop into an oilseed-rape rotation
        choice = crop_id
        break
    if choice is None:
        return {}
    cover = {}
    n = len(sequence)
    for i, crop_id in enumerate(sequence):
        current, following = catalog.crop(crop_id), catalog.crop(sequence[(i + 1) % n])
        if current.harvest_month is None or following.season != "spring":
            continue
        gap = (12 - current.harvest_month) + (following.sow_month - 1)
        if current.harvest_month <= LATEST_COVER_SOWING and gap >= MIN_GAP_MONTHS:
            cover[i] = choice
    return cover


def jaccard_distance(a: set[str], b: set[str]) -> float:
    union = a | b
    return 1 - len(a & b) / len(union) if union else 0.0


def _expanded(current: list[str]) -> list[str]:
    """A one- or two-year rotation written out over four years, so one year can change."""
    if len(current) >= EXPANDED_YEARS:
        return list(current)
    repeats = -(-EXPANDED_YEARS // len(current))
    return (list(current) * repeats)[:EXPANDED_YEARS]


def candidates(current: list[str], constraints: Constraints, catalog: Catalog) -> list[Candidate]:
    """Current first, then every distinct allowed alternative (not yet scored or trimmed)."""
    out = [
        Candidate(
            "current", "Your current rotation", list(current), is_current=True, origin="current"
        )
    ]
    seen = {out[0].key}
    must = set(constraints.must_include)

    def add(candidate: Candidate) -> None:
        crops = [catalog.crop(c) for c in candidate.sequence]
        if not all(allowed(c, constraints) for c in crops):
            return
        if not must <= set(candidate.sequence):
            return
        candidate.cover = fill_cover(candidate.sequence, catalog, constraints)
        if candidate.key not in seen:
            seen.add(candidate.key)
            out.append(candidate)

    # 1. The farmer's own crops, plus winter cover crops.
    add(
        Candidate(
            "current_cover", "Your crops, with winter cover crops", list(current), origin="cover"
        )
    )

    # 2. The farmer's own rotation with one year changed to a break crop (or a must-include).
    base = _expanded(current)
    most_common = Counter(base).most_common(1)[0][0]
    swap_at = len(base) - 1 - base[::-1].index(most_common)
    for crop_id in (*sorted(must), *BREAK_CROPS):
        if crop_id in base or crop_id not in catalog.crops:
            continue
        changed = list(base)
        changed[swap_at] = crop_id
        name = catalog.crop(crop_id).name.lower()
        add(
            Candidate(
                f"current_plus_{crop_id}", f"Your rotation with {name}", changed, origin="step"
            )
        )

    # 3. Sourced templates.
    for template in catalog.templates:
        add(Candidate(template.id, template.label, list(template.sequence), template=template))
    return out
