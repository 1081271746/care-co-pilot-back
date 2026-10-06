"""Orientación de seguridad; no constituye evaluación clínica."""

from typing import Literal
from datetime import date

from pydantic import BaseModel

RiskLevel = Literal["unassessed", "elevated", "urgent"]
EmotionalStage = Literal[
    "denial", "anger", "bargaining", "intense_sadness", "acceptance", "uncertain",
]

DISCLAIMER = (
    "Co-Piloto de Duelo es una herramienta de acompañamiento. No realiza "
    "diagnósticos ni sustituye a profesionales de salud mental o servicios de emergencia."
)


class HelpResource(BaseModel):
    title: str
    url: str | None = None
    description: str
    phone: str | None = None
    country_code: str | None = None
    coverage: str | None = None
    availability: str | None = None
    verified_on: date | None = None


class SafetyResult(BaseModel):
    risk_level: RiskLevel
    requires_help: bool
    source: Literal["local_safety_rules", "openai_safety_signal"] = "local_safety_rules"
    message: str
    resources: list[HelpResource]
    disclaimer: str = DISCLAIMER
    limitations: str = (
        "Esta revisión automática puede omitir señales o producir falsas alarmas. "
        "No detectar una señal no demuestra que estés a salvo."
    )
