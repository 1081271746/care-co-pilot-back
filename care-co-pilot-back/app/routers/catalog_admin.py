"""Administración limitada al contenido compartido del catálogo."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.catalog_authorization import get_catalog_admin
from app.models.catalog import Exercise, Resource
from app.routers.catalog import Cursor, Database, PageLimit, catalog_page
from app.schemas.auth import AuthenticatedUser
from app.schemas.catalog import CatalogStage
from app.schemas.catalog_admin import (
    AdminExercisePage, AdminExerciseResponse, AdminResourcePage, AdminResourceResponse,
    ExerciseCreate, ExerciseUpdate, ResourceCreate, ResourceUpdate,
)
from app.services.catalog_admin import (
    catalog_item, deactivate_catalog_item, save_catalog_item, update_catalog_item,
)

router = APIRouter(prefix="/admin", tags=["Administración del catálogo"])
Admin = Annotated[AuthenticatedUser, Depends(get_catalog_admin)]


@router.get("/resources", response_model=AdminResourcePage)
def list_resources(
    current: Admin, db: Database, limit: PageLimit = 20, before_id: Cursor = None,
    stage: CatalogStage | None = None, is_active: bool | None = None,
):
    return catalog_page(db, Resource, AdminResourceResponse, limit, before_id, stage, is_active)


@router.get("/resources/{item_id}", response_model=AdminResourceResponse)
def read_resource(item_id: int, current: Admin, db: Database):
    return catalog_item(db, Resource, item_id)


@router.post("/resources", response_model=AdminResourceResponse, status_code=201)
def create_resource(payload: ResourceCreate, current: Admin, db: Database):
    return save_catalog_item(db, Resource(**payload.model_dump()))


@router.patch("/resources/{item_id}", response_model=AdminResourceResponse)
def update_resource(item_id: int, payload: ResourceUpdate, current: Admin, db: Database):
    return update_catalog_item(db, catalog_item(db, Resource, item_id), payload)


@router.delete("/resources/{item_id}", status_code=204)
def deactivate_resource(item_id: int, current: Admin, db: Database):
    deactivate_catalog_item(db, catalog_item(db, Resource, item_id))
    return Response(status_code=204)


@router.get("/exercises", response_model=AdminExercisePage)
def list_exercises(
    current: Admin, db: Database, limit: PageLimit = 20, before_id: Cursor = None,
    stage: CatalogStage | None = None, is_active: bool | None = None,
):
    return catalog_page(db, Exercise, AdminExerciseResponse, limit, before_id, stage, is_active)


@router.get("/exercises/{item_id}", response_model=AdminExerciseResponse)
def read_exercise(item_id: int, current: Admin, db: Database):
    return catalog_item(db, Exercise, item_id)


@router.post("/exercises", response_model=AdminExerciseResponse, status_code=201)
def create_exercise(payload: ExerciseCreate, current: Admin, db: Database):
    return save_catalog_item(db, Exercise(**payload.model_dump()))


@router.patch("/exercises/{item_id}", response_model=AdminExerciseResponse)
def update_exercise(item_id: int, payload: ExerciseUpdate, current: Admin, db: Database):
    return update_catalog_item(db, catalog_item(db, Exercise, item_id), payload)


@router.delete("/exercises/{item_id}", status_code=204)
def deactivate_exercise(item_id: int, current: Admin, db: Database):
    deactivate_catalog_item(db, catalog_item(db, Exercise, item_id))
    return Response(status_code=204)
