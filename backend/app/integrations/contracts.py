"""Contracts for Google Workspace and MCP integrations."""
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


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
    name: str = Field(min_length=1, max_length=255)
    endpoint: HttpUrl
    auth_mode: Literal["bearer", "oauth"] = "bearer"
    bearer_token: str | None = Field(default=None, max_length=10000)
    oauth_client_id: str | None = Field(default=None, min_length=1, max_length=2000)
    oauth_client_secret: str | None = Field(default=None, max_length=10000)
    oauth_token_endpoint_auth_method: Literal[
        "none", "client_secret_post", "client_secret_basic"
    ] = "client_secret_post"
    enabled: bool = True

    @model_validator(mode="after")
    def validate_auth_mode(self):
        if self.auth_mode == "bearer" and (
            self.oauth_client_id or self.oauth_client_secret
        ):
            raise ValueError("OAuth client credentials require auth_mode='oauth'.")
        if self.auth_mode == "oauth" and self.bearer_token:
            raise ValueError("Bearer token and OAuth authentication cannot be combined.")
        if (
            self.oauth_token_endpoint_auth_method != "none"
            and self.oauth_client_id
            and not self.oauth_client_secret
        ):
            raise ValueError("This OAuth token authentication method requires a client secret.")
        return self


class McpToolCall(BaseModel):
    tool_name:str=Field(min_length=1,max_length=255)
    arguments:dict=Field(default_factory=dict)
    confirmed:bool=False
