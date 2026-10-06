"""006 — enforce active knowledge-source deduplication and chunk ordering."""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "pamasmma_knowledge_source_hash_mode_active_idx",
        "pamasmma_knowledge_sources",
        ["user_id", "content_hash", "training_mode"],
        unique=True,
        postgresql_where=sa.text("status IN ('processing', 'ready')"),
    )
    op.create_index(
        "pamasmma_knowledge_chunk_source_ordinal_idx",
        "pamasmma_knowledge_chunks",
        ["source_id", "ordinal"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "pamasmma_knowledge_chunk_source_ordinal_idx",
        table_name="pamasmma_knowledge_chunks",
    )
    op.drop_index(
        "pamasmma_knowledge_source_hash_mode_active_idx",
        table_name="pamasmma_knowledge_sources",
    )
