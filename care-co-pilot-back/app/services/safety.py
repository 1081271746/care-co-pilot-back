"""Detección conservadora inicial; no reemplaza una evaluación profesional."""

import re
import unicodedata

from app.schemas.safety import HelpResource, SafetyResult
from app.services.emergency_resources import colombia_resources

URGENT_PHRASES = (
    "quiero morir", "quiero matarme", "me voy a matar", "voy a suicidarme",
    "quiero suicidarme", "quiero hacerme dano", "voy a hacerme dano",
    "hacerme dano ahora", "estoy en peligro", "i want to die", "kill myself",
)
ELEVATED_PHRASES = (
    "no quiero seguir", "no puedo mas", "no vale la pena vivir",
    "me hago dano", "suicidio", "suicida", "autolesion",
)


def normalize_text(content: str) -> str:
    plain = "".join(
        character for character in unicodedata.normalize("NFKD", content.casefold())
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def help_resources(country_code: str = "CO") -> list[HelpResource]:
    local = colombia_resources() if country_code.upper() == "CO" else []
    return local + [
        HelpResource(
            title="Peligro inmediato",
            description=(
                "Contacta a los servicios de emergencia de tu país o acude a urgencias. "
                "Si es seguro, pide a alguien de confianza que permanezca contigo."
            ),
        ),
        HelpResource(
            title="Buscar líneas de apoyo por país",
            url="https://findahelpline.com/",
            description=(
                "Directorio de líneas de apoyo. La disponibilidad depende del país; "
                "no sustituye los servicios de emergencia."
            ),
        ),
        HelpResource(
            title="Acompañamiento profesional",
            description="Busca apoyo de un profesional de salud mental o de tu servicio de salud.",
        ),
    ]


def review_safety(content: str, country_code: str = "CO") -> SafetyResult:
    normalized = f" {normalize_text(content)} "
    urgent = any(f" {phrase} " in normalized for phrase in URGENT_PHRASES)
    elevated = any(f" {phrase} " in normalized for phrase in ELEVATED_PHRASES)
    level = "urgent" if urgent else "elevated" if elevated else "unassessed"
    return safety_for_level(level, country_code=country_code)


def safety_for_level(level: str, country_code: str = "CO", source: str = "local_safety_rules") -> SafetyResult:
    """El mensaje de ayuda se escribe en el servidor, nunca lo inventa el modelo."""
    if level == "urgent":
        message = (
            "Lo que escribiste puede indicar una situación de riesgo. "
            "No tienes que afrontarla a solas. Prioriza ayuda humana inmediata; "
            "esta aplicación no puede atender una emergencia."
        )
    elif level == "elevated":
        message = (
            "Lo que escribiste merece apoyo y atención. Habla con alguien de confianza "
            "y busca acompañamiento profesional. Si existe peligro inmediato, "
            "contacta a emergencias."
        )
    else:
        message = (
            ("La revisión local no encontró las expresiones que reconoce. "
             if source == "local_safety_rules"
             else "El análisis de esta entrada no identificó señales de riesgo reconocibles. ")
            +
            "Esto no es una evaluación de seguridad ni un diagnóstico. "
            "Puedes buscar ayuda en cualquier momento."
        )
    return SafetyResult(
        risk_level=level, requires_help=level != "unassessed", message=message,
        resources=help_resources(country_code), source=source,
    )
