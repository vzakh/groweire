"""Write backend/tests/fixtures/api/*.json: example responses for the frontend (task 27).

    make fixtures        # needs `make db-up migrate` and `make load-pilot DATA=...` first

Boots the real app on the loaded database, with the model from ml/artifacts/CURRENT, an
in-memory Redis and mocked external APIs (no network). Field ids and the clock are fixed, so a
re-export only changes values when the model or the data changed. Each file carries
`_fixture_source` (the model version) and `_request`.
"""

from __future__ import annotations

import itertools
import json
import sys
from datetime import date

import respx
from fastapi.testclient import TestClient
from sqlalchemy import text

from clients import nominatim, power, soilgrids
from clients.cache import Cache
from core.config import REPO_ROOT
from main import create_app
from services import context
from services import fields as field_service
from testing import FakeRedis, nominatim_payload, power_responder, soil_payload

OUT_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "api"
FROZEN_TODAY = date(2026, 11, 14)
API = "/api/v1"
PILOT_POINT = [-6.955, 52.705]  # near Bagenalstown, Co. Carlow
POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [[-7.25, 52.65], [-7.24, 52.65], [-7.24, 52.66], [-7.25, 52.66], [-7.25, 52.65]]
    ],
}
ROTATION = {
    "current_rotation": ["spring_barley"] * 4,
    "priorities": ["income_stability", "simplicity", "soil_cover"],
    "constraints": {
        "has_livestock": False,
        "irrigation": False,
        "equipment": None,
        "excluded_crops": ["potatoes"],
        "must_include": [],
        "market_contracts": ["malting_barley"],
    },
    "n_alternatives": 3,
}
MAX_LAYER_FEATURES = 60  # the full grid is ~1 MB; the fixture keeps a sample
GAZETTEER_SEED = """
    INSERT INTO gazetteer (place_id, name, ascii_name, kind, county, geom, population)
    VALUES (-1, 'Bagenalstown', 'Bagenalstown', 'village', 'Carlow',
            ST_SetSRID(ST_MakePoint(-6.96, 52.70), 4326), 2950)
    ON CONFLICT DO NOTHING
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    counter = itertools.count(1)
    field_service.secrets.token_hex = lambda _n=4: f"{next(counter):08x}"  # stable field ids
    context.today = lambda: FROZEN_TODAY
    app = create_app()
    written = []

    with TestClient(app) as client, respx.mock(assert_all_called=False) as mock:
        app.state.redis = FakeRedis()
        app.state.cache = Cache(app.state.redis, app.state.session_factory)
        mock.get(power.POWER_URL).mock(side_effect=power_responder)
        mock.get(soilgrids.SOILGRIDS_URL).respond(json=soil_payload())
        osm = mock.get(nominatim.NOMINATIM_URL).respond(json=nominatim_payload())
        source = app.state.stress_model.version
        engine = app.state.engine

        def save(name: str, method: str, path: str, body=None, expect: int = 200, trim=None):
            response = client.request(method, API + path, json=body)
            if response.status_code != expect:
                raise SystemExit(
                    f"{name}: expected {expect}, got {response.status_code}: {response.text}"
                )
            payload = response.json()
            if trim:
                trim(payload)
            payload = {
                "_fixture_source": source,
                "_request": {"method": method, "path": API + path, "body": body, "status": expect},
                **payload,
            }
            (OUT_DIR / f"{name}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            written.append(name)
            return payload

        with engine.begin() as c:
            c.execute(text("DELETE FROM fields WHERE field_id ~ '^f_0000'"))
            c.execute(text(GAZETTEER_SEED))
        try:
            save("health_ready", "GET", "/health/ready")
            save("places", "GET", "/places?q=Bagenalstown")
            # Nominatim down -> answered from the local GeoNames gazetteer.
            osm.respond(503)
            app.state.redis.store.pop(nominatim.BUCKET_KEY, None)
            save("places_fallback", "GET", "/places?q=bagenalstwn")
            osm.respond(json=nominatim_payload())

            pilot = save(
                "fields_create_point",
                "POST",
                "/fields",
                {"name": "Home field", "point": PILOT_POINT, "area_ha": 10},
                201,
            )["field_id"]
            save(
                "fields_create_polygon",
                "POST",
                "/fields",
                {"name": "Drawn field", "geometry": POLYGON},
                201,
            )
            kenya = client.post(API + "/fields", json={"point": [36.9, -0.4], "area_ha": 5}).json()[
                "field_id"
            ]
            save("fields_get", "GET", f"/fields/{pilot}")
            save("conditions_pilot", "GET", f"/fields/{pilot}/conditions")
            save("conditions_non_pilot", "GET", f"/fields/{kenya}/conditions")
            save(
                "predict_seasonal_profile",
                "POST",
                "/predict/stress-risk",
                {"field_id": pilot, "mode": "seasonal_profile", "crop_id": "spring_barley"},
            )
            save(
                "predict_seasonal_profile_no_crop",
                "POST",
                "/predict/stress-risk",
                {"field_id": pilot, "mode": "seasonal_profile"},
            )
            save(
                "predict_next_month",
                "POST",
                "/predict/stress-risk",
                {"field_id": pilot, "mode": "next_month", "crop_id": "spring_barley"},
            )
            save(
                "predict_non_pilot",
                "POST",
                "/predict/stress-risk",
                {"field_id": kenya, "mode": "seasonal_profile"},
            )
            save("crops", "GET", "/crops?region=IE")
            save("rotations_compare", "POST", "/rotations/compare", {"field_id": pilot, **ROTATION})
            save("layers", "GET", "/layers")

            def sample(payload: dict) -> None:
                payload["_truncated_from"] = len(payload["features"])
                payload["features"] = payload["features"][:MAX_LAYER_FEATURES]

            save("layers_stress_risk", "GET", "/layers/stress-risk?month=7", trim=sample)
            save("glossary", "GET", "/glossary")
            save("error_field_not_found", "GET", "/fields/f_ffffffff", expect=404)
            save("error_validation", "POST", "/fields", {"name": "no shape"}, 422)
        finally:
            with engine.begin() as c:
                c.execute(text("DELETE FROM fields WHERE field_id ~ '^f_0000'"))
                c.execute(text("DELETE FROM gazetteer WHERE place_id = -1"))

    print(f"wrote {len(written)} fixtures to {OUT_DIR.relative_to(REPO_ROOT)} (source: {source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
