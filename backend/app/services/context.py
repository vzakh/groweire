"""What we know about a field: its pilot cells, static description and POWER monthly history.

Shared by the conditions, predict and rotation services, so each fact is computed in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx
import pandas as pd
from sqlalchemy import text

from agrolens_ml import CELL_STATIC_KEYS, MONTHLY_INPUT_COLUMNS, power_daily_to_monthly
from clients import power
from clients.cache import Cache
from core.deps import read_data_source
from core.errors import AppError
from db import queries

HISTORY_YEARS = 30  # one canonical POWER range per grid node -> one cached response
MAX_HISTORY_YEARS = 40
_NUMERIC_STATIC = [k for k in CELL_STATIC_KEYS if k not in ("lat", "lon", "drainage_class")]

_CELLS = text(f"""
    SELECT cell_id, drainage_class, {", ".join(_NUMERIC_STATIC)}
    FROM grid_cells WHERE cell_id = ANY(:ids)
    """)


@dataclass
class FieldContext:
    field_id: str
    lon: float
    lat: float
    area_ha: float
    pilot: bool
    weights: dict[str, float]  # cell_id -> share of the field (sums to 1); empty outside the pilot
    static: dict  # exactly CELL_STATIC_KEYS; None where unknown
    data_source: str | None  # dataset_meta.source
    missing_static: list[str] = field(default_factory=list)


def today() -> date:
    """Wrapped so tests and the fixture export can freeze the clock."""
    return date.today()


def weighted(values: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Area-weighted mean over the cells that have a value."""
    pairs = [(v, weights[c]) for c, v in values.items() if v is not None and c in weights]
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total > 0 else None


def load_context(session_factory, field_id: str) -> FieldContext:
    """Sync (run in a threadpool from async routes). Raises AppError 404 for an unknown field."""
    with session_factory() as db:
        row = queries.select_field(db, field_id) if field_id.startswith("f_") else None
        if row is None:
            raise AppError("field_not_found", "We could not find that field.", status=404)
        weights = queries.cell_weights(db, field_id)
        static: dict = {key: None for key in CELL_STATIC_KEYS}
        static["lat"], static["lon"] = row["lat"], row["lon"]
        if weights:
            cells = db.execute(_CELLS, {"ids": list(weights)}).mappings().all()
            for key in _NUMERIC_STATIC:
                static[key] = weighted({c["cell_id"]: c[key] for c in cells}, weights)
            # An ordinal class cannot be averaged: take the cell covering most of the field.
            by_share = sorted(cells, key=lambda c: -weights[c["cell_id"]])
            static["drainage_class"] = next(
                (c["drainage_class"] for c in by_share if c["drainage_class"] is not None), None
            )
        return FieldContext(
            field_id=field_id,
            lon=row["lon"],
            lat=row["lat"],
            area_ha=row["area_ha"],
            pilot=bool(weights),
            weights=weights,
            static=static,
            data_source=read_data_source(db),
        )


def history_range(years: int = HISTORY_YEARS) -> tuple[date, date]:
    """[Jan 1 of N years back, last day of the last complete month]."""
    end = today().replace(day=1) - timedelta(days=1)
    span = HISTORY_YEARS if years <= HISTORY_YEARS else MAX_HISTORY_YEARS
    return date(end.year - span, 1, 1), end


async def monthly_history(
    http: httpx.AsyncClient,
    cache: Cache,
    lat: float,
    lon: float,
    elev_m: float | None,
    years: int = HISTORY_YEARS,
) -> tuple[pd.DataFrame, float | None]:
    """(monthly_history, POWER elevation): POWER daily -> agrolens_ml.power_daily_to_monthly, cached.

    Columns = MONTHLY_INPUT_COLUMNS.

    Raises UpstreamError("power_unavailable").
    """
    start, end = history_range(years)
    node_lat, node_lon = power.snap(lat, lon)
    elev_tag = "p" if elev_m is None else f"{elev_m:.0f}"
    key = f"monthly:v2:{node_lat:.3f}:{node_lon:.4f}:{start}:{end}:{elev_tag}:{lat:.1f}"

    async def load() -> dict:
        payload = await power.fetch_daily(http, cache, lat, lon, start, end)
        elevation = elev_m if elev_m is not None else (payload.get("elevation_m") or 0.0)
        monthly = power_daily_to_monthly(power.daily_frame(payload), elev_m=elevation, lat=lat)
        monthly = monthly.assign(month=monthly["month"].astype(str))
        rows = monthly.astype(object).where(monthly.notna(), None).to_dict("records")
        return {"elevation_m": payload.get("elevation_m"), "rows": rows}

    blob = await cache.get_or_set(key, power.TTL_S, load)
    frame = pd.DataFrame.from_records(blob["rows"], columns=list(MONTHLY_INPUT_COLUMNS))
    numeric = [c for c in MONTHLY_INPUT_COLUMNS if c != "month"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce").astype(float)
    frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
    return frame, blob.get("elevation_m")
