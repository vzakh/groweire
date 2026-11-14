"""Settings: env vars only (brief §12.7). No .env file is read here."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_PREFIX = "/api/v1"
REPO_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", protected_namespaces=())

    app_env: str = "dev"  # dev | test | prod
    version: str = "0.1.0"
    database_url: str = "postgresql+psycopg2://agrolens:agrolens@localhost:55432/agrolens"
    redis_url: str = "redis://localhost:56379/0"
    # False in prod: /health/ready then refuses synthetic tables. (The name is kept from the
    # model era so deploy env files keep working; no model is loaded any more, PLAN_40.)
    allow_stub_model: bool = True
    log_level: str = "INFO"
    frontend_origin: str = "http://localhost:5173"
    domain: str = "localhost"
    enable_docs: bool = True
    repo_url: str = "https://example.org/agrolens"
    contact_email: str = "change-me@example.org"

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
