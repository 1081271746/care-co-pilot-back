"""La ayuda está disponible incluso sin iniciar sesión."""

from typing import Annotated
from fastapi import APIRouter, Query

from app.schemas.safety import DISCLAIMER
from app.services.safety import help_resources
from app.schemas.analysis import privacy_notice

router = APIRouter(prefix="/help", tags=["Seguridad y ayuda"])


@router.get("/privacy")
def get_analysis_privacy():
    """Aviso público para mostrar antes de pedir consentimiento en el cliente."""
    return privacy_notice()


@router.get("")
def get_help(country_code: Annotated[str, Query(pattern=r"^[A-Za-z]{2}$")] = "CO"):
    return {
        "disclaimer": DISCLAIMER,
        "resources": help_resources(country_code),
        "country_specific_numbers_configured": country_code.upper() == "CO",
        "country_code": country_code.upper(),
        "supported_countries": ["CO"],
        "message": "Si existe peligro inmediato, contacta a emergencias de tu país o acude a urgencias.",
    }
