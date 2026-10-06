"""Biblioteca persistente, filtros y progreso privado por usuario."""

import test_private_records as fixture

from app.models.catalog import Exercise, Resource
from app.services.catalog_seed import seed_catalog


class CatalogHttpTests(fixture.PrivateRecordHttpTests):
    def setUp(self):
        super().setUp()
        with self.session_factory() as session:
            seed_catalog(session)

    def test_seed_is_idempotent_and_catalog_is_persisted(self):
        with self.session_factory() as session:
            result = seed_catalog(session)
            self.assertEqual(result, {"resources_created": 0, "exercises_created": 0})
            self.assertEqual(session.query(Resource).count(), 6)
            self.assertEqual(session.query(Exercise).count(), 6)
        for path in ("/resources", "/exercises"):
            response = self.request_as("1", "GET", path + "?stage=anger")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["items"]), 1)
            self.assertEqual(response.json()["items"][0]["stage"], "anger")
            self.assertEqual(self.request_as(None, "GET", path).status_code, 401)

    def test_inactive_resources_and_exercises_are_hidden(self):
        with self.session_factory() as session:
            session.get(Resource, 1).is_active = False
            session.get(Exercise, 1).is_active = False
            session.commit()
        for path in ("/resources", "/exercises"):
            self.assertEqual(self.request_as("1", "GET", f"{path}/1").status_code, 404)
            response = self.request_as("1", "GET", path).json()
            self.assertNotIn(1, [item["id"] for item in response["items"]])
        self.assertEqual(self.request_as("1", "POST", "/exercises/1/completions", json={}).status_code, 404)

    def test_exercise_completion_crud_is_private(self):
        created = self.request_as("1", "POST", "/exercises/1/completions", json={"note": "Mi nota"})
        self.assertEqual(created.status_code, 201)
        completion = created.json()
        self.assertNotIn("owner_id", completion)
        self.assertEqual(self.request_as("2", "GET", "/progress/exercises").json()["items"], [])
        for method, body in (("GET", None), ("PATCH", {"note": "Ajeno"}), ("DELETE", None)):
            path = f"/progress/exercises/{completion['id']}"
            foreign = self.request_as("2", method, path, json=body)
            missing = self.request_as("2", method, "/progress/exercises/9999", json=body)
            self.assertEqual(foreign.status_code, 404)
            self.assertEqual(foreign.json(), missing.json())
        updated = self.request_as("1", "PATCH", f"/progress/exercises/{completion['id']}", json={"note": ""})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["note"], "")
        self.assertEqual(self.request_as("1", "DELETE", f"/progress/exercises/{completion['id']}").status_code, 204)
        self.assertEqual(self.request_as("1", "GET", "/progress/exercises").json()["items"], [])

    def test_client_cannot_assign_completion_owner(self):
        response = self.request_as("1", "POST", "/exercises/1/completions", json={"owner_id": 2})
        self.assertEqual(response.status_code, 422)
