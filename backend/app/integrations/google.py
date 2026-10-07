"""Google Workspace OAuth and Gmail/Drive API client."""
import base64
import json
from email.message import EmailMessage
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import get_settings

settings = get_settings()
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
DRIVE_URL = "https://www.googleapis.com/drive/v3"
GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_SCOPES = (
    "openid email profile "
    "https://www.googleapis.com/auth/gmail.modify "
    "https://www.googleapis.com/auth/drive"
)


class GoogleProviderError(RuntimeError):
    """Raised when Google OAuth or API operations fail."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def authorization_url(state: str) -> str:
    if not settings.google_client_id or not settings.google_redirect_uri:
        raise GoogleProviderError("Google OAuth is not configured.", 503)

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


async def exchange_code(code: str) -> dict[str, Any]:
    if (
        not settings.google_client_id
        or not settings.google_client_secret
        or not settings.google_redirect_uri
    ):
        raise GoogleProviderError("Google OAuth is not configured.", 503)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.is_error:
        raise GoogleProviderError("Google token exchange failed.", 502)
    return response.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    if not settings.google_client_id or not settings.google_client_secret:
        raise GoogleProviderError("Google OAuth refresh is not configured.", 503)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
    if response.is_error:
        raise GoogleProviderError("Google token refresh failed.", 502)
    return response.json()


async def userinfo(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.is_error:
        raise GoogleProviderError("Google identity lookup failed.", 502)
    return response.json()


async def request_json(
    method: str,
    url: str,
    access_token: str,
    **kwargs: Any,
) -> dict[str, Any]:
    headers = dict(kwargs.pop("headers", {}))
    headers["Authorization"] = f"Bearer {access_token}"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.request(
            method,
            url,
            headers=headers,
            **kwargs,
        )
    if response.is_error:
        raise GoogleProviderError(
            f"Google API request failed: {response.text[:1000]}",
            response.status_code,
        )
    return response.json() if response.content else {}


def encode_raw_message(payload: dict[str, Any]) -> str:
    message = EmailMessage()
    for field in ("to", "cc", "bcc"):
        values = payload.get(field) or []
        if isinstance(values, str):
            values = [values]
        if values:
            message[field.title()] = ", ".join(values)

    message["Subject"] = str(payload["subject"])
    message.set_content(str(payload["body"]))
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")


async def list_messages(
    access_token: str,
    query: str | None,
    max_results: int = 50,
) -> dict[str, Any]:
    params: dict[str, Any] = {"maxResults": max_results}
    if query:
        params["q"] = query
    return await request_json(
        "GET",
        f"{GMAIL_URL}/messages",
        access_token,
        params=params,
    )


async def get_message(
    access_token: str,
    message_id: str,
) -> dict[str, Any]:
    return await request_json(
        "GET",
        f"{GMAIL_URL}/messages/{message_id}",
        access_token,
        params={"format": "full"},
    )


async def send_message(
    access_token: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return await request_json(
        "POST",
        f"{GMAIL_URL}/messages/send",
        access_token,
        json={"raw": encode_raw_message(payload)},
    )


async def list_drive(
    access_token: str,
    query: str | None,
    page_size: int = 100,
) -> dict[str, Any]:
    params = {
        "pageSize": page_size,
        "fields": (
            "files(id,name,mimeType,size,modifiedTime,webViewLink),"
            "nextPageToken"
        ),
        "q": query or "trashed = false",
    }
    return await request_json(
        "GET",
        f"{DRIVE_URL}/files",
        access_token,
        params=params,
    )


async def get_drive_file(
    access_token: str,
    file_id: str,
) -> dict[str, Any]:
    return await request_json(
        "GET",
        f"{DRIVE_URL}/files/{file_id}",
        access_token,
        params={
            "fields": (
                "id,name,mimeType,size,modifiedTime,webViewLink,parents"
            )
        },
    )


async def delete_drive_file(
    access_token: str,
    file_id: str,
) -> dict[str, Any]:
    return await request_json(
        "DELETE",
        f"{DRIVE_URL}/files/{file_id}",
        access_token,
    )


async def upload_drive_file(
    access_token: str,
    name: str,
    mime_type: str,
    content: bytes,
    parent_id: str | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {"name": name}
    if parent_id:
        metadata["parents"] = [parent_id]

    boundary = "pamasmma-google-upload"
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        + json.dumps(metadata)
        + f"\r\n--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "https://www.googleapis.com/upload/drive/v3/files"
            "?uploadType=multipart"
            "&fields=id,name,mimeType,size,modifiedTime,webViewLink",
            headers=headers,
            content=body,
        )
    if response.is_error:
        raise GoogleProviderError(
            "Google Drive upload failed.",
            response.status_code,
        )
    return response.json()
