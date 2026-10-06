"""Preferencias voluntarias, sin atributos de autorización editables."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    accompaniment_goal: str | None = Field(default=None, max_length=500)

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("Envía al menos una preferencia.")
        if any(getattr(self, field) is None for field in self.model_fields_set if field != "country_code"):
            raise ValueError("Solo el país admite un valor nulo.")
        return self


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    first_name: str = ""
    last_name: str = ""
    country_code: str | None = None
    accompaniment_goal: str = ""
    updated_at: datetime | None = None
