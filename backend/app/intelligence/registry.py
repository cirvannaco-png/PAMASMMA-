"""Backward-compatible provider registry."""
from app.intelligence.contracts import Sensitivity, TaskComplexity
from app.intelligence.provider_router import ProviderRouter


def get_model_provider():
    """Return the default routed provider for compatibility integrations.

    Cognitive requests should use ProviderRouter with task context.
    """
    return ProviderRouter().select(
        TaskComplexity.MODERATE,
        Sensitivity.STANDARD,
    ).provider
