"""API local desechable: mismos endpoints, datos ficticios y ninguna IA externa."""

import argparse
from contextlib import asynccontextmanager
import os
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import create_engine, event

from app.core.config import BACKEND_ROOT, Settings
from app.database.connection import create_session_factory, get_db
from app.demo_data import DEMO_ACCOUNTS, DEMO_PASSWORD, seed_demo_data
from app.main import create_app
from app.services.openai_analysis import get_analysis_provider, OpenAIAnalyzer


def create_demo_app():
    if os.getenv("APP_ENV") == "production":
        raise RuntimeError("La demostración no puede iniciarse con APP_ENV=production.")
    settings = Settings(
        app_name="Co-Piloto de Duelo — DEMO LOCAL",
        jwt_secret_key=SecretStr(secrets.token_urlsafe(48)),
        cors_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
        openai_analysis_enabled=False,
    )
    application = create_app(settings)
    application.description += (
        " DEMOSTRACIÓN LOCAL: datos ficticios y temporales. Sin PostgreSQL real "
        "ni solicitudes a OpenAI. Todo se pierde al detener el proceso. "
        "Nunca introducir datos personales ni publicar esta demostración."
    )
    application.state.demo_mode = True

    @asynccontextmanager
    async def lifespan(app):
        with TemporaryDirectory(prefix="copilot_demo_") as directory:
            engine = create_engine(
                f"sqlite+pysqlite:///{Path(directory) / 'demo.sqlite3'}",
                connect_args={"check_same_thread": False, "timeout": 30},
                hide_parameters=True,
            )

            @event.listens_for(engine, "connect")
            def enable_foreign_keys(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")

            try:
                config = Config(str(BACKEND_ROOT / "alembic.ini"))
                config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
                with engine.begin() as connection:
                    config.attributes["connection"] = connection
                    command.upgrade(config, "head")
                factory = create_session_factory(engine)
                with factory() as db:
                    seed_demo_data(db)

                def demo_db():
                    with factory() as db:
                        yield db

                app.dependency_overrides[get_db] = demo_db
                app.dependency_overrides[get_analysis_provider] = lambda: OpenAIAnalyzer(settings)
                yield
            finally:
                app.dependency_overrides.clear()
                engine.dispose()

    application.router.lifespan_context = lifespan

    @application.middleware("http")
    async def label_demo(request, call_next):
        response = await call_next(request)
        response.headers["X-CoPilot-Mode"] = "demo-local"
        return response

    @application.get("/demo/info", tags=["Demostración local"])
    def demo_info():
        return {
            "mode": "demo-local",
            "data": "fictitious",
            "persistence": "Se elimina al detener el servidor.",
            "external_analysis_enabled": False,
            "accounts": [{"email": email, "role": role} for email, role, _ in DEMO_ACCOUNTS],
            "password": DEMO_PASSWORD,
            "warning": "Solo pruebas locales. No introducir datos reales ni publicar.",
        }

    return application


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1 y 65535.")
    import uvicorn
    print("DEMO LOCAL: datos ficticios, temporales y sin llamadas a OpenAI.")
    print(f"Swagger: http://127.0.0.1:{args.port}/docs")
    print(f"Cuentas de ejemplo: http://127.0.0.1:{args.port}/demo/info")
    uvicorn.run(create_demo_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
