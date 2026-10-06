"""Registro real, validación segura y recorrido cuenta → login → registro."""

from unittest.mock import patch

from app.core.security import _legacy_hash_password, verify_password
from app.models.user import User
from test_login import LoginHttpTests, TEST_SETTINGS


class RegistrationHttpTests(LoginHttpTests):
    def setUp(self):
        super().setUp()
        self.addCleanup(self.client.close)

    def test_register_persists_only_password_hash_and_allows_login(self):
        password = "Una frase privada suficientemente larga"
        response = self.client.post(
            "/auth/register",
            json={"email": "  NUEVA@EXAMPLE.COM ", "password": password},
        )
        self.assertEqual(response.status_code, 201)
        account = response.json()
        self.assertEqual(account["email"], "nueva@example.com")
        self.assertEqual(set(account), {"id", "email", "created_at"})
        self.assertNotIn(password, response.text)
        with self.session_factory() as session:
            user = session.get(User, int(account["id"]))
            self.assertNotEqual(user.password_hash, password)
            self.assertTrue(user.password_hash.startswith("$argon2id$"))
            self.assertTrue(verify_password(password, user.password_hash))
        with patch("app.core.security.load_settings", return_value=TEST_SETTINGS):
            login = self.client.post(
                "/auth/login", json={"email": account["email"], "password": password},
            )
            self.assertEqual(login.status_code, 200)
            token = login.json()["access_token"]
            created = self.client.post(
                "/records",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": "Nota", "content": "Solo para mi cuenta"},
            )
            self.assertEqual(created.status_code, 201)

    def test_duplicate_email_is_rejected_without_creating_another_user(self):
        response = self.client.post(
            "/auth/register",
            json={
                "email": "  PERSONA@EXAMPLE.COM ",
                "password": "Una contraseña suficientemente larga",
            },
        )
        self.assertEqual(response.status_code, 409)
        with self.session_factory() as session:
            self.assertEqual(session.query(User).count(), 1)

    def test_legacy_account_can_login_and_hash_is_upgraded_to_argon2(self):
        password = "Una frase segura para iniciar sesión"
        with self.session_factory() as session:
            user = session.get(User, 1)
            user.password_hash = _legacy_hash_password(password)
            session.commit()
        with patch("app.core.security.load_settings", return_value=TEST_SETTINGS):
            response = self.client.post(
                "/auth/login", json={"email": "persona@example.com", "password": password},
            )
        self.assertEqual(response.status_code, 200)
        with self.session_factory() as session:
            self.assertTrue(session.get(User, 1).password_hash.startswith("$argon2id$"))

    def test_rejects_invalid_email_short_password_and_server_owned_fields(self):
        for payload in (
            {"email": None, "password": "frase privada suficientemente larga"},
            {"email": {"correo": "nueva@example.com"}, "password": "frase privada suficientemente larga"},
            {"email": "no-es-correo", "password": "frase privada suficientemente larga"},
            {"email": "nueva@example.com", "password": "privada"},
            {"email": "nueva@example.com", "password": "frase privada suficientemente larga", "id": 5},
            {"email": "nueva@example.com", "password": "frase privada suficientemente larga", "password_hash": "falso"},
        ):
            with self.subTest(payload_keys=list(payload)):
                response = self.client.post("/auth/register", json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn(payload["password"], response.text)
                for error in response.json()["detail"]:
                    self.assertNotIn("input", error)
        with self.session_factory() as session:
            self.assertEqual(session.query(User).count(), 1)
