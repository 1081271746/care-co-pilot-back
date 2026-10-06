"""Pruebas HTTP reales sin dependencias adicionales de pruebas."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import SecretStr

from app.core.config import Settings
from app.core.security import create_access_token

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_JWT_SECRET = "solo-para-pruebas-" + ("x" * 32)


class HealthHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # El sistema elige un puerto libre para no interferir con otros servicios.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]

        cls.base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy()
        environment.update(
            APP_ENV="test",
            APP_NAME="API de prueba",
            JWT_SECRET_KEY=TEST_JWT_SECRET,
        )
        cls.server = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", str(port),
                "--log-level", "warning",
            ],
            cwd=BACKEND_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        cls.addClassCleanup(cls.stop_server)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if cls.server.poll() is not None:
                output = cls.server.stdout.read()
                raise RuntimeError(f"Uvicorn no pudo iniciar:\n{output}")
            try:
                with urlopen(f"{cls.base_url}/health", timeout=1) as response:
                    if response.status == 200:
                        return
            except (URLError, TimeoutError):
                time.sleep(0.1)
        raise RuntimeError("La API no respondió dentro del tiempo de espera.")

    @classmethod
    def stop_server(cls):
        if cls.server.poll() is None:
            cls.server.terminate()
        try:
            cls.server.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.communicate()

    def test_health_returns_ok(self):
        with urlopen(f"{self.base_url}/health", timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("application/json", response.headers["Content-Type"])
            self.assertEqual(json.load(response), {"status": "ok"})

    def test_openapi_documents_health(self):
        with urlopen(f"{self.base_url}/openapi.json", timeout=2) as response:
            specification = json.load(response)
        self.assertEqual(specification["info"]["title"], "API de prueba")
        self.assertIn("get", specification["paths"]["/health"])

    def test_swagger_is_available(self):
        with urlopen(f"{self.base_url}/docs", timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("swagger-ui", response.read().decode())

    def test_unknown_route_returns_404(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(f"{self.base_url}/ruta-inexistente", timeout=2)
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()

    def test_auth_me_returns_identity_for_a_valid_token(self):
        token = create_access_token(
            "user-123",
            settings=Settings(jwt_secret_key=SecretStr(TEST_JWT_SECRET)),
        )
        request = Request(
            f"{self.base_url}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        with urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response), {"id": "user-123"})

    def test_auth_me_rejects_missing_and_invalid_tokens(self):
        for headers in ({}, {"Authorization": "Bearer token-manipulado"}):
            with self.subTest(headers=headers):
                request = Request(f"{self.base_url}/auth/me", headers=headers)
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=2)
                self.assertEqual(caught.exception.code, 401)
                self.assertEqual(caught.exception.headers["www-authenticate"], "Bearer")
                caught.exception.close()


if __name__ == "__main__":
    unittest.main()
