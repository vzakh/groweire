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
    model_dir: Path | None = None  # baked into the image; in dev resolved from ml/artifacts/CURRENT
    allow_stub_model: bool = True  # false in prod: /health/ready then refuses stub / synthetic
    log_level: str = "INFO"
    frontend_origin: str = "http://localhost:5173"
    domain: str = "localhost"
    enable_docs: bool = True
    repo_url: str = "https://example.org/agrolens"
    contact_email: str = "change-me@example.org"

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"

    def resolved_model_dir(self) -> Path:
        """MODEL_DIR if set, else ml/artifacts/<CURRENT>. The folder name is never hard-coded."""
        if self.model_dir is not None:
            return self.model_dir
        artifacts = REPO_ROOT / "ml" / "artifacts"
        current = (artifacts / "CURRENT").read_text(encoding="utf-8").strip()
        if not current:
            raise RuntimeError(f"{artifacts / 'CURRENT'} is empty")
        return artifacts / current


@lru_cache
def get_settings() -> Settings:
    return Settings()
