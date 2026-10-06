"""Fuentes y coberturas explícitas; no se inventa la ubicación del usuario."""

import test_private_records as fixture
from app.services.safety import review_safety


class EmergencyResourceTests(fixture.PrivateRecordHttpTests):
    def test_public_help_includes_verified_colombian_numbers(self):
        response = self.client.get("/help")
        self.assertEqual(response.status_code, 200)
        resources = response.json()["resources"]
        self.assertTrue(response.json()["country_specific_numbers_configured"])
        self.assertEqual([item["phone"] for item in resources[:2]], ["123", "106"])
        self.assertIn("policia.gov.co", resources[0]["url"])
        self.assertIn("minsalud.gov.co", resources[1]["url"])
        self.assertIn("Bogotá", resources[2]["coverage"])
        self.assertIn("no nacional", resources[2]["coverage"])
        self.assertTrue(resources[0]["verified_on"])

    def test_other_countries_do_not_receive_colombian_numbers(self):
        response = self.client.get("/help?country_code=us")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["country_specific_numbers_configured"])
        self.assertTrue(all(item["phone"] is None for item in response.json()["resources"]))
        self.request_as("1", "PATCH", "/profile", json={"country_code": "US"})
        entry = self.request_as("1", "POST", "/journal", json={"content": "quiero morir"}).json()
        self.assertTrue(all(item["phone"] is None for item in entry["safety_result"]["resources"]))

    def test_crisis_help_shows_emergency_first(self):
        result = review_safety("quiero hacerme daño")
        self.assertEqual(result.resources[0].phone, "123")
        self.assertEqual(result.resources[1].phone, "106")
