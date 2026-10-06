"""Mismos contratos HTTP y roles sobre PostgreSQL local migrado y desechable."""

import unittest

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import test_account_roles as role_fixture
import test_catalog_admin as catalog_fixture
import test_postgres_journal as postgres_fixture
from postgres_support import PostgresSandbox


def align_account_sequence(engine):
    # Las cuentas de la fixture tienen id explícito; SERIAL no avanza al insertarlas.
    with engine.begin() as connection:
        connection.execute(text(
            "SELECT setval(pg_get_serial_sequence('users', 'id'), "
            "(SELECT max(id) FROM users))"
        ))


class PostgresCatalogAdminTests(catalog_fixture.CatalogAdminTests):
    def setUp(self):
        postgres_fixture.PostgresJournalTests.setUp(self)
        align_account_sequence(self.engine)
        self.prepare_catalog_admin()

    def test_history_foreign_key_prevents_physical_exercise_deletion(self):
        completed = self.request_as("1", "POST", "/exercises/1/completions", json={"note": "Privada"})
        self.assertEqual(completed.status_code, 201)
        self.assertEqual(self.request_as("2", "DELETE", "/admin/exercises/1").status_code, 204)
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as connection:
                connection.execute(text("DELETE FROM exercises WHERE id=1"))
        self.assertEqual(self.request_as("1", "GET",
            f"/progress/exercises/{completed.json()['id']}").json(), completed.json())


class PostgresAccountRoleTests(role_fixture.AccountRoleTests):
    def setUp(self):
        postgres_fixture.PostgresJournalTests.setUp(self)
        align_account_sequence(self.engine)


class PostgresRoleMigrationTests(unittest.TestCase):
    def test_migration_preserves_existing_accounts_and_restricts_roles(self):
        sandbox = PostgresSandbox(self)
        role_fixture.check_role_migration(self, sandbox.engine)
