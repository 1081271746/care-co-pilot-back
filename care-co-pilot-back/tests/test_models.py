"""Pruebas del mapeo ORM mínimo del primer flujo."""

import unittest

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, inspect
from sqlalchemy.orm import configure_mappers

from app.models import Base, User


class UserModelTests(unittest.TestCase):
    def test_user_maps_only_the_initial_account_fields(self):
        configure_mappers()
        mapper = inspect(User)

        self.assertIs(mapper.registry, Base.registry)
        self.assertEqual(User.__tablename__, "users")
        self.assertEqual(
            set(mapper.columns.keys()),
            {"id", "email", "password_hash", "created_at"},
        )
        self.assertIsInstance(User.__table__.c.id.type, Integer)
        self.assertIsInstance(User.__table__.c.email.type, String)
        self.assertEqual(User.__table__.c.email.type.length, 320)
        self.assertIsInstance(User.__table__.c.password_hash.type, String)
        self.assertEqual(User.__table__.c.password_hash.type.length, 255)
        self.assertIsInstance(User.__table__.c.created_at.type, DateTime)
        self.assertTrue(User.__table__.c.created_at.type.timezone)

    def test_email_is_required_and_unique_and_created_at_has_a_server_default(self):
        email = User.__table__.c.email
        created_at = User.__table__.c.created_at
        unique_constraints = {
            constraint.name
            for constraint in User.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }

        self.assertFalse(email.nullable)
        self.assertFalse(User.__table__.c.password_hash.nullable)
        self.assertIn("uq_users_email", unique_constraints)
        self.assertFalse(created_at.nullable)
        self.assertIsNotNone(created_at.server_default)


if __name__ == "__main__":
    unittest.main()
