"""Multi-model routing, sensitive-data guardrails, and provider failover tests."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from app.config import Settings
from app.intelligence.contracts import Sensitivity, TaskComplexity
from app.intelligence.provider_router import ProviderRouter


def pool_settings(**overrides):
    settings = {
        "model_provider": "pool",
        "intelligence_cloud_for_sensitive": False,
        "model_pool_fast": "fast-a,fast-b",
        "model_pool_deep": "deep-a",
    }
    settings.update(overrides)
    return SimpleNamespace(**settings)


class NamedProvider:
    def __init__(self, name, fail=False, response=None):
        self.name = name
        self.fail = fail
        self.response = response or f"answer from {name}"
        self.calls = 0

    async def generate(self, system_prompt, messages, max_tokens):
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"{self.name} unavailable")
        return self.response


def test_pool_routes_complex_and_strategic_tasks_to_deep_models_first(monkeypatch):
    monkeypatch.setattr(
        "app.intelligence.provider_router.get_settings", lambda: pool_settings()
    )
    monkeypatch.setattr(
        ProviderRouter,
        "_instantiate_pool",
        staticmethod(lambda model: NamedProvider(model)),
    )

    router = ProviderRouter()
    heavy = router.select(TaskComplexity.STRATEGIC, Sensitivity.STANDARD)
    complex_task = router.select(TaskComplexity.COMPLEX, Sensitivity.STANDARD)
    routine = router.select(TaskComplexity.ROUTINE, Sensitivity.STANDARD)

    assert heavy.name == "pool:deep-a"
    assert complex_task.name == "pool:deep-a"
    assert [item.name for item in heavy.fallbacks] == [
        "pool:fast-a", "pool:fast-b"
    ]
    assert routine.name == "pool:fast-a"
    assert [item.name for item in routine.fallbacks] == [
        "pool:fast-b", "pool:deep-a"
    ]


def test_pool_deduplicates_and_ignores_blank_model_ids(monkeypatch):
    monkeypatch.setattr(
        "app.intelligence.provider_router.get_settings",
        lambda: pool_settings(model_pool_fast="fast-a, ,fast-a,fast-b",
                              model_pool_deep="deep-a,fast-a"),
    )
    monkeypatch.setattr(
        ProviderRouter,
        "_instantiate_pool",
        staticmethod(lambda model: NamedProvider(model)),
    )
    selected = ProviderRouter().select(TaskComplexity.ROUTINE, Sensitivity.STANDARD)
    assert [selected.name, *(f.name for f in selected.fallbacks)] == [
        "pool:fast-a", "pool:fast-b", "pool:deep-a"
    ]


@pytest.mark.parametrize(
    "provider_name", ["pool", "anthropic", "openai-compatible", "hybrid", "ollama"]
)
def test_sensitive_requests_never_select_remote_provider_by_default(
    monkeypatch, provider_name
):
    monkeypatch.setattr(
        "app.intelligence.provider_router.get_settings",
        lambda: pool_settings(model_provider=provider_name),
    )
    monkeypatch.setattr(
        ProviderRouter,
        "_instantiate_pool",
        staticmethod(lambda _model: pytest.fail("sensitive request instantiated pool model")),
    )
    monkeypatch.setattr(
        ProviderRouter,
        "_instantiate",
        staticmethod(lambda _name: pytest.fail("sensitive request instantiated remote provider")),
    )
    selection = ProviderRouter().select(
        TaskComplexity.STRATEGIC, Sensitivity.SENSITIVE
    )
    assert selection.name == "kernel"
    assert not selection.fallbacks


def test_sensitive_remote_opt_in_is_explicit(monkeypatch):
    monkeypatch.setattr(
        "app.intelligence.provider_router.get_settings",
        lambda: pool_settings(intelligence_cloud_for_sensitive=True),
    )
    monkeypatch.setattr(
        ProviderRouter,
        "_instantiate_pool",
        staticmethod(lambda model: NamedProvider(model)),
    )
    selection = ProviderRouter().select(
        TaskComplexity.STRATEGIC, Sensitivity.SENSITIVE
    )
    assert selection.name == "pool:deep-a"


@pytest.mark.asyncio
async def test_runtime_failover_tries_models_in_order_before_kernel(monkeypatch):
    monkeypatch.setattr(
        "app.intelligence.provider_router.get_settings", lambda: pool_settings()
    )
    created = {
        "deep-a": NamedProvider("deep-a", fail=True),
        "fast-a": NamedProvider("fast-a", fail=True),
        "fast-b": NamedProvider("fast-b", response="good result"),
    }
    monkeypatch.setattr(
        ProviderRouter,
        "_instantiate_pool",
        staticmethod(lambda model: created[model]),
    )
    router = ProviderRouter()
    selected = router.select(TaskComplexity.STRATEGIC, Sensitivity.STANDARD)
    routed, response = await router.generate(
        selected, "system", [{"role": "user", "content": "test"}], 128
    )

    assert created["deep-a"].calls == 1
    assert created["fast-a"].calls == 1
    assert created["fast-b"].calls == 1
    assert routed.name == "pool:fast-b"
    assert response == "good result"
    assert not routed.fallbacks


@pytest.mark.asyncio
async def test_pool_exhaustion_falls_back_to_local_kernel(monkeypatch):
    monkeypatch.setattr(
        "app.intelligence.provider_router.get_settings", lambda: pool_settings()
    )
    monkeypatch.setattr(
        ProviderRouter,
        "_instantiate_pool",
        staticmethod(lambda model: NamedProvider(model, fail=True)),
    )
    selected = ProviderRouter().select(TaskComplexity.ROUTINE, Sensitivity.STANDARD)
    routed, response = await ProviderRouter().generate(
        selected, "system", [{"role": "user", "content": "test"}], 128
    )
    assert routed.name == "kernel"
    assert response.strip()


def test_pool_requires_base_url_key_and_at_least_one_model():
    base = {
        "_env_file": None,
        "app_env": "test",
        "persistence_mode": "memory",
        "model_provider": "pool",
        "model_api_key": "hf_test_token",
    }
    with pytest.raises(ValueError, match="MODEL_API_BASE_URL"):
        Settings(**base, model_pool_fast="model-a")

    with pytest.raises(ValueError, match="MODEL_API_KEY"):
        Settings(
            **{**base, "model_api_key": None},
            model_api_base_url="https://router.huggingface.co/v1",
            model_pool_fast="model-a",
        )

    with pytest.raises(ValueError, match="MODEL_POOL"):
        Settings(
            **base,
            model_api_base_url="https://router.huggingface.co/v1",
            model_pool_fast=" , ",
            model_pool_deep="",
        )


def test_pool_openai_client_uses_target_model_timeout_and_disables_internal_retries(
    monkeypatch,
):
    captured = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "app.intelligence.providers.openai_compatible.get_settings",
        lambda: SimpleNamespace(
            model_api_base_url="https://router.huggingface.co/v1",
            model_api_key=SecretStr("hf_test_token"),
            model_timeout_seconds=7,
            model_name="fallback-model",
        ),
    )
    monkeypatch.setattr(
        "app.intelligence.providers.openai_compatible.AsyncOpenAI",
        FakeAsyncOpenAI,
    )

    from app.intelligence.providers.openai_compatible import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(model="deepseek-ai/DeepSeek-R1:fastest", max_retries=0)
    assert provider.model == "deepseek-ai/DeepSeek-R1:fastest"
    assert captured["base_url"] == "https://router.huggingface.co/v1/"
    assert captured["timeout"] == 7
    assert captured["max_retries"] == 0
    assert captured["api_key"] == "hf_test_token"


@pytest.mark.asyncio
async def test_non_pool_remote_failure_still_falls_back_to_kernel():
    class BrokenProvider:
        async def generate(self, system_prompt, messages, max_tokens):
            raise TimeoutError("inference timed out")

    from app.intelligence.provider_router import ProviderSelection

    routed, response = await ProviderRouter().generate(
        ProviderSelection("broken-remote", BrokenProvider()),
        "system",
        [{"role": "user", "content": "test"}],
        128,
    )
    assert routed.name == "kernel"
    assert response.strip()
