"""Contenido administrativo acotado, sin campos de propiedad ni datos privados."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator

from app.schemas.catalog import CatalogStage, ExerciseResponse, ResourceResponse

Slug = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=1, max_length=100,
    pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]
Kind = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
Instruction = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Instructions = Annotated[list[Instruction], Field(min_length=1, max_length=30)]


class CatalogWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResourceCreate(CatalogWrite):
    slug: Slug
    title: Title
    description: Description
    kind: Kind
    stage: CatalogStage
    content: Content
    is_active: StrictBool = True


class ExerciseCreate(CatalogWrite):
    slug: Slug
    title: Title
    description: Description
    stage: CatalogStage
    instructions: Instructions
    is_active: StrictBool = True


class CatalogUpdate(CatalogWrite):
    @model_validator(mode="after")
    def require_changes_without_nulls(self):
        if not self.model_fields_set:
            raise ValueError("Envía al menos un campo para modificar.")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Los campos del catálogo no admiten null.")
        return self


class ResourceUpdate(CatalogUpdate):
    slug: Slug | None = None
    title: Title | None = None
    description: Description | None = None
    kind: Kind | None = None
    stage: CatalogStage | None = None
    content: Content | None = None
    is_active: StrictBool | None = None


class ExerciseUpdate(CatalogUpdate):
    slug: Slug | None = None
    title: Title | None = None
    description: Description | None = None
    stage: CatalogStage | None = None
    instructions: Instructions | None = None
    is_active: StrictBool | None = None


class AdminResourceResponse(ResourceResponse):
    slug: str
    is_active: bool


class AdminExerciseResponse(ExerciseResponse):
    slug: str
    is_active: bool


class AdminResourcePage(BaseModel):
    items: list[AdminResourceResponse]
    next_cursor: int | None
    has_more: bool
    limit: int


class AdminExercisePage(BaseModel):
    items: list[AdminExerciseResponse]
    next_cursor: int | None
    has_more: bool
    limit: int
