"""Contratos de biblioteca educativa e historial de ejercicios."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CatalogStage = Literal["general", "denial", "anger", "bargaining", "intense_sadness", "acceptance"]


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    kind: str
    stage: CatalogStage
    content: str


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    stage: CatalogStage
    instructions: list[str]


class CompletionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str = Field(default="", max_length=2000)


class CompletionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str = Field(max_length=2000)


class CompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_id: int
    note: str
    completed_at: datetime


class ResourcePage(BaseModel):
    items: list[ResourceResponse]
    next_cursor: int | None
    has_more: bool
    limit: int


class ExercisePage(BaseModel):
    items: list[ExerciseResponse]
    next_cursor: int | None
    has_more: bool
    limit: int


class CompletionPage(BaseModel):
    items: list[CompletionResponse]
    next_cursor: int | None
    has_more: bool
    limit: int
