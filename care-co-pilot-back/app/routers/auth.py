"""Rutas de identidad que requieren un token JWT válido."""

from typing import Annotated
from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    AuthenticationConfigurationError,
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    decode_access_claims,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.models.revoked_token import RevokedToken
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
    if user is None or not password_matches or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.password_hash.startswith("$argon2"):
        user.password_hash = hash_password(password)
        db.commit()

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


def get_active_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthenticatedUser:
    """Exige una cuenta vigente y una sesión que no se haya cerrado."""
    try:
        user_id = int(current_user.id)
    except (ValueError, TypeError):
        user_id = 0
    user = db.get(User, user_id) if user_id > 0 else None
    digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    if (
        user is None or not user.is_active or str(user.id) != current_user.id
        or db.get(RevokedToken, digest) is not None
    ):
        raise HTTPException(
            status_code=401, detail="Se requiere un token de acceso válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


@router.get("/me", response_model=AccountResponse)
def read_current_user(
    current_user: Annotated[AuthenticatedUser, Depends(get_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountResponse:
    """Devuelve solo los datos públicos de la cuenta persistida actual."""
    user = db.get(User, int(current_user.id))
    return AccountResponse(id=str(user.id), email=user.email, created_at=user.created_at)


@router.post("/logout", status_code=204)
def logout(
    current_user: Annotated[AuthenticatedUser, Depends(get_active_user)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Revoca el JWT actual; otras sesiones del usuario siguen funcionando."""
    claims = decode_access_claims(credentials.credentials)
    digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at <= datetime.now(timezone.utc)))
    db.add(RevokedToken(
        token_hash=digest, expires_at=datetime.fromtimestamp(claims["exp"], timezone.utc),
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.get(RevokedToken, digest) is None:
            raise
    return Response(status_code=204)
