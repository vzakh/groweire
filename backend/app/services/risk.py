"""Counted weather risk for a field (PLAN_40 task 43; replaces the stress model, plan 20 task 24).

"In N of the last 25 years, July was too dry here": the risk of a month is how often an absolute
rule fired in NASA weather history. The rules and the counting live in agrolens_ml.

Pilot fields: the pre-computed `risk_counts` table (weather of the area, soil drainage of the cell).
Other fields: the same rules on live POWER data for the point (drainage unknown -> a gap).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import httpx
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from agrolens_ml import RISK_RULES_VERSION, RISK_TYPES
from clients.cache import Cache
from core.deps import is_synthetic
from core.errors import AppError, UpstreamError
from core.metrics import PREDICTIONS
from models.common import OUTSIDE_PILOT, SYNTHETIC_DATA, InformationGap, provenance
from models.predict import Driver, MonthRiskOut, PredictOut, TypeCountOut
from services import context, plain
from services.context import FieldContext

SEASON = range(3, 11)  # March..October, the counted season (brief §8.1)
STRESS_KINDS = RISK_TYPES
INTERVAL_Z = 1.645  # 90% Wilson range for "N years out of M" (a statistical choice, not agronomy)
METHOD = "counted_history"

_COUNTS = text("""
    SELECT calendar_month, stress_type, years_hit, years_total, frequency, recent_frequency,
           example_years
    FROM risk_counts WHERE cell_id = :cell_id
    """)


@dataclass
class TypeCount:
    stress_type: str
    years_hit: int
    years_total: int
    frequency: float
    recent_frequency: float | None
    example_years: list[int]


@dataclass
class MonthRisk:
    month: int
    probability: float  # counted frequency of the dominant stress type
    interval: tuple[float, float]
    stress_types: list[str]  # the dominant type, or [] when nothing was ever counted
    counts: list[TypeCount]  # every stress type, most frequent first
    needs_local_review: bool = True


@dataclass
class Profile:
    months: list[MonthRisk]
    data_quality: list[str] = field(default_factory=list)
    gaps: list[InformationGap] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def gap(self, code: str, message: str) -> None:
        if code not in {g.code for g in self.gaps}:
            self.gaps.append(InformationGap(code=code, text=message))


def wilson_interval(hit: int, total: int, z: float = INTERVAL_Z) -> tuple[float, float]:
    """A plain binomial range for `hit` years out of `total` (Wilson score interval)."""
    if total <= 0:
        return (0.0, 1.0)
    p = hit / total
    centre = p + z * z / (2 * total)
    spread = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    denom = 1 + z * z / total
    return (max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom))


def _finite(value) -> float | None:
    return None if value is None or not math.isfinite(value) else float(value)


def months_from_counts(rows: list[dict]) -> list[MonthRisk]:
    """risk_counts rows of one place -> one MonthRisk per calendar month of the season."""
    priority = {kind: i for i, kind in enumerate(plain.config()["type_priority"])}
    months = []
    for month in SEASON:
        counts = [
            TypeCount(
                stress_type=r["stress_type"],
                years_hit=int(r["years_hit"]),
                years_total=int(r["years_total"]),
                frequency=_finite(r["frequency"]) or 0.0,
                recent_frequency=_finite(r["recent_frequency"]),
                example_years=[int(y) for y in (r["example_years"] or [])],
            )
            for r in rows
            if r["calendar_month"] == month and r["stress_type"] in STRESS_KINDS
        ]
        if not counts:
            continue
        counts.sort(key=lambda c: (-c.frequency, priority.get(c.stress_type, 99)))
        top = counts[0]
        months.append(
            MonthRisk(
                month=month,
                probability=top.frequency,
                interval=wilson_interval(top.years_hit, top.years_total),
                stress_types=[top.stress_type] if top.years_hit > 0 else [],
                counts=counts,
            )
        )
    return months


def _pilot_rows(session_factory, ctx: FieldContext) -> list[dict]:
    # A field is far smaller than a cell: the cell covering most of it gives whole-year counts.
    dominant = max(ctx.weights, key=ctx.weights.get)
    with session_factory() as db:
        return [dict(r) for r in db.execute(_COUNTS, {"cell_id": dominant}).mappings().all()]


async def field_profile(
    ctx: FieldContext, http: httpx.AsyncClient, cache: Cache, session_factory
) -> Profile:
    """The counted risk profile of a field, before any crop weighting or wording."""
    profile = Profile(months=[], sources=["power", "met_eireann_smd"])
    if ctx.pilot:
        rows = await run_in_threadpool(_pilot_rows, session_factory, ctx)
        profile.sources.append("irish_sis")
        profile.gap(
            "weather_is_area_average",
            "The weather is for your area, about 50 km wide. The soil is for your field.",
        )
        if is_synthetic(ctx.data_source):
            profile.data_quality.append(SYNTHETIC_DATA)
        else:
            profile.sources.append("imerg")  # the real table scales POWER rain to IMERG totals
    else:
        try:
            rows = await context.counted_risks(
                http, cache, ctx.lat, ctx.lon, ctx.static.get("elev_m"), None
            )
        except UpstreamError as exc:
            raise AppError(
                "climate_unavailable",
                "We could not get the weather history right now. Please try again in a moment.",
                status=503,
            ) from exc
        profile.data_quality.append(OUTSIDE_PILOT)
        profile.gap(
            "outside_pilot",
            "The risk rules were made for Irish soils and weather. "
            "Use this as a rough guide only.",
        )
    profile.months = months_from_counts(rows)
    PREDICTIONS.inc(len(profile.months))
    if ctx.static.get("drainage_class") is None:
        profile.data_quality.append("drainage_unknown")
        profile.gap(
            "drainage_unknown",
            "We do not know how well this field drains. We assumed average drainage, "
            "so the wet months are a rough guide.",
        )
    profile.gap(
        "risk_rules_unverified",
        "How many dry, wet, hot or frosty days make a bad month is our own rule. "
        "It has not been checked by an advisor yet.",
    )
    return profile


def crop_sensitivity(crop, month: int, stress_types: list[str]) -> float | None:
    """Max sensitivity of the crop over the counted stress types in that month, or None."""
    values = []
    for kind in stress_types:
        series = crop.stress_sensitivity.get(kind) if kind in STRESS_KINDS else None
        if series is not None:
            values.append(series[month - 1])
    return max(values) if values else None


def _drivers(m: MonthRisk) -> list[Driver]:
    """One counted fact per stress type that ever happened in this month."""
    return [
        Driver(
            feature=c.stress_type,
            value=float(c.years_hit),
            contribution=round(c.frequency, 4),
            text=plain.evidence_text(
                m.month, c.stress_type, c.years_hit, c.years_total, c.example_years
            ),
        )
        for c in m.counts
        if c.years_hit > 0
    ]


async def predict_stress_risk(
    field_id: str,
    crop_id: str | None,
    *,
    catalog,
    http: httpx.AsyncClient,
    cache: Cache,
    session_factory,
) -> PredictOut:
    crop = None
    if crop_id is not None:
        crop = catalog.crops.get(crop_id)
        if crop is None:
            raise AppError("unknown_crop", "We do not know that crop.", status=422)
    ctx = await run_in_threadpool(context.load_context, session_factory, field_id)
    profile = await field_profile(ctx, http, cache, session_factory)

    crop_name = crop.name if crop else None
    if crop is not None:
        profile.sources.append("crops_ie")
        if crop.stress_sensitivity.get("source") == "draft_unverified":
            profile.gap(
                "crop_sensitivity_unverified",
                f"How much {crop.name.lower()} suffers in each month is our first estimate. "
                "It has not been checked against field trials.",
            )

    months_out: list[MonthRiskOut] = []
    shown: list[dict] = []
    for m in profile.months:
        sensitivity = crop_sensitivity(crop, m.month, m.stress_types) if crop else None
        weighted = None if sensitivity is None else m.probability * sensitivity
        if crop is not None and sensitivity is None and m.stress_types:
            profile.gap(
                "crop_sensitivity_unknown",
                "For some months we do not know how this crop reacts. "
                "Those months show the general risk for crops.",
            )
        # The crop decides how much a month matters (level, label, riskiest month). The words
        # "N years in 10" always describe the counted weather, so a farmer can check them.
        risk = m.probability if weighted is None else weighted
        risk_level = plain.level(risk)
        month_label = plain.label(risk_level, m.stress_types)
        often = plain.frequency_text(m.probability)
        shown.append(
            {
                "month": m.month,
                "risk": risk,
                "frequency": m.probability,
                "stress_types": m.stress_types,
            }
        )
        top = m.counts[0]
        months_out.append(
            MonthRiskOut(
                month=m.month,
                probability=round(m.probability, 4),
                interval=(round(m.interval[0], 4), round(m.interval[1], 4)),
                years_hit=top.years_hit,
                years_total=top.years_total,
                stress_types=m.stress_types,
                counts=[
                    TypeCountOut(
                        stress_type=c.stress_type,
                        years_hit=c.years_hit,
                        years_total=c.years_total,
                        frequency=round(c.frequency, 4),
                        recent_frequency=(
                            None if c.recent_frequency is None else round(c.recent_frequency, 4)
                        ),
                        example_years=c.example_years,
                    )
                    for c in m.counts
                ],
                drivers=_drivers(m),
                crop_sensitivity=sensitivity,
                crop_weighted_risk=None if weighted is None else round(weighted, 4),
                level=risk_level,
                label=month_label,
                frequency_text=often,
                aria_label=plain.aria_label(
                    m.month,
                    crop_name,
                    month_label,
                    often,
                    m.interval,
                    m.stress_types[0] if m.stress_types else None,
                ),
            )
        )

    return PredictOut(
        field_id=field_id,
        crop_id=crop_id,
        model_version=RISK_RULES_VERSION,
        pilot_coverage=ctx.pilot,
        headline=plain.headline(shown, crop_name),
        months=months_out,
        riskiest_month=plain.riskiest_month(shown),
        data_quality=list(dict.fromkeys(profile.data_quality)),
        information_gaps=profile.gaps,
        needs_local_review=True,  # the day-count rules are draft_unverified (PLAN_40 task 41)
        provenance=provenance(*profile.sources),
    )
