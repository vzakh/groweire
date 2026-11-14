"""JSON cache: Redis first, Postgres `api_cache` as the fallback (brief §9.2, D16).

If Redis is unreachable the API keeps serving from Postgres (degraded, not failing).
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from core.metrics import CACHE_HITS

_PG_GET = text("""
    SELECT payload FROM api_cache
    WHERE key = :key AND (ttl_s IS NULL OR fetched_at + ttl_s * interval '1 second' > now())
    """)
_PG_SET = text("""
    INSERT INTO api_cache (key, payload, fetched_at, ttl_s)
    VALUES (:key, CAST(:payload AS jsonb), now(), :ttl_s)
    ON CONFLICT (key) DO UPDATE
    SET payload = EXCLUDED.payload, fetched_at = EXCLUDED.fetched_at, ttl_s = EXCLUDED.ttl_s
    """)


class Cache:
    """`ttl_s=None` means keep forever."""

    def __init__(self, redis, session_factory=None):
        self.redis = redis
        self.session_factory = session_factory

    # --- Postgres fallback (sync, run in a threadpool) ---
    def _pg_get(self, key: str) -> Any | None:
        with self.session_factory() as session:
            row = session.execute(_PG_GET, {"key": key}).scalar_one_or_none()
        return None if row is None else row.get("v")

    def _pg_set(self, key: str, value: Any, ttl_s: int | None) -> None:
        with self.session_factory() as session:
            session.execute(
                _PG_SET, {"key": key, "payload": json.dumps({"v": value}), "ttl_s": ttl_s}
            )
            session.commit()

    async def _fallback(self, func, *args) -> Any | None:
        if self.session_factory is None:
            return None
        try:
            return await run_in_threadpool(func, *args)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("cache_fallback_failed error={}", type(exc).__name__)
            return None

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self.redis.get(key)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("cache_degraded op=get error={}", type(exc).__name__)
            value = await self._fallback(self._pg_get, key)
            if value is not None:
                CACHE_HITS.labels(layer="postgres").inc()
            return value
        if raw is None:
            return None
        CACHE_HITS.labels(layer="redis").inc()
        return json.loads(raw)

    async def set(self, key: str, value: Any, ttl_s: int | None) -> None:
        try:
            await self.redis.set(key, json.dumps(value), ex=ttl_s)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("cache_degraded op=set error={}", type(exc).__name__)
            await self._fallback(self._pg_set, key, value, ttl_s)

    async def get_or_set(
        self, key: str, ttl_s: int | None, loader: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Cached value, or `await loader()` stored under `key`. Loader errors are not cached."""
        hit = await self.get(key)
        if hit is not None:
            return hit
        value = await loader()
        if value is not None:
            await self.set(key, value, ttl_s)
        return value
