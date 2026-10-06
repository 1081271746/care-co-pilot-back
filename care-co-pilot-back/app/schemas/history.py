"""Datos de evolución para una visualización, sin puntuaciones clínicas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import ExerciseResponse, ResourceResponse
from app.schemas.safety import DISCLAIMER, EmotionalStage, SafetyResult


class DailyHistory(BaseModel):
    date: date
    journal_entries: int = 0
    completed_exercises: int = 0
    entries_with_safety_signals: int = 0


class StageCount(BaseModel):
    stage: str
    count: int


class HistoryResponse(BaseModel):
    timezone: Literal["UTC"] = "UTC"
    start_date: date
    end_date: date
    daily: list[DailyHistory]
    estimated_stages: list[StageCount]
    disclaimer: str = DISCLAIMER
    interpretation: str = (
        "Estos datos muestran actividad y estimaciones orientativas, no progreso "
        "clínico. El duelo no tiene un orden obligatorio ni un ritmo esperado."
    )


class RecentEntry(BaseModel):
    id: int
    created_at: datetime
    analysis_status: str
    estimated_stage: EmotionalStage | None
    safety_result: SafetyResult


class DashboardResponse(BaseModel):
    journal_entries: int
    completed_exercises: int
    pending_analyses: int
    latest_entry: RecentEntry | None
    disclaimer: str = DISCLAIMER


class RecommendationsResponse(BaseModel):
    mode: Literal["safety", "general", "orientative"]
    entry_id: int
    estimated_stage: EmotionalStage | None
    safety_result: SafetyResult
    resources: list[ResourceResponse] = Field(default_factory=list)
    exercises: list[ExerciseResponse] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
