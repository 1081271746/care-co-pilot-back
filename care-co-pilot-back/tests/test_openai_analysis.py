"""Pruebas sin red ni facturación; las respuestas artificiales solo viven aquí."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from app.core.config import Settings
from app.schemas.analysis import ProviderAnalysis
from app.services.openai_analysis import OpenAIAnalyzer, AnalysisUnavailable, MAX_RESPONSE_BYTES

SETTINGS = Settings(
    openai_analysis_enabled=True, openai_api_key="credential-only-for-tests",
)
VALID = {"estimated_stage": "intense_sadness", "risk_level": "unassessed", "emotions": ["sadness"]}


def envelope(value=VALID):
    return {"status": "completed", "output": [{
        "type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": json.dumps(value)},
        ],
    }]}


def fake_response(value):
    return io.BytesIO(json.dumps(value).encode())


class OpenAIAdapterTests(unittest.TestCase):
    def test_request_minimizes_data_and_enforces_schema(self):
        with patch("app.services.openai_analysis.urlopen", return_value=fake_response(envelope())) as transport:
            result = OpenAIAnalyzer(SETTINGS).analyze("Una entrada privada.")
        self.assertIsInstance(result, ProviderAnalysis)
        request = transport.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertFalse(body["store"])
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertFalse(body["text"]["format"]["schema"]["additionalProperties"])
        self.assertEqual(json.loads(body["input"][0]["content"][0]["text"]), {"diary_entry": "Una entrada privada."})
        self.assertNotIn("credential-only-for-tests", repr(SETTINGS))
        self.assertEqual(transport.call_count, 1)

    def test_disabled_or_missing_key_never_sends_content(self):
        for settings in (Settings(), Settings(openai_analysis_enabled=True)):
            with patch("app.services.openai_analysis.urlopen") as transport:
                with self.assertRaises(AnalysisUnavailable):
                    OpenAIAnalyzer(settings).analyze("Una entrada.")
                transport.assert_not_called()

    def test_rejects_bad_json_diagnoses_unrestricted_text_and_incomplete_results(self):
        cases = [
            envelope({**VALID, "estimated_stage": "depression"}),
            envelope({**VALID, "advice": "Texto no permitido"}),
            envelope({**VALID, "risk_level": "safe"}),
            {"status": "incomplete", "output": envelope()["output"]},
            {"status": "completed", "output": [{"type": "message", "role": "assistant", "content": [{"type": "refusal"}]}]},
            {"status": "completed", "output": []},
            {"status": "completed", "output": [None]},
        ]
        for value in cases:
            with self.subTest(value=value):
                with patch("app.services.openai_analysis.urlopen", return_value=fake_response(value)):
                    with self.assertRaises(AnalysisUnavailable) as caught:
                        OpenAIAnalyzer(SETTINGS).analyze("Una entrada.")
                    self.assertEqual(caught.exception.status_code, 502)

    def test_provider_errors_are_safe_and_not_retried(self):
        for error in (
            HTTPError("https://api.openai.com", 401, "private-provider-message", {}, io.BytesIO(b"private-provider-body")),
            URLError("private-provider-message"), TimeoutError("private-provider-message"),
        ):
            with patch("app.services.openai_analysis.urlopen", side_effect=error) as transport:
                with self.assertRaises(AnalysisUnavailable) as caught:
                    OpenAIAnalyzer(SETTINGS).analyze("Una entrada.")
                self.assertNotIn("private-provider", str(caught.exception))
                self.assertEqual(transport.call_count, 1)

    def test_oversized_response_is_rejected(self):
        with patch("app.services.openai_analysis.urlopen", return_value=io.BytesIO(b"x" * (MAX_RESPONSE_BYTES + 1))):
            with self.assertRaises(AnalysisUnavailable):
                OpenAIAnalyzer(SETTINGS).analyze("Una entrada.")
