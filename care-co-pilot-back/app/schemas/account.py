"""Datos públicos de cuentas; nunca incluyen hashes ni contraseñas."""

from datetime import datetime

from pydantic import Field

from app.schemas.auth import LoginRequest


class RegisterRequest(LoginRequest):
    """Acepta frases de contraseña sin imponer símbolos arbitrarios."""

    password: LoginRequest.model_fields["password"].annotation = Field(
        min_length=12, max_length=1024,
    )


class AccountResponse(LoginRequest.__bases__[0]):
    id: str
    email: str
    created_at: datetime
