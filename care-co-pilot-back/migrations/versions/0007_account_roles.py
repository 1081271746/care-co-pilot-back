"""Roles explícitos; las cuentas existentes siguen siendo usuarias normales."""

from alembic import op
import sqlalchemy as sa

revision = "0007_account_roles"
down_revision = "0006_emotional_profiles"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column(
            "role", sa.String(10), nullable=False, server_default="user",
        ))
        batch.create_check_constraint("ck_users_role", "role IN ('user', 'admin')")


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role", type_="check")
        batch.drop_column("role")
