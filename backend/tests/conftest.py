"""Backend test setup. Tests never hit the network (brief rule 3).

DB tests (marker `db`) use a SEPARATE database `agrolens_test` on the local PostGIS from
`make db-up`, loaded with a small seeded synthetic pilot around Co. Carlow. They are skipped
when PostGIS is not reachable.
"""

from __future__ import annotations

import os
from pathlib import Path

ADMIN_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL", "postgresql+psycopg2://agrolens:agrolens@localhost:55432/agrolens"
)
TEST_DB = "agrolens_test"
TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + "/" + TEST_DB

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = TEST_URL  # never the dev or prod database
os.environ.setdefault("ALLOW_STUB_MODEL", "true")  # = allow synthetic tables (no model is loaded)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from agrolens_ml import make_synthetic_tables  # noqa: E402
from clients.cache import Cache  # noqa: E402
from core.config import REPO_ROOT, get_settings  # noqa: E402
from testing import FakeRedis  # noqa: E402

BACKEND = REPO_ROOT / "backend"
GRID_CSV = REPO_ROOT / "ml" / "pipelines" / "config" / "grid_005deg.csv"
TEST_BBOX = (-7.6, 52.3, -6.4, 53.1)  # lon_min, lat_min, lon_max, lat_max: Carlow / Kilkenny


@pytest.fixture
def app():
    """A fresh app per test, so dependency overrides and settings never leak between tests."""
    get_settings.cache_clear()
    from main import create_app  # pylint: disable=import-outside-toplevel

    application = create_app()
    yield application
    application.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def client(app):
    with TestClient(app) as c:  # runs lifespan
        # Tests never depend on a running Redis: swap in the in-memory fake.
        app.state.redis = FakeRedis()
        app.state.cache = Cache(app.state.redis, app.state.session_factory)
        yield c


@pytest.fixture(scope="session")
def pilot_dir(tmp_path_factory) -> Path:
    """A small schema-exact synthetic pilot (a few hundred real grid cells)."""
    work = tmp_path_factory.mktemp("pilot")
    lon0, lat0, lon1, lat1 = TEST_BBOX
    lines = GRID_CSV.read_text(encoding="utf-8").splitlines()
    keep = [lines[0]]
    for line in lines[1:]:
        _, lon, lat = line.split(",")
        if lon0 <= float(lon) <= lon1 and lat0 <= float(lat) <= lat1:
            keep.append(line)
    grid = work / "grid.csv"
    grid.write_text("\n".join(keep) + "\n", encoding="utf-8")
    return Path(make_synthetic_tables(grid, work / "synthetic", seed=7))


@pytest.fixture(scope="session")
def pg_engine(pilot_dir):
    """Migrated + loaded test database; skips the test when PostGIS is not running."""
    from alembic import command  # pylint: disable=import-outside-toplevel
    from alembic.config import Config  # pylint: disable=import-outside-toplevel

    from jobs.load_pilot import load_pilot  # pylint: disable=import-outside-toplevel

    try:
        admin = create_engine(
            ADMIN_URL, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 2}
        )
        with admin.connect() as c:
            exists = c.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB}
            ).scalar()
            if not exists:
                c.execute(text(f"CREATE DATABASE {TEST_DB}"))
        admin.dispose()
    except OperationalError:
        pytest.skip("PostGIS is not reachable: run `make db-up`")

    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["url"] = TEST_URL
    command.upgrade(cfg, "head")

    engine = create_engine(TEST_URL)
    load_pilot(engine, pilot_dir)
    yield engine
    engine.dispose()


@pytest.fixture
def db_client(pg_engine, client):
    """A client on the loaded test database; rows the test creates are removed afterwards."""
    yield client
    with pg_engine.begin() as c:
        c.execute(text("TRUNCATE fields, api_cache"))


@pytest.fixture
def pilot_field(db_client) -> str:
    """A 10 ha field near Bagenalstown, Co. Carlow (inside the pilot grid)."""
    r = db_client.post("/api/v1/fields", json={"point": [-6.955, 52.705], "area_ha": 10})
    return r.json()["field_id"]


@pytest.fixture
def kenya_field(db_client) -> str:
    """A field outside the pilot (Kenya highlands)."""
    r = db_client.post("/api/v1/fields", json={"point": [36.9, -0.4], "area_ha": 5})
    return r.json()["field_id"]
