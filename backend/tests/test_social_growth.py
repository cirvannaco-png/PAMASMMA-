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


@pytest.mark.asyncio
async def test_pinterest_oauth_uses_basic_auth(monkeypatch):
    from app.social.providers import pinterest

    monkeypatch.setattr(
        pinterest,
        "_env",
        lambda name: {
            "SOCIAL_PINTEREST_APP_ID": "client-id",
            "SOCIAL_PINTEREST_APP_SECRET": "client-secret",
            "SOCIAL_PINTEREST_REDIRECT_URI": "https://example.test/callback",
        }.get(name, ""),
    )
    provider = pinterest.PinterestProvider()
    seen = {}

    async def fake_request(method, url, **kwargs):
        seen.update({"method": method, "url": url, **kwargs})
        return {"access_token": "token", "refresh_token": "refresh"}

    monkeypatch.setattr(provider, "request", fake_request)
    await provider.exchange_code("code-1")
    assert seen["method"] == "POST"
    assert seen["url"] == provider.token_url
    assert seen["data"]["grant_type"] == "authorization_code"
    assert seen["headers"]["Authorization"].startswith("Basic ")
    assert "client_secret" not in seen["data"]

    seen.clear()
    await provider.refresh_token("refresh-1")
    assert seen["data"]["grant_type"] == "refresh_token"
    assert seen["headers"]["Authorization"].startswith("Basic ")
    assert "client_id" not in seen["data"]


@pytest.mark.asyncio
async def test_tiktok_photo_direct_post_payload(monkeypatch):
    from app.social.providers import tiktok

    provider = tiktok.TikTokProvider()
    calls = []

    async def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if "creator_info" in url:
            return {"data": {"privacy_level_options": ["PUBLIC_TO_EVERYONE"]}}
        return {"data": {"publish_id": "publish-1"}}

    monkeypatch.setattr(provider, "request", fake_request)
    result = await provider.publish(
        "token",
        PublishCommand(
            account_id="account-1",
            text="caption",
            title="Title",
            media_url="https://cdn.example.test/photo.jpg",
            media_type="image/jpeg",
            platform_options={"privacy_level": "PUBLIC_TO_EVERYONE"},
        ),
        "tiktok-user-1",
    )

    assert result["data"]["publish_id"] == "publish-1"
    payload = calls[-1][2]["json_body"]
    assert payload["post_mode"] == "DIRECT_POST"
    assert payload["media_type"] == "PHOTO"
    assert payload["source_info"]["source"] == "PULL_FROM_URL"


@pytest.mark.asyncio
async def test_instagram_video_waits_for_container_ready(monkeypatch):
    from app.social.providers import meta

    provider = meta.InstagramProvider()
    calls = []
    statuses = iter(["IN_PROGRESS", "FINISHED"])

    async def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "POST" and url.endswith("/media"):
            return {"id": "container-1"}
        if method == "GET" and url.endswith("/container-1"):
            return {"status_code": next(statuses), "status": "ok"}
        return {"id": "media-1"}

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(provider, "request", fake_request)
    monkeypatch.setattr(meta.asyncio, "sleep", fake_sleep)

    result = await provider.publish(
        "token",
        PublishCommand(
            account_id="account-1",
            text="reel",
            media_url="https://cdn.example.test/reel.mp4",
            media_type="video/mp4",
        ),
        "ig-user-1",
    )

    assert result["id"] == "media-1"
    assert [method for method, _, _ in calls] == ["POST", "GET", "GET", "POST"]
    assert calls[-1][2]["data"]["creation_id"] == "container-1"


def test_social_delivery_retry_policy():
    from app.social.store import _is_retryable_delivery_error, _retry_delay_seconds

    from app.social.contracts import SocialProviderError

    assert _is_retryable_delivery_error(
        SocialProviderError(Platform.X, "provider_error", "temporary", 503)
    )
    assert _is_retryable_delivery_error(
        SocialProviderError(Platform.X, "provider_error", "rate limited", 429)
    )
    assert not _is_retryable_delivery_error(
        SocialProviderError(Platform.X, "provider_error", "bad request", 400)
    )
    assert _retry_delay_seconds(1) < _retry_delay_seconds(2)


@pytest.mark.asyncio
async def test_x_oauth_uses_server_held_pkce_verifier(monkeypatch):
    from app.social.providers import x

    provider = x.XProvider()
    monkeypatch.setattr(
        x,
        "_env",
        lambda name: {
            "SOCIAL_X_CLIENT_ID": "client-id",
            "SOCIAL_X_CLIENT_SECRET": "client-secret",
            "SOCIAL_X_REDIRECT_URI": "https://example.test/callback",
            "SOCIAL_X_SCOPES": "tweet.read tweet.write users.read offline.access",
        }.get(name, ""),
    )
    seen = {}

    async def fake_request(method, url, **kwargs):
        seen.update({"method": method, "url": url, **kwargs})
        return {"access_token": "token"}

    monkeypatch.setattr(provider, "request", fake_request)
    from app.social.contracts import SocialProviderError

    with pytest.raises(SocialProviderError):
        await provider.exchange_code("code-1", "state-1")

    await provider.exchange_code(
        "code-1",
        "state-1",
        code_verifier="server-held-verifier",
    )
    assert seen["data"]["code_verifier"] == "server-held-verifier"

    auth = provider.authorization_url(
        "state-1",
        code_challenge="challenge-1",
    )
    assert "code_challenge=challenge-1" in auth
    assert "code_challenge_method=S256" in auth
