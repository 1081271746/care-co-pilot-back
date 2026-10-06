"""El rol del catálogo no concede acceso a información privada ajena."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import get_active_user
from app.schemas.auth import AuthenticatedUser


def get_catalog_admin(
    current: Annotated[AuthenticatedUser, Depends(get_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthenticatedUser:
    # Consultar la cuenta vigente, no un claim de rol aportado por el cliente.
    user = db.get(User, int(current.id))
    if user is None or user.role != "admin":
        raise HTTPException(status_code=403, detail="Se requiere el rol administrador.")
    return current
