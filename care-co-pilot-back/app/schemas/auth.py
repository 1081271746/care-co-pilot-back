"""Esquemas públicos de identidad autenticada."""

from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    id: str = Field(min_length=1, max_length=128)
