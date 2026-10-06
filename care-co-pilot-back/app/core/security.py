"""Creación y validación de tokens JWT para identidades autenticadas."""

from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import SecretStr

from app.core.config import Settings, load_settings

JWT_ALGORITHM = "HS256"
JWT_ISSUER = "care-co-pilot-back"
ACCESS_TOKEN_TYPE = "access"
DEFAULT_ACCESS_TOKEN_DURATION = timedelta(minutes=30)
MINIMUM_SECRET_LENGTH = 32


class AuthenticationConfigurationError(RuntimeError):
    """La configuración de autenticación está ausente o no es segura."""


class InvalidAccessTokenError(ValueError):
    """El token está vencido, malformado o no es válido para esta API."""


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
