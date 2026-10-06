"""Pruebas del inicio de sesión contra cuentas persistidas."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.security import (
    decode_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.main import create_app
from app.models import Base, User

TEST_SETTINGS = Settings(
    jwt_secret_key=SecretStr("solo-para-pruebas-" + ("x" * 32))
)
TEST_EMAIL = "persona@example.com"
TEST_PASSWORD = "Una frase segura para iniciar sesión"


class PasswordHashTests(unittest.TestCase):
    def test_password_hash_is_salted_and_can_be_verified(self):
        first_hash = hash_password(TEST_PASSWORD)
        second_hash = hash_password(TEST_PASSWORD)

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(verify_password(TEST_PASSWORD, first_hash))
        self.assertFalse(verify_password("otra contraseña", first_hash))

    def test_malformed_hash_does_not_authenticate(self):
        self.assertFalse(verify_password(TEST_PASSWORD, "hash-inválido"))

    def test_missing_hash_does_not_authenticate(self):
        self.assertFalse(verify_password(TEST_PASSWORD, None))


class LoginHttpTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

        with self.session_factory() as session:
            session.add(
                User(
                    email=TEST_EMAIL,
                    password_hash=hash_password(TEST_PASSWORD),
                )
            )
            session.commit()

        self.app = create_app()

        def override_get_db():
            with self.session_factory() as session:
                yield session

        self.app.dependency_overrides[get_db] = override_get_db
        self.addCleanup(self.app.dependency_overrides.clear)
        self.client = TestClient(self.app)

    def test_valid_credentials_receive_a_token_for_the_persisted_user(self):
        with patch("app.core.security.load_settings", return_value=TEST_SETTINGS):
            response = self.client.post(
                "/auth/login",
                json={"email": "  PERSONA@EXAMPLE.COM ", "password": TEST_PASSWORD},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(
            decode_access_token(body["access_token"], settings=TEST_SETTINGS),
            "1",
        )

    def test_login_route_is_documented_in_openapi(self):
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("post", response.json()["paths"]["/auth/login"])

    def test_invalid_password_is_rejected(self):
        with patch("app.core.security.load_settings", return_value=TEST_SETTINGS):
            response = self.client.post(
                "/auth/login",
                json={"email": TEST_EMAIL, "password": "contraseña incorrecta"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Correo o contraseña incorrectos.")

    def test_nonexistent_account_has_the_same_failure_response(self):
        with patch("app.core.security.load_settings", return_value=TEST_SETTINGS):
            wrong_password = self.client.post(
                "/auth/login",
                json={"email": TEST_EMAIL, "password": "contraseña incorrecta"},
            )
            missing_account = self.client.post(
                "/auth/login",
                json={"email": "no-existe@example.com", "password": TEST_PASSWORD},
            )

        self.assertEqual(missing_account.status_code, 401)
        self.assertEqual(missing_account.json(), wrong_password.json())


if __name__ == "__main__":
    unittest.main()
