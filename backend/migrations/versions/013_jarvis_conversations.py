"""013 — durable JARVIS conversations and ordered text messages."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pamasmma_jarvis_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(160), nullable=False, server_default="New conversation"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("active_turn_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active_turn_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_jarvis_conversation_status"),
    )
    op.create_index("ix_pamasmma_jarvis_conversations_user_id", "pamasmma_jarvis_conversations", ["user_id"])
    op.create_index("ix_jarvis_conversations_user_updated", "pamasmma_jarvis_conversations", ["user_id", "updated_at"])

    op.create_table(
        "pamasmma_jarvis_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("modality", sa.String(16), nullable=False, server_default="text"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["pamasmma_jarvis_conversations.id"], ondelete="CASCADE", name="fk_jarvis_message_conversation"),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_jarvis_message_sequence"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_jarvis_message_role"),
        sa.CheckConstraint("modality IN ('text', 'voice')", name="ck_jarvis_message_modality"),
    )
    op.create_index("ix_pamasmma_jarvis_messages_conversation_id", "pamasmma_jarvis_messages", ["conversation_id"])
    op.create_index("ix_pamasmma_jarvis_messages_user_id", "pamasmma_jarvis_messages", ["user_id"])
    op.create_index("ix_jarvis_messages_owner_created", "pamasmma_jarvis_messages", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_jarvis_messages_owner_created", table_name="pamasmma_jarvis_messages")
    op.drop_index("ix_pamasmma_jarvis_messages_user_id", table_name="pamasmma_jarvis_messages")
    op.drop_index("ix_pamasmma_jarvis_messages_conversation_id", table_name="pamasmma_jarvis_messages")
    op.drop_table("pamasmma_jarvis_messages")
    op.drop_index("ix_jarvis_conversations_user_updated", table_name="pamasmma_jarvis_conversations")
    op.drop_index("ix_pamasmma_jarvis_conversations_user_id", table_name="pamasmma_jarvis_conversations")
    op.drop_table("pamasmma_jarvis_conversations")
