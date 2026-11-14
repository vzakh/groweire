"""Data products match schemas.py and agree with the bundle (brief §13.2)."""

from __future__ import annotations

import joblib
import pyarrow.parquet as pq
import pytest

from agrolens_ml import CONTRACT_VERSION, FEATURE_NAMES, schemas

pytestmark = pytest.mark.contract

TABLES = {
    "grid_cells": schemas.GRID_CELLS_SCHEMA,
    "cell_month_features": schemas.CELL_MONTH_SCHEMA,
    "risk_grid": schemas.RISK_GRID_SCHEMA,
}


def _types(schema):
    return [(f.name, f.type) for f in schema]


@pytest.mark.parametrize("name", TABLES)
def test_table_schema(data_dir, name):
    actual = pq.read_schema(data_dir / f"{name}.parquet")
    assert _types(actual) == _types(TABLES[name])


def test_manifest(manifest):
    assert set(schemas.MANIFEST_KEYS) <= set(manifest)
    assert manifest["source"] in ("synthetic", "real")
    assert manifest["contract_version"] == CONTRACT_VERSION
    assert manifest["feature_names_sha256"] == schemas.feature_names_sha256(FEATURE_NAMES)


def test_manifest_matches_bundle(manifest, bundle_dir):
    bundle = joblib.load(bundle_dir / "bundle.joblib")
    if bundle["kind"] == "stub" and manifest["source"] == "real":
        pytest.skip("stub bundle serving real tables (sync point S1): hash check skipped")
    assert manifest["feature_names_sha256"] == schemas.feature_names_sha256(bundle["feature_names"])


def test_cell_month_keys_unique(data_dir):
    cm = pq.read_table(data_dir / "cell_month_features.parquet", columns=["cell_id", "month"])
    df = cm.to_pandas()
    assert not df.duplicated().any()
    assert df["month"].str.fullmatch(r"\d{4}-\d{2}").all()


def test_risk_grid(data_dir):
    risk = pq.read_table(data_dir / "risk_grid.parquet").to_pandas()
    cells = pq.read_table(data_dir / "grid_cells.parquet", columns=["cell_id"]).to_pandas()
    counts = risk.groupby("cell_id").size()
    assert set(counts.index) == set(cells["cell_id"])
    assert (counts == 8).all()
    assert set(risk["calendar_month"]) == set(range(3, 11))
    for col in ("p_mean_10y", "p_lo", "p_hi"):
        assert risk[col].between(0, 1).all(), col
    assert (risk["p_lo"] <= risk["p_mean_10y"] + 1e-6).all()
    assert (risk["p_mean_10y"] <= risk["p_hi"] + 1e-6).all()
    assert set(risk["dominant_type"].dropna()) <= {
        "drought",
        "waterlogging",
        "heat",
        "frost",
        "other",
    }
