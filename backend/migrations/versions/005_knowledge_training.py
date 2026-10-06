"""004 — governed knowledge training storage."""
from alembic import op
import sqlalchemy as sa
revision="005"; down_revision="004"; branch_labels=None; depends_on=None
def upgrade()->None:
    op.create_table("pamasmma_knowledge_sources",
      sa.Column("id",sa.UUID(),primary_key=True),sa.Column("user_id",sa.String(255),nullable=False,index=True),
      sa.Column("filename",sa.String(512),nullable=False),sa.Column("media_type",sa.String(32),nullable=False),
      sa.Column("status",sa.String(24),nullable=False),sa.Column("content_hash",sa.String(64),nullable=False,index=True),
      sa.Column("size_bytes",sa.BigInteger(),nullable=False),sa.Column("chunk_count",sa.Integer(),nullable=False,server_default="0"),
      sa.Column("training_mode",sa.String(24),nullable=False,server_default="knowledge"),sa.Column("metadata",sa.Text(),nullable=True),
      sa.Column("error",sa.Text(),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
      sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("pamasmma_knowledge_chunks",
      sa.Column("id",sa.UUID(),primary_key=True),sa.Column("source_id",sa.UUID(),sa.ForeignKey("pamasmma_knowledge_sources.id",ondelete="CASCADE"),nullable=False,index=True),
      sa.Column("user_id",sa.String(255),nullable=False,index=True),sa.Column("ordinal",sa.Integer(),nullable=False),sa.Column("content",sa.Text(),nullable=False),
      sa.Column("locator",sa.String(255),nullable=True),sa.Column("embedding",sa.Text(),nullable=True),sa.Column("metadata",sa.Text(),nullable=True),
      sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.execute("ALTER TABLE pamasmma_knowledge_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
    op.execute("CREATE INDEX pamasmma_knowledge_chunks_embedding_idx ON pamasmma_knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    op.create_index("pamasmma_knowledge_source_user_created_idx","pamasmma_knowledge_sources",["user_id","created_at"])
def downgrade()->None:
    op.drop_index("pamasmma_knowledge_source_user_created_idx",table_name="pamasmma_knowledge_sources")
    op.drop_table("pamasmma_knowledge_chunks"); op.drop_table("pamasmma_knowledge_sources")
