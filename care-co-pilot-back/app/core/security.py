"""Creación y validación de tokens JWT para identidades autenticadas."""

import base64
import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import SecretStr

from app.core.config import Settings, load_settings

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "care-co-pilot-back"
ACCESS_TOKEN_TYPE = "access"
DEFAULT_ACCESS_TOKEN_DURATION = timedelta(minutes=30)
MINIMUM_SECRET_LENGTH = 32
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_SALT_LENGTH = 16
PASSWORD_DERIVED_KEY_LENGTH = 32
MINIMUM_ACCEPTED_PASSWORD_HASH_ITERATIONS = 100_000
MAXIMUM_ACCEPTED_PASSWORD_HASH_ITERATIONS = 1_000_000


class AuthenticationConfigurationError(RuntimeError):
    """La configuración de autenticación está ausente o no es segura."""


class InvalidAccessTokenError(ValueError):
    """El token está vencido, malformado o no es válido para esta API."""


def hash_password(password: str) -> str:
    """Almacena una contraseña con PBKDF2-HMAC-SHA256 y sal aleatoria."""
    if not isinstance(password, str) or not password:
        raise ValueError("La contraseña no puede estar vacía.")

    salt = secrets.token_bytes(PASSWORD_SALT_LENGTH)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
        dklen=PASSWORD_DERIVED_KEY_LENGTH,
    )
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    encoded_key = base64.urlsafe_b64encode(derived_key).decode("ascii").rstrip("=")
    return (
        f"{PASSWORD_HASH_ALGORITHM}${PASSWORD_HASH_ITERATIONS}"
        f"${encoded_salt}${encoded_key}"
    )


def verify_password(password: str, encoded_hash: str | None) -> bool:
    """Compara contraseñas y simula el coste de hash si no hay cuenta."""
    if not isinstance(password, str):
        return False

    has_stored_hash = isinstance(encoded_hash, str) and bool(encoded_hash)
    hash_to_verify = encoded_hash if has_stored_hash else _DUMMY_PASSWORD_HASH
    try:
        (
            algorithm,
            raw_iterations,
            raw_salt,
            raw_expected_key,
        ) = hash_to_verify.split("$")
        iterations = int(raw_iterations)
        if (
            algorithm != PASSWORD_HASH_ALGORITHM
            or not MINIMUM_ACCEPTED_PASSWORD_HASH_ITERATIONS
            <= iterations
            <= MAXIMUM_ACCEPTED_PASSWORD_HASH_ITERATIONS
        ):
            return False

        salt = _decode_urlsafe_base64(raw_salt)
        expected_key = _decode_urlsafe_base64(raw_expected_key)
        if (
            len(salt) != PASSWORD_SALT_LENGTH
            or len(expected_key) != PASSWORD_DERIVED_KEY_LENGTH
        ):
            return False

        actual_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=PASSWORD_DERIVED_KEY_LENGTH,
        )
    except (ValueError, UnicodeEncodeError, binascii.Error):
        return False

    return has_stored_hash and hmac.compare_digest(actual_key, expected_key)


def _decode_urlsafe_base64(value: str) -> bytes:
    padded_value = value + "=" * (-len(value) % 4)
    return base64.b64decode(padded_value, altchars=b"-_", validate=True)


# Usado para que una cuenta inexistente también realice una verificación costosa.
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def _signing_key(settings: Settings | None = None) -> str:
    configured_settings = settings or load_settings()
    secret: SecretStr | None = configured_settings.jwt_secret_key
    if secret is None:
        raise AuthenticationConfigurationError(
            "JWT_SECRET_KEY no está configurada en el entorno."
        )

    value = secret.get_secret_value()
    if (
        len(value.encode("utf-8")) < MINIMUM_SECRET_LENGTH
        or not value.strip()
    ):
        raise AuthenticationConfigurationError(
            "JWT_SECRET_KEY debe tener al menos 32 bytes aleatorios."
        )
    return value


def create_access_token(
    user_id: str,
    expires_delta: timedelta | None = None,
    *,
    settings: Settings | None = None,
) -> str:
    """Firma un token de acceso; llamar solo después de autenticar la cuenta."""
    subject = user_id.strip()
    if not subject or len(subject) > 128:
        raise ValueError("El identificador del usuario debe tener de 1 a 128 caracteres.")

    now = datetime.now(timezone.utc)
    duration = (
        expires_delta
        if expires_delta is not None
        else DEFAULT_ACCESS_TOKEN_DURATION
    )
    if duration <= timedelta(0):
        raise ValueError("La duración del token debe ser positiva.")
    claims = {
        "sub": subject,
        "iat": now,
        "exp": now + duration,
        "iss": JWT_ISSUER,
        "type": ACCESS_TOKEN_TYPE,
    }
    return jwt.encode(claims, _signing_key(settings), algorithm=JWT_ALGORITHM)


def decode_access_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> str:
    """Valida firma, algoritmo, emisor, uso y expiración; devuelve el subject."""
    try:
        claims = jwt.decode(
            token,
            _signing_key(settings),
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub", "type"]},
        )
    except AuthenticationConfigurationError:
        raise
    except InvalidTokenError:
        raise InvalidAccessTokenError("El token de acceso no es válido.") from None

    subject = claims.get("sub")
    if claims.get("type") != ACCESS_TOKEN_TYPE or not isinstance(subject, str):
        raise InvalidAccessTokenError("El token de acceso no es válido.")
    subject = subject.strip()
    if not subject:
        raise InvalidAccessTokenError("El token de acceso no es válido.")
    return subject
