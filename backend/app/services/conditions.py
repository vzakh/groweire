"""Climate summary, trends, soil and satellite series for a field (plan 20 task 23)."""

from __future__ import annotations

import math
from datetime import date

import httpx
import numpy as np
import pandas as pd
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from clients import soilgrids
from clients.cache import Cache
from core.deps import is_synthetic
from core.errors import UpstreamError
from models.common import OUTSIDE_PILOT, SYNTHETIC_DATA, InformationGap, provenance
from models.conditions import (
    Climate,
    ClimateMonth,
    ConditionsOut,
    GreennessHistory,
    Series,
    Soil,
    SoilFact,
    Trends,
)
from services import context, plain
from services.context import FieldContext

SERIES_YEARS = 10
MIN_TREND_YEARS = 10

_SERIES = text("""
    SELECT cell_id, month, ndvi, ndvi_z, sm_rootzone FROM cell_month
    WHERE cell_id = ANY(:ids) AND month >= :since ORDER BY month
    """)


# Mean NDVI of June-August per cell and year; a summer needs at least two months with data.
_SUMMER_NDVI = text("""
    SELECT cell_id, EXTRACT(YEAR FROM month)::int AS year, avg(ndvi) AS ndvi, count(ndvi) AS n
    FROM cell_month
    WHERE cell_id = ANY(:ids) AND EXTRACT(MONTH FROM month) IN (6, 7, 8)
    GROUP BY cell_id, EXTRACT(YEAR FROM month)
    """)
MIN_SUMMER_MONTHS = 2


def _num(value, digits: int = 1) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits)


def sens_slope(values: list[float]) -> float | None:
    """Median of all pairwise slopes (robust to outliers), per step."""
    y = np.asarray(values, dtype=float)
    i, j = np.triu_indices(len(y), k=1)
    slopes = (y[j] - y[i]) / (j - i)
    slopes = slopes[~np.isnan(slopes)]
    return float(np.median(slopes)) if len(slopes) else None


def climate_summary(monthly: pd.DataFrame, years: int) -> tuple[Climate, Trends | None]:
    last = monthly["month"].max()
    recent = monthly[monthly["month"] > last - 12 * years]
    by_month = recent.groupby(recent["month"].dt.month).mean(numeric_only=True)
    months = [
        ClimateMonth(
            month=int(m),
            precip_mm=_num(r["precip"]),
            tmax_c=_num(r["tmax"]),
            tmin_c=_num(r["tmin"]),
            et0_mm=_num(r["et0"]),
            p_minus_et0_mm=_num(r["p_minus_et0"]),
            frost_days=_num(r["frost_days"]),
            hot_days=_num(r["hot_days"]),
            heavy_rain_days=_num(r["heavy_rain_days"]),
        )
        for m, r in by_month.iterrows()
    ]
    period = f"{recent['month'].min().year}–{last.year}"

    counts = recent.groupby(recent["month"].dt.year)["month"].count()
    full_years = counts[counts == 12].index
    annual = recent[recent["month"].dt.year.isin(full_years)].groupby(recent["month"].dt.year)
    trends = None
    if len(full_years) >= MIN_TREND_YEARS:

        def per_decade(series: pd.Series, digits: int) -> float | None:
            slope = sens_slope(series.tolist())
            return None if slope is None else round(slope * 10, digits)

        trends = Trends(
            precip_mm_per_decade=per_decade(annual["precip"].sum(min_count=1), 1),
            tmax_c_per_decade=per_decade(annual["tmax"].mean(), 2),
            frost_days_per_decade=per_decade(annual["frost_days"].sum(min_count=1), 1),
            n_years=len(full_years),
        )
    return Climate(period=period, months=months), trends


def _series(session_factory, ctx: FieldContext, since: date) -> Series | None:
    with session_factory() as db:
        rows = db.execute(_SERIES, {"ids": list(ctx.weights), "since": since}).mappings().all()
    if not rows:
        return None
    by_month: dict[date, list] = {}
    for r in rows:
        by_month.setdefault(r["month"], []).append(r)
    out = Series(months=[], ndvi=[], ndvi_z=[], sm_rootzone=[])
    for month, cells in sorted(by_month.items()):
        out.months.append(f"{month:%Y-%m}")
        for name, digits in (("ndvi", 3), ("ndvi_z", 2), ("sm_rootzone", 3)):
            value = context.weighted({c["cell_id"]: c[name] for c in cells}, ctx.weights)
            getattr(out, name).append(_num(value, digits))
    return out


def _greenness(session_factory, ctx: FieldContext) -> GreennessHistory | None:
    with session_factory() as db:
        rows = db.execute(_SUMMER_NDVI, {"ids": list(ctx.weights)}).mappings().all()
    by_year: dict[int, dict[str, float | None]] = {}
    for r in rows:
        value = r["ndvi"] if r["n"] >= MIN_SUMMER_MONTHS else None
        by_year.setdefault(r["year"], {})[r["cell_id"]] = value
    if not by_year:
        return None
    years = sorted(by_year)
    values = [_num(context.weighted(by_year[y], ctx.weights), 3) for y in years]
    known = sorted((v, y) for v, y in zip(values, years, strict=True) if v is not None)
    lowest = [y for _, y in known[: plain.config()["greenness_lowest_years"]]]
    if len(known) <= len(lowest):  # too few summers to call any of them "the least green"
        lowest = []
    return GreennessHistory(
        years=years, summer_ndvi=values, lowest_years=lowest, text=plain.greenness_text(lowest)
    )


async def get_conditions(
    field_id: str,
    years: int,
    http: httpx.AsyncClient,
    cache: Cache,
    session_factory,
) -> ConditionsOut:
    ctx: FieldContext = await run_in_threadpool(context.load_context, session_factory, field_id)
    gaps: list[InformationGap] = []
    quality: list[str] = []
    sources = ["power"]

    # --- soil ---
    soil: Soil | None = None
    static = ctx.static
    if ctx.pilot:
        sources += ["soilgrids", "srtm", "irish_sis"]
        soil = Soil(
            source="pilot_grid",
            **{k: _num(static[k], 2) for k in ("clay", "sand", "soc", "phh2o", "bdod")},
            drainage_class=static["drainage_class"],
            elev_m=_num(static["elev_m"]),
            slope_deg=_num(static["slope_deg"]),
        )
        if static["drainage_class"] is None:
            gaps.append(
                InformationGap(
                    code="drainage_unknown", text="We do not know how well this soil drains."
                )
            )
    else:
        try:
            sg = await soilgrids.fetch_soil(http, cache, ctx.lat, ctx.lon)
            sources.append("soilgrids")
            soil = Soil(
                source="soilgrids",
                **{k: sg[k] for k in ("clay", "sand", "soc", "phh2o", "bdod")},
                drainage_class=None,
                elev_m=None,
                slope_deg=None,
                uncertainty=sg.get("uncertainty") or None,
            )
            if all(sg[k] is None for k in ("clay", "sand", "soc")):
                gaps.append(
                    InformationGap(
                        code="soil_unavailable", text="There is no soil estimate for this spot."
                    )
                )
        except UpstreamError:
            gaps.append(
                InformationGap(
                    code="soil_unavailable",
                    text="We could not get the soil estimate right now. Try again later.",
                )
            )
    if soil is not None:
        soil.plain = [SoilFact(label=label, text=text_) for label, text_ in plain.soil_facts(soil)]
        gaps.append(
            InformationGap(
                code="no_soil_test",
                text="Soil values are estimates from a global map, not a test of your field.",
            )
        )

    # --- climate + trends ---
    climate = trends = None
    try:
        monthly, elevation = await context.monthly_history(
            http, cache, ctx.lat, ctx.lon, static["elev_m"], years
        )
        climate, trends = climate_summary(monthly, years)
        if soil is not None and soil.elev_m is None:
            soil.elev_m = _num(elevation)
    except UpstreamError:
        gaps.append(
            InformationGap(
                code="climate_unavailable",
                text="We could not get the weather history right now. Try again later.",
            )
        )

    # --- satellite series (pilot only) ---
    series = greenness = None
    if ctx.pilot:
        since = date(context.today().year - SERIES_YEARS, 1, 1)
        series = await run_in_threadpool(_series, session_factory, ctx, since)
        greenness = await run_in_threadpool(_greenness, session_factory, ctx)
        if greenness is not None:
            gaps.append(
                InformationGap(
                    code="greenness_is_area_not_field",
                    text="The satellite sees squares of about 250 metres, so this is the land "
                    "around your field, not only your field.",
                )
            )
        sources += ["modis_ndvi", "smap"]
        if is_synthetic(ctx.data_source):
            quality.append(SYNTHETIC_DATA)
    else:
        quality.append(OUTSIDE_PILOT)
        gaps.append(
            InformationGap(
                code="outside_pilot",
                text="Satellite crop history is only ready for Ireland. "
                "Here you see weather and soil only.",
            )
        )

    return ConditionsOut(
        field_id=field_id,
        pilot_coverage=ctx.pilot,
        climate=climate,
        trends=trends,
        soil=soil,
        series=series,
        greenness_history=greenness,
        data_quality=quality,
        information_gaps=gaps,
        provenance=provenance(*sources),
    )
