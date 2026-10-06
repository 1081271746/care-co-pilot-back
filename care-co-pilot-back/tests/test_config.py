import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.core.config import load_settings


class SettingsTests(unittest.TestCase):
    def test_reads_dotenv_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "APP_NAME=Nombre desde archivo\nAPP_ENV=test\n",
                encoding="utf-8",
            )
            with patch("app.core.config.BACKEND_ROOT", root):
                with patch.dict(os.environ, {}, clear=True):
                    settings = load_settings()

        self.assertEqual(settings.app_name, "Nombre desde archivo")
        self.assertEqual(settings.app_env, "test")

    def test_environment_has_priority_over_dotenv(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "APP_NAME=Nombre desde archivo\nAPP_ENV=production\n",
                encoding="utf-8",
            )
            with patch("app.core.config.BACKEND_ROOT", root):
                with patch.dict(
                    os.environ,
                    {"APP_NAME": "Nombre desde entorno", "APP_ENV": "test"},
                    clear=True,
                ):
                    settings = load_settings()

        self.assertEqual(settings.app_name, "Nombre desde entorno")
        self.assertEqual(settings.app_env, "test")

    def test_reads_environment_variables(self):
        with patch.dict(
            os.environ,
            {"APP_NAME": "Backend de prueba", "APP_ENV": "test"},
        ):
            settings = load_settings()

        self.assertEqual(settings.app_name, "Backend de prueba")
        self.assertEqual(settings.app_env, "test")

    def test_rejects_unknown_environment(self):
        with patch.dict(os.environ, {"APP_ENV": "desconocido"}):
            with self.assertRaises(ValidationError):
                load_settings()

    def test_rejects_empty_application_name(self):
        with patch.dict(os.environ, {"APP_NAME": "", "APP_ENV": "test"}):
            with self.assertRaises(ValidationError):
                load_settings()


if __name__ == "__main__":
    unittest.main()
