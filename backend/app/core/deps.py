"""FastAPI dependencies. Tests swap these through app.dependency_overrides."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import get_settings

__all__ = [
    "get_settings",
    "get_db",
    "get_http",
    "get_redis",
    "get_cache",
    "get_catalog",
    "get_data_source",
    "is_synthetic",
]


def get_db(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


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


def is_synthetic(data_source: str | None) -> bool:
    """True when a response is built on synthetic tables (brief §8.8)."""
    return data_source != "real"
