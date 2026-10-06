"""Operación local exclusiva de quien tiene acceso autorizado al servidor y DB."""

import argparse

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.connection import DatabaseConfigurationError, get_session_factory
from app.models.user import User


def set_account_role(
    db: Session, account_id: int, role: str, *, confirmed: bool = False,
) -> None:
    """Sin confirmación local no se aplica ningún cambio; no se expone por HTTP."""
    if not confirmed:
        raise ValueError("Se requiere confirmación explícita del operador local.")
    if account_id < 1 or role not in {"user", "admin"}:
        raise ValueError("Cuenta o rol inválido.")
    user = db.get(User, account_id)
    if user is None or not user.is_active:
        raise ValueError("La cuenta no existe o está inactiva.")
    user.role = role
    db.commit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Cambiar un rol desde el servidor; solo para operadores autorizados.",
    )
    parser.add_argument("--account-id", type=int, required=True)
    parser.add_argument("--role", choices=("user", "admin"), required=True)
    parser.add_argument("--confirm-local-role-change", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        with get_session_factory()() as db:
            set_account_role(
                db, args.account_id, args.role,
                confirmed=args.confirm_local_role_change,
            )
    except (ValueError, DatabaseConfigurationError):
        parser.exit(1, "No se pudo cambiar el rol: revisa cuenta, confirmación y configuración.\n")
    except SQLAlchemyError:
        parser.exit(1, "No se pudo cambiar el rol: revisa conexión y migraciones.\n")
    print("Rol actualizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
