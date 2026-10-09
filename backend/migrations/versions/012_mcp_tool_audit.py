"""012 — durable MCP tool invocation audit."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pamasmma_mcp_tool_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("connector_name", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("confirmation_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("arguments_sha256", sa.String(64), nullable=False),
        sa.Column("result_sha256", sa.String(64), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["connector_id"],
            ["pamasmma_mcp_connectors.id"],
            ondelete="SET NULL",
            name="fk_mcp_tool_audit_connector",
        ),
        sa.CheckConstraint(
            "status IN ('started', 'succeeded', 'failed', 'blocked')",
            name="ck_mcp_tool_audit_status",
        ),
    )
    op.create_index(
        "pamasmma_mcp_audit_user_created_idx",
        "pamasmma_mcp_tool_audit",
        ["user_id", "created_at"],
    )
    op.create_index(
        "pamasmma_mcp_audit_connector_created_idx",
        "pamasmma_mcp_tool_audit",
        ["connector_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "pamasmma_mcp_audit_connector_created_idx",
        table_name="pamasmma_mcp_tool_audit",
    )
    op.drop_index(
        "pamasmma_mcp_audit_user_created_idx",
        table_name="pamasmma_mcp_tool_audit",
    )
    op.drop_table("pamasmma_mcp_tool_audit")
