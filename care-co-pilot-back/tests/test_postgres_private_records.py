"""Mismos contratos HTTP, pero sobre PostgreSQL migrado (no create_all)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database.connection import get_db, create_session_factory
from app.main import create_app
from app.models.private_record import PrivateRecord
from app.models.user import User
from postgres_support import PostgresSandbox
import test_private_records as fast_tests


class PostgresPrivateRecordHttpTests(fast_tests.PrivateRecordHttpTests):
    """Hereda todos los contratos rápidos sin cambiar sus pruebas SQLite."""

    def setUp(self):
        sandbox = PostgresSandbox(self)
        self.engine = sandbox.engine
        self.session_factory = create_session_factory(self.engine)
        with self.session_factory() as session:
            session.add_all([
                User(id=1, email="uno@example.test", password_hash="hash"),
                User(id=2, email="dos@example.test", password_hash="hash"),
            ])
            session.commit()
        # No leer configuración de la aplicación (ni su archivo .env).
        with patch("app.main.load_settings", return_value=fast_tests.TEST_SETTINGS):
            self.app = create_app()

        def override_get_db():
            with self.session_factory() as session:
                yield session

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)
        self.addCleanup(self.cleanup)

    def test_both_owners_complete_crud_without_affecting_each_other(self):
        ids = {}
        for owner in ("1", "2"):
            created = self.create_record(owner, title=f"Nota de {owner}")
            self.assertEqual(created.status_code, 201)
            ids[owner] = created.json()["id"]
            self.assertNotIn("owner_id", created.json())

        for owner, other in (("1", "2"), ("2", "1")):
            with self.subTest(owner=owner):
                listed = self.request_as(owner, "GET", "/records")
                self.assertEqual(listed.status_code, 200)
                self.assertEqual(
                    [r["id"] for r in listed.json()["items"]], [ids[owner]],
                )
                for method, payload in (
                    ("GET", None),
                    ("PATCH", {"content": "Intento ajeno"}),
                    ("DELETE", None),
                ):
                    foreign = self.request_as(
                        owner, method, f"/records/{ids[other]}", json=payload,
                    )
                    missing = self.request_as(
                        owner, method, "/records/999999", json=payload,
                    )
                    self.assertEqual(foreign.status_code, 404)
                    self.assertEqual(missing.status_code, 404)
                    self.assertEqual(foreign.content, missing.content)
                    self.assertEqual(dict(foreign.headers), dict(missing.headers))
                read = self.request_as(owner, "GET", f"/records/{ids[owner]}")
                self.assertEqual(read.status_code, 200)
                self.assertEqual(read.json()["content"], "Contenido confidencial")
                updated = self.request_as(
                    owner, "PATCH", f"/records/{ids[owner]}",
                    json={"content": f"Actualizado por {owner}"},
                )
                self.assertEqual(updated.status_code, 200)
                self.assertEqual(updated.json()["content"], f"Actualizado por {owner}")

        with self.session_factory() as session:
            for owner, record_id in ids.items():
                record = session.get(PrivateRecord, record_id)
                self.assertEqual(record.owner_id, int(owner))
                self.assertEqual(record.content, f"Actualizado por {owner}")

        for owner, other in (("1", "2"), ("2", "1")):
            deleted = self.request_as(owner, "DELETE", f"/records/{ids[owner]}")
            self.assertEqual(deleted.status_code, 204)
            self.assertEqual(deleted.content, b"")
            self.assertEqual(
                self.request_as(owner, "GET", "/records").json(),
                {"items": [], "limit": 20, "offset": 0, "has_more": False},
            )
            self.assertEqual(
                self.request_as(owner, "GET", f"/records/{ids[owner]}").status_code,
                404,
            )
            if owner == "1":
                self.assertEqual(
                    self.request_as(other, "GET", f"/records/{ids[other]}").status_code,
                    200,
                )
