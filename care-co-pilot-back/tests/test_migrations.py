"""Prueba reversible de la primera migración sin una base externa."""

import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "0001_create_users.py"
)
SPEC = importlib.util.spec_from_file_location("migration_0001_create_users", MIGRATION_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("No se pudo cargar la migración inicial de users.")
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


class UserMigrationTests(unittest.TestCase):
    def test_upgrade_creates_users_and_downgrade_removes_it(self):
        engine = create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)

        with engine.begin() as connection:
            migration_context = MigrationContext.configure(connection)
            with Operations.context(migration_context):
                MIGRATION.upgrade()

            inspector = inspect(connection)
            self.assertIn("users", inspector.get_table_names())
            columns = {column["name"] for column in inspector.get_columns("users")}
            self.assertEqual(
                columns,
                {"id", "email", "password_hash", "created_at"},
            )
            self.assertEqual(
                [
                    constraint["name"]
                    for constraint in inspector.get_unique_constraints("users")
                ],
                ["uq_users_email"],
            )

            with Operations.context(migration_context):
                MIGRATION.downgrade()

            self.assertNotIn("users", inspect(connection).get_table_names())


if __name__ == "__main__":
    unittest.main()
