"""POST /rotations/compare (brief §9)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Request

from clients.cache import Cache
from core.deps import get_cache, get_catalog, get_http
from models.common import ErrorOut
from models.rotations import CompareIn, CompareOut
from services import rotation

router = APIRouter(prefix="/rotations", tags=["rotations"])


@router.post(
    "/compare",
    response_model=CompareOut,
    summary="Compare the current rotation with alternatives, weighted by the farmer's priorities",
    responses={404: {"model": ErrorOut}, 422: {"model": ErrorOut}},
)
async def compare(
    request: Request,
    body: CompareIn,
    catalog=Depends(get_catalog),
    http: httpx.AsyncClient = Depends(get_http),
    cache: Cache = Depends(get_cache),
) -> CompareOut:
    return await rotation.compare(
        body,
        catalog=catalog,
        http=http,
        cache=cache,
        session_factory=request.app.state.session_factory,
    )
