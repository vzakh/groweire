"""Sync SQLAlchemy engine + session factory (plan 20 principle 7)."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str) -> Engine:
    # 5 + 5 per worker: keep replicas x workers x 10 < max_connections (brief §12.8).
    return create_engine(database_url, pool_size=5, max_overflow=5, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
