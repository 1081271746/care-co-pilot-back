"""Comprobaciones reutilizables de propiedad para rutas con datos personales."""

from fastapi import HTTPException, status

from app.schemas.auth import AuthenticatedUser


def assert_record_owner(
    record_owner_id: str | None,
    current_user: AuthenticatedUser,
) -> None:
    """Oculta registros inexistentes y ajenos usando la misma respuesta 404."""
    if record_owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El recurso solicitado no existe.",
        )
