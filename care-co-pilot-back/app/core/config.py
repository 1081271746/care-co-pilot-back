"""Configuración básica a partir del entorno y del archivo .env del backend."""

import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr, field_validator

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    app_name: str = Field(default="Co-Piloto de Duelo", min_length=1)
    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = Field(default=None, repr=False)
    jwt_secret_key: SecretStr | None = Field(default=None, repr=False)
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, origins):
        for origin in origins:
            parts = urlsplit(origin)
            if (
                parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.path or parts.query or parts.fragment
                or parts.username or parts.password or "*" in origin
            ):
                raise ValueError("CORS_ORIGINS debe contener orígenes HTTP/HTTPS exactos, sin rutas ni comodines.")
            try:
                parts.port
            except ValueError:
                raise ValueError("Un origen CORS contiene un puerto inválido.") from None
        return list(dict.fromkeys(origins))


def load_settings() -> Settings:
    # Las variables ya configuradas en el entorno tienen prioridad sobre .env.
    load_dotenv(BACKEND_ROOT / ".env", override=False)
    app_env = os.getenv("APP_ENV", "development")
    default_origins = "" if app_env == "production" else "http://localhost:4200,http://127.0.0.1:4200"
    return Settings(
        app_name=os.getenv("APP_NAME", "Co-Piloto de Duelo"),
        app_env=app_env,
        database_url=os.getenv("DATABASE_URL") or None,
        jwt_secret_key=os.getenv("JWT_SECRET_KEY") or None,
        cors_origins=[
            origin.strip() for origin in os.getenv("CORS_ORIGINS", default_origins).split(",")
            if origin.strip()
        ],
    )
