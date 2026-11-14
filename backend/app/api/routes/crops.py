"""GET /crops: the crop catalogue for the pilot region (brief §9)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from core.deps import get_catalog
from core.errors import AppError
from models.common import provenance
from models.crops import CropOut, CropsOut

router = APIRouter(prefix="/crops", tags=["crops"])


@router.get("", response_model=CropsOut, summary="Crops the tool knows about")
def list_crops(region: str = Query(default="IE"), catalog=Depends(get_catalog)) -> CropsOut:
    if region.upper() != "IE":
        raise AppError("unknown_region", "The crop list is only ready for Ireland.", status=422)
    return CropsOut(
        crops=[
            CropOut(
                id=c.id,
                name=c.name,
                family=c.family,
                season=c.season,
                role=c.role,
                sow_months=c.calendar.sow_months,
                harvest_months=c.calendar.harvest_months,
                n_fixing=c.n_fixing,
                forage_value=c.forage_value,
                requires_livestock=c.requires_livestock,
                market=c.market,
                sources=c.source,
            )
            for c in catalog.crops.values()
        ],
        provenance=provenance("crops_ie"),
    )
