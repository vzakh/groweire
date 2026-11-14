"""Rotation engine: generate -> score -> explain -> present -> sort (plan 20 task 26).

Deterministic and rule-based (D5): every number traces to a metric or a catalogue source.
"""

from __future__ import annotations

import httpx
from starlette.concurrency import run_in_threadpool

from agrolens_ml import StressModel
from clients.cache import Cache
from core.deps import ModelInfo
from core.errors import AppError, UpstreamError
from models.common import SYNTHETIC_DATA, InformationGap, provenance
from models.rotations import CompareIn, CompareOut, CoverCropUse, Metrics, Strategy
from services import conditions, context, plain, risk
from services.rotation import explain as explain_mod
from services.rotation import generate, present, score
from services.rotation.catalog import Catalog


def check_codes(catalog: Catalog) -> None:
    """Fail at startup (not in front of a farmer) if a risk/gap code has no advisor question."""
    missing = [c for c in explain_mod.CODES if c not in catalog.advisor_questions]
    if missing:
        raise ValueError(f"advisor_questions.json lacks codes: {missing}")


def _validate(body: CompareIn, catalog: Catalog) -> None:
    c = body.constraints
    for crop_id in (*body.current_rotation, *c.excluded_crops, *c.must_include):
        if crop_id not in catalog.crops:
            raise AppError("unknown_crop", f"We do not know the crop '{crop_id}'.", status=422)
    for crop_id in (*body.current_rotation, *c.must_include):
        if catalog.crop(crop_id).role != "main":
            raise AppError(
                "unknown_crop", f"'{crop_id}' is a cover crop, not a main crop.", status=422
            )
    if set(c.must_include) & set(c.excluded_crops):
        raise AppError(
            "constraints_conflict", "A crop cannot be both required and excluded.", status=422
        )


def select(scored: list[tuple], n_alternatives: int) -> list[tuple]:
    """Current first, then the best alternatives that differ enough from it."""
    current = next(item for item in scored if item[0].is_current)
    others = sorted(
        (item for item in scored if not item[0].is_current), key=lambda item: (-item[3], item[0].id)
    )
    picked: list[tuple] = []
    seen_origins: set[str] = set()
    for item in others:
        cand = item[0]
        if len(picked) == n_alternatives:
            break
        distance = generate.jaccard_distance(cand.crop_set, current[0].crop_set)
        if distance < generate.MIN_JACCARD_DISTANCE:
            continue
        # Offer different kinds of change: at most one "small step" and one "cover crops only".
        if cand.origin in ("step", "cover") and cand.origin in seen_origins:
            continue
        seen_origins.add(cand.origin)
        picked.append(item)
    return [current, *picked]


async def compare(
    body: CompareIn,
    *,
    model: StressModel,
    info: ModelInfo,
    catalog: Catalog,
    http: httpx.AsyncClient,
    cache: Cache,
    session_factory,
) -> CompareOut:
    _validate(body, catalog)
    ctx = await run_in_threadpool(context.load_context, session_factory, body.field_id)
    gaps: list[InformationGap] = []
    quality: list[str] = []
    sources = ["crops_ie"]

    # The field's seasonal risk profile, computed once and reused for every candidate.
    env = score.Env(
        slope_deg=ctx.static.get("slope_deg"),
        market_contracts=tuple(body.constraints.market_contracts),
    )
    try:
        profile = await risk.field_profile(
            ctx, "seasonal_profile", model, http, cache, session_factory
        )
        env.risk = {
            m.month: (m.probability, plain.dominant_type(m.stress_types)) for m in profile.months
        }
        gaps += profile.gaps
        quality += profile.data_quality
        sources += profile.sources
    except AppError as exc:
        if exc.code != "climate_unavailable":
            raise
        gaps.append(
            InformationGap(
                code="risk_unavailable",
                text="We could not work out the weather risk right now. "
                "The options are compared without it.",
            )
        )
    try:
        monthly, _ = await context.monthly_history(
            http, cache, ctx.lat, ctx.lon, ctx.static.get("elev_m")
        )
        climate, _ = conditions.climate_summary(monthly, context.HISTORY_YEARS)
        if all(m.et0_mm is not None for m in climate.months) and len(climate.months) == 12:
            env.et0 = {m.month: m.et0_mm for m in climate.months}
            env.heavy_rain_days = {m.month: m.heavy_rain_days or 0.0 for m in climate.months}
            sources.append("power")
    except UpstreamError:
        pass
    if env.et0 is None:
        gaps.append(
            InformationGap(
                code="climate_unavailable",
                text="Weather history was not available. Water use and erosion are not compared.",
            )
        )
    if info.kind == "stub" or (ctx.pilot and ctx.data_source != "real"):
        quality.append(SYNTHETIC_DATA)
    gaps.append(
        InformationGap(
            code="crop_sensitivity_unverified",
            text="How much each crop suffers in each month is our first estimate. "
            "It has not been checked against field trials.",
        )
    )
    gaps.append(
        InformationGap(
            code="no_soil_test",
            text="Soil values are estimates from a map, not a test of your field.",
        )
    )

    cands = generate.candidates(body.current_rotation, body.constraints, catalog)
    results = [score.evaluate(c, catalog, env) for c in cands]
    all_scores = score.criteria(results)
    weight_by_criterion = score.weights(list(body.priorities))
    scored = [
        (c, r, s, score.total_score(s, weight_by_criterion))
        for c, r, s in zip(cands, results, all_scores, strict=True)
    ]
    chosen = select(scored, body.n_alternatives)
    current, current_result, current_scores, _ = chosen[0]

    strategies = []
    for cand, result, scores, total in chosen:
        explained = explain_mod.explain(
            cand,
            result,
            scores,
            current,
            current_result,
            current_scores,
            weight_by_criterion,
            env,
            catalog,
            body.constraints,
            ctx.pilot,
        )
        strategies.append(
            Strategy(
                id=cand.id,
                label=cand.label,
                sequence=cand.sequence,
                cover_crops=[
                    CoverCropUse(after_year=year + 1, crop_id=crop_id)
                    for year, crop_id in sorted(cand.cover.items())
                ],
                is_current=cand.is_current,
                headline=present.headline(cand, current, catalog),
                one_line_why=present.one_line_why(
                    scores, current_scores, weight_by_criterion, cand.is_current
                ),
                vs_current=None if cand.is_current else present.vs_current(result, current_result),
                score=round(total, 3),
                criteria=scores,
                metrics=Metrics(**result.metrics),
                explanation=explained.explanation,
                advisor_questions=present.advisor_questions(explained.codes, catalog),
            )
        )

    return CompareOut(
        field_id=body.field_id,
        strategies=strategies,
        weights_used=weight_by_criterion,
        data_quality=list(dict.fromkeys(quality)),
        information_gaps=list({g.code: g for g in gaps}.values()),
        provenance=provenance(*sources),
    )
