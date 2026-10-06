"""Conexiones de integración optativas, locales y aisladas por esquema."""

import os
from pathlib import Path
import unittest
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]


def validate_test_url(environ):
    """No aceptar DATABASE_URL, producción, hosts remotos ni opciones de DSN."""
    raw_url = environ.get("TEST_DATABASE_URL")
    if not raw_url:
        raise ValueError("Define TEST_DATABASE_URL explícitamente para esta suite.")
    if (
        environ.get("APP_ENV") != "test"
        or environ.get("TEST_POSTGRES_ALLOW_MIGRATIONS") != "1"
    ):
        raise ValueError("Requiere APP_ENV=test y TEST_POSTGRES_ALLOW_MIGRATIONS=1.")
    try:
        url = make_url(raw_url)
    except ArgumentError:
        raise ValueError("TEST_DATABASE_URL tiene un formato inválido.") from None
    if (
        url.drivername not in {"postgresql", "postgresql+psycopg"}
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or not url.database
        or not url.database.endswith("_test")
        or url.query
    ):
        raise ValueError(
            "Usa PostgreSQL local, una base dedicada terminada en _test "
            "y una URL sin parámetros adicionales."
        )
    return url.set(drivername="postgresql+psycopg")


class PostgresSandbox:
    """Un esquema único por prueba; nunca borrar tablas o esquemas ajenos."""

    def __init__(self, test):
        if not os.environ.get("TEST_DATABASE_URL"):
            if os.environ.get("TEST_POSTGRES_ALLOW_MIGRATIONS") == "1":
                raise ValueError("Falta TEST_DATABASE_URL; no se omitirá la suite.")
            raise unittest.SkipTest(
                "PostgreSQL optativo: ejecuta python tests/run_postgres.py."
            )
        url = validate_test_url(os.environ)
        self.schema = "private_test_" + uuid4().hex
        self.admin = create_engine(
            url, hide_parameters=True, connect_args={"connect_timeout": 5},
        )
        test.addCleanup(self.admin.dispose)
        try:
            with self.admin.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        except SQLAlchemyError:
            raise RuntimeError(
                "No se pudo preparar PostgreSQL de pruebas; revisa acceso y permisos."
            ) from None
        test.addCleanup(self.drop_schema)
        # No incluir public: todos los objetos, incluido alembic_version,
        # deben quedar dentro del esquema exclusivo de esta prueba.
        self.engine = create_engine(
            url,
            hide_parameters=True,
            connect_args={
                "connect_timeout": 5,
                "options": f"-csearch_path={self.schema}",
            },
        )
        test.addCleanup(self.engine.dispose)
        self.migrate("upgrade", "head")

    def migrate(self, operation, revision):
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "migrations"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            getattr(command, operation)(config, revision)

    def drop_schema(self):
        try:
            with self.admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        except SQLAlchemyError:
            raise RuntimeError(
                "No se pudo eliminar el esquema temporal de pruebas."
            ) from None
