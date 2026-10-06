"""Filtro por registro y propietario para cualquier entidad privada."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session


def owned_record(db: Session, model, record_id: int, owner_id: int):
    record = db.scalar(
        select(model).where(model.id == record_id, model.owner_id == owner_id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="El recurso solicitado no existe.")
    return record
