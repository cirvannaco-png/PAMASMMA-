"""Persistent social accounts, content, engagement and campaign records."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class SocialAccount(Base):
    __tablename__="pamasmma_social_accounts"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4,server_default=func.uuid_generate_v4())
    user_id: Mapped[str]=mapped_column(String(255),nullable=False,index=True)
    platform: Mapped[str]=mapped_column(String(30),nullable=False,index=True)
    external_account_id: Mapped[str]=mapped_column(String(255),nullable=False)
    display_name: Mapped[str|None]=mapped_column(String(255),nullable=True)
    access_token_enc: Mapped[str]=mapped_column(Text,nullable=False)
    refresh_token_enc: Mapped[str|None]=mapped_column(Text,nullable=True)
    token_expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    scopes: Mapped[list]=mapped_column(JSONB,default=list,nullable=False)
    metadata_: Mapped[dict]=mapped_column("metadata",JSONB,default=dict,nullable=False)
    status: Mapped[str]=mapped_column(String(30),default="active",nullable=False,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

class SocialPost(Base):
    __tablename__="pamasmma_social_posts"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4,server_default=func.uuid_generate_v4())
    account_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),nullable=False,index=True)
    platform_post_id: Mapped[str|None]=mapped_column(String(255),nullable=True,index=True)
    status: Mapped[str]=mapped_column(String(30),default="queued",nullable=False,index=True)
    content: Mapped[dict]=mapped_column(JSONB,default=dict,nullable=False)
    scheduled_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True,index=True)
    published_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    metrics: Mapped[dict]=mapped_column(JSONB,default=dict,nullable=False)
    error: Mapped[str|None]=mapped_column(Text,nullable=True)
    delivery_attempts: Mapped[int]=mapped_column(default=0,nullable=False)
    next_attempt_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True,index=True)
    last_attempt_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    lease_expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)

class SocialEngagement(Base):
    __tablename__="pamasmma_social_engagement"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4,server_default=func.uuid_generate_v4())
    account_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),nullable=False,index=True)
    item_id: Mapped[str]=mapped_column(String(255),nullable=False,index=True)
    kind: Mapped[str]=mapped_column(String(30),nullable=False)
    author_name: Mapped[str|None]=mapped_column(String(255),nullable=True)
    text: Mapped[str|None]=mapped_column(Text,nullable=True)
    intent: Mapped[str|None]=mapped_column(String(50),nullable=True)
    sentiment: Mapped[str|None]=mapped_column(String(30),nullable=True)
    priority: Mapped[str]=mapped_column(String(20),default="normal",nullable=False,index=True)
    responded_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    metadata_: Mapped[dict]=mapped_column("metadata",JSONB,default=dict,nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)

class SocialCampaign(Base):
    __tablename__="pamasmma_social_campaigns"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4,server_default=func.uuid_generate_v4())
    account_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),nullable=False,index=True)
    ad_account_id: Mapped[str|None]=mapped_column(String(255),nullable=True)
    external_campaign_id: Mapped[str|None]=mapped_column(String(255),nullable=True,index=True)
    name: Mapped[str]=mapped_column(String(255),nullable=False)
    objective: Mapped[str]=mapped_column(String(100),nullable=False)
    budget: Mapped[float|None]=mapped_column(Float,nullable=True)
    currency: Mapped[str]=mapped_column(String(3),nullable=False)
    status: Mapped[str]=mapped_column(String(30),default="planned",nullable=False,index=True)
    config: Mapped[dict]=mapped_column(JSONB,default=dict,nullable=False)
    metrics: Mapped[dict]=mapped_column(JSONB,default=dict,nullable=False)
    approved_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
