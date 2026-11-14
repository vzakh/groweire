"""Crop catalogue and rotation templates (plan 20 task 25)."""

from __future__ import annotations

import json
import shutil

import pytest

from services.rotation.catalog import DATA_DIR, STRESS_KINDS, load_catalog

EXPECTED_CROPS = {
    "spring_barley",
    "winter_wheat",
    "winter_barley",
    "spring_oats",
    "winter_oats",
    "spring_beans",
    "winter_oilseed_rape",
    "potatoes",
    "maize_silage",
    "grass_clover_ley",
    "multispecies_sward",
    "cover_mustard",
    "cover_phacelia",
    "cover_oats_vetch",
}


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def test_all_brief_crops_are_present(catalog):
    assert set(catalog.crops) == EXPECTED_CROPS


def test_every_crop_is_valid_and_sourced(catalog):
    for crop in catalog.crops.values():
        months = [
            *crop.calendar.sow_months,
            *crop.calendar.harvest_months,
            *crop.calendar.ground_cover_months,
        ]
        assert all(1 <= m <= 12 for m in months), crop.id
        assert crop.calendar.source in catalog.sources
        for kind in STRESS_KINDS:
            series = crop.stress_sensitivity[kind]
            assert series is None or len(series) == 12, crop.id
        if any(crop.stress_sensitivity[k] is not None for k in STRESS_KINDS):
            assert crop.stress_sensitivity["source"] in catalog.sources
        if crop.kc.mid is not None:
            assert crop.kc.source in catalog.sources
        assert all(s in catalog.sources for s in crop.source)


def test_templates_use_known_main_crops(catalog):
    assert len(catalog.templates) >= 5
    for template in catalog.templates:
        assert template.source in catalog.sources
        assert all(catalog.crops[c].role == "main" for c in template.sequence)


def test_advisor_questions_state_no_numbers(catalog):
    assert len(catalog.advisor_questions) >= 10
    for question in catalog.advisor_questions.values():
        assert question.endswith("?")
        assert not any(ch.isdigit() for ch in question) and "%" not in question


def _broken_copy(tmp_path, mutate):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data)
    crops = json.loads((data / "crops_ie.json").read_text())
    mutate(crops["crops"][0])
    (data / "crops_ie.json").write_text(json.dumps(crops))
    return data


def test_unsourced_kc_number_fails_fast(tmp_path):
    data = _broken_copy(tmp_path, lambda crop: crop["kc"].update(source=None))
    with pytest.raises(ValueError, match="no source"):
        load_catalog(data)


def test_unsourced_sensitivity_fails_fast(tmp_path):
    data = _broken_copy(tmp_path, lambda crop: crop["stress_sensitivity"].update(source=None))
    with pytest.raises(ValueError, match="no source"):
        load_catalog(data)


def test_unknown_source_id_fails_fast(tmp_path):
    data = _broken_copy(tmp_path, lambda crop: crop["calendar"].update(source="made_up"))
    with pytest.raises(ValueError, match="unknown source"):
        load_catalog(data)


def test_wrong_sensitivity_length_fails_fast(tmp_path):
    data = _broken_copy(
        tmp_path, lambda crop: crop["stress_sensitivity"].update(drought=[0.1] * 11)
    )
    with pytest.raises(ValueError, match="12 values"):
        load_catalog(data)


def test_crops_endpoint(client):
    r = client.get("/api/v1/crops")
    assert r.status_code == 200
    body = r.json()
    assert {c["id"] for c in body["crops"]} == EXPECTED_CROPS
    assert body["disclaimer"] and body["provenance"][0]["dataset_id"] == "crops_ie"
    assert client.get("/api/v1/crops", params={"region": "KE"}).json()["code"] == "unknown_region"
