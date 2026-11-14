"""Liveness and readiness (brief §9, §12.8)."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Request
from loguru import logger
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from agrolens_ml import CONTRACT_VERSION, StressModel
from core.config import Settings
from core.deps import (
    ModelInfo,
    get_model,
    get_model_info,
    get_settings,
    is_synthetic,
    read_data_source,
)
from core.errors import AppError

router = APIRouter(prefix="/health", tags=["health"])


class LiveOut(BaseModel):
    status: str = "ok"


class ReadyOut(BaseModel):
    status: str = "ok"
    model_version: str
    model_kind: str
    data_source: str
    contract_version: str
    cache: str  # "redis" | "degraded" (Postgres fallback, brief §9.2)


def _data_source(session_factory) -> str | None:
    with session_factory() as session:
        return read_data_source(session)


def _self_check(model: StressModel, info: ModelInfo) -> None:
    """One prediction on the bundle's example.json must reproduce its expected probability."""
    features = {
        k: (math.nan if v is None else v) for k, v in info.example.get("features", {}).items()
    }
    got = model.predict([features])[0]["probability"]
    want = info.example.get("expected", {}).get("probability")
    if not math.isfinite(got) or (want is not None and abs(got - want) > 1e-6):
        raise AppError("model_selfcheck_failed", "The model self-check failed.", 503)


@router.get("/live", response_model=LiveOut, summary="Process is up")
def live() -> LiveOut:
    return LiveOut()


@router.get("/ready", response_model=ReadyOut, summary="DB, cache and model are usable")
async def ready(
    request: Request,
    settings: Settings = Depends(get_settings),
    model: StressModel = Depends(get_model),
    info: ModelInfo = Depends(get_model_info),
) -> ReadyOut:
    try:
        data_source = await run_in_threadpool(_data_source, request.app.state.session_factory)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("ready_db_failed error={}", type(exc).__name__)
        raise AppError("db_unavailable", "The database is not reachable.", 503) from exc
    if data_source is None:
        raise AppError("dataset_not_loaded", "No pilot data is loaded yet (run load-pilot).", 503)

    _self_check(model, info)

    if not settings.allow_stub_model and is_synthetic(info, data_source):
        raise AppError(
            "stub_model_in_prod", "The stub model or synthetic data is loaded in production.", 503
        )

    # Redis down is degraded, not failing: the cache falls back to Postgres (brief §9.2).
    try:
        await request.app.state.redis.ping()
        cache = "redis"
    except Exception:  # pylint: disable=broad-except
        cache = "degraded"

    return ReadyOut(
        model_version=model.version,
        model_kind=info.kind,
        data_source=data_source,
        contract_version=CONTRACT_VERSION,
        cache=cache,
    )
