"""Perfil e historial con agrupación de fechas real sobre PostgreSQL."""

import test_accompaniment as fixture
import test_postgres_catalog as postgres_fixture


class PostgresAccompanimentTests(fixture.AccompanimentHttpTests):
    def setUp(self):
        postgres_fixture.PostgresCatalogTests.setUp(self)
