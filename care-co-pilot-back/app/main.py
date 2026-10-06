from fastapi import FastAPI

from app.core.config import Settings, load_settings
from app.core.errors import register_error_handlers
from app.core.http import configure_http
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.private_records import router as private_records_router
from app.routers.journal import router as journal_router
from app.routers.help import router as help_router
from app.routers.catalog import router as catalog_router
from app.routers.catalog_admin import router as catalog_admin_router
from app.routers.profile import router as profile_router
from app.routers.history import router as history_router


def create_app(settings: Settings | None = None) -> FastAPI:
    explicit_settings = settings
    settings = settings or load_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "API de acompañamiento emocional. No sustituye atención profesional "
            "ni servicios de emergencia."
        ),
    )
    if explicit_settings is not None:
        application.state.auth_settings = explicit_settings
    register_error_handlers(application)
    configure_http(application, settings)
    application.include_router(auth_router)
    application.include_router(private_records_router)
    application.include_router(journal_router)
    application.include_router(help_router)
    application.include_router(catalog_router)
    application.include_router(catalog_admin_router)
    application.include_router(profile_router)
    application.include_router(history_router)
    application.include_router(health_router)
    return application


app = create_app()
