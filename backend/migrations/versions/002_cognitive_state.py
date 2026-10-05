"""002_cognitive_state — decisions, beliefs, outcomes and world model."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pamasmma_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("primary_system_id", sa.String(10), nullable=False, index=True),
        sa.Column("objective", sa.Text, nullable=False),
        sa.Column("context", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("constraints", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("memories", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("options", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("assumptions", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("risks", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("certainty_band", sa.String(30), nullable=False),
        sa.Column("selected_action", sa.Text, nullable=False),
        sa.Column("alternatives_rejected", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("owner", sa.String(100), nullable=False),
        sa.Column("expected_outcome", sa.Text, nullable=True),
        sa.Column("deadline", sa.String(100), nullable=True),
        sa.Column("horizon_checks", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("observed_outcome", sa.Text, nullable=True),
        sa.Column("prediction_error", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "pamasmma_beliefs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("statement", sa.Text, nullable=False),
        sa.Column("evidence_type", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reliability", sa.Float, nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("predicate", sa.String(100), nullable=True),
        sa.Column("object", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.UniqueConstraint("user_id", "statement", name="uq_pamasmma_belief_statement"),
    )

    op.create_table(
        "pamasmma_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("expected_outcome", sa.Text, nullable=False),
        sa.Column("observed_outcome", sa.Text, nullable=False),
        sa.Column("success_score", sa.Float, nullable=True),
        sa.Column("prediction_error", sa.Float, nullable=True),
        sa.Column("failure_domain", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("lesson", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )

    op.create_table(
        "pamasmma_world_entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("attributes", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.UniqueConstraint("user_id", "name", name="uq_pamasmma_world_entity"),
    )

    op.create_table(
        "pamasmma_world_relationships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("relation", sa.String(100), nullable=False),
        sa.Column("object", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.UniqueConstraint("user_id", "subject", "relation", "object", name="uq_pamasmma_world_relation"),
    )


def downgrade() -> None:
    op.drop_table("pamasmma_world_relationships")
    op.drop_table("pamasmma_world_entities")
    op.drop_table("pamasmma_outcomes")
    op.drop_table("pamasmma_beliefs")
    op.drop_table("pamasmma_decisions")
