from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.google import GOOGLE_SCOPES, encode_raw_message
from app.integrations.mcp import requires_confirmation
from app.integrations.mcp_catalog import recommended_mcp_connections


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
