"""Pruebas HTTP del aislamiento por propietario en registros privados."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.security import create_access_token
from app.database.connection import get_db
from app.main import create_app
from app.models.base import Base
from app.models.private_record import PrivateRecord
from app.models.user import User

TEST_SECRET = "solo-para-pruebas-" + ("x" * 32)
TEST_SETTINGS = Settings(jwt_secret_key=SecretStr(TEST_SECRET))


class PrivateRecordHttpTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )
        with self.session_factory() as session:
            session.add_all(
                [
                    User(id=1, email="persona-uno@example.test", password_hash="hash"),
                    User(id=2, email="persona-dos@example.test", password_hash="hash"),
                ]
            )
            session.commit()

        self.app = create_app()

        def override_get_db():
            with self.session_factory() as session:
                yield session

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.app.dependency_overrides.clear()
        self.client.close()
        self.engine.dispose()

    def token(self, user_id: str) -> str:
        return create_access_token(user_id, settings=TEST_SETTINGS)

    def request_as(self, user_id: str | None, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        if user_id is not None:
            headers["Authorization"] = f"Bearer {self.token(user_id)}"
        with patch("app.core.security.load_settings", return_value=TEST_SETTINGS):
            return self.client.request(
                method,
                path,
                headers=headers,
                **kwargs,
            )

    def create_record(self, user_id: str = "1", title: str = "Nota privada"):
        return self.request_as(
            user_id,
            "POST",
            "/records",
            json={"title": title, "content": "Contenido confidencial"},
        )

    def test_each_private_route_rejects_missing_or_invalid_jwt(self):
        requests = [
            ("GET", "/records", None),
            ("POST", "/records", {"title": "Nota", "content": "Texto"}),
            ("GET", "/records/1", None),
            ("PATCH", "/records/1", {"content": "Cambio"}),
            ("DELETE", "/records/1", None),
        ]
        for method, path, body in requests:
            with self.subTest(method=method, path=path):
                response = self.request_as(None, method, path, json=body)
                self.assertEqual(response.status_code, 401)

    def test_create_assigns_owner_from_jwt_and_list_filters_by_owner(self):
        created = self.create_record()
        self.assertEqual(created.status_code, 201)
        record_id = created.json()["id"]
        self.assertNotIn("owner_id", created.json())

        owner_records = self.request_as("1", "GET", "/records")
        other_records = self.request_as("2", "GET", "/records")
        self.assertEqual(owner_records.status_code, 200)
        self.assertEqual([record["id"] for record in owner_records.json()], [record_id])
        self.assertEqual(other_records.status_code, 200)
        self.assertEqual(other_records.json(), [])

    def test_client_cannot_choose_a_different_record_owner(self):
        response = self.request_as(
            "1",
            "POST",
            "/records",
            json={
                "title": "Nota",
                "content": "Texto",
                "owner_id": 2,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_owner_can_read_update_and_delete_their_record(self):
        created = self.create_record()
        record_id = created.json()["id"]

        read = self.request_as("1", "GET", f"/records/{record_id}")
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()["content"], "Contenido confidencial")

        updated = self.request_as(
            "1",
            "PATCH",
            f"/records/{record_id}",
            json={"content": "Contenido actualizado"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["content"], "Contenido actualizado")

        deleted = self.request_as("1", "DELETE", f"/records/{record_id}")
        self.assertEqual(deleted.status_code, 204)
        missing = self.request_as("1", "GET", f"/records/{record_id}")
        self.assertEqual(missing.status_code, 404)

    def test_other_owner_get_patch_and_delete_match_missing_record_404(self):
        created = self.create_record()
        record_id = created.json()["id"]
        missing_id = record_id + 1000

        operations = [
            ("GET", None),
            ("PATCH", {"content": "Intento ajeno"}),
            ("DELETE", None),
        ]
        for method, body in operations:
            with self.subTest(method=method):
                foreign = self.request_as(
                    "2",
                    method,
                    f"/records/{record_id}",
                    json=body,
                )
                missing = self.request_as(
                    "2",
                    method,
                    f"/records/{missing_id}",
                    json=body,
                )
                self.assertEqual(foreign.status_code, 404)
                self.assertEqual(missing.status_code, 404)
                self.assertEqual(foreign.json(), missing.json())
                self.assertEqual(
                    foreign.json(),
                    {"detail": "El recurso solicitado no existe."},
                )

        owner_read = self.request_as("1", "GET", f"/records/{record_id}")
        self.assertEqual(owner_read.status_code, 200)
        self.assertEqual(owner_read.json()["content"], "Contenido confidencial")


if __name__ == "__main__":
    unittest.main()
