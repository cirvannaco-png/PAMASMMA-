"""014 — durable JARVIS voice sessions, delegation idempotency and usage ledger."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pamasmma_jarvis_voice_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_session_id", sa.String(255), nullable=False, unique=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pamasmma_jarvis_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False, server_default="openai"),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'closed', 'failed', 'expired')", name="ck_jarvis_voice_session_status"),
    )
    op.create_index("ix_jarvis_voice_sessions_owner_created", "pamasmma_jarvis_voice_sessions", ["user_id", "created_at"])
    op.create_table(
        "pamasmma_jarvis_voice_delegations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pamasmma_jarvis_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_session_id", sa.String(255), nullable=True),
        sa.Column("delegation_id", sa.String(128), nullable=False),
        sa.Column("transcript_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "conversation_id", "delegation_id", name="uq_jarvis_voice_delegation_owner_key"),
        sa.CheckConstraint("status IN ('processing', 'completed', 'failed')", name="ck_jarvis_voice_delegation_status"),
    )
    op.create_index("ix_jarvis_voice_delegations_created", "pamasmma_jarvis_voice_delegations", ["user_id", "created_at"])
    op.create_table(
        "pamasmma_jarvis_voice_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("voice_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pamasmma_jarvis_voice_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="awaiting_provider"),
        sa.Column("input_audio_tokens", sa.Integer(), nullable=True),
        sa.Column("output_audio_tokens", sa.Integer(), nullable=True),
        sa.Column("input_text_tokens", sa.Integer(), nullable=True),
        sa.Column("output_text_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("provider_event_id", sa.String(255), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("voice_session_id", name="uq_jarvis_voice_usage_session"),
        sa.CheckConstraint("status IN ('awaiting_provider', 'captured', 'unavailable')", name="ck_jarvis_voice_usage_status"),
    )
    op.create_index("ix_jarvis_voice_usage_owner_created", "pamasmma_jarvis_voice_usage", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_jarvis_voice_usage_owner_created", table_name="pamasmma_jarvis_voice_usage")
    op.drop_table("pamasmma_jarvis_voice_usage")
    op.drop_index("ix_jarvis_voice_delegations_created", table_name="pamasmma_jarvis_voice_delegations")
    op.drop_table("pamasmma_jarvis_voice_delegations")
    op.drop_index("ix_jarvis_voice_sessions_owner_created", table_name="pamasmma_jarvis_voice_sessions")
    op.drop_table("pamasmma_jarvis_voice_sessions")
