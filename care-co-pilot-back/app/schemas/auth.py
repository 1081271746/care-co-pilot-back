"""Esquemas públicos de identidad autenticada."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class AuthenticatedUser(BaseModel):
    id: str = Field(min_length=1, max_length=128)


class LoginRequest(BaseModel):
    """Credenciales enviadas al inicio de sesión."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not normalized:
            raise ValueError("El correo electrónico no puede estar vacío.")
        return normalized


class LoginResponse(BaseModel):
    """Token de acceso emitido después de comprobar las credenciales."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
