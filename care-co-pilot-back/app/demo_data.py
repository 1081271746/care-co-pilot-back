"""Datos exclusivamente ficticios para una base de demostración recién creada."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.models import User
from app.models.catalog import Exercise, ExerciseCompletion
from app.models.emotional_profile import EmotionalProfile
from app.models.journal_entry import JournalEntry
from app.services.catalog_seed import seed_catalog
from app.services.safety import review_safety

# Credenciales públicas de demostración, jamás válidas para una instalación real.
DEMO_PASSWORD = "DemoSoloLocal2026!"
DEMO_ACCOUNTS = (
    ("usuario.demo@example.com", "user", "Persona de ejemplo"),
    ("otra.demo@example.com", "user", "Otra persona de ejemplo"),
    ("admin.demo@example.com", "admin", "Administración de ejemplo"),
)


def seed_demo_data(db):
    """Solo llamar sobre la base temporal propia de app.demo, nunca la real."""
    if db.scalar(select(User.id).limit(1)) is not None:
        raise ValueError("La carga ficticia exige una base vacía.")
    seed_catalog(db)
    now = datetime.now(timezone.utc)
    password_hash = hash_password(DEMO_PASSWORD)
    for index, (email, role, name) in enumerate(DEMO_ACCOUNTS):
        user = User(email=email, password_hash=password_hash, role=role)
        db.add(user)
        db.flush()
        db.add(EmotionalProfile(
            owner_id=user.id, first_name=name, country_code="CO",
            accompaniment_goal="Ejemplo ficticio para probar el acompañamiento.",
        ))
        contents = [
            "Ejemplo ficticio: hoy recordé una conversación agradable con alguien querido.",
            "Ejemplo ficticio: escribir y hablar con amistades me ayudó a expresar tristeza.",
            "Ejemplo ficticio para probar seguridad: no puedo más.",
        ] if index == 0 else ["Ejemplo ficticio de un diario privado de otra cuenta."]
        for offset, content in enumerate(contents):
            safety = review_safety(content, country_code="CO")
            db.add(JournalEntry(
                owner_id=user.id, title=f"Ejemplo {offset + 1}", content=content,
                risk_level=safety.risk_level, safety_result=safety.model_dump(mode="json"),
                analysis_status="safety_priority" if safety.requires_help else "pending",
                created_at=now - timedelta(days=len(contents) - offset - 1),
            ))
        exercise = db.scalar(select(Exercise).where(Exercise.stage == "general"))
        db.add(ExerciseCompletion(
            owner_id=user.id, exercise_id=exercise.id,
            note="Nota ficticia: pude escribir un recuerdo y decidí descansar.",
            completed_at=now - timedelta(days=index),
        ))
    db.commit()
