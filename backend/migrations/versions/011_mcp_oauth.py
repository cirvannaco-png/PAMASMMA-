"""011 — MCP OAuth client credentials and connection state."""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pamasmma_mcp_connectors",
        sa.Column("auth_mode", sa.String(20), nullable=False, server_default="bearer"),
    )
    op.add_column(
        "pamasmma_mcp_connectors",
        sa.Column("auth_status", sa.String(30), nullable=False, server_default="configured"),
    )
    op.add_column(
        "pamasmma_mcp_connectors",
        sa.Column("oauth_tokens_enc", sa.Text(), nullable=True),
    )
    op.add_column(
        "pamasmma_mcp_connectors",
        sa.Column("oauth_client_info_enc", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_pamasmma_mcp_auth_mode",
        "pamasmma_mcp_connectors",
        "auth_mode IN ('bearer', 'oauth')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_pamasmma_mcp_auth_mode",
        "pamasmma_mcp_connectors",
        type_="check",
    )
    op.drop_column("pamasmma_mcp_connectors", "oauth_client_info_enc")
    op.drop_column("pamasmma_mcp_connectors", "oauth_tokens_enc")
    op.drop_column("pamasmma_mcp_connectors", "auth_status")
    op.drop_column("pamasmma_mcp_connectors", "auth_mode")
