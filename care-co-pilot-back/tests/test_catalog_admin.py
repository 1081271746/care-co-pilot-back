"""Administración HTTP: permisos vigentes, validación y privacidad sin excepciones."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt

import test_private_records as fixture
from app.core.security import create_access_token
from app.models.catalog import Exercise, ExerciseCompletion, Resource
from app.models.user import User
from app.services.account_roles import set_account_role
from app.services.catalog_seed import seed_catalog


class CatalogAdminTests(fixture.PrivateRecordHttpTests):
    def setUp(self):
        super().setUp()
        self.prepare_catalog_admin()

    def prepare_catalog_admin(self):
        with self.session_factory() as db:
            seed_catalog(db)
            set_account_role(db, 2, "admin", confirmed=True)

    def payload(self, collection, slug="contenido-nuevo"):
        body = {
            "slug": slug, "title": "Título", "description": "Descripción",
            "stage": "general",
        }
        if collection == "resources":
            body.update(kind="educational", content="Contenido educativo.")
        else:
            body["instructions"] = ["Respira a tu ritmo.", "Escribe si te resulta útil."]
        return body

    def operations(self):
        for collection in ("resources", "exercises"):
            path = "/admin/" + collection
            yield "GET", path, None
            yield "GET", path + "/1", None
            yield "POST", path, self.payload(collection)
            yield "PATCH", path + "/1", {"title": "Actualización"}
            yield "DELETE", path + "/1", None

    def test_all_admin_routes_require_authentication_and_admin_role(self):
        for method, path, body in self.operations():
            with self.subTest(method=method, path=path):
                self.assertEqual(self.request_as(None, method, path, json=body).status_code, 401)
                self.assertEqual(self.request_as("1", method, path, json=body).status_code, 403)
                self.assertEqual(self.request_as("999", method, path, json=body).status_code, 401)
        with self.session_factory() as db:
            self.assertEqual(db.query(Resource).count(), 6)
            self.assertEqual(db.query(Exercise).count(), 6)
            self.assertTrue(db.get(Exercise, 1).is_active)

    def test_admin_crud_and_inactive_catalog_for_both_collections(self):
        for collection, model in (("resources", Resource), ("exercises", Exercise)):
            path = "/admin/" + collection
            created = self.request_as("2", "POST", path, json=self.payload(collection))
            self.assertEqual(created.status_code, 201, created.text)
            item = created.json()
            item_id = item["id"]
            self.assertTrue(item["is_active"])
            public_path = f"/{collection}/{item_id}"
            public = self.request_as("1", "GET", public_path)
            self.assertEqual(public.status_code, 200)
            self.assertNotIn("is_active", public.json())
            self.assertNotIn("slug", public.json())
            updated = self.request_as("2", "PATCH", f"{path}/{item_id}", json={
                "title": " Nuevo título ", "stage": "anger",
                **({"content": "Nuevo contenido"} if collection == "resources"
                   else {"instructions": [" Nuevo paso "]}),
            })
            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.json()["title"], "Nuevo título")
            self.assertEqual(updated.json()["slug"], item["slug"])
            if collection == "exercises":
                self.assertEqual(updated.json()["instructions"], ["Nuevo paso"])
            self.assertEqual(self.request_as("1", "GET", public_path).json()["stage"], "anger")
            for _ in range(2):
                self.assertEqual(self.request_as("2", "DELETE", f"{path}/{item_id}").status_code, 204)
            for user in ("1", "2"):
                self.assertEqual(self.request_as(user, "GET", public_path).status_code, 404)
                self.assertNotIn(item_id, [
                    row["id"] for row in self.request_as(user, "GET", "/" + collection).json()["items"]
                ])
            inactive = self.request_as("2", "GET", path + "?is_active=false").json()["items"]
            self.assertEqual([row["id"] for row in inactive], [item_id])
            self.assertFalse(self.request_as("2", "GET", f"{path}/{item_id}").json()["is_active"])
            with self.session_factory() as db:
                self.assertIsNotNone(db.get(model, item_id))
            self.assertEqual(self.request_as("2", "PATCH", f"{path}/{item_id}", json={
                "is_active": True,
            }).status_code, 200)
            self.assertEqual(self.request_as("1", "GET", public_path).status_code, 200)
            hidden = self.request_as("2", "POST", path, json={
                **self.payload(collection, "borrador-nuevo"), "is_active": False,
            })
            self.assertEqual(hidden.status_code, 201)
            self.assertEqual(self.request_as("1", "GET", f"/{collection}/{hidden.json()['id']}").status_code, 404)

    def test_duplicate_slugs_and_missing_items(self):
        for collection in ("resources", "exercises"):
            path = "/admin/" + collection
            created = self.request_as("2", "POST", path, json=self.payload(collection))
            item_id = created.json()["id"]
            self.assertEqual(self.request_as("2", "POST", path, json=self.payload(collection)).status_code, 409)
            original = self.request_as("2", "GET", path + "/1").json()
            conflict = self.request_as("2", "PATCH", path + "/1", json={
                "slug": "contenido-nuevo", "title": "No debe persistir",
            })
            self.assertEqual(conflict.status_code, 409)
            self.assertEqual(self.request_as("2", "GET", path + "/1").json(), original)
            self.request_as("2", "DELETE", f"{path}/{item_id}")
            self.assertEqual(self.request_as("2", "POST", path, json=self.payload(collection)).status_code, 409)
            for method, body in (("GET", None), ("PATCH", {"title": "Cambio"}), ("DELETE", None)):
                self.assertEqual(self.request_as("2", method, path + "/99999", json=body).status_code, 404)

    def test_invalid_content_and_mass_assignment_are_rejected(self):
        invalid = [
            {"slug": ""}, {"slug": "Con espacios"}, {"slug": "a" * 101},
            {"title": " "}, {"title": "x" * 201}, {"description": ""},
            {"description": "x" * 5001}, {"stage": "depression"},
            {"stage": None}, {"is_active": "false"}, {"id": 45},
            {"owner_id": 1}, {"role": "admin"}, {"is_admin": True},
        ]
        for collection in ("resources", "exercises"):
            cases = invalid + (
                [{"content": " "}, {"content": "x" * 20001}, {"kind": " "}, {"kind": "x" * 31}]
                if collection == "resources" else
                [{"instructions": []}, {"instructions": [" "]}, {"instructions": "paso"},
                 {"instructions": ["x" * 2001]}, {"instructions": ["paso"] * 31}]
            )
            path = "/admin/" + collection
            for body in cases:
                with self.subTest(collection=collection, body_keys=list(body)):
                    self.assertEqual(self.request_as("2", "POST", path, json={
                        **self.payload(collection), **body,
                    }).status_code, 422)
                    self.assertEqual(self.request_as("2", "PATCH", path + "/1", json=body).status_code, 422)
            for field in self.payload(collection):
                self.assertEqual(self.request_as("2", "PATCH", path + "/1", json={field: None}).status_code, 422)
            self.assertEqual(self.request_as("2", "PATCH", path + "/1", json={}).status_code, 422)
            self.assertEqual(self.request_as("2", "POST", path, json={}).status_code, 422)

    def test_admin_pagination_filters_and_inactive_rows(self):
        for collection in ("resources", "exercises"):
            path = "/admin/" + collection
            self.request_as("2", "DELETE", path + "/1")
            ids = []
            cursor = None
            for _ in range(3):
                params = {"limit": 2}
                if cursor:
                    params["before_id"] = cursor
                page = self.request_as("2", "GET", path, params=params).json()
                ids.extend(item["id"] for item in page["items"])
                cursor = page["next_cursor"]
            self.assertEqual(ids, [6, 5, 4, 3, 2, 1])
            self.assertIsNone(cursor)
            self.assertEqual(len(self.request_as("2", "GET", path + "?is_active=true").json()["items"]), 5)
            stage = self.request_as("2", "GET", path + "?stage=anger").json()["items"]
            self.assertTrue(stage)
            self.assertTrue(all(row["stage"] == "anger" for row in stage))
            for query in ("limit=0", "limit=101", "before_id=0", "stage=unknown", "is_active=unknown"):
                self.assertEqual(self.request_as("2", "GET", path + "?" + query).status_code, 422)

    def test_role_claims_and_public_routes_cannot_elevate_privileges(self):
        claims = jwt.decode(self.token("1"), fixture.TEST_SECRET, algorithms=["HS256"])
        claims.update(role="admin", is_admin=True)
        asserted = jwt.encode(claims, fixture.TEST_SECRET, algorithm="HS256")
        self.assertEqual(self.request_as(None, "POST", "/admin/resources", json=self.payload("resources"),
            headers={"Authorization": "Bearer " + asserted}).status_code, 403)
        for path in ("/auth/register", "/auth/login"):
            self.assertEqual(self.request_as(None, "POST", path, json={
                "email": "person@example.com", "password": "frase-de-prueba-larga", "role": "admin",
            }).status_code, 422)
        for path in ("/auth/me", "/auth/role", "/admin/users/1"):
            self.assertIn(self.request_as("1", "PATCH", path, json={"role": "admin"}).status_code, (404, 405))
        with self.session_factory() as db:
            self.assertEqual(db.get(User, 1).role, "user")

    def test_expired_invalid_revoked_and_inactive_admin_sessions_are_denied(self):
        with patch("app.core.security.datetime") as clock:
            clock.now.return_value = datetime.now(timezone.utc) - timedelta(hours=1)
            expired = create_access_token("2", expires_delta=timedelta(seconds=1), settings=fixture.TEST_SETTINGS)
        for token in (expired, "invalido"):
            for method, path, body in self.operations():
                self.assertEqual(self.request_as(None, method, path, json=body,
                    headers={"Authorization": "Bearer " + token}).status_code, 401)
        token = self.token("2")
        headers = {"Authorization": "Bearer " + token}
        self.assertEqual(self.request_as(None, "POST", "/auth/logout", headers=headers).status_code, 204)
        for method, path, body in self.operations():
            self.assertEqual(self.request_as(None, method, path, json=body, headers=headers).status_code, 401)
        with self.session_factory() as db:
            db.get(User, 2).is_active = False
            db.commit()
        for method, path, body in self.operations():
            self.assertEqual(self.request_as("2", method, path, json=body).status_code, 401)

    def test_demotion_takes_effect_with_an_existing_token(self):
        token = self.token("2")
        with patch("app.core.security.load_settings", return_value=fixture.TEST_SETTINGS):
            headers = {"Authorization": "Bearer " + token}
            self.assertEqual(self.client.get("/admin/resources", headers=headers).status_code, 200)
            with self.session_factory() as db:
                set_account_role(db, 2, "user", confirmed=True)
            for method, path, body in self.operations():
                self.assertEqual(self.client.request(method, path, json=body, headers=headers).status_code, 403)

    def test_admin_has_no_access_to_foreign_notes_or_journals(self):
        record = self.create_record().json()["id"]
        journal_response = self.request_as("1", "POST", "/journal", json={
            "content": "Hoy recuerdo a mi ser querido.",
        })
        self.assertEqual(journal_response.status_code, 201, journal_response.text)
        journal = journal_response.json()["id"]
        completion = self.request_as("1", "POST", "/exercises/1/completions",
            json={"note": "Una nota personal"}).json()["id"]
        for path, update in (
            (f"/records/{record}", {"content": "Cambio"}),
            (f"/journal/{journal}", {"content": "Cambio"}),
            (f"/progress/exercises/{completion}", {"note": "Cambio"}),
        ):
            for method, body in (("GET", None), ("PATCH", update), ("DELETE", None)):
                self.assertEqual(self.request_as("2", method, path, json=body).status_code, 404)
        self.assertEqual(self.request_as("2", "POST", f"/journal/{journal}/analyze",
            json={"consent_to_external_analysis": True}).status_code, 404)
        self.assertEqual(self.request_as("2", "GET", f"/journal/{journal}/recommendations").status_code, 404)
        for path in ("/records", "/journal", "/progress/exercises"):
            self.assertEqual(self.request_as("2", "GET", path).json()["items"], [])
        self.assertEqual(self.request_as("1", "GET", f"/progress/exercises/{completion}").json()["note"], "Una nota personal")

    def test_deactivation_preserves_history_and_seed_respects_changes(self):
        created = self.request_as("1", "POST", "/exercises/1/completions", json={"note": "Nota anterior"})
        self.assertEqual(created.status_code, 201)
        completion = created.json()
        for collection in ("resources", "exercises"):
            self.assertEqual(self.request_as("2", "PATCH", f"/admin/{collection}/1",
                json={"title": "Título editado"}).status_code, 200)
            self.assertEqual(self.request_as("2", "DELETE", f"/admin/{collection}/1").status_code, 204)
        self.assertEqual(self.request_as("1", "POST", "/exercises/1/completions", json={}).status_code, 404)
        with self.session_factory() as db:
            self.assertEqual(seed_catalog(db), {"resources_created": 0, "exercises_created": 0})
            self.assertEqual(db.get(ExerciseCompletion, completion["id"]).exercise_id, 1)
            self.assertEqual(db.get(Exercise, 1).title, "Título editado")
            self.assertFalse(db.get(Exercise, 1).is_active)
            self.assertFalse(db.get(Resource, 1).is_active)
        self.assertEqual(self.request_as("1", "GET", f"/progress/exercises/{completion['id']}").json(), completion)
        self.assertEqual(self.request_as("1", "GET", "/progress/exercises").json()["items"], [completion])

    def test_real_login_and_local_cli_promotion_and_demotion(self):
        registered = self.request_as(None, "POST", "/auth/register", json={
            "email": "operator@example.com", "password": "Una frase de prueba muy larga",
        })
        self.assertEqual(registered.status_code, 201)
        account_id = int(registered.json()["id"])
        login = self.request_as(None, "POST", "/auth/login", json={
            "email": "operator@example.com", "password": "Una frase de prueba muy larga",
        })
        self.assertEqual(login.status_code, 200)
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        self.assertEqual(self.request_as(None, "GET", "/admin/resources", headers=headers).status_code, 403)
        with patch("app.services.account_roles.get_session_factory", return_value=self.session_factory):
            self.assertEqual(main_role_command(account_id, "admin"), 0)
            self.assertEqual(self.request_as(None, "POST", "/admin/resources",
                json=self.payload("resources"), headers=headers).status_code, 201)
            self.assertEqual(main_role_command(account_id, "user"), 0)
        self.assertEqual(self.request_as(None, "GET", "/admin/resources", headers=headers).status_code, 403)

    def test_inactive_content_is_not_recommended(self):
        entry = self.request_as("1", "POST", "/journal", json={
            "content": "Quiero guardar un recuerdo importante.",
        })
        self.assertEqual(entry.status_code, 201)
        path = f"/journal/{entry.json()['id']}/recommendations"
        recommendations = self.request_as("1", "GET", path)
        self.assertEqual(recommendations.status_code, 200)
        for collection in ("resources", "exercises"):
            self.assertTrue(recommendations.json()[collection])
            for item in recommendations.json()[collection]:
                self.assertEqual(self.request_as("2", "DELETE",
                    f"/admin/{collection}/{item['id']}").status_code, 204)
        after = self.request_as("1", "GET", path).json()
        for collection in ("resources", "exercises"):
            inactive_ids = {item["id"] for item in recommendations.json()[collection]}
            self.assertFalse(inactive_ids & {item["id"] for item in after[collection]})


def main_role_command(account_id, role):
    from app.services.account_roles import main
    return main([
        "--account-id", str(account_id), "--role", role, "--confirm-local-role-change",
    ])
