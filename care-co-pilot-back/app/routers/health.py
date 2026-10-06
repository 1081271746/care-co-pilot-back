from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["Salud"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Confirma que la API está disponible; no comprueba la base de datos."""
    return HealthResponse()
