"""Datos orientativos limitados: sin diagnóstico ni texto libre del proveedor."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.safety import EmotionalStage, RiskLevel, DISCLAIMER

PRIVACY_NOTICE_VERSION = "2026-10-06"
Emotion = Literal[
    "sadness", "anger", "fear", "guilt", "loneliness", "longing",
    "relief", "gratitude", "hope", "uncertain",
]


class ProviderAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    estimated_stage: EmotionalStage
    risk_level: RiskLevel
    emotions: list[Emotion] = Field(max_length=5)


def privacy_notice() -> dict:
    return {
        "version": PRIVACY_NOTICE_VERSION,
        "provider": "OpenAI",
        "requires_explicit_consent": True,
        "content_sent": "Solo el contenido de la entrada seleccionada, no el resto del diario.",
        "account_data_sent": False,
        "personal_information_warning": (
            "El propio texto puede contener información personal. Revisa la entrada "
            "y evita datos identificables innecesarios antes de aceptar enviarla."
        ),
        "provider_storage_requested": False,
        "external_retention": (
            "Se solicita store=false. No garantiza retención cero: OpenAI puede "
            "retener contenido para controles de seguridad y prevención de abuso, "
            "por defecto hasta 30 días, con excepciones según su política."
        ),
        "provider_policy_url": "https://developers.openai.com/api/docs/guides/your-data",
        "cost": "El uso se cobra a la cuenta de OpenAI del responsable de la aplicación.",
        "limitations": (
            "Estimación basada en una sola entrada; puede equivocarse u omitir señales "
            "de riesgo. Las etapas no son obligatorias ni lineales. No confirma seguridad."
        ),
        "disclaimer": DISCLAIMER,
    }


ORIENTATIONS = {
    "denial": "El texto puede reflejar dificultad para reconocer la pérdida. Puedes explorar lo que sientes a tu ritmo.",
    "anger": "El texto puede reflejar enojo o frustración. Reconocer esas emociones puede orientar el acompañamiento.",
    "bargaining": "El texto puede reflejar pensamientos sobre lo que desearías cambiar. No implica que seas responsable de lo ocurrido.",
    "intense_sadness": "El texto puede reflejar tristeza intensa. No significa una depresión diagnosticada; puedes buscar acompañamiento profesional.",
    "acceptance": "El texto puede reflejar momentos de integración de la pérdida. No significa que el duelo haya terminado.",
    "uncertain": "Esta entrada no permite estimar una etapa con claridad. Puedes recibir acompañamiento general sin una clasificación.",
}
