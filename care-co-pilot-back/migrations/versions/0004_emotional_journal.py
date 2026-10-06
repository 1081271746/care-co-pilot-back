"""Diario con señales de riesgo y resultados de análisis separados."""

from alembic import op
import sqlalchemy as sa

revision = "0004_emotional_journal"
down_revision = "0003_account_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False),
        sa.Column("safety_result", sa.JSON(), nullable=False),
        sa.Column("analysis_status", sa.String(30), nullable=False),
        sa.Column("estimated_stage", sa.String(30), nullable=True),
        sa.Column("analysis_result", sa.JSON(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_journal_entries_owner_id", "journal_entries", ["owner_id"])


def downgrade():
    op.drop_index("ix_journal_entries_owner_id", table_name="journal_entries")
    op.drop_table("journal_entries")
