"""El mismo recorrido de IA controlada sobre migraciones y PostgreSQL real."""

import test_journal_analysis as fixture
import test_postgres_catalog as postgres_fixture


class PostgresAnalysisTests(fixture.JournalAnalysisTests):
    def setUp(self):
        postgres_fixture.PostgresCatalogTests.setUp(self)
        self.configure_analysis()
