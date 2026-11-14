"""Load the ML data products (parquet) into PostGIS. Idempotent (plan 20 task 20).

    python -m jobs.load_pilot data/synthetic            # tasks 20-27
    python -m jobs.load_pilot data/processed            # task 28

The folder's _MANIFEST.json must match the installed agrolens_ml (contract version and
FEATURE_NAMES hash); otherwise nothing is loaded. Data and its `dataset_meta` label are written
in ONE transaction, so they can never disagree.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import time
from pathlib import Path

import pyarrow.parquet as pq
from sqlalchemy import Engine

from agrolens_ml import CONTRACT_VERSION, FEATURE_NAMES, schemas
from core.config import REPO_ROOT, get_settings
from db.session import make_engine

BATCH_ROWS = 20_000
ISLAND_BBOX = (-10.7, 51.3, -5.4, 55.5)  # lon_min, lat_min, lon_max, lat_max (brief D1)
GEONAMES_FILES = ("IE.txt", "GB.txt")
# GeoNames feature codes -> our `kind` (anything else in class P is a "locality").
KIND_BY_CODE = {
    "PPLC": "city",
    "PPLA": "town",
    "PPLA2": "town",
    "PPLA3": "town",
    "PPLA4": "town",
    "PPL": "village",
    "PPLF": "village",
}
TOWNLAND_CODES = ("ADM4", "ADM5", "PRSH")
LOCALITY_CODES = ("LCTY", "AREA")

GRID_STATIC = [f.name for f in schemas.GRID_CELLS_SCHEMA if f.name not in ("cell_id", "geom")]
CELL_MONTH_FIXED = [
    f.name for f in schemas.CELL_MONTH_FIXED_FIELDS if f.name not in ("cell_id", "month")
]
RISK_COLUMNS = list(schemas.RISK_COUNTS_SCHEMA.names)


class LoadError(Exception):
    """The folder cannot be loaded; the message says why in plain words."""


def _clean(value):
    """NaN -> None (SQL NULL / JSON null); everything else unchanged."""
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def read_manifest(data_dir: Path) -> dict:
    path = data_dir / "_MANIFEST.json"
    if not path.exists():
        raise LoadError(f"{path} is missing. Run `make synthetic` or point to data/processed.")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in schemas.MANIFEST_KEYS if k not in manifest]
    if missing:
        raise LoadError(f"{path}: missing keys {missing}")
    if manifest["source"] not in ("synthetic", "real"):
        raise LoadError(f"{path}: source must be 'synthetic' or 'real', got {manifest['source']!r}")
    if manifest["contract_version"] != CONTRACT_VERSION:
        raise LoadError(
            f"{path}: contract_version {manifest['contract_version']!r} does not match the "
            f"installed agrolens_ml CONTRACT_VERSION {CONTRACT_VERSION!r}. Refusing to load."
        )
    installed = schemas.feature_names_sha256(FEATURE_NAMES)
    if manifest["feature_names_sha256"] != installed:
        raise LoadError(
            f"{path}: feature_names_sha256 does not match the installed agrolens_ml FEATURE_NAMES. "
            "The tables were built by a different ML version. Rebuild them or update the package."
        )
    return manifest


def _check_schema(path: Path, expected) -> None:
    if not path.exists():
        raise LoadError(f"{path} is missing")
    got = pq.read_schema(path)
    if not got.equals(expected):
        got_f = {f.name: str(f.type) for f in got}
        exp_f = {f.name: str(f.type) for f in expected}
        diff = {
            "missing": sorted(set(exp_f) - set(got_f)),
            "unexpected": sorted(set(got_f) - set(exp_f)),
            "wrong_type": sorted(k for k in set(got_f) & set(exp_f) if got_f[k] != exp_f[k]),
        }
        raise LoadError(f"{path.name}: schema does not match agrolens_ml.schemas: {diff}")


def _copy(cur, table: str, columns: list[str], rows) -> int:
    buf = io.StringIO()
    writer = csv.writer(buf)
    n = 0
    for row in rows:
        writer.writerow(row)
        n += 1
    buf.seek(0)
    cur.copy_expert(
        f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, NULL '')", buf
    )
    return n


def _batches(path: Path):
    for batch in pq.ParquetFile(path).iter_batches(batch_size=BATCH_ROWS):
        yield batch.to_pylist()


def _load_grid(cur, path: Path) -> int:
    columns = ["cell_id", "geom", "centroid", *GRID_STATIC]
    total = 0
    for rows in _batches(path):
        total += _copy(
            cur,
            "grid_cells",
            columns,
            (
                [
                    r["cell_id"],
                    f"SRID=4326;{r['geom']}",
                    f"SRID=4326;POINT({r['lon']} {r['lat']})",
                    *(_clean(r[c]) for c in GRID_STATIC),
                ]
                for r in rows
            ),
        )
    return total


def _load_cell_month(cur, path: Path) -> int:
    columns = ["cell_id", "month", "features", *CELL_MONTH_FIXED]
    total = 0
    for rows in _batches(path):
        total += _copy(
            cur,
            "cell_month",
            columns,
            (
                [
                    r["cell_id"],
                    f"{r['month']}-01",
                    json.dumps({k: _clean(r[k]) for k in FEATURE_NAMES}, allow_nan=False),
                    *(_clean(r[c]) for c in CELL_MONTH_FIXED),
                ]
                for r in rows
            ),
        )
    return total


def _pg_value(value):
    """NaN -> NULL; a list -> a Postgres array literal."""
    if isinstance(value, list):
        return "{" + ",".join(str(int(v)) for v in value) + "}"
    return _clean(value)


def _load_risk(cur, path: Path) -> int:
    total = 0
    for rows in _batches(path):
        total += _copy(
            cur,
            "risk_counts",
            RISK_COLUMNS,
            ([_pg_value(r[c]) for c in RISK_COLUMNS] for r in rows),
        )
    return total


def _county_names(geonames_dir: Path) -> dict[str, str]:
    """`<country>.<admin1>.<admin2>` -> name, from GeoNames admin2Codes.txt when it is present."""
    path = geonames_dir / "admin2Codes.txt"
    if not path.exists():
        return {}
    names = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[0].startswith(("IE.", "GB.")):
                names[parts[0]] = parts[1]
    return names


def _kind(f_class: str, f_code: str) -> str | None:
    if f_class == "P":
        return KIND_BY_CODE.get(f_code, "locality")
    if f_class in ("L", "A"):
        if f_code in TOWNLAND_CODES:
            return "townland"
        if f_code in LOCALITY_CODES:
            return "locality"
    return None


def _gazetteer_rows(geonames_dir: Path):
    counties = _county_names(geonames_dir)
    lon0, lat0, lon1, lat1 = ISLAND_BBOX
    for filename in GEONAMES_FILES:
        path = geonames_dir / filename
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) < 15:
                    continue
                kind = _kind(p[6], p[7])
                if kind is None:
                    continue
                try:
                    lat, lon = float(p[4]), float(p[5])
                except ValueError:
                    continue
                if not (lon0 <= lon <= lon1 and lat0 <= lat <= lat1):
                    continue
                # GB rows inside the island bbox = Northern Ireland (admin1 NIR); skip Scotland.
                if p[8] == "GB" and p[10] != "NIR":
                    continue
                county = counties.get(f"{p[8]}.{p[10]}.{p[11]}")
                population = int(p[14]) if p[14].isdigit() else 0
                point = f"SRID=4326;POINT({lon} {lat})"
                yield [int(p[0]), p[1], p[2] or p[1], kind, county, point, population]


def load_gazetteer(engine: Engine, geonames_dir: Path) -> int | None:
    """Load GeoNames IE + GB(NI) places. Returns None when the dumps are not there."""
    if not any((geonames_dir / f).exists() for f in GEONAMES_FILES):
        return None
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur:
            cur.execute("TRUNCATE gazetteer")
            n = _copy(
                cur,
                "gazetteer",
                ["place_id", "name", "ascii_name", "kind", "county", "geom", "population"],
                _gazetteer_rows(geonames_dir),
            )
            cur.execute("ANALYZE gazetteer")
        raw.commit()
        return n
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def load_pilot(engine: Engine, data_dir: Path) -> dict:
    """Validate, then replace grid_cells / cell_month / risk_counts / dataset_meta atomically."""
    data_dir = Path(data_dir)
    manifest = read_manifest(data_dir)
    files = {
        "grid_cells": (data_dir / "grid_cells.parquet", schemas.GRID_CELLS_SCHEMA),
        "cell_month_features": (
            data_dir / "cell_month_features.parquet",
            schemas.cell_month_schema(FEATURE_NAMES),
        ),
        "risk_counts": (data_dir / "risk_counts.parquet", schemas.RISK_COUNTS_SCHEMA),
    }
    for path, expected in files.values():
        _check_schema(path, expected)

    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur:
            cur.execute("TRUNCATE grid_cells, cell_month, risk_counts, dataset_meta")
            counts = {
                "grid_cells": _load_grid(cur, files["grid_cells"][0]),
                "cell_month": _load_cell_month(cur, files["cell_month_features"][0]),
                "risk_counts": _load_risk(cur, files["risk_counts"][0]),
            }
            cur.execute(
                "INSERT INTO dataset_meta (source, contract_version, feature_names_sha256,"
                " ml_version, row_counts) VALUES (%s, %s, %s, %s, %s)",
                (
                    manifest["source"],
                    manifest["contract_version"],
                    manifest["feature_names_sha256"],
                    manifest.get("ml_version"),
                    json.dumps(counts),
                ),
            )
            cur.execute("ANALYZE grid_cells")
            cur.execute("ANALYZE cell_month")
            cur.execute("ANALYZE risk_counts")
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    return {"source": manifest["source"], "ml_version": manifest.get("ml_version"), **counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data_dir", type=Path, nargs="?", help="data/synthetic or data/processed")
    parser.add_argument(
        "--gazetteer-only",
        action="store_true",
        help="load only the GeoNames gazetteer and leave the pilot tables alone",
    )
    parser.add_argument(
        "--geonames",
        type=Path,
        default=REPO_ROOT / "data" / "raw" / "geonames",
        help="folder with the GeoNames IE.txt / GB.txt dumps (optional)",
    )
    args = parser.parse_args(argv)
    if args.data_dir is None and not args.gazetteer_only:
        parser.error("data_dir is required unless --gazetteer-only is given")
    engine = make_engine(get_settings().database_url)
    if not args.gazetteer_only:
        started = time.perf_counter()
        try:
            result = load_pilot(engine, args.data_dir)
        except LoadError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        print(f"loaded {result} in {time.perf_counter() - started:.1f}s")
    places = load_gazetteer(engine, args.geonames)
    if places is None:
        print(
            f"gazetteer skipped: no GeoNames dumps in {args.geonames} (place-search fallback off)"
        )
    else:
        print(f"gazetteer: {places} places")
    engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
