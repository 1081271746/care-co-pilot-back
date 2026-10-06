"""Lectura del catálogo y registros de progreso por propietario."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.catalog import Exercise, ExerciseCompletion, Resource
from app.routers.auth import get_active_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.catalog import (
    CatalogStage, CompletionCreate, CompletionResponse, CompletionUpdate,
    ExerciseResponse, ResourceResponse, ResourcePage, ExercisePage, CompletionPage,
)
from app.services.ownership import owned_record

router = APIRouter(tags=["Recursos, ejercicios y progreso"])
Identity = Annotated[AuthenticatedUser, Depends(get_active_user)]
Database = Annotated[Session, Depends(get_db)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[int | None, Query(ge=1)]


def catalog_page(db, model, response_model, limit, before_id, stage):
    statement = select(model).where(model.is_active.is_(True))
    if stage:
        statement = statement.where(model.stage == stage)
    if before_id:
        statement = statement.where(model.id < before_id)
    rows = list(db.scalars(statement.order_by(model.id.desc()).limit(limit + 1)))
    return {
        "items": [response_model.model_validate(item) for item in rows[:limit]],
        "next_cursor": rows[limit - 1].id if len(rows) > limit else None,
        "has_more": len(rows) > limit,
        "limit": limit,
    }


def active_item(db, model, item_id):
    item = db.scalar(select(model).where(model.id == item_id, model.is_active.is_(True)))
    if item is None:
        raise HTTPException(status_code=404, detail="El recurso solicitado no existe.")
    return item


@router.get("/resources", response_model=ResourcePage)
def list_resources(
    current: Identity, db: Database, limit: PageLimit = 20,
    before_id: Cursor = None, stage: CatalogStage | None = None,
):
    return catalog_page(db, Resource, ResourceResponse, limit, before_id, stage)


@router.get("/resources/{resource_id}", response_model=ResourceResponse)
def read_resource(resource_id: int, current: Identity, db: Database):
    return active_item(db, Resource, resource_id)


@router.get("/exercises", response_model=ExercisePage)
def list_exercises(
    current: Identity, db: Database, limit: PageLimit = 20,
    before_id: Cursor = None, stage: CatalogStage | None = None,
):
    return catalog_page(db, Exercise, ExerciseResponse, limit, before_id, stage)


@router.get("/exercises/{exercise_id}", response_model=ExerciseResponse)
def read_exercise(exercise_id: int, current: Identity, db: Database):
    return active_item(db, Exercise, exercise_id)


@router.post("/exercises/{exercise_id}/completions", response_model=CompletionResponse, status_code=201)
def complete_exercise(
    exercise_id: int, payload: CompletionCreate, current: Identity, db: Database,
):
    active_item(db, Exercise, exercise_id)
    completion = ExerciseCompletion(
        owner_id=int(current.id), exercise_id=exercise_id, note=payload.note,
    )
    db.add(completion)
    db.commit()
    db.refresh(completion)
    return completion


@router.get("/progress/exercises", response_model=CompletionPage)
def list_completions(
    current: Identity, db: Database, limit: PageLimit = 20, before_id: Cursor = None,
):
    statement = select(ExerciseCompletion).where(ExerciseCompletion.owner_id == int(current.id))
    if before_id:
        statement = statement.where(ExerciseCompletion.id < before_id)
    rows = list(db.scalars(statement.order_by(ExerciseCompletion.id.desc()).limit(limit + 1)))
    return {
        "items": [CompletionResponse.model_validate(row) for row in rows[:limit]],
        "has_more": len(rows) > limit,
        "next_cursor": rows[limit - 1].id if len(rows) > limit else None,
        "limit": limit,
    }


@router.get("/progress/exercises/{completion_id}", response_model=CompletionResponse)
def read_completion(completion_id: int, current: Identity, db: Database):
    return owned_record(db, ExerciseCompletion, completion_id, int(current.id))


@router.patch("/progress/exercises/{completion_id}", response_model=CompletionResponse)
def update_completion(
    completion_id: int, payload: CompletionUpdate, current: Identity, db: Database,
):
    completion = owned_record(db, ExerciseCompletion, completion_id, int(current.id))
    completion.note = payload.note
    db.commit()
    db.refresh(completion)
    return completion


@router.delete("/progress/exercises/{completion_id}", status_code=204)
def delete_completion(completion_id: int, current: Identity, db: Database):
    db.delete(owned_record(db, ExerciseCompletion, completion_id, int(current.id)))
    db.commit()
    return Response(status_code=204)
