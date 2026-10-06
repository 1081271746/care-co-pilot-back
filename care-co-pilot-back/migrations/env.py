"""Configuración Alembic: usa PostgreSQL y la metadata de los modelos."""

from alembic import context

from app.database.connection import create_database_engine
from app.models import Base, User  # noqa: F401 - registra los modelos en metadata

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera SQL sin abrir una conexión a PostgreSQL."""
    engine = create_database_engine()
    try:
        context.configure(
            url=engine.url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    finally:
        engine.dispose()


def run_migrations_online() -> None:
    """Aplica migraciones usando la configuración PostgreSQL de la aplicación."""
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
