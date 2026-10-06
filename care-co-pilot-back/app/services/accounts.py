"""Persistencia de cuentas y manejo de correos duplicados."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.account import RegisterRequest


class DuplicateEmailError(ValueError):
    """El correo normalizado ya pertenece a una cuenta."""


def find_account_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.casefold()))


def register_account(db: Session, payload: RegisterRequest) -> User:
    email = str(payload.email).casefold()
    if find_account_by_email(db, email) is not None:
        raise DuplicateEmailError()
    user = User(
        email=email,
        password_hash=hash_password(payload.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # La restricción UNIQUE cubre registros simultáneos del mismo correo.
        if find_account_by_email(db, email) is not None:
            raise DuplicateEmailError() from None
        raise
    db.refresh(user)
    return user
