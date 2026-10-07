from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.google import GOOGLE_SCOPES, encode_raw_message
from app.integrations.mcp import requires_confirmation


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
