"""FastAPI dependencies. Tests swap these through app.dependency_overrides."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import httpx
from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from agrolens_ml import StressModel
from core.config import get_settings

__all__ = [
    "ModelInfo",
    "get_settings",
    "get_db",
    "get_model",
    "get_model_info",
    "get_http",
    "get_redis",
    "get_cache",
    "get_catalog",
    "get_data_source",
    "is_synthetic",
]


@dataclass(frozen=True)
class ModelInfo:
    """What the bundle folder says about itself (model_card.json + example.json)."""

    version: str
    kind: str
    example: dict


def get_db(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_model(request: Request) -> StressModel:
    return request.app.state.stress_model


def get_model_info(request: Request) -> ModelInfo:
    return request.app.state.model_info


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def get_redis(request: Request):
    return request.app.state.redis


def get_cache(request: Request):
    return request.app.state.cache


def get_catalog(request: Request):
    return request.app.state.catalog


def read_data_source(db: Session) -> str | None:
    """`dataset_meta.source` ('synthetic' | 'real'), or None when no data is loaded yet."""
    return db.execute(text("SELECT source FROM dataset_meta LIMIT 1")).scalar_one_or_none()


def get_data_source(db: Session = Depends(get_db)) -> str | None:
    return read_data_source(db)


def is_synthetic(info: ModelInfo, data_source: str | None) -> bool:
    """True when a response is built on the stub model or on synthetic tables (brief §8.8)."""
    return info.kind == "stub" or data_source != "real"
