"""GET /places: server-side place-name search (brief §9, D20)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Query, Request

from clients.cache import Cache
from core.deps import get_cache, get_http
from models.common import ErrorOut
from models.places import PlacesOut
from services import places as service

router = APIRouter(prefix="/places", tags=["places"])


@router.get(
    "",
    response_model=PlacesOut,
    summary="Find a town, village or townland by name (Ireland and Northern Ireland)",
    responses={503: {"model": ErrorOut, "description": "code=place_search_busy"}},
)
async def search_places(
    request: Request,
    q: str = Query(min_length=2, max_length=100, examples=["Bagenalstown"]),
    http: httpx.AsyncClient = Depends(get_http),
    cache: Cache = Depends(get_cache),
) -> PlacesOut:
    return await service.search(q, http, cache, request.app.state.session_factory)
