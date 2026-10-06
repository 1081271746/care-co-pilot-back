"""Las guardas de PostgreSQL se prueban sin abrir ninguna conexión."""

import unittest

from postgres_support import validate_test_url


class PostgresSafetyTests(unittest.TestCase):
    def configuration(self, **overrides):
        return {
            "APP_ENV": "test",
            "TEST_POSTGRES_ALLOW_MIGRATIONS": "1",
            "TEST_DATABASE_URL": "postgresql://localhost/copilot_test",
            **overrides,
        }

    def test_accepts_only_explicit_local_test_configuration(self):
        for host in ("localhost", "127.0.0.1", "[::1]"):
            with self.subTest(host=host):
                url = validate_test_url(self.configuration(
                    TEST_DATABASE_URL=f"postgresql://{host}/copilot_test",
                ))
                self.assertEqual(url.drivername, "postgresql+psycopg")

    def test_rejects_unsafe_configuration_without_exposing_credentials(self):
        cases = [
            {"APP_ENV": "production"},
            {"APP_ENV": "development"},
            {"TEST_POSTGRES_ALLOW_MIGRATIONS": "0"},
            {"TEST_DATABASE_URL": ""},
            {"TEST_DATABASE_URL": "not-a-url"},
            {"TEST_DATABASE_URL": "sqlite:///copilot_test"},
            {"TEST_DATABASE_URL": "postgresql://remote.example/copilot_test"},
            {"TEST_DATABASE_URL": "postgresql://localhost/copilot"},
            {"TEST_DATABASE_URL": "postgresql://localhost/copilot_test?host=remote"},
            {"TEST_DATABASE_URL": "postgresql://localhost/copilot_test?options=x"},
            {"TEST_DATABASE_URL": "postgresql://user:sentinel@remote/copilot_test"},
        ]
        for overrides in cases:
            with self.subTest(case=list(overrides)):
                with self.assertRaises(ValueError) as error:
                    validate_test_url(self.configuration(**overrides))
                self.assertNotIn("sentinel", str(error.exception))

    def test_never_falls_back_to_application_database(self):
        with self.assertRaises(ValueError):
            validate_test_url({
                "APP_ENV": "test",
                "TEST_POSTGRES_ALLOW_MIGRATIONS": "1",
                "DATABASE_URL": "postgresql://localhost/production",
            })
