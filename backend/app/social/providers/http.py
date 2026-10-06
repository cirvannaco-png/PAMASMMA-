"""Small async HTTP primitive shared by all provider adapters."""
from typing import Any, cast

import httpx

from app.social.contracts import Platform, SocialProviderError


class HttpProvider:
    def __init__(self, platform: Platform, timeout: float = 30.0) -> None:
        self.platform = platform
        self.timeout = timeout

    async def request(self, method: str, url: str, *, token: str | None = None, json_body: dict[str, Any] | None = None, data: dict[str, Any] | None = None, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        request_headers = {"Accept": "application/json"}
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        if headers:
            request_headers.update(headers)
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.request(method, url, headers=request_headers, json=json_body, data=data, params=params)
        except httpx.HTTPError as exc:
            raise SocialProviderError(self.platform, "network_error", str(exc), 502) from exc
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = {"raw": response.text[:1000]}
            raise SocialProviderError(self.platform, "provider_error", str(detail), response.status_code)
        if not response.content:
            return {}
        try:
            return cast(dict[str, Any], response.json())
        except ValueError as exc:
            raise SocialProviderError(self.platform, "invalid_provider_response", "Provider returned a non-JSON response.", 502) from exc
