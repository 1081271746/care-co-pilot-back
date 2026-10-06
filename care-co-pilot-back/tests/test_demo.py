"""Recorridos de la API real en demostración, sin PostgreSQL ni red externa."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.demo import create_demo_app
from app.demo_data import DEMO_ACCOUNTS, DEMO_PASSWORD
from app.main import create_app
from app.schemas.analysis import PRIVACY_NOTICE_VERSION


class DemoTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"APP_ENV": "development"}):
            self.app = create_demo_app()
        self.network = patch(
            "app.services.openai_analysis.urlopen",
            side_effect=AssertionError("La demo nunca debe llamar a OpenAI."),
        )
        self.network_mock = self.network.start()
        self.addCleanup(self.network.stop)
        self.database = patch(
            "app.database.connection.create_database_engine",
            side_effect=AssertionError("La demo nunca debe abrir la base real."),
        )
        self.database.start()
        self.addCleanup(self.database.stop)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def login(self, index=0):
        response = self.client.post("/auth/login", json={
            "email": DEMO_ACCOUNTS[index][0], "password": DEMO_PASSWORD,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_seed_readiness_history_and_permissions(self):
        headers = self.login()
        self.assertEqual(self.client.get("/health/ready").status_code, 200)
        response = self.client.get("/journal", headers=headers)
        self.assertEqual(response.headers["X-CoPilot-Mode"], "demo-local")
        self.assertEqual(len(response.json()["items"]), 3)
        dashboard = self.client.get("/dashboard", headers=headers).json()
        self.assertEqual(dashboard["journal_entries"], 3)
        self.assertEqual(dashboard["completed_exercises"], 1)
        history = self.client.get("/history?days=7", headers=headers).json()
        self.assertEqual(sum(row["journal_entries"] for row in history["daily"]), 3)
        self.assertEqual(len(history["daily"]), 7)
        self.assertEqual(self.client.get("/profile", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/resources", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/admin/exercises", headers=headers).status_code, 403)
        admin = self.login(2)
        self.assertEqual(self.client.get("/auth/me", headers=admin).json()["role"], "admin")
        self.assertEqual(self.client.get("/auth/me", headers=headers).json()["role"], "user")
        self.assertEqual(self.client.get("/admin/exercises", headers=admin).status_code, 200)
        entry_id = response.json()["items"][0]["id"]
        self.assertEqual(self.client.get(f"/journal/{entry_id}", headers=admin).status_code, 404)
        self.assertEqual(self.client.get(f"/journal/{entry_id}", headers=self.login(1)).status_code, 404)
        self.assertEqual(self.client.get("/journal").status_code, 401)

    def test_crud_registration_completions_and_logout(self):
        registered = self.client.post("/auth/register", json={
            "email": "nueva.demo@example.com", "password": DEMO_PASSWORD,
        })
        self.assertEqual(registered.status_code, 201, registered.text)
        login = self.client.post("/auth/login", json={
            "email": "nueva.demo@example.com", "password": DEMO_PASSWORD,
        })
        self.assertEqual(login.status_code, 200)
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        response = self.client.post("/journal", headers=headers, json={"content": "Texto ficticio nuevo."})
        self.assertEqual(response.status_code, 201)
        entry = response.json()
        self.assertEqual(entry["analysis_status"], "pending")
        path = f"/journal/{entry['id']}"
        self.assertEqual(self.client.patch(path, headers=headers, json={"title": "Editado"}).status_code, 200)
        recommendations = self.client.get(path + "/recommendations", headers=headers).json()
        self.assertEqual(recommendations["mode"], "general")
        exercise = recommendations["exercises"][0]["id"]
        completion = self.client.post(f"/exercises/{exercise}/completions", headers=headers, json={
            "note": "Nota ficticia.",
        })
        self.assertEqual(completion.status_code, 201)
        progress = f"/progress/exercises/{completion.json()['id']}"
        self.assertEqual(self.client.patch(progress, headers=headers, json={"note": "Cambio ficticio."}).status_code, 200)
        self.assertEqual(self.client.delete(progress, headers=headers).status_code, 204)
        self.assertEqual(self.client.delete(path, headers=headers).status_code, 204)
        self.assertEqual(self.client.get(path, headers=headers).status_code, 404)
        self.assertEqual(self.client.post("/auth/logout", headers=headers).status_code, 204)
        self.assertEqual(self.client.get("/auth/me", headers=headers).status_code, 401)

    def test_analysis_disabled_even_with_consent_and_safety_still_works(self):
        headers = self.login()
        entry = self.client.post("/journal", headers=headers, json={"content": "Ejemplo ficticio de recuerdo."}).json()
        response = self.client.post(f"/journal/{entry['id']}/analyze", headers=headers, json={
            "consent_to_external_analysis": True, "privacy_notice_version": PRIVACY_NOTICE_VERSION,
        })
        self.assertEqual(response.status_code, 503, response.text)
        saved = self.client.get(f"/journal/{entry['id']}", headers=headers).json()
        self.assertIsNone(saved["analysis_result"])
        self.assertEqual(saved["analysis_status"], "pending")
        crisis = self.client.post("/journal", headers=headers, json={"content": "Texto ficticio: quiero morir."}).json()
        self.assertEqual(crisis["analysis_status"], "safety_priority")
        recs = self.client.get(f"/journal/{crisis['id']}/recommendations", headers=headers).json()
        self.assertEqual(recs["mode"], "safety")
        self.assertEqual(recs["exercises"], [])
        self.network_mock.assert_not_called()

    def test_restart_discards_data_and_tokens(self):
        headers = self.login()
        self.client.post("/journal", headers=headers, json={"content": "Entrada descartable."})
        with patch.dict(os.environ, {"APP_ENV": "development"}):
            other = create_demo_app()
        with TestClient(other) as client:
            self.assertEqual(client.get("/journal", headers=headers).status_code, 401)
            login = client.post("/auth/login", json={
                "email": DEMO_ACCOUNTS[0][0], "password": DEMO_PASSWORD,
            })
            fresh_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            self.assertEqual(len(client.get("/journal", headers=fresh_headers).json()["items"]), 3)

    def test_production_is_rejected_and_normal_app_has_no_demo_endpoint(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            with self.assertRaises(RuntimeError):
                create_demo_app()
        self.assertNotIn("/demo/info", create_app().openapi()["paths"])
        info = self.client.get("/demo/info").json()
        self.assertEqual(info["data"], "fictitious")
        self.assertFalse(info["external_analysis_enabled"])

    def test_explicit_jwt_settings_do_not_leak_between_apps(self):
        from app.core.config import Settings
        from app.core.security import InvalidAccessTokenError, decode_access_token
        from pydantic import SecretStr
        token = self.login()["Authorization"].split(" ", 1)[1]
        with self.assertRaises(InvalidAccessTokenError):
            decode_access_token(token, settings=Settings(jwt_secret_key=SecretStr("x" * 48)))
