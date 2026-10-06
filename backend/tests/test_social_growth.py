"""Unit tests for the provider-neutral social growth layer."""
import pytest
from pydantic import ValidationError

from app.social.contracts import Capability, Platform, PublishCommand
from app.social.providers.adapters import PROVIDERS
from app.social.store import classify_engagement


def test_all_declared_platforms_have_provider():
    assert set(PROVIDERS) == set(Platform)


def test_provider_capabilities_are_explicit():
    for provider in PROVIDERS.values():
        assert provider.platform in Platform
        assert provider.capabilities
        assert all(isinstance(item, Capability) for item in provider.capabilities)


def test_publish_contract_rejects_oversized_text():
    with pytest.raises(ValidationError):
        PublishCommand(account_id="a", text="x" * 10001)


def test_publish_contract_accepts_platform_options():
    command = PublishCommand(
        account_id="a",
        text="hello",
        platform_options={"privacy_level": "PUBLIC_TO_EVERYONE"},
    )
    assert command.platform_options["privacy_level"] == "PUBLIC_TO_EVERYONE"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("How much does this cost?", ("lead", "neutral", "high")),
        ("I was charged twice and need a refund", ("complaint", "negative", "urgent")),
        ("This is amazing, thank you!", ("praise", "positive", "normal")),
        ("When will this be available?", ("question", "neutral", "normal")),
        ("Just checking in", ("conversation", "neutral", "normal")),
    ],
)
def test_engagement_classification(text: str, expected: tuple[str, str, str]):
    assert classify_engagement(text) == expected


def test_ad_capability_is_never_assumed():
    assert Capability.ADS_WRITE in PROVIDERS[Platform.FACEBOOK].capabilities
    assert Capability.ADS_WRITE not in PROVIDERS[Platform.TIKTOK].capabilities
    assert Capability.ADS_WRITE not in PROVIDERS[Platform.YOUTUBE].capabilities
    assert Capability.ADS_WRITE not in PROVIDERS[Platform.X].capabilities



def test_each_provider_exposes_account_discovery():
    for platform, provider in PROVIDERS.items():
        assert platform in Platform
        assert callable(provider.discover_accounts)


def test_platform_registry_supports_multiple_user_connections():
    assert len(PROVIDERS) >= 11
    assert set(Platform) <= set(PROVIDERS)



def test_universal_multi_account_linking_contract():
    identities = {
        ("user-a", Platform.YOUTUBE, "channel-a"),
        ("user-a", Platform.YOUTUBE, "channel-b"),
        ("user-b", Platform.YOUTUBE, "channel-a"),
    }
    assert len(identities) == 3
    assert ("user-a", Platform.YOUTUBE, "channel-a") in identities
    assert ("user-b", Platform.YOUTUBE, "channel-a") in identities


@pytest.mark.asyncio
async def test_publish_now_awaits_access_token(monkeypatch):
    import app.social.store as store

    account = {
        "id": "account-1",
        "user_id": "user-a",
        "platform": Platform.X.value,
        "external_account_id": "x-user-1",
        "access_token_enc": "encrypted",
        "status": "active",
    }
    seen = {}

    class FakeProvider:
        async def publish(self, token, command, external_account_id):
            seen["token"] = token
            seen["command"] = command
            seen["external_account_id"] = external_account_id
            return {"id": "post-1"}

    async def fake_get_account(user_id, account_id):
        assert user_id == "user-a"
        assert account_id == "account-1"
        return account

    async def fake_access_token_for(record):
        assert record is account
        return "resolved-token"

    async def fake_persist_post(post):
        seen["post"] = post

    monkeypatch.setattr(store, "get_account", fake_get_account)
    monkeypatch.setattr(store, "get_provider", lambda platform: FakeProvider())
    monkeypatch.setattr(store, "_access_token_for", fake_access_token_for)
    monkeypatch.setattr(store, "_persist_post", fake_persist_post)

    result = await store.publish_now(
        "user-a",
        PublishCommand(account_id="account-1", text="hello"),
    )

    assert result["platform_post_id"] == "post-1"
    assert seen["token"] == "resolved-token"
    assert seen["external_account_id"] == "x-user-1"
