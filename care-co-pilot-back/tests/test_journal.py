"""Diario privado, prioridad de seguridad y ausencia explícita de IA."""

import unittest

import test_private_records as fixture
from app.models.journal_entry import JournalEntry
from app.services.safety import review_safety


class SafetyTests(unittest.TestCase):
    def test_required_risk_expressions_are_never_minimized(self):
        for text in ("QUIERO MORIR", "quiero hacerme daño", "no quiero seguir", "no puedo más"):
            with self.subTest(text=text):
                result = review_safety(text)
                self.assertTrue(result.requires_help)
                self.assertIn(result.risk_level, ("elevated", "urgent"))
                self.assertTrue(result.resources)
                self.assertIn("no", result.disclaimer.lower())

    def test_absence_of_signal_is_not_described_as_low_risk_or_diagnosis(self):
        result = review_safety("Hoy recordé a mi padre con tristeza.")
        self.assertEqual(result.risk_level, "unassessed")
        self.assertIn("no demuestra", result.limitations)
        self.assertEqual(result.source, "local_safety_rules")


class JournalHttpTests(fixture.PrivateRecordHttpTests):
    def create_entry(self, user="1", content="Hoy recordé un momento importante."):
        response = self.request_as(user, "POST", "/journal", json={"content": content})
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_entry_is_saved_with_safety_review_but_without_fake_ai(self):
        entry = self.create_entry()
        self.assertEqual(entry["analysis_status"], "pending")
        self.assertIsNone(entry["estimated_stage"])
        self.assertIsNone(entry["analysis_result"])
        self.assertNotIn("owner_id", entry)
        response = self.request_as("1", "POST", f"/journal/{entry['id']}/analyze", json={
            "consent_to_external_analysis": True,
        })
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            self.request_as("1", "GET", f"/journal/{entry['id']}").status_code, 200,
        )

    def test_crisis_prioritizes_help_even_without_external_analysis(self):
        entry = self.create_entry(content="No puedo más, quiero morir")
        self.assertEqual(entry["analysis_status"], "safety_priority")
        self.assertEqual(entry["risk_level"], "urgent")
        response = self.request_as("1", "POST", f"/journal/{entry['id']}/analyze", json={})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["analysis_result"])
        updated = self.request_as("1", "PATCH", f"/journal/{entry['id']}", json={
            "content": "Hoy quiero escribir un recuerdo.",
        })
        self.assertEqual(updated.json()["analysis_status"], "pending")
        self.assertIsNone(updated.json()["estimated_stage"])

    def test_journal_all_operations_hide_foreign_entries(self):
        entry = self.create_entry()
        self.assertEqual(self.request_as("2", "GET", "/journal").json()["items"], [])
        for method, suffix, body in (
            ("GET", "", None), ("PATCH", "", {"content": "Ajeno"}),
            ("DELETE", "", None),
            ("POST", "/analyze", {"consent_to_external_analysis": True}),
        ):
            foreign = self.request_as("2", method, f"/journal/{entry['id']}{suffix}", json=body)
            missing = self.request_as("2", method, f"/journal/9999{suffix}", json=body)
            self.assertEqual(foreign.status_code, 404)
            self.assertEqual(foreign.json(), missing.json())
        self.assertEqual(self.request_as("1", "DELETE", f"/journal/{entry['id']}").status_code, 204)
        self.assertEqual(self.request_as("1", "GET", f"/journal/{entry['id']}").status_code, 404)

    def test_cursor_remains_stable_after_insertion(self):
        first = self.create_entry()
        second = self.create_entry()
        page = self.request_as("1", "GET", "/journal?limit=1").json()
        self.assertEqual(page["items"][0]["id"], second["id"])
        self.create_entry()
        next_page = self.request_as(
            "1", "GET", f"/journal?limit=1&before_id={page['next_cursor']}",
        ).json()
        self.assertEqual(next_page["items"][0]["id"], first["id"])

    def test_journal_requires_authentication_and_rejects_client_analysis(self):
        for method, path, body in (
            ("GET", "/journal", None), ("POST", "/journal", {"content": "Nota"}),
            ("GET", "/journal/1", None), ("PATCH", "/journal/1", {"content": "Nota"}),
            ("DELETE", "/journal/1", None), ("POST", "/journal/1/analyze", {}),
        ):
            self.assertEqual(self.request_as(None, method, path, json=body).status_code, 401)
        for payload in ({"content": "  "}, {"content": "Nota", "owner_id": 2},
                        {"content": "Nota", "estimated_stage": "acceptance"}):
            self.assertEqual(self.request_as("1", "POST", "/journal", json=payload).status_code, 422)
        with self.session_factory() as session:
            self.assertEqual(session.query(JournalEntry).count(), 0)
