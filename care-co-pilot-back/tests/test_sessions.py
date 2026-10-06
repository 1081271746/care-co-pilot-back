"""Sesiones revocables y cuentas persistidas, sin acceso entre propietarios."""

from unittest.mock import patch

from app.models.user import User
from app.models.revoked_token import RevokedToken
import test_login as fixture


class SessionHttpTests(fixture.LoginHttpTests):
    def login_token(self):
        response = self.client.post("/auth/login", json={
            "email": fixture.TEST_EMAIL, "password": fixture.TEST_PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def test_current_user_has_public_data_only(self):
        with patch("app.core.security.load_settings", return_value=fixture.TEST_SETTINGS):
            token = self.login_token()
            response = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], fixture.TEST_EMAIL)
        self.assertEqual(set(response.json()), {"id", "email", "created_at", "role"})
        self.assertEqual(response.json()["role"], "user")

    def test_current_role_is_read_from_database_even_with_an_existing_token(self):
        with patch("app.core.security.load_settings", return_value=fixture.TEST_SETTINGS):
            token = self.login_token()
            headers = {"Authorization": f"Bearer {token}"}
            with self.session_factory() as session:
                session.get(User, 1).role = "admin"
                session.commit()
            response = self.client.get("/auth/me", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["role"], "admin")
            with self.session_factory() as session:
                session.get(User, 1).role = "user"
                session.commit()
            self.assertEqual(self.client.get("/auth/me", headers=headers).json()["role"], "user")

    def test_logout_revokes_only_current_session_and_private_routes(self):
        with patch("app.core.security.load_settings", return_value=fixture.TEST_SETTINGS):
            first = self.login_token()
            second = self.login_token()
            self.assertNotEqual(first, second)
            headers = {"Authorization": f"Bearer {first}"}
            self.assertEqual(self.client.post("/auth/logout", headers=headers).status_code, 204)
            for method, path, body in (
                ("GET", "/auth/me", None), ("GET", "/records", None),
                ("POST", "/records", {"title": "Nota", "content": "Contenido"}),
                ("GET", "/records/1", None), ("PATCH", "/records/1", {"content": "Intento"}),
                ("DELETE", "/records/1", None),
            ):
                response = self.client.request(method, path, headers=headers, json=body)
                self.assertEqual(response.status_code, 401)
            self.assertEqual(self.client.get(
                "/auth/me", headers={"Authorization": f"Bearer {second}"},
            ).status_code, 200)
        with self.session_factory() as session:
            self.assertIsNone(session.get(RevokedToken, first))
            self.assertEqual(session.query(RevokedToken).count(), 1)

    def test_inactive_or_deleted_account_cannot_use_a_previously_valid_token(self):
        for deleted in (False, True):
            with self.subTest(deleted=deleted):
                with patch("app.core.security.load_settings", return_value=fixture.TEST_SETTINGS):
                    token = self.login_token()
                    with self.session_factory() as session:
                        user = session.get(User, 1)
                        if deleted:
                            session.delete(user)
                        else:
                            user.is_active = False
                        session.commit()
                    headers = {"Authorization": f"Bearer {token}"}
                    self.assertEqual(self.client.get("/auth/me", headers=headers).status_code, 401)
                    self.assertEqual(self.client.get("/records", headers=headers).status_code, 401)
                    if not deleted:
                        denied = self.client.post("/auth/login", json={
                            "email": fixture.TEST_EMAIL, "password": fixture.TEST_PASSWORD,
                        })
                        self.assertEqual(denied.status_code, 401)
                        with self.session_factory() as session:
                            session.get(User, 1).is_active = True
                            session.commit()
