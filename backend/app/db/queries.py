"""SQL used by the services. Geometry travels as hex EWKB; areas are computed on geography (m²)."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

# A geodesic circle: buffering a geography keeps the radius in metres on the spheroid.
_CIRCLE = text("""
    SELECT encode(ST_AsEWKB(g.geom), 'hex') AS ewkb, ST_Area(g.geom::geography) / 10000 AS area_ha
    FROM (
        SELECT ST_Buffer(
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m, 'quad_segs=16'
        )::geometry AS geom
    ) g
    """)

_AREA = text("SELECT ST_Area(CAST(:ewkb AS geometry)::geography) / 10000")

_INSERT_FIELD = text("""
    INSERT INTO fields (field_id, name, geom, area_ha, area_source, input_point, centroid,
                        pilot_coverage)
    SELECT :field_id, :name, g.geom, :area_ha, :area_source,
           CASE WHEN CAST(:lon AS double precision) IS NULL THEN NULL
                ELSE ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) END,
           CASE WHEN CAST(:lon AS double precision) IS NULL THEN ST_Centroid(g.geom)
                ELSE ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) END,
           EXISTS (SELECT 1 FROM grid_cells c WHERE ST_Intersects(c.geom, g.geom))
    FROM (SELECT CAST(:ewkb AS geometry) AS geom) g
    """)

_SELECT_FIELD = text("""
    SELECT field_id, name, area_ha, area_source, ST_X(centroid) AS lon, ST_Y(centroid) AS lat,
           pilot_coverage, ST_AsGeoJSON(geom, 6) AS geojson
    FROM fields WHERE field_id = :field_id
    """)

# Area-weighted: a field across two cells gets a mixed answer. ST_Intersects uses the GiST index.
_CELLS_FOR_FIELD = text("""
    SELECT c.cell_id, ST_Area(ST_Intersection(c.geom, f.geom)::geography) AS overlap_m2
    FROM grid_cells c JOIN fields f ON ST_Intersects(c.geom, f.geom)
    WHERE f.field_id = :field_id
    ORDER BY overlap_m2 DESC, c.cell_id
    """)


def circle(db: Session, lon: float, lat: float, radius_m: float) -> tuple[str, float]:
    row = db.execute(_CIRCLE, {"lon": lon, "lat": lat, "radius_m": radius_m}).one()
    return row.ewkb, float(row.area_ha)


def area_ha(db: Session, ewkb_hex: str) -> float:
    return float(db.execute(_AREA, {"ewkb": ewkb_hex}).scalar_one())


def insert_field(db: Session, **params) -> None:
    db.execute(_INSERT_FIELD, params)


def select_field(db: Session, field_id: str) -> dict | None:
    row = db.execute(_SELECT_FIELD, {"field_id": field_id}).mappings().one_or_none()
    if row is None:
        return None
    out = dict(row)
    out["geometry"] = json.loads(out.pop("geojson"))
    return out


def cells_for_field(db: Session, field_id: str) -> list[tuple[str, float]]:
    """[(cell_id, overlap_m2)] for the pilot cells under a field, largest overlap first."""
    rows = db.execute(_CELLS_FOR_FIELD, {"field_id": field_id}).all()
    return [(r.cell_id, float(r.overlap_m2)) for r in rows]


def cell_weights(db: Session, field_id: str) -> dict[str, float]:
    """cell_id -> share of the field's pilot overlap (sums to 1). Empty outside the pilot."""
    cells = cells_for_field(db, field_id)
    total = sum(m2 for _, m2 in cells)
    if total <= 0:
        return {cid: 1 / len(cells) for cid, _ in cells} if cells else {}
    return {cid: m2 / total for cid, m2 in cells}
