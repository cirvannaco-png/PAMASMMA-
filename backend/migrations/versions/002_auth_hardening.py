"""002_auth_hardening — stable user key for authenticated persistence.

Revision ID: 002
Revises: 001
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pamasmma_users",
        sa.Column("user_key", sa.String(255), nullable=True),
    )
    op.execute(
        "UPDATE pamasmma_users SET user_key = username WHERE user_key IS NULL"
    )
    op.alter_column(
        "pamasmma_users",
        "user_key",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_pamasmma_users_user_key",
        "pamasmma_users",
        ["user_key"],
    )
    op.create_index(
        "ix_pamasmma_users_user_key",
        "pamasmma_users",
        ["user_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pamasmma_users_user_key",
        table_name="pamasmma_users",
    )
    op.drop_constraint(
        "uq_pamasmma_users_user_key",
        "pamasmma_users",
        type_="unique",
    )
    op.drop_column("pamasmma_users", "user_key")
