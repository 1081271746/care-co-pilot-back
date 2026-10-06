"""Clase base compartida por los modelos SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Metadatos ORM versionados mediante migraciones Alembic."""
