"""Carga explícita e idempotente de material educativo inicial, no terapéutico."""

from sqlalchemy import select

from app.database.connection import get_session_factory
from app.models.catalog import Exercise, Resource
from app.schemas.safety import DISCLAIMER

STAGES = {
    "general": ("Dar espacio a tus emociones", "Escribe cómo te sientes hoy, sin intentar cambiarlo ni juzgarlo."),
    "denial": ("Reconocer lo que sientes", "Escribe una emoción que reconoces hoy, sin obligarte a aceptar nada."),
    "anger": ("Identificar la ira", "Describe qué emoción notas, sin juzgarla ni dirigirla hacia otras personas."),
    "bargaining": ("Reflexionar sobre pensamientos recurrentes", "Anota un pensamiento recurrente y algo que sí puedes decidir hoy."),
    "intense_sadness": ("Autocuidado suave", "Elige una acción pequeña de cuidado o contacto con alguien de confianza."),
    "acceptance": ("Guardar un recuerdo significativo", "Escribe un recuerdo que quieras conservar, si hoy te resulta cómodo."),
}


def seed_catalog(db):
    created_resources = 0
    created_exercises = 0
    for stage, (title, instruction) in STAGES.items():
        resource_slug = f"understanding-{stage}"
        if db.scalar(select(Resource.id).where(Resource.slug == resource_slug)) is None:
            db.add(Resource(
                slug=resource_slug, title=title, stage=stage, kind="educational",
                description="Material inicial de acompañamiento orientativo.",
                content=(
                    f"{instruction} Las emociones pueden cambiar y coexistir; no hay etapas "
                    f"obligatorias ni un orden que debas cumplir. Puedes pausar en cualquier momento. {DISCLAIMER}"
                ),
            ))
            created_resources += 1
        exercise_slug = f"reflection-{stage}"
        if db.scalar(select(Exercise.id).where(Exercise.slug == exercise_slug)) is None:
            db.add(Exercise(
                slug=exercise_slug, title=title, stage=stage,
                description=f"Ejercicio opcional de reflexión. {DISCLAIMER}",
                instructions=[
                    "Realízalo solo si te resulta cómodo y puedes detenerte cuando quieras.",
                    instruction,
                    "Si te genera malestar, pausa y busca apoyo humano. Ante riesgo, prioriza ayuda profesional.",
                ],
            ))
            created_exercises += 1
    db.commit()
    return {"resources_created": created_resources, "exercises_created": created_exercises}


if __name__ == "__main__":
    with get_session_factory()() as session:
        result = seed_catalog(session)
        print(f"Recursos creados: {result['resources_created']}; ejercicios creados: {result['exercises_created']}.")
