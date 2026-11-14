"""Shared ML -> Backend contract suite (brief §13.2). Parametrised by bundle dir and data dir:

    pytest ml/tests/contract -m contract --bundle ml/artifacts/stub_v0 --data data/synthetic
    pytest ml/tests/contract -m contract --bundle ml/artifacts/stress_lgbm_v1 --data data/processed

The backend runs the same suite from backend/tests/contract/ (PLAN_20).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("agrolens contract")
    group.addoption(
        "--bundle",
        default=str(REPO / "ml/artifacts/stub_v0"),
        help="model bundle directory (default: ml/artifacts/stub_v0)",
    )
    group.addoption(
        "--data",
        default=str(REPO / "data/synthetic"),
        help="data products directory (default: data/synthetic)",
    )


def _resolve(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() or p.exists() else REPO / p


@pytest.fixture(scope="session")
def bundle_dir(request: pytest.FixtureRequest) -> Path:
    path = _resolve(request.config.getoption("--bundle"))
    if not (path / "bundle.joblib").exists():
        pytest.fail(f"no bundle.joblib in {path} (run `make stub`)")
    return path


@pytest.fixture(scope="session")
def data_dir(request: pytest.FixtureRequest) -> Path:
    path = _resolve(request.config.getoption("--data"))
    if not (path / "_MANIFEST.json").exists():
        pytest.fail(f"no _MANIFEST.json in {path} (run `make synthetic`)")
    return path


@pytest.fixture(scope="session")
def model(bundle_dir: Path):
    from agrolens_ml import load_bundle

    return load_bundle(bundle_dir)


@pytest.fixture(scope="session")
def example(bundle_dir: Path) -> dict:
    return json.loads((bundle_dir / "example.json").read_text())


@pytest.fixture(scope="session")
def manifest(data_dir: Path) -> dict:
    return json.loads((data_dir / "_MANIFEST.json").read_text())
