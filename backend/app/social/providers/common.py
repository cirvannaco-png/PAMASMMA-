"""Shared provider configuration and errors."""
from typing import Any
from app.config import get_settings
from app.social.contracts import SocialProviderError, Platform

def _env(name: str) -> str:
    field = name.lower()
    value = getattr(get_settings(), field, None)
    if value is None:
        import os
        return os.getenv(name, "").strip()
    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()
    return str(value).strip()

def provider_error(platform: Platform, code: str, message: str, status_code: int = 502) -> SocialProviderError:
    return SocialProviderError(platform, code, message, status_code)
