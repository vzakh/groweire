"""GET /layers, GET /layers/stress-risk, GET /glossary (brief §9, plan 20 task 27)."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from core.config import APP_DIR
from core.deps import is_synthetic
from core.errors import AppError
from models.common import DISCLAIMER, SYNTHETIC_DATA, ErrorOut, Provenance, provenance
from services import plain, risk

router = APIRouter(tags=["layers"])
StressType = Literal["drought", "waterlogging", "heat", "frost"]

# One row per cell: the requested stress type, or (type omitted) the most frequent one, with ties
# going to the first type in plain.yaml `type_priority`.
_GRID = text("""
    SELECT DISTINCT ON (c.cell_id)
           c.cell_id, ST_AsGeoJSON(c.geom, 3) AS geometry, r.stress_type, r.years_hit,
           r.years_total, r.frequency
    FROM risk_counts r JOIN grid_cells c USING (cell_id)
    WHERE r.calendar_month = :month AND r.frequency IS NOT NULL
      AND (CAST(:type AS text) IS NULL OR r.stress_type = :type)
    ORDER BY c.cell_id, r.frequency DESC, array_position(CAST(:priority AS text[]), r.stress_type)
    """)
_META = text("SELECT source FROM dataset_meta LIMIT 1")


class LayerTime(BaseModel):
    default: str
    period: str


class Layer(BaseModel):
    id: str
    title: str
    description: str
    kind: str = Field(description="gibs_wmts | geojson")
    gibs_identifier: str | None
    url_template: str
    tile_matrix_set: str | None
    format: str
    max_zoom: int | None
    time: LayerTime
    attribution: str
    dataset_id: str


class LayersOut(BaseModel):
    gibs_as_of: str
    layers: list[Layer]


class StressRiskLayer(BaseModel):
    """GeoJSON FeatureCollection: one polygon per pilot cell.

    `properties.p` = counted frequency of `properties.stress_type` in that month.
    """

    type: str = "FeatureCollection"
    month: int
    stress_type: str | None = Field(
        description="The requested type; null = each cell shows its most frequent type"
    )
    features: list[dict]
    data_quality: list[str]
    disclaimer: str = DISCLAIMER
    provenance: list[Provenance]


class GlossaryTerm(BaseModel):
    id: str
    title: str = Field(description="Farmer words, shown on the main path")
    term: str = Field(description="Technical term, shown in the glossary only")
    text: str


class GlossaryOut(BaseModel):
    terms: list[GlossaryTerm]


@lru_cache
def _data(name: str) -> dict:
    return json.loads((APP_DIR / "data" / name).read_text(encoding="utf-8"))


@router.get("/layers", response_model=LayersOut, summary="Map layers: NASA GIBS + our risk grid")
def list_layers() -> LayersOut:
    return LayersOut(**{k: v for k, v in _data("layers.json").items() if not k.startswith("_")})


def _grid(session_factory, month: int, stress_type: str | None) -> tuple[list[dict], str | None]:
    params = {"month": month, "type": stress_type, "priority": plain.config()["type_priority"]}
    with session_factory() as db:
        source = db.execute(_META).scalar_one_or_none()
        rows = db.execute(_GRID, params).mappings().all()
    features = []
    for r in rows:
        low, high = risk.wilson_interval(r["years_hit"], r["years_total"])
        features.append(
            {
                "type": "Feature",
                "id": r["cell_id"],
                "geometry": json.loads(r["geometry"]),
                "properties": {
                    "cell_id": r["cell_id"],
                    "p": round(r["frequency"], 3),
                    "p_lo": round(low, 3),
                    "p_hi": round(high, 3),
                    "stress_type": r["stress_type"],
                    # Kept from 1.0 for older clients: same value as stress_type, or "other"
                    # when the rule never fired in this cell and month.
                    "dominant_type": r["stress_type"] if r["years_hit"] > 0 else "other",
                    "years_hit": r["years_hit"],
                    "years_total": r["years_total"],
                    "level": plain.level(r["frequency"]),
                },
            }
        )
    return features, source


@router.get(
    "/layers/stress-risk",
    response_model=StressRiskLayer,
    summary="Pilot grid as GeoJSON: how often a month was too dry, wet, hot or frosty per cell",
    responses={404: {"model": ErrorOut}},
)
async def stress_risk_layer(
    request: Request,
    month: int = Query(ge=3, le=10, description="Calendar month, March (3) to October (10)"),
    stress_type: StressType | None = Query(
        default=None,
        alias="type",
        description="drought | waterlogging | heat | frost. Omit for each cell's most frequent.",
    ),
) -> StressRiskLayer:
    features, source = await run_in_threadpool(
        _grid, request.app.state.session_factory, month, stress_type
    )
    if not features:
        raise AppError("layer_not_available", "The risk map is not loaded yet.", status=404)
    return StressRiskLayer(
        month=month,
        stress_type=stress_type,
        features=features,
        data_quality=[SYNTHETIC_DATA] if is_synthetic(source) else [],
        provenance=provenance("power", "met_eireann_smd", "irish_sis"),
    )


@router.get(
    "/glossary", response_model=GlossaryOut, tags=["glossary"], summary="Plain-language terms"
)
def glossary() -> GlossaryOut:
    return GlossaryOut(**_data("glossary.json"))
