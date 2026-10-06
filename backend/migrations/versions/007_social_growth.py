"""007 — governed social growth subsystem."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision="007"
down_revision="006"
branch_labels=None
depends_on=None

def upgrade()->None:
    op.create_table("pamasmma_social_accounts",
        sa.Column("id",UUID(as_uuid=True),primary_key=True,server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",sa.String(255),nullable=False,index=True),
        sa.Column("platform",sa.String(30),nullable=False,index=True),
        sa.Column("external_account_id",sa.String(255),nullable=False),
        sa.Column("display_name",sa.String(255),nullable=True),
        sa.Column("access_token_enc",sa.Text,nullable=False),
        sa.Column("refresh_token_enc",sa.Text,nullable=True),
        sa.Column("token_expires_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("scopes",JSONB,nullable=False,server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata",JSONB,nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("status",sa.String(30),nullable=False,server_default="active"),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
    )
    op.create_index("pamasmma_social_accounts_unique","pamasmma_social_accounts",["user_id","platform","external_account_id"],unique=True)
    op.create_table("pamasmma_social_posts",
        sa.Column("id",UUID(as_uuid=True),primary_key=True,server_default=sa.text("uuid_generate_v4()")),
        sa.Column("account_id",UUID(as_uuid=True),nullable=False,index=True),
        sa.Column("platform_post_id",sa.String(255),nullable=True,index=True),
        sa.Column("status",sa.String(30),nullable=False,server_default="queued",index=True),
        sa.Column("content",JSONB,nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("scheduled_at",sa.DateTime(timezone=True),nullable=True,index=True),
        sa.Column("published_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("metrics",JSONB,nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("error",sa.Text,nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),index=True),
    )
    op.create_table("pamasmma_social_engagement",
        sa.Column("id",UUID(as_uuid=True),primary_key=True,server_default=sa.text("uuid_generate_v4()")),
        sa.Column("account_id",UUID(as_uuid=True),nullable=False,index=True),
        sa.Column("item_id",sa.String(255),nullable=False,index=True),
        sa.Column("kind",sa.String(30),nullable=False),
        sa.Column("author_name",sa.String(255),nullable=True),
        sa.Column("text",sa.Text,nullable=True),
        sa.Column("intent",sa.String(50),nullable=True),
        sa.Column("sentiment",sa.String(30),nullable=True),
        sa.Column("priority",sa.String(20),nullable=False,server_default="normal",index=True),
        sa.Column("responded_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("metadata",JSONB,nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),index=True),
    )
    op.create_index("pamasmma_social_engagement_dedupe","pamasmma_social_engagement",["account_id","item_id"],unique=True)
    op.create_table("pamasmma_social_campaigns",
        sa.Column("id",UUID(as_uuid=True),primary_key=True,server_default=sa.text("uuid_generate_v4()")),
        sa.Column("account_id",UUID(as_uuid=True),nullable=False,index=True),
        sa.Column("ad_account_id",sa.String(255),nullable=True),
        sa.Column("external_campaign_id",sa.String(255),nullable=True,index=True),
        sa.Column("name",sa.String(255),nullable=False),
        sa.Column("objective",sa.String(100),nullable=False),
        sa.Column("budget",sa.Float,nullable=True),
        sa.Column("currency",sa.String(3),nullable=False),
        sa.Column("status",sa.String(30),nullable=False,server_default="planned",index=True),
        sa.Column("config",JSONB,nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("metrics",JSONB,nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("approved_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),index=True),
    )

def downgrade()->None:
    op.drop_table("pamasmma_social_campaigns")
    op.drop_index("pamasmma_social_engagement_dedupe",table_name="pamasmma_social_engagement")
    op.drop_table("pamasmma_social_engagement")
    op.drop_table("pamasmma_social_posts")
    op.drop_index("pamasmma_social_accounts_unique",table_name="pamasmma_social_accounts")
    op.drop_table("pamasmma_social_accounts")
