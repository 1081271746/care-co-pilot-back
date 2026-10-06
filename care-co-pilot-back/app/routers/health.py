from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.security import AuthenticationConfigurationError, verify_authentication_configuration
from app.database import get_db
from app.models import Base

from app.schemas.health import HealthResponse

router = APIRouter(tags=["Salud"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Confirma que la API está disponible; no comprueba la base de datos."""
    return HealthResponse()


@router.get("/health/ready")
def get_readiness(db: Annotated[Session, Depends(get_db)]):
    """Comprueba conexión, columnas migradas y JWT, sin aplicar migraciones."""
    try:
        verify_authentication_configuration()
    except AuthenticationConfigurationError:
        raise HTTPException(status_code=503, detail="La autenticación no está configurada.") from None
    db.execute(text("SELECT 1"))
    inspector = inspect(db.get_bind())
    tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in tables:
            raise HTTPException(status_code=503, detail="El esquema de la base de datos no está preparado.")
        actual_columns = {column["name"] for column in inspector.get_columns(table.name)}
        if not set(table.columns.keys()).issubset(actual_columns):
            raise HTTPException(status_code=503, detail="El esquema de la base de datos no está preparado.")
    return {"status": "ready"}
