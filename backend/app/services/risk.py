"""Stress risk for a field (plan 20 task 24).

Pilot fields: pre-computed `risk_grid` + feature rows from the DB -> model.
Other fields: live POWER + SoilGrids -> agrolens_ml.build_feature_row -> model ("not calibrated").
The backend never looks inside a feature row (D22): rows go from ML code to ML code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import httpx
import pandas as pd
from loguru import logger
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from agrolens_ml import FEATURE_NAMES, StressModel, build_feature_row
from clients import soilgrids
from clients.cache import Cache
from core.deps import ModelInfo
from core.errors import AppError, UpstreamError
from core.metrics import PREDICTIONS
from models.common import OUTSIDE_PILOT, SYNTHETIC_DATA, InformationGap, provenance
from models.predict import Driver, MonthRiskOut, PredictOut, Trend
from services import context, plain
from services.context import FieldContext

SEASON = range(3, 11)  # March..October, the modelled season (brief §8.1)
LIVE_PROFILE_YEARS = 5
TREND_BAND = 0.01  # per decade; smaller changes read as "stable"
STRESS_KINDS = ("drought", "waterlogging", "heat", "frost")

_RISK_GRID = text("""
    SELECT cell_id, calendar_month, p_mean_10y, p_lo, p_hi, trend_per_decade
    FROM risk_grid WHERE cell_id = ANY(:ids)
    """)
# The latest year's feature row for each calendar month of one cell.
_LATEST_ROWS = text("""
    SELECT DISTINCT ON (EXTRACT(MONTH FROM month)) month, features
    FROM cell_month WHERE cell_id = :cell_id
    ORDER BY EXTRACT(MONTH FROM month), month DESC
    """)
_ROW_FOR_MONTH = text("SELECT features FROM cell_month WHERE cell_id = :cell_id AND month = :month")


@dataclass
class MonthRisk:
    month: int
    probability: float
    interval: tuple[float, float]
    stress_types: list[str]
    drivers: list[dict]
    needs_local_review: bool
    year: int | None = None


@dataclass
class Profile:
    months: list[MonthRisk]
    trend: Trend | None = None
    data_quality: list[str] = field(default_factory=list)
    gaps: list[InformationGap] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def gap(self, code: str, message: str) -> None:
        if code not in {g.code for g in self.gaps}:
            self.gaps.append(InformationGap(code=code, text=message))


def _to_model_row(features: dict) -> dict:
    """jsonb row -> model row: JSON null back to NaN."""
    return {k: (math.nan if v is None else float(v)) for k, v in features.items()}


def _finite(value) -> float | None:
    return None if value is None or not math.isfinite(value) else float(value)


def _clean_drivers(raw: list[dict], profile: Profile) -> list[dict]:
    """Keep ML's farmer-word texts; drop any that leak a technical term (brief §10.5)."""
    kept = []
    for d in raw:
        if plain.driver_text_ok(d.get("text", ""), FEATURE_NAMES):
            kept.append(
                {
                    "feature": d["feature"],
                    "value": _finite(d.get("value")),
                    "contribution": _finite(d.get("contribution")),
                    "text": d["text"],
                }
            )
        else:
            logger.warning("driver_text_rejected feature={}", d.get("feature"))
            profile.gap("driver_text_rejected", "One reason behind this result could not be shown.")
    return kept


# ---------- pilot: DB ----------


def _pilot_db(session_factory, ctx: FieldContext) -> tuple[list, dict[int, dict]]:
    dominant = max(ctx.weights, key=ctx.weights.get)
    with session_factory() as db:
        grid = db.execute(_RISK_GRID, {"ids": list(ctx.weights)}).mappings().all()
        latest = db.execute(_LATEST_ROWS, {"cell_id": dominant}).all()
    return grid, {r.month.month: r.features for r in latest}


async def _pilot_profile(ctx, model: StressModel, session_factory) -> Profile:
    grid, rows = await run_in_threadpool(_pilot_db, session_factory, ctx)
    profile = Profile(months=[], sources=["modis_ndvi", "power", "smap", "soilgrids", "srtm"])
    months = sorted({r["calendar_month"] for r in grid})
    with_rows = [m for m in months if m in rows]
    PREDICTIONS.inc(len(with_rows))
    predictions = dict(
        zip(with_rows, model.predict([_to_model_row(rows[m]) for m in with_rows]), strict=True)
    )
    trends: dict[int, float] = {}
    for m in months:
        cells = [r for r in grid if r["calendar_month"] == m]

        def mean(column: str, cells=cells) -> float | None:
            return context.weighted({c["cell_id"]: c[column] for c in cells}, ctx.weights)

        p = mean("p_mean_10y")
        if p is None:
            continue
        pred = predictions.get(m)
        if pred is None:
            profile.gap("drivers_unavailable", "We cannot show the reasons for some months.")
        profile.months.append(
            MonthRisk(
                month=m,
                probability=p,
                interval=(mean("p_lo") or p, mean("p_hi") or p),
                stress_types=list(pred["stress_types"]) if pred else ["other"],
                drivers=_clean_drivers(pred["drivers"], profile) if pred else [],
                needs_local_review=bool(pred["needs_local_review"]) if pred else True,
            )
        )
        trend = mean("trend_per_decade")
        if trend is not None:
            trends[m] = trend
    if trends:
        overall = sum(trends.values()) / len(trends)
        direction = (
            "increasing"
            if overall > TREND_BAND
            else "decreasing" if overall < -TREND_BAND else "stable"
        )
        sign = 1 if overall >= 0 else -1
        profile.trend = Trend(
            per_decade=round(overall, 3),
            direction=direction,
            months_affected=(
                [m for m, t in trends.items() if t * sign > TREND_BAND]
                if direction != "stable"
                else []
            ),
        )
    return profile


# ---------- live: POWER (+ SoilGrids outside the pilot) ----------


async def _live_inputs(ctx, http, cache, profile: Profile) -> tuple[dict, pd.DataFrame]:
    """cell_static (exactly CELL_STATIC_KEYS) and monthly_history for any point on Earth."""
    static = dict(ctx.static)
    if not ctx.pilot:
        try:
            soil = await soilgrids.fetch_soil(http, cache, ctx.lat, ctx.lon)
            for key in ("clay", "sand", "soc", "phh2o", "bdod"):
                static[key] = soil.get(key)
            profile.sources.append("soilgrids")
        except UpstreamError:
            profile.gap("soil_unavailable", "We could not get the soil estimate right now.")
    try:
        monthly, elevation = await context.monthly_history(
            http, cache, ctx.lat, ctx.lon, static["elev_m"]
        )
    except UpstreamError as exc:
        raise AppError(
            "climate_unavailable",
            "We could not get the weather history right now. Please try again in a moment.",
            status=503,
        ) from exc
    if static["elev_m"] is None:
        static["elev_m"] = elevation
    profile.sources.append("power")
    return static, monthly


def _build_and_predict(model, static, monthly, targets: list[pd.Period]) -> list[dict]:
    rows = [build_feature_row(static, monthly, target) for target in targets]
    PREDICTIONS.inc(len(rows))
    return model.predict(rows)


async def _live_profile(ctx, model, http, cache) -> Profile:
    profile = Profile(months=[])
    static, monthly = await _live_inputs(ctx, http, cache, profile)
    newest = monthly["month"].max() + 1  # the first month we have full history before
    targets = [
        pd.Period(year=newest.year - back, month=m, freq="M")
        for back in range(LIVE_PROFILE_YEARS + 1)
        for m in SEASON
    ]
    targets = sorted(t for t in targets if t <= newest)[-LIVE_PROFILE_YEARS * len(SEASON) :]
    predictions = await run_in_threadpool(_build_and_predict, model, static, monthly, targets)
    for m in SEASON:
        hits = [(t, p) for t, p in zip(targets, predictions, strict=True) if t.month == m]
        if not hits:
            continue
        latest = hits[-1][1]
        n = len(hits)
        profile.months.append(
            MonthRisk(
                month=m,
                probability=sum(p["probability"] for _, p in hits) / n,
                interval=(
                    sum(p["interval"][0] for _, p in hits) / n,
                    sum(p["interval"][1] for _, p in hits) / n,
                ),
                stress_types=list(latest["stress_types"]),
                drivers=_clean_drivers(latest["drivers"], profile),
                needs_local_review=True,
            )
        )
    profile.gap("trend_unavailable", "We cannot show a long-term trend for this place.")
    return profile


def _fresh_row(session_factory, ctx, target: pd.Period) -> dict | None:
    dominant = max(ctx.weights, key=ctx.weights.get)
    with session_factory() as db:
        return db.execute(
            _ROW_FOR_MONTH, {"cell_id": dominant, "month": target.to_timestamp().date()}
        ).scalar_one_or_none()


async def _next_month(ctx, model, http, cache, session_factory) -> Profile:
    today = context.today()
    target = pd.Period(year=today.year, month=today.month, freq="M")  # last full month + 1
    profile = Profile(months=[])
    stored = (
        await run_in_threadpool(_fresh_row, session_factory, ctx, target) if ctx.pilot else None
    )
    if stored is not None:
        prediction = model.predict([_to_model_row(stored)])[0]
        profile.sources += ["modis_ndvi", "power", "smap"]
    else:
        # Stored features are older than this month: rebuild the row from live POWER.
        static, monthly = await _live_inputs(ctx, http, cache, profile)
        prediction = (
            await run_in_threadpool(_build_and_predict, model, static, monthly, [target])
        )[0]
        if ctx.pilot:
            profile.data_quality.append("live_weather_only")
            profile.gap(
                "satellite_history_not_current",
                "The newest satellite crop data is not in yet. This month uses weather only.",
            )
    if target.month not in SEASON:
        profile.data_quality.append("outside_growing_season")
        profile.gap(
            "outside_growing_season",
            "The model covers March to October. Treat this month with care.",
        )
    profile.months.append(
        MonthRisk(
            month=target.month,
            year=target.year,
            probability=prediction["probability"],
            interval=tuple(prediction["interval"]),
            stress_types=list(prediction["stress_types"]),
            drivers=_clean_drivers(prediction["drivers"], profile),
            needs_local_review=bool(prediction["needs_local_review"]),
        )
    )
    return profile


async def field_profile(
    ctx: FieldContext, mode: str, model: StressModel, http, cache: Cache, session_factory
) -> Profile:
    """The risk profile of a field, before any crop weighting or wording."""
    if mode == "next_month":
        profile = await _next_month(ctx, model, http, cache, session_factory)
    elif ctx.pilot:
        profile = await _pilot_profile(ctx, model, session_factory)
    else:
        profile = await _live_profile(ctx, model, http, cache)
    if not ctx.pilot:
        profile.data_quality.append(OUTSIDE_PILOT)
        profile.gap(
            "outside_pilot",
            "The risk model is not calibrated here. It was built for Ireland. "
            "Use this as a rough guide only.",
        )
    return profile


def crop_sensitivity(crop, month: int, stress_types: list[str]) -> float | None:
    """Max sensitivity of the crop over the predicted stress types in that month, or None."""
    values = []
    for kind in stress_types:
        series = crop.stress_sensitivity.get(kind) if kind in STRESS_KINDS else None
        if series is not None:
            values.append(series[month - 1])
    return max(values) if values else None


async def predict_stress_risk(
    field_id: str,
    mode: str,
    crop_id: str | None,
    *,
    model: StressModel,
    info: ModelInfo,
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
    profile = await field_profile(ctx, mode, model, http, cache, session_factory)

    if info.kind == "stub" or (ctx.pilot and ctx.data_source != "real"):
        profile.data_quality.append(SYNTHETIC_DATA)
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
        if crop is not None and sensitivity is None:
            profile.gap(
                "crop_sensitivity_unknown",
                "For some months we do not know how this crop reacts. "
                "Those months show the general risk for crops.",
            )
        risk = m.probability if weighted is None else weighted
        risk_level = plain.level(risk)
        month_label = plain.label(risk_level, m.stress_types)
        often = plain.frequency_text(risk)
        shown.append({"month": m.month, "risk": risk, "stress_types": m.stress_types})
        months_out.append(
            MonthRiskOut(
                month=m.month,
                year=m.year,
                probability=round(m.probability, 4),
                interval=(round(m.interval[0], 4), round(m.interval[1], 4)),
                stress_types=m.stress_types,
                drivers=[Driver(**d) for d in m.drivers],
                crop_sensitivity=sensitivity,
                crop_weighted_risk=None if weighted is None else round(weighted, 4),
                level=risk_level,
                label=month_label,
                frequency_text=often,
                aria_label=plain.aria_label(m.month, crop_name, month_label, often, m.interval),
            )
        )

    return PredictOut(
        field_id=field_id,
        mode=mode,
        crop_id=crop_id,
        model_version=model.version,
        pilot_coverage=ctx.pilot,
        headline=plain.headline(shown, crop_name),
        months=months_out,
        riskiest_month=plain.riskiest_month(shown),
        trend=profile.trend,
        data_quality=list(dict.fromkeys(profile.data_quality)),
        information_gaps=profile.gaps,
        needs_local_review=(not ctx.pilot) or any(m.needs_local_review for m in profile.months),
        provenance=provenance(*profile.sources),
    )
