"""Creación diferida y comprobación explícita de la conexión PostgreSQL."""

from functools import lru_cache
from typing import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, load_settings


class DatabaseConfigurationError(RuntimeError):
    """La conexión no está configurada o no apunta a PostgreSQL."""


class DatabaseConnectionError(RuntimeError):
    """No fue posible completar la comprobación de conexión."""


def _postgresql_url(settings: Settings) -> URL:
    if settings.database_url is None:
        raise DatabaseConfigurationError(
            "PostgreSQL no está configurado. Define DATABASE_URL en el entorno."
        )

    try:
        url = make_url(settings.database_url.get_secret_value())
    except ArgumentError:
        raise DatabaseConfigurationError(
            "DATABASE_URL no tiene un formato válido para SQLAlchemy."
        ) from None

    # SQLAlchemy usa psycopg2 por defecto para postgresql://. Esta aplicación
    # instala psycopg 3 y fija el controlador para evitar una selección implícita.
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    elif url.drivername != "postgresql+psycopg":
        raise DatabaseConfigurationError(
            "DATABASE_URL debe usar PostgreSQL con el controlador psycopg."
        )

    if not url.host or not url.database:
        raise DatabaseConfigurationError(
            "DATABASE_URL debe incluir el host y el nombre de la base de datos."
        )

    return url


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Crea un motor sin abrir conexión ni ejecutar cambios de esquema."""
    configured_settings = settings or load_settings()
    url = _postgresql_url(configured_settings)

    try:
        return create_engine(url, pool_pre_ping=True)
    except (ImportError, SQLAlchemyError):
        raise DatabaseConfigurationError(
            "No fue posible crear el motor PostgreSQL; revisa DATABASE_URL "
            "y que el controlador psycopg esté instalado."
        ) from None


@lru_cache(maxsize=1)
def get_database_engine() -> Engine:
    """Devuelve el motor compartido, creado solo cuando se solicita."""
    return create_database_engine()


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Construye una fábrica de sesiones para el motor indicado."""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_database_engine())


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: entrega una sesión y siempre la cierra."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def verify_database_connection(engine: Engine | None = None) -> None:
    """Comprueba PostgreSQL mediante SELECT 1, sin crear tablas."""
    selected_engine = engine or get_database_engine()
    try:
        with selected_engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        raise DatabaseConnectionError(
            "No fue posible conectar a PostgreSQL. Revisa la disponibilidad "
            "de la base y la configuración de DATABASE_URL."
        ) from None

    if result != 1:
        raise DatabaseConnectionError(
            "PostgreSQL respondió un resultado inesperado a la comprobación."
        )
