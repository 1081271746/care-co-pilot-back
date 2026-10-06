"""La ayuda está disponible incluso sin iniciar sesión."""

from fastapi import APIRouter

from app.schemas.safety import DISCLAIMER
from app.services.safety import help_resources

router = APIRouter(prefix="/help", tags=["Seguridad y ayuda"])


@router.get("")
def get_help():
    return {
        "disclaimer": DISCLAIMER,
        "resources": help_resources(),
        "country_specific_numbers_configured": False,
        "message": "Si existe peligro inmediato, contacta a emergencias de tu país o acude a urgencias.",
    }
