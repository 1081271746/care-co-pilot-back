"""El diario usa PostgreSQL migrado real, aislado y desechable."""

from sqlalchemy.orm import sessionmaker

from postgres_support import PostgresSandbox
from test_journal import JournalHttpTests
from app.models.user import User
from app.main import create_app
from app.database import get_db
from fastapi.testclient import TestClient


class PostgresJournalTests(JournalHttpTests):
    def setUp(self):
        sandbox = PostgresSandbox(self)
        self.engine = sandbox.engine
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False)
        with self.session_factory() as session:
            session.add_all([
                User(id=1, email="uno@example.test", password_hash="hash"),
                User(id=2, email="dos@example.test", password_hash="hash"),
            ])
            session.commit()
        self.app = create_app()

        def database():
            with self.session_factory() as session:
                yield session

        self.app.dependency_overrides[get_db] = database
        self.addCleanup(self.app.dependency_overrides.clear)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
