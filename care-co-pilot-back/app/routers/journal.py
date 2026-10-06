"""CRUD del diario, revisión local de riesgo y análisis explícitamente pendiente."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.journal_entry import JournalEntry
from app.routers.auth import get_active_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.journal import (
    AnalysisRequest, JournalCreate, JournalPage, JournalResponse, JournalUpdate,
)
from app.services.ownership import owned_record
from app.services.safety import review_safety

router = APIRouter(prefix="/journal", tags=["Diario emocional"])
Identity = Annotated[AuthenticatedUser, Depends(get_active_user)]
Database = Annotated[Session, Depends(get_db)]


def set_safety(entry: JournalEntry) -> None:
    result = review_safety(entry.content)
    entry.safety_result = result.model_dump(mode="json")
    entry.risk_level = result.risk_level
    entry.analysis_status = "safety_priority" if result.requires_help else "pending"
    entry.estimated_stage = None
    entry.analysis_result = None
    entry.analyzed_at = None


@router.post("", response_model=JournalResponse, status_code=201)
def create_entry(payload: JournalCreate, current: Identity, db: Database):
    entry = JournalEntry(owner_id=int(current.id), **payload.model_dump())
    set_safety(entry)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=JournalPage)
def list_entries(
    current: Identity, db: Database,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before_id: Annotated[int | None, Query(ge=1)] = None,
):
    statement = select(JournalEntry).where(JournalEntry.owner_id == int(current.id))
    if before_id is not None:
        statement = statement.where(JournalEntry.id < before_id)
    rows = list(db.scalars(statement.order_by(JournalEntry.id.desc()).limit(limit + 1)))
    items = rows[:limit]
    has_more = len(rows) > limit
    return JournalPage(
        items=items, limit=limit, before_id=before_id,
        next_cursor=items[-1].id if has_more else None, has_more=has_more,
    )


@router.get("/{entry_id}", response_model=JournalResponse)
def read_entry(entry_id: int, current: Identity, db: Database):
    return owned_record(db, JournalEntry, entry_id, int(current.id))


@router.patch("/{entry_id}", response_model=JournalResponse)
def update_entry(entry_id: int, payload: JournalUpdate, current: Identity, db: Database):
    entry = owned_record(db, JournalEntry, entry_id, int(current.id))
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    if "content" in payload.model_fields_set:
        set_safety(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: int, current: Identity, db: Database):
    entry = owned_record(db, JournalEntry, entry_id, int(current.id))
    db.delete(entry)
    db.commit()
    return Response(status_code=204)


@router.post("/{entry_id}/analyze", response_model=JournalResponse)
def analyze_entry(
    entry_id: int, payload: AnalysisRequest, current: Identity, db: Database,
):
    entry = owned_record(db, JournalEntry, entry_id, int(current.id))
    if entry.risk_level != "unassessed":
        # No enviar contenido de crisis a IA ni recomendar ejercicios normales.
        return entry
    if not payload.consent_to_external_analysis:
        raise HTTPException(status_code=422, detail="Se necesita consentimiento explícito para el análisis externo.")
    raise HTTPException(
        status_code=503,
        detail="El proveedor de IA aún no está configurado. Tu entrada sigue guardada; no se envió a terceros.",
    )
