"""pyarrow schemas of the data products (brief §13.2). Part of the ML -> Backend contract."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

import pyarrow as pa

from agrolens_ml.contract import CELL_STATIC_KEYS

_F32 = pa.float32()

_GRID_TYPES = {"lat": pa.float64(), "lon": pa.float64(), "drainage_class": pa.int8()}
GRID_CELLS_SCHEMA = pa.schema(
    [
        pa.field("cell_id", pa.string(), nullable=False),
        pa.field("geom", pa.string(), nullable=False),
    ]
    + [pa.field(k, _GRID_TYPES.get(k, _F32)) for k in CELL_STATIC_KEYS]
    + [pa.field("arable_fraction", _F32)]  # optional EUCROPMAP refinement; null if not computed
)

# Fixed columns of cell_month_features; one float32 column per FEATURE_NAMES follows (D22).
CELL_MONTH_FIXED_FIELDS: tuple[pa.Field, ...] = (
    pa.field("cell_id", pa.string(), nullable=False),
    pa.field("month", pa.string(), nullable=False),  # "YYYY-MM"
    pa.field("ndvi", _F32),
    pa.field("ndvi_z", _F32),
    pa.field("stress_label", pa.bool_()),  # null = excluded from training (low valid_frac / winter)
    pa.field("valid_frac", _F32),
    pa.field("precip", _F32),
    pa.field("et0", _F32),
    pa.field("p_minus_et0", _F32),
    pa.field("t2m", _F32),
    pa.field("sm_rootzone", _F32),
)


def cell_month_schema(feature_names: Sequence[str]) -> pa.Schema:
    """Schema of cell_month_features.parquet for a given FEATURE_NAMES."""
    return pa.schema(list(CELL_MONTH_FIXED_FIELDS) + [pa.field(f, _F32) for f in feature_names])


def _default_cell_month_schema() -> pa.Schema:
    from agrolens_ml.features.build import FEATURE_NAMES  # pylint: disable=import-outside-toplevel

    return cell_month_schema(FEATURE_NAMES)


CELL_MONTH_SCHEMA = _default_cell_month_schema()

RISK_GRID_SCHEMA = pa.schema(
    [
        pa.field("cell_id", pa.string(), nullable=False),
        pa.field("calendar_month", pa.int8(), nullable=False),  # 3..10
        pa.field("p_mean_10y", _F32),
        pa.field("p_lo", _F32),
        pa.field("p_hi", _F32),
        pa.field("trend_per_decade", _F32),
        pa.field("dominant_type", pa.string()),
    ]
)

MANIFEST_KEYS: tuple[str, ...] = (
    "source",  # "synthetic" | "real"
    "contract_version",
    "feature_names_sha256",
    "created_at",
    "ml_version",
)

TABLE_SCHEMAS: dict[str, str] = {
    "grid_cells": "GRID_CELLS_SCHEMA",
    "cell_month_features": "CELL_MONTH_SCHEMA",
    "risk_grid": "RISK_GRID_SCHEMA",
}


def feature_names_sha256(feature_names: Sequence[str] | None = None) -> str:
    """Stable hash of a FEATURE_NAMES tuple; tables and bundle must agree on it."""
    if feature_names is None:
        from agrolens_ml.features.build import (
            FEATURE_NAMES,
        )  # pylint: disable=import-outside-toplevel

        feature_names = FEATURE_NAMES
    return hashlib.sha256("\n".join(feature_names).encode()).hexdigest()
