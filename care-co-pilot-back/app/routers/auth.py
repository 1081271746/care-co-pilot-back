"""Rutas de identidad que requieren un token JWT válido."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import (
    AuthenticationConfigurationError,
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas.auth import AuthenticatedUser, LoginRequest, LoginResponse
from app.schemas.account import AccountResponse, RegisterRequest
from app.services.accounts import DuplicateEmailError, register_account

router = APIRouter(prefix="/auth", tags=["Autenticación"])
bearer_scheme = HTTPBearer(auto_error=False)
INVALID_CREDENTIALS_DETAIL = "Correo o contraseña incorrectos."


@router.post(
    "/register", response_model=AccountResponse, status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    """Crea una cuenta; para obtener JWT se debe iniciar sesión."""
    try:
        user = register_account(db, payload)
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo crear la cuenta con ese correo.",
        ) from None
    return AccountResponse(
        id=str(user.id), email=user.email, created_at=user.created_at,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    """Autentica una cuenta persistida y solo entonces emite un JWT."""
    user = db.scalar(
        select(User).where(func.lower(User.email) == credentials.email)
    )
    password = credentials.password.get_secret_value()
    password_matches = verify_password(
        password,
        user.password_hash if user is not None else None,
    )
    if user is None or not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        access_token = create_access_token(str(user.id))
    except AuthenticationConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación no está configurada.",
        ) from None

    return LoginResponse(access_token=access_token)


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
