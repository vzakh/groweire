"""Pilot loader (plan 20 task 20). Needs PostGIS: `make db-up`."""

from __future__ import annotations

import json
import shutil

import pyarrow.parquet as pq
import pytest
from sqlalchemy import text

from agrolens_ml import FEATURE_NAMES
from jobs.load_pilot import LoadError, load_gazetteer, load_pilot

pytestmark = pytest.mark.db


def test_loaded_counts_and_meta(pg_engine, pilot_dir):
    manifest = json.loads((pilot_dir / "_MANIFEST.json").read_text())
    with pg_engine.connect() as c:
        meta = c.execute(text("SELECT * FROM dataset_meta")).mappings().one()
        cells = c.execute(text("SELECT count(*) FROM grid_cells")).scalar_one()
        months = c.execute(text("SELECT count(*) FROM cell_month")).scalar_one()
        risk = c.execute(text("SELECT count(*) FROM risk_grid")).scalar_one()
    assert meta["source"] == "synthetic"
    assert meta["contract_version"] == manifest["contract_version"]
    assert (cells, months, risk) == (
        manifest["rows"]["grid_cells"],
        manifest["rows"]["cell_month_features"],
        manifest["rows"]["risk_grid"],
    )


def test_features_jsonb_has_exactly_feature_names_and_null_for_nan(pg_engine):
    with pg_engine.connect() as c:
        features = c.execute(text("SELECT features FROM cell_month LIMIT 50")).scalars().all()
    assert all(set(f) == set(FEATURE_NAMES) for f in features)
    values = [v for f in features for v in f.values()]
    assert all(v is None or isinstance(v, (int, float)) for v in values)


def test_db_features_predict_like_the_parquet_row(pg_engine, pilot_dir, stub_model):
    """jsonb / NaN / float conversion must not change what the model sees."""
    row = pq.read_table(pilot_dir / "cell_month_features.parquet").slice(100, 1).to_pylist()[0]
    with pg_engine.connect() as c:
        from_db = c.execute(
            text("SELECT features FROM cell_month WHERE cell_id = :c AND month = :m"),
            {"c": row["cell_id"], "m": f"{row['month']}-01"},
        ).scalar_one()
    from_parquet = {k: row[k] for k in FEATURE_NAMES}
    nan = float("nan")
    a = stub_model.predict([{k: nan if v is None else v for k, v in from_db.items()}])[0]
    b = stub_model.predict([{k: nan if v is None else v for k, v in from_parquet.items()}])[0]
    assert a["probability"] == pytest.approx(b["probability"], abs=1e-9)


def test_wrong_contract_version_is_refused_and_db_untouched(pg_engine, pilot_dir, tmp_path):
    bad = tmp_path / "bad"
    shutil.copytree(pilot_dir, bad)
    manifest = json.loads((bad / "_MANIFEST.json").read_text())
    manifest["contract_version"] = "9.9"
    (bad / "_MANIFEST.json").write_text(json.dumps(manifest))
    with pytest.raises(LoadError, match="contract_version"):
        load_pilot(pg_engine, bad)
    with pg_engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM grid_cells")).scalar_one() > 0


def test_wrong_feature_hash_is_refused(pg_engine, pilot_dir, tmp_path):
    bad = tmp_path / "bad"
    shutil.copytree(pilot_dir, bad)
    manifest = json.loads((bad / "_MANIFEST.json").read_text())
    manifest["feature_names_sha256"] = "0" * 64
    (bad / "_MANIFEST.json").write_text(json.dumps(manifest))
    with pytest.raises(LoadError, match="feature_names_sha256"):
        load_pilot(pg_engine, bad)


def test_cells_for_field_can_use_the_gist_index(pg_engine):
    with pg_engine.connect() as c:
        c.execute(text("SET enable_seqscan = off"))
        plan = c.execute(text("""
                EXPLAIN SELECT cell_id FROM grid_cells
                WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint(-6.955, 52.705), 4326))
                """)).scalars().all()
    assert "grid_cells_geom_idx" in "\n".join(plan)


def test_gazetteer_load_and_trigram_search(pg_engine, tmp_path):
    def line(gid, name, lat, lon, fclass, fcode, country, admin1, pop):
        cols = [
            gid,
            name,
            name,
            "",
            lat,
            lon,
            fclass,
            fcode,
            country,
            "",
            admin1,
            "01",
            "",
            "",
            pop,
        ]
        return "\t".join(str(x) for x in cols + ["", "", "Europe/Dublin", "2024-01-01"])

    (tmp_path / "IE.txt").write_text(
        "\n".join(
            [
                line(1, "Bagenalstown", 52.7, -6.96, "P", "PPL", "IE", "L", 2950),
                line(2, "Ballon", 52.74, -6.77, "P", "PPL", "IE", "L", 700),
                line(3, "Some Lake", 52.7, -6.9, "H", "LK", "IE", "L", 0),
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "GB.txt").write_text(
        "\n".join(
            [
                line(4, "Armagh", 54.35, -6.65, "P", "PPL", "GB", "NIR", 14700),
                line(5, "Campbeltown", 55.42, -5.6, "P", "PPL", "GB", "SCT", 4800),
                line(6, "London", 51.5, -0.12, "P", "PPLC", "GB", "ENG", 8900000),
            ]
        ),
        encoding="utf-8",
    )
    assert load_gazetteer(pg_engine, tmp_path) == 3
    with pg_engine.connect() as c:
        names = c.execute(text("""
                SELECT name FROM gazetteer WHERE lower(ascii_name) % 'bagenalstown'
                ORDER BY similarity(lower(ascii_name), 'bagenalstown') DESC LIMIT 5
                """)).scalars().all()
        c.execute(text("TRUNCATE gazetteer"))
        c.commit()
    assert names[0] == "Bagenalstown"


def test_gazetteer_is_skipped_without_dumps(pg_engine, tmp_path):
    assert load_gazetteer(pg_engine, tmp_path) is None
