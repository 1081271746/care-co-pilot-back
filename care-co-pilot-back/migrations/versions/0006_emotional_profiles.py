"""Preferencias voluntarias de acompañamiento de cada persona."""

from alembic import op
import sqlalchemy as sa

revision = "0006_emotional_profiles"
down_revision = "0005_catalog_progress"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "emotional_profiles",
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("accompaniment_goal", sa.String(500), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("emotional_profiles")
