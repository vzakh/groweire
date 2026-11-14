"""POST /fields, GET /fields/{id} (brief §9). DB-only, so plain `def` (runs in a threadpool)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.deps import get_db
from models.common import ErrorOut
from models.fields import FieldCreate, FieldOut
from services import fields as service

router = APIRouter(prefix="/fields", tags=["fields"])


@router.post(
    "",
    response_model=FieldOut,
    status_code=201,
    summary="Create a field from a point + approximate area, or from a drawn polygon",
    responses={422: {"model": ErrorOut}},
)
def create_field(body: FieldCreate, db: Session = Depends(get_db)) -> FieldOut:
    return service.create_field(db, body)


@router.get(
    "/{field_id}",
    response_model=FieldOut,
    summary="Field metadata",
    responses={404: {"model": ErrorOut}},
)
def get_field(field_id: str, db: Session = Depends(get_db)) -> FieldOut:
    return service.get_field(db, field_id)
