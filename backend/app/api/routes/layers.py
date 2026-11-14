"""GET /layers, GET /layers/stress-risk, GET /glossary (brief §9, plan 20 task 27)."""

from __future__ import annotations

import json
from functools import lru_cache

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from core.config import APP_DIR
from core.deps import ModelInfo, get_model_info, is_synthetic
from core.errors import AppError
from models.common import DISCLAIMER, SYNTHETIC_DATA, ErrorOut, Provenance, provenance
from services import plain

router = APIRouter(tags=["layers"])

_GRID = text("""
    SELECT c.cell_id, ST_AsGeoJSON(c.geom, 3) AS geometry, r.p_mean_10y, r.p_lo, r.p_hi,
           r.dominant_type
    FROM risk_grid r JOIN grid_cells c USING (cell_id)
    WHERE r.calendar_month = :month AND r.p_mean_10y IS NOT NULL
    ORDER BY c.cell_id
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
    """GeoJSON FeatureCollection: one polygon per pilot cell, `properties.p` = risk in that month."""

    type: str = "FeatureCollection"
    month: int
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


def _grid(session_factory, month: int) -> tuple[list[dict], str | None]:
    with session_factory() as db:
        source = db.execute(_META).scalar_one_or_none()
        rows = db.execute(_GRID, {"month": month}).mappings().all()
    features = [
        {
            "type": "Feature",
            "id": r["cell_id"],
            "geometry": json.loads(r["geometry"]),
            "properties": {
                "cell_id": r["cell_id"],
                "p": round(r["p_mean_10y"], 3),
                "p_lo": None if r["p_lo"] is None else round(r["p_lo"], 3),
                "p_hi": None if r["p_hi"] is None else round(r["p_hi"], 3),
                "dominant_type": r["dominant_type"],
                "level": plain.level(r["p_mean_10y"]),
            },
        }
        for r in rows
    ]
    return features, source


@router.get(
    "/layers/stress-risk",
    response_model=StressRiskLayer,
    summary="Pilot grid as GeoJSON with the stress risk per cell for one month",
    responses={404: {"model": ErrorOut}},
)
async def stress_risk_layer(
    request: Request,
    month: int = Query(ge=3, le=10, description="Calendar month, March (3) to October (10)"),
    info: ModelInfo = Depends(get_model_info),
) -> StressRiskLayer:
    features, source = await run_in_threadpool(_grid, request.app.state.session_factory, month)
    if not features:
        raise AppError("layer_not_available", "The risk map is not loaded yet.", status=404)
    return StressRiskLayer(
        month=month,
        features=features,
        data_quality=[SYNTHETIC_DATA] if is_synthetic(info, source) else [],
        provenance=provenance("modis_ndvi", "power", "smap"),
    )


@router.get(
    "/glossary", response_model=GlossaryOut, tags=["glossary"], summary="Plain-language terms"
)
def glossary() -> GlossaryOut:
    return GlossaryOut(**_data("glossary.json"))
