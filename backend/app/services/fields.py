"""Fields: point + approximate area -> geodesic circle, or a drawn polygon (plan 20 task 21)."""

from __future__ import annotations

import math
import re
import secrets

from shapely import wkb
from shapely.geometry import Polygon
from shapely.validation import explain_validity
from sqlalchemy.orm import Session

from core.errors import AppError
from db import queries
from models.fields import FieldCreate, FieldOut, PolygonIn

MIN_AREA_HA = 0.1
MAX_AREA_HA = 2_000.0
MAX_VERTICES = 500
CIRCLE_SIDES = 64  # ST_Buffer quad_segs=16
_FIELD_ID = re.compile(r"^f_[0-9a-f]{8}$")


def _bad(code: str, detail: str) -> AppError:
    return AppError(code, detail, status=422)


def _check_lon_lat(lon: float, lat: float) -> None:
    if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
        raise _bad("invalid_point", "The point must be [lon, lat] with lon -180..180, lat -90..90.")


def _check_area(area_ha: float) -> None:
    if not math.isfinite(area_ha) or not MIN_AREA_HA <= area_ha <= MAX_AREA_HA:
        raise _bad("area_out_of_range", "The field must be between 0.1 and 2,000 hectares.")


def circle_radius_m(area_ha: float) -> float:
    """Radius whose 64-sided buffer polygon has the requested area (a true circle is ~0.2% more)."""
    polygon_factor = (CIRCLE_SIDES / 2) * math.sin(2 * math.pi / CIRCLE_SIDES)  # -> pi as n grows
    return math.sqrt(area_ha * 10_000 / polygon_factor)


def polygon_from_geojson(geometry: PolygonIn) -> Polygon:
    if geometry.type != "Polygon":
        raise _bad("invalid_geometry", "The geometry must be a GeoJSON Polygon.")
    rings = geometry.coordinates
    if not rings:
        raise _bad("invalid_geometry", "The polygon has no rings.")
    if sum(len(ring) for ring in rings) > MAX_VERTICES:
        raise _bad("too_many_vertices", "The field outline has too many points (500 at most).")
    clean: list[list[tuple[float, float]]] = []
    for ring in rings:
        if len(ring) < 4:
            raise _bad("invalid_geometry", "Each ring needs at least 4 positions.")
        if any(len(position) < 2 for position in ring):
            raise _bad("invalid_geometry", "Each position must be [lon, lat].")
        if ring[0][:2] != ring[-1][:2]:
            raise _bad("invalid_geometry", "Each ring must be closed (first = last position).")
        for position in ring:
            _check_lon_lat(position[0], position[1])
        clean.append([(position[0], position[1]) for position in ring])
    polygon = Polygon(clean[0], clean[1:])
    if not polygon.is_valid:
        raise _bad("invalid_geometry", f"The outline is not valid: {explain_validity(polygon)}.")
    if polygon.is_empty or polygon.area == 0:
        raise _bad("invalid_geometry", "The outline has no area.")
    return polygon


def create_field(db: Session, body: FieldCreate) -> FieldOut:
    lon = lat = None
    if body.geometry is None:
        lon, lat = body.point
        _check_lon_lat(lon, lat)
        _check_area(body.area_ha)
        ewkb, area = queries.circle(db, lon, lat, circle_radius_m(body.area_ha))
        area_source = "approximate"
    else:
        polygon = polygon_from_geojson(body.geometry)
        ewkb = wkb.dumps(polygon, hex=True, srid=4326)
        area = queries.area_ha(db, ewkb)
        area_source = "drawn"
    _check_area(area)

    field_id = "f_" + secrets.token_hex(4)
    queries.insert_field(
        db,
        field_id=field_id,
        name=(body.name or "").strip() or None,
        ewkb=ewkb,
        area_ha=area,
        area_source=area_source,
        lon=lon,
        lat=lat,
    )
    out = _read(db, field_id)
    db.commit()
    return out


def _read(db: Session, field_id: str) -> FieldOut:
    row = queries.select_field(db, field_id)
    if row is None:
        raise AppError("field_not_found", "We could not find that field.", status=404)
    return FieldOut(
        field_id=row["field_id"],
        name=row["name"],
        area_ha=round(row["area_ha"], 2),
        area_source=row["area_source"],
        centroid=(round(row["lon"], 6), round(row["lat"], 6)),
        pilot_coverage=row["pilot_coverage"],
        cell_ids=[cell_id for cell_id, _ in queries.cells_for_field(db, field_id)],
        geometry=row["geometry"],
    )


def get_field(db: Session, field_id: str) -> FieldOut:
    if not _FIELD_ID.match(field_id):
        raise AppError("field_not_found", "We could not find that field.", status=404)
    return _read(db, field_id)
