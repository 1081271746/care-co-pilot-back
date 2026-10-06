"""Contratos del diario: propietario y resultados solo los fija el servidor."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.safety import EmotionalStage, SafetyResult


class JournalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="", max_length=200)
    content: str = Field(min_length=1, max_length=20_000)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str):
        if not value.strip():
            raise ValueError("La entrada no puede estar vacía.")
        return value


class JournalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=20_000)

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("Envía al menos un campo no nulo.")
        if self.content is not None and not self.content.strip():
            raise ValueError("La entrada no puede estar vacía.")
        return self


class JournalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content: str
    risk_level: str
    safety_result: SafetyResult
    analysis_status: Literal["pending", "completed", "safety_priority"]
    estimated_stage: EmotionalStage | None
    analysis_result: dict | None
    analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JournalPage(BaseModel):
    items: list[JournalResponse]
    limit: int
    before_id: int | None
    next_cursor: int | None
    has_more: bool


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent_to_external_analysis: bool = Field(default=False, strict=True)
