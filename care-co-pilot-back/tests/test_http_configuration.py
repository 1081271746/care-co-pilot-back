"""CORS, errores seguros, no-caché y disponibilidad del esquema."""

from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import test_private_records as fixture
from app.core.config import Settings
from app.database import get_db


class HttpConfigurationTests(fixture.PrivateRecordHttpTests):
    def test_angular_preflight_accepts_only_configured_origin(self):
        for origin, expected in (
            ("http://localhost:4200", 200), ("https://sitio-ajeno.example", 400),
        ):
            response = self.client.options(
                "/journal", headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            )
            self.assertEqual(response.status_code, expected)
            if expected == 200:
                self.assertEqual(response.headers["access-control-allow-origin"], origin)
            else:
                self.assertNotIn("access-control-allow-origin", response.headers)

    def test_cors_does_not_accept_wildcards_or_url_credentials(self):
        for origin in ("*", "https://*.example.com", "https://example.com/path", "https://user:pass@example.com"):
            with self.assertRaises(ValidationError):
                Settings(cors_origins=[origin])

    def test_auth_and_private_responses_cannot_be_cached(self):
        for path in ("/auth/me", "/journal", "/profile", "/history"):
            response = self.request_as("1", "GET", path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_database_exceptions_do_not_expose_connection_details(self):
        def broken_database():
            raise OperationalError("private statement", {}, RuntimeError("private credentials"))
            yield

        self.app.dependency_overrides[get_db] = broken_database
        response = self.request_as("1", "GET", "/journal")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text)

    def test_ready_endpoint_checks_migrations_and_does_not_create_tables(self):
        with patch("app.core.security.load_settings", return_value=fixture.TEST_SETTINGS):
            self.assertEqual(self.client.get("/health/ready").status_code, 200)
            with self.engine.begin() as connection:
                connection.execute(text("DROP TABLE emotional_profiles"))
            response = self.client.get("/health/ready")
            self.assertEqual(response.status_code, 503)
            self.assertIn("esquema", response.json()["detail"])
        self.assertEqual(self.client.get("/health").status_code, 200)
