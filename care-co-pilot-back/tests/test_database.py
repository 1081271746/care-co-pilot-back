import unittest
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from pydantic import SecretStr

from app.core.config import Settings
from app.database import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    create_database_engine,
    verify_database_connection,
)


class DatabaseConfigurationTests(unittest.TestCase):
    def test_requires_explicit_database_url(self):
        with patch.dict("os.environ", {"DATABASE_URL": ""}, clear=True):
            with self.assertRaisesRegex(DatabaseConfigurationError, "DATABASE_URL"):
                create_database_engine()

    def test_normalizes_postgresql_url_to_psycopg(self):
        settings = Settings(
            database_url=SecretStr("postgresql://user:password@localhost/test_db")
        )
        engine = create_database_engine(settings)
        self.addCleanup(engine.dispose)

        self.assertEqual(engine.url.drivername, "postgresql+psycopg")

    def test_accepts_explicit_psycopg_driver(self):
        settings = Settings(
            database_url=SecretStr(
                "postgresql+psycopg://user:password@localhost/test_db"
            )
        )
        engine = create_database_engine(settings)
        self.addCleanup(engine.dispose)

        self.assertEqual(engine.url.drivername, "postgresql+psycopg")

    def test_rejects_non_postgresql_url(self):
        settings = Settings(database_url=SecretStr("sqlite:///local.db"))

        with self.assertRaisesRegex(DatabaseConfigurationError, "PostgreSQL"):
            create_database_engine(settings)

    def test_verify_connection_executes_select_one(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)

        self.assertIsNone(verify_database_connection(engine))

    def test_connection_errors_are_explicit_and_sanitized(self):
        engine = Mock(spec=Engine)
        engine.connect.side_effect = OperationalError(
            "SELECT 1", {}, RuntimeError("private connection detail")
        )

        with self.assertRaises(DatabaseConnectionError) as caught:
            verify_database_connection(engine)

        self.assertIn("PostgreSQL", str(caught.exception))
        self.assertNotIn("private connection detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
