"""Biblioteca e historial probados sobre PostgreSQL aislado."""

import test_catalog as catalog_fixture
import test_postgres_journal as postgres_fixture

from app.services.catalog_seed import seed_catalog


class PostgresCatalogTests(catalog_fixture.CatalogHttpTests):
    def setUp(self):
        postgres_fixture.PostgresJournalTests.setUp(self)
        with self.session_factory() as session:
            seed_catalog(session)
