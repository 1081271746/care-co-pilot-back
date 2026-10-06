"""Permite desactivar cuentas y revocar sesiones."""

from alembic import op
import sqlalchemy as sa

revision = "0003_account_sessions"
down_revision = "0002_private_records"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column(
        "is_active", sa.Boolean(), nullable=False, server_default=sa.true(),
    ))
    op.create_table(
        "revoked_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade():
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
    op.drop_column("users", "is_active")
