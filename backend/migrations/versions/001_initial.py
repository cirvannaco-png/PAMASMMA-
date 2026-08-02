"""001_initial — PAMASMMA v4 schema

Creates:
  - pamasmma_memories     (pgvector memory store)
  - pamasmma_action_log   (cognitive invocation log)
  - pamasmma_override_queue (S7 behavioral override queue)
  - pamasmma_users        (founder identity)

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # ── Users ──────────────────────────────────────────────────────────────
    op.create_table(
        "pamasmma_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("totp_secret_enc", sa.Text, nullable=True),           # encrypted at rest
        sa.Column("totp_enabled", sa.Boolean, default=False, nullable=False),
        sa.Column("webauthn_registered", sa.Boolean, default=False, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Memory Store (pgvector) ────────────────────────────────────────────
    op.create_table(
        "pamasmma_memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("system_id", sa.String(10), nullable=False, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.Text, nullable=True),  # stored as vector string; cast in queries
        sa.Column("metadata", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )
    # Convert embedding column to vector type
    op.execute("ALTER TABLE pamasmma_memories ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
    op.execute("CREATE INDEX pamasmma_memories_embedding_idx ON pamasmma_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")

    # ── Action Log ─────────────────────────────────────────────────────────
    op.create_table(
        "pamasmma_action_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("system_id", sa.String(10), nullable=False, index=True),
        sa.Column("system_name", sa.String(100), nullable=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("query_preview", sa.String(500), nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # ── Override Queue ─────────────────────────────────────────────────────
    op.create_table(
        "pamasmma_override_queue",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("system_id", sa.String(10), nullable=False, index=True),
        sa.Column("directive", sa.Text, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("pamasmma_override_queue")
    op.drop_table("pamasmma_action_log")
    op.drop_table("pamasmma_memories")
    op.drop_table("pamasmma_users")
