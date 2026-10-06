"""Rutas de identidad que requieren un token JWT válido."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import (
    AuthenticationConfigurationError,
    InvalidAccessTokenError,
    decode_access_token,
)
from app.schemas.auth import AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["Autenticación"])
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthenticatedUser:
    """Identifica al usuario desde un bearer token verificado."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un token de acceso válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidAccessTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un token de acceso válido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except AuthenticationConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación no está configurada.",
        ) from None

    return AuthenticatedUser(id=user_id)


@router.get("/me", response_model=AuthenticatedUser)
def read_current_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Devuelve la identidad asociada al token sin exponer datos personales."""
    return current_user
