"""Crea registros privados asociados a su dueño."""

from alembic import op
import sqlalchemy as sa

revision = "0002_private_records"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crea la tabla y el índice que facilitan filtrar por propietario."""
    op.create_table(
        "private_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_private_records_owner_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_private_records_owner_id",
        "private_records",
        ["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    """Elimina la tabla de registros privados y su índice."""
    op.drop_index("ix_private_records_owner_id", table_name="private_records")
    op.drop_table("private_records")
