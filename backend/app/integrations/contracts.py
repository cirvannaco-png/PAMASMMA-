"""Contracts for Google Workspace and MCP integrations."""
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class IntegrationProvider(StrEnum):
    GOOGLE="google"
    MCP="mcp"


class GoogleService(StrEnum):
    GMAIL="gmail"
    DRIVE="drive"


class GoogleSendEmail(BaseModel):
    to:list[str]=Field(min_length=1,max_length=50)
    subject:str=Field(min_length=1,max_length=998)
    body:str=Field(min_length=1,max_length=1_000_000)
    cc:list[str]=Field(default_factory=list,max_length=50)
    bcc:list[str]=Field(default_factory=list,max_length=50)


class DriveUpload(BaseModel):
    name:str=Field(min_length=1,max_length=255)
    mime_type:str=Field(default="application/octet-stream",max_length=255)
    content_base64:str=Field(min_length=1,max_length=25_000_000)
    parent_id:str|None=Field(default=None,max_length=255)


class McpConnectorCreate(BaseModel):
    name:str=Field(min_length=1,max_length=255)
    endpoint:HttpUrl
    bearer_token:str|None=Field(default=None,max_length=10000)
    enabled:bool=True


class McpToolCall(BaseModel):
    tool_name:str=Field(min_length=1,max_length=255)
    arguments:dict=Field(default_factory=dict)
    confirmed:bool=False
