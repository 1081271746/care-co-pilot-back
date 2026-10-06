from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.core.config import load_settings
from app.core.errors import safe_validation_error
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.private_records import router as private_records_router


def create_app() -> FastAPI:
    settings = load_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "API de acompañamiento emocional. No sustituye atención profesional "
            "ni servicios de emergencia."
        ),
    )
    application.add_exception_handler(RequestValidationError, safe_validation_error)
    application.include_router(auth_router)
    application.include_router(private_records_router)
    application.include_router(health_router)
    return application


app = create_app()
