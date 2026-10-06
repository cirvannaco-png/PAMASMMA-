"""005_knowledge_training — governed uploaded-source knowledge fabric."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pamasmma_knowledge_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(150), nullable=False),
        sa.Column("training_mode", sa.String(30), nullable=False, server_default="reference"),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("extraction_method", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "content_hash", name="uq_pamasmma_knowledge_source_hash"),
    )

    op.create_table(
        "pamasmma_knowledge_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.ForeignKeyConstraint(["source_id"], ["pamasmma_knowledge_sources.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("source_id", "ordinal", name="uq_pamasmma_knowledge_chunk_ordinal"),
    )
    op.execute("ALTER TABLE pamasmma_knowledge_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
    op.execute("CREATE INDEX pamasmma_knowledge_embedding_idx ON pamasmma_knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")


def downgrade() -> None:
    op.drop_index("pamasmma_knowledge_embedding_idx", table_name="pamasmma_knowledge_chunks")
    op.drop_table("pamasmma_knowledge_chunks")
    op.drop_table("pamasmma_knowledge_sources")
