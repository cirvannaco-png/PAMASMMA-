"""008 — social growth referential integrity and cleanup semantics."""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_social_posts_account",
        "pamasmma_social_posts",
        "pamasmma_social_accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_social_engagement_account",
        "pamasmma_social_engagement",
        "pamasmma_social_accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_social_campaigns_account",
        "pamasmma_social_campaigns",
        "pamasmma_social_accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_social_campaigns_account",
        "pamasmma_social_campaigns",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_social_engagement_account",
        "pamasmma_social_engagement",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_social_posts_account",
        "pamasmma_social_posts",
        type_="foreignkey",
    )
