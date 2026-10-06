from fastapi import FastAPI

from app.core.config import load_settings
from app.routers.health import router as health_router


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
    application.include_router(health_router)
    return application


app = create_app()
