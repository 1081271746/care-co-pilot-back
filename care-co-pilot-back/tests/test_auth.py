"""Pruebas de JWT, identidad y autorización por propietario."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt
from pydantic import SecretStr

from app.core.authorization import assert_record_owner
from app.core.config import Settings
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    AuthenticationConfigurationError,
    InvalidAccessTokenError,
    JWT_ALGORITHM,
    JWT_ISSUER,
    create_access_token,
    decode_access_token,
)
from app.routers.auth import get_current_user
from app.schemas.auth import AuthenticatedUser

TEST_SECRET = "solo-para-pruebas-" + ("x" * 32)
TEST_SETTINGS = Settings(jwt_secret_key=SecretStr(TEST_SECRET))


class JwtAuthenticationTests(unittest.TestCase):
    def test_valid_token_identifies_its_user(self):
        token = create_access_token("user-123", settings=TEST_SETTINGS)

        self.assertEqual(decode_access_token(token, settings=TEST_SETTINGS), "user-123")
        with patch("app.core.security.load_settings", return_value=TEST_SETTINGS):
            identity = get_current_user(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            )
        self.assertEqual(identity, AuthenticatedUser(id="user-123"))

    def test_token_signed_with_another_secret_is_invalid(self):
        token = create_access_token("user-123", settings=TEST_SETTINGS)
        other_settings = Settings(jwt_secret_key=SecretStr("y" * 40))

        with self.assertRaises(InvalidAccessTokenError):
            decode_access_token(token, settings=other_settings)

    def test_expired_token_is_invalid(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "user-123",
                "iat": now - timedelta(seconds=10),
                "exp": now - timedelta(seconds=1),
                "iss": JWT_ISSUER,
                "type": ACCESS_TOKEN_TYPE,
            },
            TEST_SECRET,
            algorithm=JWT_ALGORITHM,
        )

        with self.assertRaises(InvalidAccessTokenError):
            decode_access_token(token, settings=TEST_SETTINGS)

    def test_token_creation_rejects_a_nonpositive_duration(self):
        with self.assertRaises(ValueError):
            create_access_token(
                "user-123",
                expires_delta=timedelta(0),
                settings=TEST_SETTINGS,
            )

    def test_invalid_http_token_is_unauthorized(self):
        with patch("app.core.security.load_settings", return_value=TEST_SETTINGS):
            with self.assertRaises(HTTPException) as caught:
                get_current_user(
                    HTTPAuthorizationCredentials(
                        scheme="Bearer",
                        credentials="token-manipulado",
                    )
                )

        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.headers["WWW-Authenticate"], "Bearer")

    def test_missing_http_token_is_unauthorized(self):
        with self.assertRaises(HTTPException) as caught:
            get_current_user(None)

        self.assertEqual(caught.exception.status_code, 401)

    def test_authentication_fails_closed_without_a_configured_secret(self):
        with self.assertRaises(AuthenticationConfigurationError):
            create_access_token("user-123", settings=Settings())

    def test_authentication_rejects_a_short_signing_secret(self):
        weak_settings = Settings(jwt_secret_key=SecretStr("demasiado-corto"))

        with self.assertRaises(AuthenticationConfigurationError):
            create_access_token("user-123", settings=weak_settings)


class RecordOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.current_user = AuthenticatedUser(id="user-123")

    def test_owner_can_access_their_record(self):
        self.assertIsNone(assert_record_owner("user-123", self.current_user))

    def test_another_users_record_is_hidden_as_not_found(self):
        with self.assertRaises(HTTPException) as caught:
            assert_record_owner("user-456", self.current_user)

        self.assertEqual(caught.exception.status_code, 404)
        self.assertEqual(
            caught.exception.detail,
            "El recurso solicitado no existe.",
        )

    def test_record_without_owner_is_not_accessible(self):
        with self.assertRaises(HTTPException) as caught:
            assert_record_owner(None, self.current_user)

        self.assertEqual(caught.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
