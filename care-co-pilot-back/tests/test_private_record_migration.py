"""Verifica el esquema privado y su reversión sin una base externa."""

import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parents[1]


def load_migration(filename):
    path = ROOT / "migrations" / "versions" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar la migración.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrivateRecordMigrationTests(unittest.TestCase):
    def test_revision_follows_users_and_is_the_only_head(self):
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "migrations"))
        scripts = ScriptDirectory.from_config(config)
        self.assertEqual(scripts.get_heads(), ["0002_private_records"])
        self.assertEqual(
            scripts.get_revision("0002_private_records").down_revision,
            "0001_create_users",
        )

    def test_upgrade_and_downgrade_preserve_users(self):
        engine = create_engine("sqlite:///:memory:")
        self.addCleanup(engine.dispose)
        users = load_migration("0001_create_users.py")
        records = load_migration("0002_create_private_records.py")
        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                users.upgrade()
                records.upgrade()
            inspector = inspect(connection)
            self.assertEqual(
                {column["name"] for column in inspector.get_columns("private_records")},
                {"id", "owner_id", "title", "content", "created_at", "updated_at"},
            )
            foreign_key = inspector.get_foreign_keys("private_records")[0]
            self.assertEqual(foreign_key["constrained_columns"], ["owner_id"])
            self.assertEqual(foreign_key["referred_table"], "users")
            self.assertEqual(foreign_key["options"]["ondelete"], "CASCADE")
            self.assertTrue(
                any(index["column_names"] == ["owner_id"]
                    for index in inspector.get_indexes("private_records"))
            )
            with Operations.context(context):
                records.downgrade()
            self.assertNotIn("private_records", inspect(connection).get_table_names())
            self.assertIn("users", inspect(connection).get_table_names())


if __name__ == "__main__":
    unittest.main()
