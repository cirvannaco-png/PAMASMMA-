"""Shared OAuth transport for social providers."""
from typing import Any
from urllib.parse import urlencode

from app.social.providers.base import SocialProvider
from app.social.providers.common import _env, provider_error
from app.social.providers.http import HttpProvider


class OAuthRestProvider(SocialProvider, HttpProvider):
    """Shared OAuth 2.0 transport for providers using conventional flows."""

    auth_url: str = ""
    token_url: str = ""
    client_id_env: str = ""
    client_secret_env: str = ""
    redirect_env: str = ""
    scope_env: str = ""

    def __init__(self) -> None:
        HttpProvider.__init__(self, self.platform)

    def authorization_url(self, state: str) -> str:
        client_id = _env(self.client_id_env)
        redirect_uri = _env(self.redirect_env)
        if not client_id or not redirect_uri:
            raise provider_error(
                self.platform,
                "oauth_not_configured",
                f"{self.platform.value} OAuth is not configured.",
                503,
            )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        scopes = _env(self.scope_env)
        if scopes:
            params["scope"] = scopes
        query = urlencode(params)
        separator = "&" if "?" in self.auth_url else "?"
        return f"{self.auth_url}{separator}{query}"

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        del state
        client_id = _env(self.client_id_env)
        secret = _env(self.client_secret_env)
        redirect_uri = _env(self.redirect_env)
        if not all((client_id, secret, redirect_uri)):
            raise provider_error(
                self.platform,
                "oauth_not_configured",
                f"{self.platform.value} OAuth is not configured.",
                503,
            )

        return await self.request(
            "POST",
            self.token_url,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        client_id = _env(self.client_id_env)
        secret = _env(self.client_secret_env)
        if not refresh_token or not client_id or not secret:
            raise provider_error(
                self.platform,
                "oauth_refresh_not_configured",
                f"{self.platform.value} OAuth refresh credentials are not configured.",
                503,
            )
        return await self.request(
            "POST",
            self.token_url,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": secret,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
