"""Datos públicos de cuentas; nunca incluyen hashes ni contraseñas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, SecretStr

from app.schemas.auth import LoginRequest


class RegisterRequest(LoginRequest):
    """Acepta frases de contraseña sin imponer símbolos arbitrarios."""

    password: SecretStr = Field(
        min_length=12, max_length=1024,
    )


class AccountResponse(BaseModel):
    id: str
    email: str
    created_at: datetime


class CurrentAccountResponse(AccountResponse):
    """Rol vigente para mostrar navegación, nunca para conceder permisos."""

    role: Literal["user", "admin"]
