"""AgroLens API application factory (plan 20)."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI
from loguru import logger

from agrolens_ml import StressModel, load_bundle
from api.routes import conditions, crops, fields, health, layers, places, predict, rotations
from clients.cache import Cache
from core.config import API_PREFIX, get_settings
from core.deps import ModelInfo
from core.errors import install_error_handlers
from core.logging import setup_logging
from core.metrics import install_metrics
from core.middleware import install_middleware
from db.session import make_engine, make_session_factory
from services.rotation import check_codes
from services.rotation.catalog import load_catalog

ROUTERS = (health, places, fields, conditions, predict, crops, rotations, layers)


def read_model_info(model_dir: Path, model: StressModel) -> ModelInfo:
    card = json.loads((model_dir / "model_card.json").read_text(encoding="utf-8"))
    example = json.loads((model_dir / "example.json").read_text(encoding="utf-8"))
    kind = card.get("model_details", {}).get("kind", "unknown")
    return ModelInfo(version=model.version, kind=kind, example=example)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    setup_logging(s.log_level, json_logs=s.app_env != "test")
    app.state.engine = make_engine(s.database_url)
    app.state.session_factory = make_session_factory(app.state.engine)
    app.state.redis = aioredis.from_url(
        s.redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=2
    )
    app.state.cache = Cache(app.state.redis, app.state.session_factory)
    app.state.http = httpx.AsyncClient(
        timeout=httpx.Timeout(20, connect=5),
        # Nominatim requires a custom, identifying User-Agent (D20).
        headers={"User-Agent": f"AgroLens/{s.version} (+{s.repo_url}; {s.contact_email})"},
    )
    model_dir = s.resolved_model_dir()
    app.state.stress_model = load_bundle(model_dir)  # raises on FEATURE_NAMES drift
    app.state.model_info = read_model_info(model_dir, app.state.stress_model)
    app.state.catalog = load_catalog()  # raises on unsourced numbers
    check_codes(app.state.catalog)
    logger.info(
        "startup model_version={} model_kind={} env={}",
        app.state.model_info.version,
        app.state.model_info.kind,
        s.app_env,
    )
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()
    app.state.engine.dispose()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="AgroLens API",
        version="1.0.0",
        description="Monthly crop-stress risk and rotation comparison for Irish farms. "
        "This tool supports, not replaces, your judgment and local agronomic advice.",
        lifespan=lifespan,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs" if s.enable_docs else None,
        redoc_url=None,
    )
    for module in ROUTERS:
        app.include_router(module.router, prefix=API_PREFIX)
    install_metrics(app)
    install_middleware(app, s)
    install_error_handlers(app)
    return app


app = create_app()
