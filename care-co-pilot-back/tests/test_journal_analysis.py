"""Persistencia, consentimiento, seguridad y carreras, sin llamadas a OpenAI."""

from app.core.config import Settings
from app.models.journal_entry import JournalEntry
from app.schemas.analysis import PRIVACY_NOTICE_VERSION, ProviderAnalysis
from app.services.catalog_seed import seed_catalog
from app.services.openai_analysis import get_analysis_provider, AnalysisUnavailable
import test_private_records as fixture


class ControlledProvider:
    def __init__(self):
        self.settings = Settings(openai_model="test-model")
        self.calls = []
        self.result = ProviderAnalysis(
            estimated_stage="intense_sadness", risk_level="unassessed", emotions=["sadness"],
        )
        self.callback = None
        self.error = None

    def analyze(self, content):
        self.calls.append(content)
        if self.callback:
            self.callback()
        if self.error:
            raise self.error
        return self.result


class JournalAnalysisTests(fixture.PrivateRecordHttpTests):
    def setUp(self):
        super().setUp()
        self.configure_analysis()

    def configure_analysis(self):
        self.provider = ControlledProvider()
        self.app.dependency_overrides[get_analysis_provider] = lambda: self.provider
        with self.session_factory() as session:
            seed_catalog(session)

    def create_entry(self, content="Hoy recordé a una persona querida con mucha tristeza."):
        response = self.request_as("1", "POST", "/journal", json={"content": content})
        self.assertEqual(response.status_code, 201)
        return response.json()

    def analyze(self, entry_id, **kwargs):
        return self.request_as("1", "POST", f"/journal/{entry_id}/analyze", json={
            "consent_to_external_analysis": True,
            "privacy_notice_version": PRIVACY_NOTICE_VERSION,
        }, **kwargs)

    def test_real_result_contract_is_persisted_and_adapts_recommendations(self):
        entry = self.create_entry()
        response = self.analyze(entry["id"])
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["estimated_stage"], "intense_sadness")
        self.assertEqual(result["analysis_status"], "completed")
        self.assertEqual(result["analysis_result"]["source"], "openai")
        self.assertNotIn("revisión local", result["safety_result"]["message"])
        self.assertIn("No significa una depresión", result["analysis_result"]["orientation"])
        self.assertEqual(result["analysis_result"]["privacy_notice_version"], PRIVACY_NOTICE_VERSION)
        self.assertIsNotNone(result["analyzed_at"])
        self.assertNotIn("owner_id", result)
        with self.session_factory() as session:
            self.assertEqual(session.get(JournalEntry, entry["id"]).estimated_stage, "intense_sadness")
        recs = self.request_as("1", "GET", f"/journal/{entry['id']}/recommendations").json()
        self.assertEqual(recs["mode"], "orientative")
        self.assertTrue(any(item["stage"] == "intense_sadness" for item in recs["exercises"]))
        history = self.request_as("1", "GET", "/history?days=1").json()
        self.assertEqual(history["estimated_stages"], [{"stage": "intense_sadness", "count": 1}])
        self.assertEqual(self.analyze(entry["id"]).status_code, 200)
        self.assertEqual(len(self.provider.calls), 1)

    def test_consent_and_current_privacy_notice_are_required_before_sending(self):
        entry = self.create_entry()
        for payload in ({}, {"consent_to_external_analysis": True}, {
            "consent_to_external_analysis": "true", "privacy_notice_version": PRIVACY_NOTICE_VERSION,
        }):
            response = self.request_as("1", "POST", f"/journal/{entry['id']}/analyze", json=payload)
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.provider.calls, [])
        notice = self.client.get("/help/privacy").json()
        self.assertEqual(notice["provider"], "OpenAI")
        self.assertFalse(notice["provider_storage_requested"])
        self.assertIn("No garantiza retención cero", notice["external_retention"])

    def test_local_crisis_never_reaches_provider_and_ai_signal_blocks_exercises(self):
        local = self.create_entry("quiero morir")
        self.assertEqual(self.analyze(local["id"]).status_code, 200)
        self.assertEqual(self.provider.calls, [])
        entry = self.create_entry("Ojalá pudiera desaparecer definitivamente.")
        self.provider.result = ProviderAnalysis(
            estimated_stage="intense_sadness", risk_level="urgent", emotions=["sadness"],
        )
        result = self.analyze(entry["id"]).json()
        self.assertEqual(result["analysis_status"], "safety_priority")
        self.assertIsNone(result["estimated_stage"])
        self.assertIsNone(result["analysis_result"]["estimated_stage"])
        self.assertEqual(result["safety_result"]["source"], "openai_safety_signal")
        self.assertEqual(result["safety_result"]["resources"][0]["phone"], "123")
        recs = self.request_as("1", "GET", f"/journal/{entry['id']}/recommendations").json()
        self.assertEqual(recs["mode"], "safety")
        self.assertEqual(recs["exercises"], [])
        self.assertEqual(recs["resources"], [])

    def test_failures_preserve_pending_entry_and_privacy(self):
        entry = self.create_entry()
        self.provider.error = AnalysisUnavailable("Servicio temporalmente no disponible.")
        self.assertEqual(self.analyze(entry["id"]).status_code, 503)
        saved = self.request_as("1", "GET", f"/journal/{entry['id']}").json()
        self.assertEqual(saved["content"], entry["content"])
        self.assertIsNone(saved["analysis_result"])
        self.assertEqual(saved["analysis_status"], "pending")
        foreign = self.request_as("2", "POST", f"/journal/{entry['id']}/analyze", json={
            "consent_to_external_analysis": True, "privacy_notice_version": PRIVACY_NOTICE_VERSION,
        })
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(len(self.provider.calls), 1)

    def test_content_edit_resets_previous_analysis(self):
        entry = self.create_entry()
        self.assertEqual(self.analyze(entry["id"]).status_code, 200)
        changed = self.request_as("1", "PATCH", f"/journal/{entry['id']}", json={
            "content": "Ahora quiero escribir un recuerdo diferente.",
        }).json()
        self.assertIsNone(changed["analysis_result"])
        self.assertIsNone(changed["estimated_stage"])
        self.assertEqual(changed["analysis_status"], "pending")

    def test_concurrent_edit_does_not_receive_stale_analysis(self):
        entry = self.create_entry()
        def change_content():
            with self.session_factory() as session:
                changed = session.get(JournalEntry, entry["id"])
                changed.content = "Texto cambiado mientras esperaba."
                session.commit()
        self.provider.callback = change_content
        response = self.analyze(entry["id"])
        self.assertEqual(response.status_code, 409)
        saved = self.request_as("1", "GET", f"/journal/{entry['id']}").json()
        self.assertEqual(saved["content"], "Texto cambiado mientras esperaba.")
        self.assertIsNone(saved["analysis_result"])

    def test_deleted_entry_cannot_be_recreated_by_late_result(self):
        entry = self.create_entry()
        def delete_entry():
            with self.session_factory() as session:
                session.delete(session.get(JournalEntry, entry["id"]))
                session.commit()
        self.provider.callback = delete_entry
        self.assertEqual(self.analyze(entry["id"]).status_code, 404)

    def test_deactivated_account_cannot_save_late_result(self):
        from app.models.user import User
        entry = self.create_entry()
        def deactivate():
            with self.session_factory() as session:
                session.get(User, 1).is_active = False
                session.commit()
        self.provider.callback = deactivate
        self.assertEqual(self.analyze(entry["id"]).status_code, 401)
        with self.session_factory() as session:
            self.assertIsNone(session.get(JournalEntry, entry["id"]).analysis_result)

    def test_logout_while_waiting_prevents_saving_the_result(self):
        entry = self.create_entry()
        headers = {"Authorization": f"Bearer {self.token('1')}"}
        def logout():
            response = self.request_as(None, "POST", "/auth/logout", headers=headers)
            self.assertEqual(response.status_code, 204)
        self.provider.callback = logout
        response = self.request_as(None, "POST", f"/journal/{entry['id']}/analyze", headers=headers, json={
            "consent_to_external_analysis": True, "privacy_notice_version": PRIVACY_NOTICE_VERSION,
        })
        self.assertEqual(response.status_code, 401)
        with self.session_factory() as session:
            self.assertIsNone(session.get(JournalEntry, entry["id"]).analysis_result)
