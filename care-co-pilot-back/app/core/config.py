"""Configuración básica a partir del entorno y del archivo .env del backend."""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    app_name: str = Field(default="Co-Piloto de Duelo", min_length=1)
    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = Field(default=None, repr=False)


def load_settings() -> Settings:
    # Las variables ya configuradas en el entorno tienen prioridad sobre .env.
    load_dotenv(BACKEND_ROOT / ".env", override=False)
    return Settings(
        app_name=os.getenv("APP_NAME", "Co-Piloto de Duelo"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL") or None,
    )
