"""Fields API (plan 20 task 21). Needs PostGIS: `make db-up`."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.db
URL = "/api/v1/fields"


def square(lon: float, lat: float, d: float) -> dict:
    ring = [[lon, lat], [lon + d, lat], [lon + d, lat + d], [lon, lat + d], [lon, lat]]
    return {"type": "Polygon", "coordinates": [ring]}


def test_point_and_area_makes_a_circle_of_that_area(db_client):
    r = db_client.post(URL, json={"name": "Home field", "point": [-6.955, 52.705], "area_ha": 10})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["field_id"].startswith("f_") and len(body["field_id"]) == 10
    assert body["area_source"] == "approximate"
    assert body["area_ha"] == pytest.approx(10, rel=0.02)
    assert body["centroid"] == [-6.955, 52.705]
    assert body["pilot_coverage"] is True
    assert body["cell_ids"] == ["c01300"]
    assert body["geometry"]["type"] == "Polygon"
    assert body["name"] == "Home field"


@pytest.mark.parametrize("area", [0.05, 5000])
def test_area_out_of_range_is_rejected(db_client, area):
    r = db_client.post(URL, json={"point": [-6.955, 52.705], "area_ha": area})
    assert r.status_code == 422
    assert r.json()["code"] == "area_out_of_range"


def test_point_out_of_range_is_rejected(db_client):
    r = db_client.post(URL, json={"point": [-200, 52.7], "area_ha": 10})
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_point"


def test_both_shapes_is_ambiguous(db_client):
    body = {"point": [-6.955, 52.705], "area_ha": 10, "geometry": square(-7.25, 52.65, 0.01)}
    r = db_client.post(URL, json=body)
    assert r.status_code == 422
    assert r.json()["code"] == "field_input_ambiguous"


@pytest.mark.parametrize("body", [{}, {"name": "x"}, {"point": [-6.9, 52.7]}, {"area_ha": 10}])
def test_neither_or_half_shape_is_ambiguous(db_client, body):
    r = db_client.post(URL, json=body)
    assert r.status_code == 422
    assert r.json()["code"] == "field_input_ambiguous"


def test_valid_polygon(db_client):
    r = db_client.post(URL, json={"geometry": square(-7.25, 52.65, 0.01)})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["area_source"] == "drawn"
    assert 50 < body["area_ha"] < 100
    assert body["pilot_coverage"] is True
    assert len(body["cell_ids"]) >= 1


def test_self_intersecting_polygon(db_client):
    bowtie = [[-7.25, 52.65], [-7.24, 52.66], [-7.24, 52.65], [-7.25, 52.66], [-7.25, 52.65]]
    r = db_client.post(URL, json={"geometry": {"type": "Polygon", "coordinates": [bowtie]}})
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_geometry"
    assert "intersection" in r.json()["detail"].lower()


def test_too_large_polygon(db_client):
    r = db_client.post(URL, json={"geometry": square(-7.3, 52.6, 0.1)})
    assert r.status_code == 422
    assert r.json()["code"] == "area_out_of_range"


def test_too_many_vertices(db_client):
    ring = [[-7.25 + i * 1e-5, 52.65] for i in range(520)]
    ring += [[-7.24, 52.66], ring[0]]
    r = db_client.post(URL, json={"geometry": {"type": "Polygon", "coordinates": [ring]}})
    assert r.status_code == 422
    assert r.json()["code"] == "too_many_vertices"


def test_unclosed_ring_and_wrong_type(db_client):
    ring = [[-7.25, 52.65], [-7.24, 52.65], [-7.24, 52.66], [-7.25, 52.66]]
    r = db_client.post(URL, json={"geometry": {"type": "Polygon", "coordinates": [ring]}})
    assert r.json()["code"] == "invalid_geometry"
    r = db_client.post(URL, json={"geometry": {"type": "LineString", "coordinates": [ring]}})
    assert r.json()["code"] == "invalid_geometry"


def test_non_pilot_polygon_in_kenya(db_client):
    r = db_client.post(URL, json={"geometry": square(36.9, -0.4, 0.005)})
    assert r.status_code == 201, r.text
    assert r.json()["pilot_coverage"] is False
    assert r.json()["cell_ids"] == []


def test_polygon_across_two_cells(db_client):
    # Cells are 0.05° wide and meet at lon -6.95.
    r = db_client.post(URL, json={"geometry": square(-6.955, 52.71, 0.01)})
    assert r.status_code == 201, r.text
    assert sorted(r.json()["cell_ids"]) == ["c01300", "c01301"]


def test_get_field_roundtrip_and_404(db_client):
    created = db_client.post(URL, json={"point": [-6.955, 52.705], "area_ha": 4}).json()
    r = db_client.get(f"{URL}/{created['field_id']}")
    assert r.status_code == 200
    assert r.json() == created

    for missing in ("f_00000000", "nope", "f_ZZZZZZZZ"):
        r = db_client.get(f"{URL}/{missing}")
        assert r.status_code == 404
        assert r.json()["code"] == "field_not_found"
