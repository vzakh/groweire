"""Response pieces shared by every data endpoint (brief §9, §13.2 Backend -> Frontend)."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Hard rule 7: every user-facing recommendation carries this framing.
DISCLAIMER = "This tool supports, not replaces, your judgment and local agronomic advice."

# data_quality flag added whenever the stub model or synthetic tables are behind a response.
SYNTHETIC_DATA = "synthetic_data"
OUTSIDE_PILOT = "outside_pilot"


class ErrorOut(BaseModel):
    detail: str
    code: str


class Provenance(BaseModel):
    dataset_id: str
    description: str
    url: str
    period: str | None = None


class InformationGap(BaseModel):
    """Something we do not know. Shown to the farmer as a gap, never guessed (hard rule 1)."""

    code: str = Field(examples=["soil_from_global_model"])
    text: str


# Dataset ids and citations from brief §6. Every data response lists what it used.
_SOURCES: dict[str, tuple[str, str, str | None]] = {
    "power": (
        "NASA POWER daily weather (MERRA-2 / CERES), about 50 km grid",
        "https://power.larc.nasa.gov/",
        "1981–present",
    ),
    "modis_ndvi": (
        "MOD13Q1/MYD13Q1 v6.1 NDVI",
        "https://doi.org/10.5067/MODIS/MOD13Q1.061",
        "2001–present",
    ),
    "smap": (
        "SMAP L4 root-zone soil moisture (SPL4SMGP)",
        "https://nsidc.org/data/spl4smgp",
        "2015–present",
    ),
    "srtm": (
        "SRTMGL1 elevation and slope",
        "https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL1.003",
        None,
    ),
    "landcover": (
        "MCD12Q1 land cover",
        "https://doi.org/10.5067/MODIS/MCD12Q1.061",
        None,
    ),
    "soilgrids": (
        "ISRIC SoilGrids v2.0 (global soil model, 250 m)",
        "https://soilgrids.org/",
        None,
    ),
    "irish_sis": (
        "EPA / Teagasc indicative soil drainage map (Republic of Ireland)",
        "https://gis.epa.ie/",
        None,
    ),
    "crops_ie": (
        "AgroLens crop catalogue (FAO-56 crop coefficients, Teagasc guidance)",
        "https://www.fao.org/4/x0490e/x0490e00.htm",
        None,
    ),
}


def provenance(*dataset_ids: str) -> list[Provenance]:
    """Provenance entries for the given dataset ids (duplicates removed, order kept)."""
    out = []
    for dataset_id in dict.fromkeys(dataset_ids):
        description, url, period = _SOURCES[dataset_id]
        out.append(
            Provenance(dataset_id=dataset_id, description=description, url=url, period=period)
        )
    return out
