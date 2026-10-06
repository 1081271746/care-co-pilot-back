"""Dashboard, actividad diaria y recomendaciones sin diagnóstico."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.catalog import Exercise, ExerciseCompletion, Resource
from app.models.journal_entry import JournalEntry
from app.routers.auth import get_active_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.catalog import ExerciseResponse, ResourceResponse
from app.schemas.history import (
    DailyHistory, DashboardResponse, HistoryResponse, RecentEntry,
    RecommendationsResponse, StageCount,
)
from app.services.ownership import owned_record

router = APIRouter(tags=["Historial y acompañamiento"])
Identity = Annotated[AuthenticatedUser, Depends(get_active_user)]
Database = Annotated[Session, Depends(get_db)]


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(current: Identity, db: Database):
    owner = int(current.id)
    entries = db.scalar(select(func.count()).select_from(JournalEntry).where(JournalEntry.owner_id == owner))
    completions = db.scalar(select(func.count()).select_from(ExerciseCompletion).where(ExerciseCompletion.owner_id == owner))
    pending = db.scalar(select(func.count()).select_from(JournalEntry).where(
        JournalEntry.owner_id == owner, JournalEntry.analysis_status == "pending",
    ))
    latest = db.scalar(select(JournalEntry).where(
        JournalEntry.owner_id == owner,
    ).order_by(JournalEntry.id.desc()).limit(1))
    return DashboardResponse(
        journal_entries=entries, completed_exercises=completions, pending_analyses=pending,
        latest_entry=RecentEntry(
            id=latest.id, created_at=latest.created_at, analysis_status=latest.analysis_status,
            estimated_stage=latest.estimated_stage, safety_result=latest.safety_result,
        ) if latest else None,
    )


def utc_date_column(db, column):
    if db.get_bind().dialect.name == "postgresql":
        return cast(func.timezone("UTC", column), Date)
    return func.date(column)


@router.get("/history", response_model=HistoryResponse)
def history(
    current: Identity, db: Database,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
):
    owner = int(current.id)
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    start_time = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_time = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    daily = {
        str(start + timedelta(days=offset)): DailyHistory(date=start + timedelta(days=offset))
        for offset in range(days)
    }
    for model, column, field in (
        (JournalEntry, JournalEntry.created_at, "journal_entries"),
        (ExerciseCompletion, ExerciseCompletion.completed_at, "completed_exercises"),
    ):
        day = utc_date_column(db, column)
        rows = db.execute(select(day, func.count()).where(
            model.owner_id == owner, column >= start_time, column < end_time,
        ).group_by(day))
        for date_value, count in rows:
            setattr(daily[str(date_value)], field, count)
    day = utc_date_column(db, JournalEntry.created_at)
    signals = db.execute(select(day, func.count()).where(
        JournalEntry.owner_id == owner, JournalEntry.created_at >= start_time,
        JournalEntry.created_at < end_time, JournalEntry.risk_level != "unassessed",
    ).group_by(day))
    for date_value, count in signals:
        daily[str(date_value)].entries_with_safety_signals = count
    stages = db.execute(select(JournalEntry.estimated_stage, func.count()).where(
        JournalEntry.owner_id == owner, JournalEntry.created_at >= start_time,
        JournalEntry.created_at < end_time, JournalEntry.estimated_stage.is_not(None),
    ).group_by(JournalEntry.estimated_stage).order_by(JournalEntry.estimated_stage))
    return HistoryResponse(
        start_date=start, end_date=end, daily=list(daily.values()),
        estimated_stages=[StageCount(stage=stage, count=count) for stage, count in stages],
    )


@router.get("/journal/{entry_id}/recommendations", response_model=RecommendationsResponse)
def recommendations(entry_id: int, current: Identity, db: Database):
    entry = owned_record(db, JournalEntry, entry_id, int(current.id))
    if entry.risk_level != "unassessed":
        return RecommendationsResponse(
            mode="safety", entry_id=entry.id, estimated_stage=None,
            safety_result=entry.safety_result,
        )
    stages = ["general"]
    if entry.estimated_stage and entry.estimated_stage != "uncertain":
        stages.append(entry.estimated_stage)
    resources = db.scalars(select(Resource).where(
        Resource.is_active.is_(True), Resource.stage.in_(stages),
    ).order_by(Resource.id).limit(10))
    exercises = db.scalars(select(Exercise).where(
        Exercise.is_active.is_(True), Exercise.stage.in_(stages),
    ).order_by(Exercise.id).limit(10))
    return RecommendationsResponse(
        mode="orientative" if len(stages) > 1 else "general",
        entry_id=entry.id, estimated_stage=entry.estimated_stage,
        safety_result=entry.safety_result,
        resources=[ResourceResponse.model_validate(item) for item in resources],
        exercises=[ExerciseResponse.model_validate(item) for item in exercises],
    )
