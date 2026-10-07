"""009 — resilient scheduled social delivery state.

Adds bounded retry bookkeeping and a lease so multiple scheduler workers
cannot claim the same queued delivery concurrently.
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pamasmma_social_posts",
        sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pamasmma_social_posts",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pamasmma_social_posts",
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "pamasmma_social_posts",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "pamasmma_social_posts_due_idx",
        "pamasmma_social_posts",
        ["status", "next_attempt_at", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("pamasmma_social_posts_due_idx", table_name="pamasmma_social_posts")
    op.drop_column("pamasmma_social_posts", "lease_expires_at")
    op.drop_column("pamasmma_social_posts", "last_attempt_at")
    op.drop_column("pamasmma_social_posts", "next_attempt_at")
    op.drop_column("pamasmma_social_posts", "delivery_attempts")
