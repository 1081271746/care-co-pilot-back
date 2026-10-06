"""Persistencia optimista: no sobrescribir una entrada editada durante la llamada."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import String, cast, select, update
from sqlalchemy.orm import Session

from app.models.journal_entry import JournalEntry
from app.models.emotional_profile import EmotionalProfile
from app.schemas.analysis import ORIENTATIONS, PRIVACY_NOTICE_VERSION, privacy_notice
from app.services.openai_analysis import OpenAIAnalyzer, AnalysisUnavailable
from app.services.ownership import owned_record
from app.services.safety import safety_for_level


def analyze_and_persist(
    db: Session, entry: JournalEntry, provider: OpenAIAnalyzer, reauthorize,
):
    entry_id, owner_id = entry.id, entry.owner_id
    content = entry.content
    # Comparar la representación del motor: SQLite guarda defaults sin fracciones
    # y su adaptador enlaza datetime con .000000; el objeto Python no conserva eso.
    revision = db.scalar(select(cast(JournalEntry.updated_at, String)).where(
        JournalEntry.id == entry_id, JournalEntry.owner_id == owner_id,
    ))
    consented_at = datetime.now(timezone.utc)
    # No mantener una transacción/lock mientras esperamos a un proveedor externo.
    db.rollback()
    try:
        result = provider.analyze(content)
    except AnalysisUnavailable as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    # Comprobar de nuevo token, revocación y cuenta: pudo cerrar sesión o desactivarse.
    reauthorize()
    profile = db.get(EmotionalProfile, owner_id)
    country = profile.country_code if profile and profile.country_code else "CO"
    now = datetime.now(timezone.utc)
    has_signal = result.risk_level != "unassessed"
    analysis_result = {
        **result.model_dump(mode="json"),
        "source": "openai", "model": provider.settings.openai_model,
        "orientation": (
            "Prioriza ayuda humana y profesional; esta herramienta no puede atender una crisis."
            if has_signal else ORIENTATIONS[result.estimated_stage]
        ),
        "privacy_notice_version": PRIVACY_NOTICE_VERSION,
        "consented_at": consented_at.isoformat(),
        "limitations": privacy_notice()["limitations"],
        "disclaimer": privacy_notice()["disclaimer"],
    }
    if has_signal:
        # No mostrar una etapa ni acompañamiento normal cuando existe una señal.
        analysis_result["estimated_stage"] = None
    safety = safety_for_level(
        result.risk_level, country_code=country, source="openai_safety_signal",
    )
    written = db.execute(update(JournalEntry).where(
        JournalEntry.id == entry_id, JournalEntry.owner_id == owner_id,
        JournalEntry.content == content, cast(JournalEntry.updated_at, String) == revision,
        JournalEntry.analysis_status == "pending",
    ).values(
        analysis_result=analysis_result,
        estimated_stage=None if has_signal else result.estimated_stage,
        analysis_status="safety_priority" if has_signal else "completed",
        risk_level=result.risk_level, safety_result=safety.model_dump(mode="json"),
        analyzed_at=now,
    ).execution_options(synchronize_session=False))
    if written.rowcount != 1:
        db.rollback()
        current = owned_record(db, JournalEntry, entry_id, owner_id)
        if current.content == content and current.analysis_status in {"completed", "safety_priority"}:
            return current
        raise HTTPException(
            status_code=409,
            detail="La entrada cambió durante el análisis. El resultado anterior no se guardó; revisa el texto antes de reintentarlo.",
        )
    db.commit()
    return owned_record(db, JournalEntry, entry_id, owner_id)
