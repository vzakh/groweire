"""Alembic environment: plain SQL migrations, URL from the app settings (env vars)."""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from core.config import get_settings  # noqa: E402  pylint: disable=wrong-import-position

# Tests pass their own URL through config attributes; otherwise use DATABASE_URL.
URL = context.config.attributes.get("url") or get_settings().database_url


def run_migrations() -> None:
    engine = create_engine(URL)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
