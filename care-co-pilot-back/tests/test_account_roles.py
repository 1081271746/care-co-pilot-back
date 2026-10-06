"""Roles: migración explícita, registro sin privilegios y comando local."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

import test_private_records as fixture
from app.models.user import User
from app.services.account_roles import main, set_account_role

ROOT = Path(__file__).resolve().parents[1]


def migrate(engine, operation, revision):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        getattr(command, operation)(config, revision)


def check_role_migration(test, engine):
    migrate(engine, "downgrade", "0006_emotional_profiles")
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id, email, password_hash) "
            "VALUES (99, 'migration@example.test', 'hash')"
        ))
    migrate(engine, "upgrade", "head")
    with engine.begin() as connection:
        test.assertEqual(connection.execute(text(
            "SELECT role FROM users WHERE id=99"
        )).scalar_one(), "user")
    with test.assertRaises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE users SET role='superuser' WHERE id=99"))
    with test.assertRaises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE users SET role=NULL WHERE id=99"))
    migrate(engine, "downgrade", "0006_emotional_profiles")
    with engine.connect() as connection:
        test.assertNotIn("role", {c["name"] for c in inspect(connection).get_columns("users")})
        test.assertEqual(connection.execute(text(
            "SELECT email FROM users WHERE id=99"
        )).scalar_one(), "migration@example.test")
    migrate(engine, "upgrade", "head")


class RoleMigrationTests(TestCase):
    def test_existing_accounts_and_reversible_migration(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        migrate(engine, "upgrade", "head")
        check_role_migration(self, engine)


class AccountRoleTests(fixture.PrivateRecordHttpTests):
    def test_registration_never_accepts_roles_or_admin_flags(self):
        for extra in ({"role": "admin"}, {"is_admin": True}, {"is_active": True}):
            result = self.request_as(None, "POST", "/auth/register", json={
                "email": "new@example.com", "password": "frase-de-prueba-larga", **extra,
            })
            self.assertEqual(result.status_code, 422)
        result = self.request_as(None, "POST", "/auth/register", json={
            "email": "new@example.com", "password": "frase-de-prueba-larga",
        })
        self.assertEqual(result.status_code, 201)
        with self.session_factory() as db:
            self.assertEqual(db.get(User, int(result.json()["id"])).role, "user")

    def test_role_command_requires_local_confirmation_and_active_account(self):
        with self.session_factory() as db:
            for args in ((1, "admin", False), (999, "admin", True), (1, "root", True)):
                with self.assertRaises(ValueError):
                    set_account_role(db, args[0], args[1], confirmed=args[2])
            self.assertEqual(db.get(User, 1).role, "user")
            set_account_role(db, 1, "admin", confirmed=True)
            self.assertEqual(db.get(User, 1).role, "admin")
            set_account_role(db, 1, "user", confirmed=True)
            db.get(User, 1).is_active = False
            db.commit()
            with self.assertRaises(ValueError):
                set_account_role(db, 1, "admin", confirmed=True)

    def test_cli_without_confirmation_does_not_open_a_database(self):
        with patch("app.services.account_roles.get_session_factory") as factory:
            with self.assertRaises(SystemExit) as result:
                main(["--account-id", "1", "--role", "admin"])
            self.assertEqual(result.exception.code, 2)
            factory.assert_not_called()
