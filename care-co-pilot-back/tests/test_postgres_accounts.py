"""Registro, Argon2, usuario actual y logout contra cuentas PostgreSQL reales."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from unittest.mock import patch

from app.core.security import hash_password
from app.database import get_db
from app.main import create_app
from app.models import Base, User
from app.services.catalog_seed import seed_catalog
from postgres_support import PostgresSandbox
import test_login as login_fixture
import test_registration as registration_fixture
import test_sessions as session_fixture


class PostgresAccountTests(
    registration_fixture.RegistrationHttpTests, session_fixture.SessionHttpTests,
):
    def setUp(self):
        self.sandbox = PostgresSandbox(self)
        self.engine = self.sandbox.engine
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False)
        with self.session_factory() as session:
            session.add(User(
                email=login_fixture.TEST_EMAIL,
                password_hash=hash_password(login_fixture.TEST_PASSWORD),
            ))
            session.commit()
        self.app = create_app()

        def database():
            with self.session_factory() as session:
                yield session

        self.app.dependency_overrides[get_db] = database
        self.addCleanup(self.app.dependency_overrides.clear)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_all_migrated_tables_match_current_model_columns(self):
        with self.engine.connect() as connection:
            inspector = inspect(connection)
            for table in Base.metadata.sorted_tables:
                with self.subTest(table=table.name):
                    self.assertEqual(
                        {column["name"] for column in inspector.get_columns(table.name)},
                        set(table.columns.keys()),
                    )

    def test_complete_local_account_journal_exercise_history_logout_flow(self):
        with self.session_factory() as session:
            seed_catalog(session)
        email = "recorrido@example.com"
        password = "Una frase segura para el recorrido completo"
        registered = self.client.post("/auth/register", json={"email": email, "password": password})
        self.assertEqual(registered.status_code, 201)
        with patch("app.core.security.load_settings", return_value=login_fixture.TEST_SETTINGS):
            login = self.client.post("/auth/login", json={"email": email, "password": password})
            self.assertEqual(login.status_code, 200)
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            entry = self.client.post("/journal", json={
                "content": "Hoy quiero guardar un recuerdo importante.",
            }, headers=headers)
            self.assertEqual(entry.status_code, 201)
            entry_id = entry.json()["id"]
            recommendations = self.client.get(
                f"/journal/{entry_id}/recommendations", headers=headers,
            )
            self.assertEqual(recommendations.status_code, 200)
            exercise = recommendations.json()["exercises"][0]
            completed = self.client.post(
                f"/exercises/{exercise['id']}/completions", json={"note": "Terminé"},
                headers=headers,
            )
            self.assertEqual(completed.status_code, 201)
            dashboard = self.client.get("/dashboard", headers=headers).json()
            self.assertEqual(dashboard["journal_entries"], 1)
            self.assertEqual(dashboard["completed_exercises"], 1)
            history = self.client.get("/history?days=1", headers=headers).json()
            self.assertEqual(history["daily"][0]["journal_entries"], 1)
            self.assertEqual(history["daily"][0]["completed_exercises"], 1)
            self.assertEqual(self.client.get("/health/ready").status_code, 200)
            self.assertEqual(self.client.post("/auth/logout", headers=headers).status_code, 204)
            self.assertEqual(self.client.get("/journal", headers=headers).status_code, 401)
