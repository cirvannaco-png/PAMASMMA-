from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.google import GOOGLE_SCOPES, encode_raw_message
from app.integrations.mcp import requires_confirmation
from app.integrations.mcp_catalog import get_mcp_connection_profile, recommended_mcp_connections
from app.integrations.store import settings as integration_settings
from app.integrations.store import validate_mcp_endpoint


def test_google_scopes_include_read_write_workspace_access():
    assert "https://www.googleapis.com/auth/gmail.modify" in GOOGLE_SCOPES
    assert "https://www.googleapis.com/auth/drive" in GOOGLE_SCOPES


def test_google_email_encoding():
    raw = encode_raw_message({"to": ["user@example.com"], "subject": "Hello", "body": "World"})
    assert raw
    assert "=" not in raw[-2:]


def test_mcp_write_tools_require_confirmation():
    assert requires_confirmation("send_email")
    assert requires_confirmation("delete_file")
    assert not requires_confirmation("search_documents")

@pytest.mark.asyncio
async def test_google_oauth_state_is_user_bound():
    with patch("app.integrations.store.cache_set", new_callable=AsyncMock) as cache_set:
        from app.integrations.store import save_oauth_state
        await save_oauth_state("state123", "user-1")
        cache_set.assert_awaited_once()
        assert cache_set.await_args.args[1]["user_id"] == "user-1"


def test_mcp_catalog_contains_core_assistant_connections():
    ids = {entry["id"] for entry in recommended_mcp_connections(priority="core")}
    assert {"github", "google-workspace", "notion", "slack", "hubspot", "canva"} <= ids


def test_mcp_catalog_role_filtering():
    entries = recommended_mcp_connections(role="marketing")
    assert entries
    assert all("marketing" in entry["roles"] for entry in entries)


def test_mcp_catalog_profile_lookup():
    profile = get_mcp_connection_profile("apify")
    assert profile is not None
    assert profile["registry_server"] == "com.apify/apify-mcp-server"
    assert profile["connection_state"] == "discoverable"


def test_mcp_confirmation_fails_closed_for_unknown_tools():
    assert requires_confirmation("sync_workspace")
    assert requires_confirmation("update_customer")
    assert not requires_confirmation("search_documents")
    assert not requires_confirmation(
        "opaque_tool",
        {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    )
    assert requires_confirmation(
        "nominally_read_only",
        {"readOnlyHint": True, "destructiveHint": True},
    )


def test_mcp_endpoint_rejects_local_and_private_destinations():
    with pytest.raises(ValueError, match="Local and internal"):
        validate_mcp_endpoint("https://localhost/mcp")
    with pytest.raises(ValueError, match="Private"):
        validate_mcp_endpoint("https://127.0.0.1/mcp")
    with pytest.raises(ValueError, match="HTTPS"):
        validate_mcp_endpoint("http://mcp.example.com/mcp")


def test_mcp_endpoint_requires_exact_host_allowlist_in_production(monkeypatch):
    monkeypatch.setattr(integration_settings, "app_env", "production")
    monkeypatch.setattr(integration_settings, "mcp_allowed_hosts", ["mcp.example.com"])
    assert validate_mcp_endpoint("https://mcp.example.com/mcp") == "mcp.example.com"
    with pytest.raises(ValueError, match="not in MCP_ALLOWED_HOSTS"):
        validate_mcp_endpoint("https://other.example.com/mcp")


def test_mcp_production_connections_fail_closed_without_allowlist(monkeypatch):
    monkeypatch.setattr(integration_settings, "app_env", "production")
    monkeypatch.setattr(integration_settings, "mcp_allowed_hosts", [])
    with pytest.raises(ValueError, match="MCP_ALLOWED_HOSTS"):
        validate_mcp_endpoint("https://mcp.example.com/mcp")
