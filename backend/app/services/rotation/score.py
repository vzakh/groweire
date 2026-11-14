"""Metrics per rotation (brief §10.3) and the priority-weighted score (D18). Pure functions.

Indices (erosion, organic matter, simplicity) rank the options against each other. They are
not measurements, and the response says so.
"""

from __future__ import annotations

import calendar as _calendar
from dataclasses import dataclass, field

from services import plain
from services.rotation.catalog import STRESS_KINDS, Catalog, Crop
from services.rotation.generate import Candidate

CRITERIA = (
    "climate_risk",
    "income_stability",
    "simplicity",
    "soil_cover",
    "water_use",
    "forage_value",
    "nitrogen_fixing",
    "pest_break",
    "market_suitability",
)
PRIORITY_WEIGHTS = (3, 2, 1)
RESIDUE = {"low": 0.2, "medium": 0.5, "high": 1.0}
FORAGE = {"none": 0.0, "low": 0.1, "medium": 0.5, "high": 1.0}
COVER_CROP_OM_BONUS = 0.25
DAYS = [_calendar.monthrange(2023, m)[1] for m in range(1, 13)]  # a non-leap year


@dataclass
class Env:
    """What we know about the field, shared by every candidate."""

    risk: dict[int, tuple[float, str]] = field(default_factory=dict)  # month -> (p, stress kind)
    et0: dict[int, float] | None = None  # mm per calendar month (climatology)
    heavy_rain_days: dict[int, float] | None = None
    slope_deg: float | None = None
    market_contracts: tuple[str, ...] = ()


@dataclass
class Result:
    metrics: dict
    raw: dict[str, float | None]  # per criterion, higher = better, not yet normalised
    parts: dict[str, float | None]  # pieces of soil_cover + simplicity, for vs_current
    missing_parameters: list[str]


def cover_matrix(cand: Candidate, catalog: Catalog) -> list[list[bool]]:
    """covered[year][month-1] over the rotation cycle (cyclic: the last year wraps to the first)."""
    n = len(cand.sequence)
    covered = [[False] * 12 for _ in range(n)]
    for y, crop_id in enumerate(cand.sequence):
        crop = catalog.crop(crop_id)
        for m in crop.calendar.ground_cover_months:
            # An autumn-sown crop is sown the year before its harvest year.
            autumn = crop.autumn_sown and m >= crop.sow_month
            covered[(y - 1) % n if autumn else y][m - 1] = True
    for y, cover_id in cand.cover.items():
        for m in catalog.crop(cover_id).calendar.ground_cover_months:
            covered[y if m >= 7 else (y + 1) % n][m - 1] = True
    return covered


def sensitivity(crop: Crop, month: int, kind: str) -> float | None:
    """Crop sensitivity for a month's stress kind; for 'other' the crop's worst kind."""
    series = crop.stress_sensitivity
    if kind in STRESS_KINDS:
        return None if series[kind] is None else series[kind][month - 1]
    known = [series[k][month - 1] for k in STRESS_KINDS if series[k] is not None]
    return max(known) if known else None


def kc_at(crop: Crop, fraction: float) -> float:
    """FAO-56 single-Kc curve at a fraction (0..1) of the season, stages scaled to the season."""
    ini, dev, mid, late = crop.kc.stage_days
    total = ini + dev + mid + late
    t = fraction * total
    if t <= ini:
        return crop.kc.ini
    if t <= ini + dev:
        return crop.kc.ini + (crop.kc.mid - crop.kc.ini) * (t - ini) / dev
    if t <= ini + dev + mid:
        return crop.kc.mid
    return crop.kc.mid + (crop.kc.end - crop.kc.mid) * (t - ini - dev - mid) / late


def crop_water_demand(crop: Crop, et0: dict[int, float]) -> float | None:
    """Sum of Kc x ET0 over the crop's season, in mm. None when a parameter is missing."""
    kc = crop.kc
    if crop.season == "perennial":
        return None if kc.mid is None else sum(kc.mid * et0[m] for m in range(1, 13))
    if None in (kc.ini, kc.mid, kc.end, kc.stage_days, crop.sow_month, crop.harvest_month):
        return None
    months = [crop.sow_month]
    while months[-1] != crop.harvest_month:
        months.append(months[-1] % 12 + 1)
    season_days = sum(DAYS[m - 1] for m in months)
    demand, elapsed = 0.0, 0.0
    for m in months:
        midpoint = (elapsed + DAYS[m - 1] / 2) / season_days
        demand += kc_at(crop, midpoint) * et0[m]
        elapsed += DAYS[m - 1]
    return demand


def two_of_four(sequence: list[str]) -> bool:
    """Irish conditionality: at least 2 different crops in every 4-year window of the cycle."""
    n = len(sequence)
    cycle = sequence * (-(-4 // n) + 1)
    return all(len(set(cycle[i : i + 4])) >= 2 for i in range(n))


def evaluate(cand: Candidate, catalog: Catalog, env: Env) -> Result:
    crops = [catalog.crop(c) for c in cand.sequence]
    n = len(crops)
    covered = cover_matrix(cand, catalog)
    bare = [(y, m) for y in range(n) for m in range(1, 13) if not covered[y][m - 1]]
    missing: list[str] = []

    stress = 0.0
    for crop in crops:
        for month, (p, kind) in env.risk.items():
            s = sensitivity(crop, month, kind)
            if s is not None:
                stress += p * s
    stress /= n

    water = None
    if env.et0 is not None:
        per_crop = [crop_water_demand(c, env.et0) for c in crops]
        missing = sorted({c.name for c, w in zip(crops, per_crop, strict=True) if w is None})
        known = [w for w in per_crop if w is not None]
        water = sum(known) / len(known) if known else None

    wet = {
        m for m, (p, kind) in env.risk.items() if kind == "waterlogging" and plain.level(p) != "low"
    }
    work_months = [m for c in crops for m in (c.sow_month, c.harvest_month) if m is not None]
    workability = sum(1 for m in work_months if m in wet) / n

    erosion = None
    if env.heavy_rain_days is not None:
        slope_factor = 1 + (env.slope_deg or 0.0) / 5
        erosion = sum(env.heavy_rain_days[m] for _, m in bare) * slope_factor / n

    transitions = [(crops[i], crops[(i + 1) % n]) for i in range(n)]
    breaks = sum(
        1
        for a, b in transitions
        if a.id != b.id and not set(a.disease_groups) & set(b.disease_groups)
    )
    organic = (
        sum(
            min(1.0, RESIDUE[c.residue_om] + (COVER_CROP_OM_BONUS if i in cand.cover else 0))
            for i, c in enumerate(crops)
        )
        / n
    )
    forage = sum(FORAGE[c.forage_value] for c in crops) / n
    if env.market_contracts:
        market = sum(1 for c in crops if set(c.market) & set(env.market_contracts)) / n
    else:
        market = sum(1 for c in crops if c.market) / n
    shares = [cand.sequence.count(c) / n for c in set(cand.sequence)]
    diversity = 1 - sum(s * s for s in shares)
    n_fixing = sum(1 for c in crops if c.n_fixing)
    complexity = len(set(cand.sequence)) + 0.5 * len(set(cand.cover.values())) + workability

    metrics = {
        "bare_months_per_year": round(len(bare) / n, 1),
        "crop_weighted_stress": round(stress, 3),
        "water_demand_mm": None if water is None else round(water),
        "workability_risk": round(workability, 2),
        "erosion_index": None if erosion is None else round(erosion, 2),
        "n_fixing_years": n_fixing,
        "pest_break_score": round(breaks / n, 2),
        "organic_matter_score": round(organic, 2),
        "forage_score": round(forage, 2),
        "market_score": round(market, 2),
        "rule_compliance": {
            "ie_crop_rotation_2_of_4": two_of_four(cand.sequence),
            "two_crop_rule_10_30ha": None,
        },
    }
    raw = {
        "climate_risk": -stress,
        "income_stability": (market + diversity) / 2,
        "simplicity": -complexity,
        "soil_cover": None,  # built from normalised parts in `criteria`
        "water_use": None if water is None else -water,
        "forage_value": forage,
        "nitrogen_fixing": n_fixing / n,
        "pest_break": breaks / n,
        "market_suitability": market,
    }
    parts = {
        "bare": -len(bare) / n,
        "erosion": None if erosion is None else -erosion,
        "organic": organic,
        "complexity": complexity,
        "stress": stress,
    }
    return Result(metrics=metrics, raw=raw, parts=parts, missing_parameters=missing)


def normalise(values: list[float | None]) -> list[float]:
    """Min-max to 0..1 across the candidate set; ties and unknowns -> 0.5."""
    known = [v for v in values if v is not None]
    if not known or max(known) - min(known) < 1e-12:
        return [0.5] * len(values)
    low, high = min(known), max(known)
    return [0.5 if v is None else (v - low) / (high - low) for v in values]


def criteria(results: list[Result]) -> list[dict[str, float]]:
    """Per-candidate criterion scores (0..1, higher = better), normalised across the set."""
    columns = {
        name: normalise([r.raw[name] for r in results]) for name in CRITERIA if name != "soil_cover"
    }
    part_names = [p for p in ("bare", "erosion", "organic") if results[0].parts[p] is not None]
    soil_parts = [normalise([r.parts[p] for r in results]) for p in part_names]
    columns["soil_cover"] = [
        sum(col[i] for col in soil_parts) / len(soil_parts) for i in range(len(results))
    ]
    return [{name: round(columns[name][i], 3) for name in CRITERIA} for i in range(len(results))]


def weights(priorities: list[str]) -> dict[str, int]:
    """climate_risk always counts 1; the ordered top-3 priorities add 3, 2, 1 (D18)."""
    out = {"climate_risk": 1}
    for priority, weight in zip(priorities, PRIORITY_WEIGHTS, strict=False):
        out[priority] = weight
    return out


def total_score(criterion_scores: dict[str, float], weight_by_criterion: dict[str, int]) -> float:
    total = sum(weight_by_criterion.values())
    return sum(w * criterion_scores[name] for name, w in weight_by_criterion.items()) / total
