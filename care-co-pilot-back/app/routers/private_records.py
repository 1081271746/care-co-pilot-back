"""Rutas autenticadas para crear y administrar registros privados."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.private_record import PrivateRecord
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.private_record import (
    DEFAULT_RECORD_LIMIT,
    MAX_RECORD_LIMIT,
    PrivateRecordCreate,
    PrivateRecordPage,
    PrivateRecordResponse,
    PrivateRecordUpdate,
)

router = APIRouter(prefix="/records", tags=["Registros privados"])


def _owner_id(current_user: AuthenticatedUser, db: Session) -> int:
    """Resuelve la identidad del JWT a una cuenta persistida."""
    try:
        owner_id = int(current_user.id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La identidad del token no es válida.",
        ) from None

    if owner_id <= 0 or db.get(User, owner_id) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La identidad del token no es válida.",
        )
    return owner_id


def _record_not_found() -> HTTPException:
    """Usa una respuesta idéntica para registros ausentes o de otro usuario."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="El recurso solicitado no existe.",
    )


def _get_owned_record(
    db: Session,
    record_id: int,
    owner_id: int,
) -> PrivateRecord:
    """Busca por identificador y dueño en la misma consulta."""
    record = db.scalar(
        select(PrivateRecord).where(
            PrivateRecord.id == record_id,
            PrivateRecord.owner_id == owner_id,
        )
    )
    if record is None:
        raise _record_not_found()
    return record


@router.post(
    "",
    response_model=PrivateRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_record(
    payload: PrivateRecordCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PrivateRecord:
    """Crea un registro asignando siempre el dueño desde el JWT."""
    record = PrivateRecord(
        owner_id=_owner_id(current_user, db),
        title=payload.title,
        content=payload.content,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=PrivateRecordPage)
def list_records(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=MAX_RECORD_LIMIT)] = DEFAULT_RECORD_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PrivateRecordPage:
    """Pagina solo los registros propios, con desempate estable por ID."""
    owner_id = _owner_id(current_user, db)
    records = list(
        db.scalars(
            select(PrivateRecord)
            .where(PrivateRecord.owner_id == owner_id)
            .order_by(PrivateRecord.created_at.desc(), PrivateRecord.id.desc())
            .offset(offset)
            .limit(limit + 1)
        ).all()
    )
    return PrivateRecordPage(
        items=records[:limit],
        limit=limit,
        offset=offset,
        has_more=len(records) > limit,
    )


@router.get("/{record_id}", response_model=PrivateRecordResponse)
def read_record(
    record_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PrivateRecord:
    """Lee un registro solo cuando pertenece al usuario autenticado."""
    owner_id = _owner_id(current_user, db)
    return _get_owned_record(db, record_id, owner_id)


@router.patch("/{record_id}", response_model=PrivateRecordResponse)
def update_record(
    record_id: int,
    payload: PrivateRecordUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PrivateRecord:
    """Actualiza campos solo después de filtrar por registro y propietario."""
    owner_id = _owner_id(current_user, db)
    record = _get_owned_record(db, record_id, owner_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Elimina únicamente registros que pertenecen al usuario autenticado."""
    owner_id = _owner_id(current_user, db)
    record = _get_owned_record(db, record_id, owner_id)
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
