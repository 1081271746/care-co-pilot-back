"""Persistencia administrativa sin borrados físicos del catálogo."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


def catalog_item(db, model, item_id):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="El recurso solicitado no existe.")
    return item


def save_catalog_item(db, item):
    slug, item_id, model = item.slug, item.id, type(item)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(select(model).where(model.slug == slug))
        if duplicate is not None and duplicate.id != item_id:
            raise HTTPException(
                status_code=409, detail="Ya existe un elemento con ese slug.",
            ) from None
        raise
    db.refresh(item)
    return item


def update_catalog_item(db, item, payload):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    return save_catalog_item(db, item)


def deactivate_catalog_item(db, item):
    item.is_active = False
    db.commit()
