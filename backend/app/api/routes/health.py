"""Liveness and readiness (brief §9, §12.8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from agrolens_ml import CONTRACT_VERSION, RISK_RULES_VERSION
from core.config import Settings
from core.deps import get_settings, is_synthetic, read_data_source
from core.errors import AppError

router = APIRouter(prefix="/health", tags=["health"])


class LiveOut(BaseModel):
    status: str = "ok"


class ReadyOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str = "ok"
    model_version: str = Field(description="Version of the counting rules (no trained model)")
    model_kind: str = Field(description="Always `counted_history` since contract 2.0")
    data_source: str
    contract_version: str
    cache: str  # "redis" | "degraded" (Postgres fallback, brief §9.2)


def _data_source(session_factory) -> str | None:
    with session_factory() as session:
        return read_data_source(session)


def _has_counts(session_factory) -> bool:
    with session_factory() as session:
        return bool(session.execute(text("SELECT EXISTS (SELECT 1 FROM risk_counts)")).scalar())


@router.get("/live", response_model=LiveOut, summary="Process is up")
def live() -> LiveOut:
    return LiveOut()


@router.get("/ready", response_model=ReadyOut, summary="DB, cache and the counted risks are usable")
async def ready(request: Request, settings: Settings = Depends(get_settings)) -> ReadyOut:
    factory = request.app.state.session_factory
    try:
        data_source = await run_in_threadpool(_data_source, factory)
        has_counts = data_source is not None and await run_in_threadpool(_has_counts, factory)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("ready_db_failed error={}", type(exc).__name__)
        raise AppError("db_unavailable", "The database is not reachable.", 503) from exc
    if data_source is None or not has_counts:
        raise AppError("dataset_not_loaded", "No pilot data is loaded yet (run load-pilot).", 503)

    if not settings.allow_stub_model and is_synthetic(data_source):
        raise AppError("stub_model_in_prod", "Synthetic data is loaded in production.", 503)

    # Redis down is degraded, not failing: the cache falls back to Postgres (brief §9.2).
    try:
        await request.app.state.redis.ping()
        cache = "redis"
    except Exception:  # pylint: disable=broad-except
        cache = "degraded"

    return ReadyOut(
        model_version=RISK_RULES_VERSION,
        model_kind="counted_history",
        data_source=data_source,
        contract_version=CONTRACT_VERSION,
        cache=cache,
    )
