"""003_cognitive_audit — enrich cognitive invocation telemetry."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pamasmma_action_log",
        sa.Column("decision_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "pamasmma_action_log",
        sa.Column("confidence", sa.Float, nullable=True),
    )
    op.add_column(
        "pamasmma_action_log",
        sa.Column("provider", sa.String(100), nullable=True),
    )
    op.add_column(
        "pamasmma_action_log",
        sa.Column("verification_score", sa.Float, nullable=True),
    )
    op.add_column(
        "pamasmma_action_log",
        sa.Column("evidence_status", sa.String(50), nullable=True),
    )
    op.add_column(
        "pamasmma_action_log",
        sa.Column(
            "routed_systems",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("pamasmma_action_log", "routed_systems")
    op.drop_column("pamasmma_action_log", "evidence_status")
    op.drop_column("pamasmma_action_log", "verification_score")
    op.drop_column("pamasmma_action_log", "provider")
    op.drop_column("pamasmma_action_log", "confidence")
    op.drop_column("pamasmma_action_log", "decision_id")
