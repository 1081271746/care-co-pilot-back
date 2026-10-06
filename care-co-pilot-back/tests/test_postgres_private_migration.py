"""Restricciones reales, revisión Alembic y reversión en PostgreSQL."""

import unittest

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from postgres_support import PostgresSandbox


class PostgresPrivateMigrationTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = PostgresSandbox(self)
        self.engine = self.sandbox.engine
        with self.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (id, email, password_hash) VALUES "
                "(1, 'uno@example.test', 'hash'), (2, 'dos@example.test', 'hash')"
            ))

    def test_foreign_keys_reject_orphans_and_cascade_only_deleted_owner(self):
        with self.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO private_records (owner_id, title, content) VALUES "
                "(1, 'Uno', 'Privado'), (2, 'Dos', 'Privado')"
            ))
        for statement in (
            "INSERT INTO private_records (owner_id, title, content) "
            "VALUES (999, 'Huérfano', 'Texto')",
            "UPDATE private_records SET owner_id = 999 WHERE owner_id = 1",
        ):
            with self.subTest(statement=statement):
                with self.assertRaises(IntegrityError) as error:
                    with self.engine.begin() as connection:
                        connection.execute(text(statement))
                self.assertEqual(error.exception.orig.sqlstate, "23503")
        with self.engine.begin() as connection:
            self.assertEqual(
                connection.execute(text(
                    "SELECT owner_id FROM private_records ORDER BY owner_id"
                )).scalars().all(), [1, 2],
            )
            connection.execute(text("DELETE FROM users WHERE id = 1"))
            self.assertEqual(
                connection.execute(text(
                    "SELECT owner_id FROM private_records"
                )).scalars().all(), [2],
            )
            self.assertEqual(connection.execute(text("SELECT id FROM users")).scalar(), 2)

    def test_private_migration_reverts_and_reapplies_preserving_accounts(self):
        with self.engine.begin() as connection:
            inspector = inspect(connection)
            columns = {c["name"]: c for c in inspector.get_columns("private_records")}
            self.assertEqual(set(columns), {
                "id", "owner_id", "title", "content", "created_at", "updated_at",
            })
            self.assertFalse(columns["owner_id"]["nullable"])
            for name in ("created_at", "updated_at"):
                self.assertTrue(columns[name]["type"].timezone)
            fk = inspector.get_foreign_keys("private_records")[0]
            self.assertEqual(fk["constrained_columns"], ["owner_id"])
            self.assertEqual(fk["referred_table"], "users")
            self.assertEqual(fk["referred_columns"], ["id"])
            self.assertEqual(fk["options"]["ondelete"], "CASCADE")
            self.assertTrue(any(
                index["column_names"] == ["owner_id"]
                for index in inspector.get_indexes("private_records")
            ))
            connection.execute(text(
                "INSERT INTO private_records (owner_id, title, content) "
                "VALUES (1, 'Nota', 'Texto')"
            ))
            accounts = connection.execute(text(
                "SELECT id, email, password_hash, created_at FROM users ORDER BY id"
            )).all()
            self.assertIn(
                "0002_private_records",
                [rev.revision for rev in self.sandbox_revision_chain()],
            )
        self.sandbox.migrate("downgrade", "0001_create_users")
        with self.engine.connect() as connection:
            self.assertNotIn("private_records", inspect(connection).get_table_names())
            self.assertEqual(connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one(), "0001_create_users")
            self.assertEqual(connection.execute(text(
                "SELECT id, email, password_hash, created_at FROM users ORDER BY id"
            )).all(), accounts)
        self.sandbox.migrate("upgrade", "head")
        with self.engine.connect() as connection:
            self.assertIn("private_records", inspect(connection).get_table_names())
            self.assertEqual(connection.execute(text(
                "SELECT count(*) FROM private_records"
            )).scalar_one(), 0)
            self.assertEqual(connection.execute(text(
                "SELECT id, email, password_hash, created_at FROM users ORDER BY id"
            )).all(), accounts)
        self.sandbox.migrate("downgrade", "base")
        with self.engine.connect() as connection:
            self.assertNotIn("users", inspect(connection).get_table_names())
            self.assertNotIn("private_records", inspect(connection).get_table_names())

    def sandbox_revision_chain(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from postgres_support import ROOT

        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "migrations"))
        return list(ScriptDirectory.from_config(config).walk_revisions())
