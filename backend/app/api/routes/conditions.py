"""GET /fields/{id}/conditions (brief §9)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Query, Request

from clients.cache import Cache
from core.deps import ModelInfo, get_cache, get_http, get_model_info
from models.common import ErrorOut
from models.conditions import ConditionsOut
from services import conditions as service

router = APIRouter(prefix="/fields", tags=["conditions"])


@router.get(
    "/{field_id}/conditions",
    response_model=ConditionsOut,
    summary="Climate summary, trends, soil and satellite history for a field",
    responses={404: {"model": ErrorOut}},
)
async def get_conditions(
    request: Request,
    field_id: str,
    years: int = Query(default=30, ge=5, le=40),
    http: httpx.AsyncClient = Depends(get_http),
    cache: Cache = Depends(get_cache),
    info: ModelInfo = Depends(get_model_info),
) -> ConditionsOut:
    return await service.get_conditions(
        field_id, years, http, cache, request.app.state.session_factory, info
    )
