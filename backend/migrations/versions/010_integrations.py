"""010 — Google Workspace and MCP connector persistence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="010";down_revision="009";branch_labels=None;depends_on=None
def upgrade():
    op.create_table("pamasmma_integration_accounts",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("user_id",sa.String(255),nullable=False,index=True),sa.Column("provider",sa.String(50),nullable=False),sa.Column("external_account_id",sa.String(255),nullable=False),sa.Column("display_name",sa.String(255)),sa.Column("access_token_enc",sa.Text(),nullable=False),sa.Column("refresh_token_enc",sa.Text(),nullable=False),sa.Column("token_expires_at",sa.DateTime(timezone=True)),sa.Column("scopes",postgresql.JSONB(),nullable=False,server_default=sa.text("'[]'::jsonb")),sa.Column("metadata",postgresql.JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")),sa.Column("status",sa.String(30),nullable=False,server_default="active"),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now()),sa.UniqueConstraint("user_id","provider","external_account_id",name="uq_pamasmma_integration_identity"))
    op.create_index("pamasmma_integrations_user_provider_idx","pamasmma_integration_accounts",["user_id","provider","status"])
    op.create_table("pamasmma_mcp_connectors",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("user_id",sa.String(255),nullable=False,index=True),sa.Column("name",sa.String(255),nullable=False),sa.Column("endpoint",sa.Text(),nullable=False),sa.Column("bearer_token_enc",sa.Text()),sa.Column("enabled",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now()))
def downgrade():
    op.drop_table("pamasmma_mcp_connectors");op.drop_index("pamasmma_integrations_user_provider_idx",table_name="pamasmma_integration_accounts");op.drop_table("pamasmma_integration_accounts")
