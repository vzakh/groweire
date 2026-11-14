"""POST /predict/stress-risk: the ML endpoint (brief §9)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from agrolens_ml import StressModel
from clients.cache import Cache
from core.deps import ModelInfo, get_cache, get_catalog, get_http, get_model, get_model_info
from models.common import ErrorOut
from models.fields import FieldCreate
from models.predict import PredictIn, PredictOut
from services import fields as field_service
from services import risk

router = APIRouter(prefix="/predict", tags=["predict"])


def _create_field(session_factory, geometry) -> str:
    with session_factory() as db:
        return field_service.create_field(db, FieldCreate(geometry=geometry)).field_id


@router.post(
    "/stress-risk",
    response_model=PredictOut,
    summary="Monthly probability of crop stress for a field, with uncertainty and reasons",
    responses={404: {"model": ErrorOut}, 422: {"model": ErrorOut}, 503: {"model": ErrorOut}},
)
async def stress_risk(
    request: Request,
    body: PredictIn,
    model: StressModel = Depends(get_model),
    info: ModelInfo = Depends(get_model_info),
    catalog=Depends(get_catalog),
    http: httpx.AsyncClient = Depends(get_http),
    cache: Cache = Depends(get_cache),
) -> PredictOut:
    session_factory = request.app.state.session_factory
    field_id = body.field_id
    if field_id is None:
        field_id = await run_in_threadpool(_create_field, session_factory, body.geometry)
    return await risk.predict_stress_risk(
        field_id,
        body.mode,
        body.crop_id,
        model=model,
        info=info,
        catalog=catalog,
        http=http,
        cache=cache,
        session_factory=session_factory,
    )
