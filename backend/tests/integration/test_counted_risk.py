"""Counted risks on the REAL tables (PLAN_40 task 44; replaces the model parity tests).

    make db-up && make migrate && make load-pilot DATA=data/processed
    PYTHONPATH=backend/app uv run --package agrolens-backend pytest backend/tests/integration -m integration

Unlike the unit tests (synthetic tables in the `agrolens_test` database, see conftest.py), these
read the loaded DEV database, read-only. They are skipped when the real tables are not there:
no PostGIS, or synthetic data loaded.

Do not loosen a check to make it pass: a failure here means the live path and the pilot table
disagree, or the counted numbers no longer say what the screen says.
"""

from __future__ import annotations

import json
import os

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from agrolens_ml import RISK_TYPES, count_risks
from clients import power
from core.config import REPO_ROOT

pytestmark = pytest.mark.integration

DEV_URL = os.environ.get(
    "INTEGRATION_DATABASE_URL", "postgresql+psycopg2://agrolens:agrolens@localhost:55432/agrolens"
)
POWER_SAMPLE = REPO_ROOT / "backend" / "tests" / "fixtures" / "power_cell_sample.json"
SEASON = range(3, 11)
# The recorded POWER response ends on 2025-06-30: March-June have every year the table has,
# July-October lack 2025.
FULL_MONTHS = (3, 4, 5, 6)


@pytest.fixture(scope="module")
def dev_db():
    engine = create_engine(DEV_URL, connect_args={"connect_timeout": 2})
    try:
        with engine.connect() as c:
            source = c.execute(text("SELECT source FROM dataset_meta LIMIT 1")).scalar_one_or_none()
            has_counts = c.execute(text("SELECT to_regclass('risk_counts')")).scalar_one()
    except OperationalError:
        pytest.skip("PostGIS is not reachable: run `make db-up`")
    if source != "real" or has_counts is None:
        pytest.skip(
            f"dev database holds {source!r} data: run `make migrate` and "
            "`make load-pilot DATA=data/processed`"
        )
    yield engine
    engine.dispose()


def _table_counts(engine, cell_id: str) -> dict[tuple[int, str], dict]:
    with engine.connect() as c:
        rows = (
            c.execute(text("SELECT * FROM risk_counts WHERE cell_id = :c"), {"c": cell_id})
            .mappings()
            .all()
        )
    return {(r["calendar_month"], r["stress_type"]): dict(r) for r in rows}


def test_every_cell_has_every_month_and_type(dev_db):
    with dev_db.connect() as c:
        cells = c.execute(text("SELECT count(*) FROM grid_cells")).scalar_one()
        per_cell = c.execute(
            text(
                "SELECT min(n), max(n), count(*) FROM (SELECT count(*) n FROM risk_counts GROUP BY cell_id) t"
            )
        ).one()
        years = c.execute(text("SELECT min(years_total), max(years_total) FROM risk_counts")).one()
    expected = len(SEASON) * len(RISK_TYPES)
    assert tuple(per_cell) == (expected, expected, cells)
    assert tuple(years) == (25, 25)  # 2001-2025, complete


def test_table_counts_reproduce_from_the_recorded_nasa_response(dev_db):
    """Recorded POWER daily + the cell's IMERG monthly rain -> the same counts the table holds.

    The model path failed its parity check (serving computed ET0 from other inputs than
    training). The counted path has ONE implementation, agrolens_ml.count_risks, used for the
    pilot table and for live points, so the numbers must be equal.
    """
    imerg_path = REPO_ROOT / "data" / "processed" / "imerg_cell_month.parquet"
    if not imerg_path.exists():
        pytest.skip("data/processed/imerg_cell_month.parquet is not there")
    recorded = json.loads(POWER_SAMPLE.read_text(encoding="utf-8"))
    cell_id = recorded["_recorded"]["pilot_cell"]
    with dev_db.connect() as c:
        drainage = c.execute(
            text("SELECT drainage_class FROM grid_cells WHERE cell_id = :c"), {"c": cell_id}
        ).scalar_one()
    table = _table_counts(dev_db, cell_id)
    imerg = pd.read_parquet(imerg_path, filters=[("cell_id", "==", cell_id)])
    lon, lat, elevation = recorded["geometry"]["coordinates"]

    # The backend's own POWER parsing (client validation + daily_frame), then the shared rules.
    payload = {
        "elevation_m": elevation,
        "parameter": {
            name: {day: (None if v == power.FILL_VALUE else v) for day, v in series.items()}
            for name, series in recorded["properties"]["parameter"].items()
        },
    }
    counts = count_risks(
        power.daily_frame(payload),
        elev_m=elevation,
        lat=lat,
        drainage_class=drainage,
        monthly_rain_mm=imerg.set_index("month")["precip_mm"],
    )
    live = {(r["calendar_month"], r["stress_type"]): r for r in counts.to_dict("records")}
    assert set(live) == set(table) == {(m, t) for m in SEASON for t in RISK_TYPES}

    problems = []
    for key, want in sorted(table.items()):
        got = live[key]
        if key[0] in FULL_MONTHS:
            same = (
                got["years_hit"] == want["years_hit"]
                and got["years_total"] == want["years_total"]
                and list(got["example_years"]) == list(want["example_years"])
            )
        else:  # 2025 is missing from the recording: at most that one year can differ
            hit_2025 = want["years_hit"] - got["years_hit"]
            same = got["years_total"] == want["years_total"] - 1 and hit_2025 in (0, 1)
        if not same:
            problems.append(f"{key}: recomputed={got} table={want}")
    assert not problems, f"{cell_id}: counts differ from the pilot table:\n" + "\n".join(problems)
