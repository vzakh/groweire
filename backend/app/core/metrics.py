"""Prometheus metrics (brief §12.8). `/metrics` is served by the API but not routed by Traefik."""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

PREDICTIONS = Counter("stress_model_predictions_total", "Feature rows scored by the stress model")
EXTERNAL_ERRORS = Counter(
    "external_api_errors_total", "Failed calls to an external API", ["source"]
)
CACHE_HITS = Counter("cache_hits_total", "Cache hits", ["layer"])  # layer: redis | postgres


def install_metrics(app: FastAPI) -> None:
    Instrumentator(excluded_handlers=["/metrics", ".*/health/live"]).instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )
