"""Perfil, resúmenes, privacidad e interrupción de recomendaciones ante riesgo."""

import test_catalog as fixture


class AccompanimentHttpTests(fixture.CatalogHttpTests):
    def test_profile_preferences_can_be_changed_cleared_and_reset_only_by_owner(self):
        updated = self.request_as("1", "PATCH", "/profile", json={
            "first_name": "Nombre de prueba", "country_code": "co",
            "accompaniment_goal": "Escribir con calma",
        })
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["country_code"], "CO")
        other = self.request_as("2", "GET", "/profile").json()
        self.assertEqual(other["first_name"], "")
        self.assertIsNone(other["country_code"])
        cleared = self.request_as("1", "PATCH", "/profile", json={"country_code": None})
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.json()["country_code"])
        self.assertEqual(self.request_as("1", "PATCH", "/profile", json={"owner_id": 2}).status_code, 422)
        self.assertEqual(self.request_as("1", "PATCH", "/profile", json={}).status_code, 422)
        self.assertEqual(self.request_as("1", "DELETE", "/profile").status_code, 204)
        self.assertEqual(self.request_as("1", "GET", "/profile").json()["first_name"], "")

    def test_dashboard_and_daily_history_include_only_current_user_activity(self):
        self.request_as("1", "POST", "/journal", json={"content": "quiero morir"})
        self.request_as("1", "POST", "/exercises/1/completions", json={"note": "Mi progreso"})
        owner = self.request_as("1", "GET", "/dashboard").json()
        other = self.request_as("2", "GET", "/dashboard").json()
        self.assertEqual(owner["journal_entries"], 1)
        self.assertEqual(owner["completed_exercises"], 1)
        self.assertEqual(owner["pending_analyses"], 0)
        self.assertEqual(owner["latest_entry"]["safety_result"]["risk_level"], "urgent")
        self.assertEqual(other["journal_entries"], 0)
        self.assertIsNone(other["latest_entry"])
        history = self.request_as("1", "GET", "/history?days=7").json()
        self.assertEqual(len(history["daily"]), 7)
        self.assertEqual(sum(day["journal_entries"] for day in history["daily"]), 1)
        self.assertEqual(sum(day["completed_exercises"] for day in history["daily"]), 1)
        self.assertEqual(sum(day["entries_with_safety_signals"] for day in history["daily"]), 1)
        other_history = self.request_as("2", "GET", "/history?days=7").json()
        self.assertEqual(sum(day["journal_entries"] for day in other_history["daily"]), 0)
        self.assertEqual(self.request_as("1", "GET", "/history?days=366").status_code, 422)
        self.assertEqual(history["estimated_stages"], [])

    def test_recommendations_are_general_without_ai_and_stop_for_risk(self):
        entry = self.request_as("1", "POST", "/journal", json={"content": "Escribo un recuerdo"}).json()
        path = f"/journal/{entry['id']}/recommendations"
        general = self.request_as("1", "GET", path).json()
        self.assertEqual(general["mode"], "general")
        self.assertIsNone(general["estimated_stage"])
        self.assertTrue(general["resources"])
        self.assertTrue(general["exercises"])
        self.assertEqual(self.request_as("2", "GET", path).status_code, 404)
        self.request_as("1", "PATCH", f"/journal/{entry['id']}", json={"content": "No puedo más"})
        safety = self.request_as("1", "GET", path).json()
        self.assertEqual(safety["mode"], "safety")
        self.assertEqual(safety["exercises"], [])
        self.assertEqual(safety["resources"], [])
        self.assertTrue(safety["safety_result"]["resources"])

    def test_new_private_routes_reject_missing_jwt(self):
        for method, path, payload in (
            ("GET", "/profile", None), ("PATCH", "/profile", {"first_name": "Nombre"}),
            ("DELETE", "/profile", None), ("GET", "/dashboard", None),
            ("GET", "/history", None), ("GET", "/journal/1/recommendations", None),
        ):
            self.assertEqual(self.request_as(None, method, path, json=payload).status_code, 401)
