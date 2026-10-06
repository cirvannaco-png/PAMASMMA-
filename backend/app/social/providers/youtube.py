"""YouTube platform adapter."""
from typing import Any
import httpx
from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand
from app.social.providers.oauth import OAuthRestProvider
from app.social.providers.common import provider_error
class YouTubeProvider(OAuthRestProvider):
    """YouTube Data API and Analytics API adapter."""

    platform = Platform.YOUTUBE
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
            Capability.ANALYTICS,
        }
    )
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    client_id_env = "SOCIAL_YOUTUBE_CLIENT_ID"
    client_secret_env = "SOCIAL_YOUTUBE_CLIENT_SECRET"
    redirect_env = "SOCIAL_YOUTUBE_REDIRECT_URI"
    scope_env = "SOCIAL_YOUTUBE_SCOPES"

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        del external_account_id
        video_path = command.platform_options.get("video_path")
        if not video_path:
            raise _provider_error(
                self.platform,
                "media_required",
                "YouTube publishing requires platform_options.video_path.",
                422,
            )

        path = __import__("pathlib").Path(str(video_path))
        if not path.is_file():
            raise _provider_error(
                self.platform,
                "media_not_found",
                "Video file was not found on the server.",
                422,
            )

        metadata = {
            "snippet": {
                "title": command.title or command.text[:100],
                "description": command.text,
            },
            "status": {
                "privacyStatus": command.platform_options.get(
                    "privacy_status",
                    "private",
                )
            },
        }
        upload_type = command.media_type or "video/mp4"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Upload-Content-Type": upload_type,
            "Content-Type": "application/json; charset=UTF-8",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos"
                "?part=snippet,status&uploadType=resumable",
                headers=headers,
                json=metadata,
            )
            if response.status_code >= 400:
                raise _provider_error(
                    self.platform,
                    "provider_error",
                    response.text[:1000],
                    response.status_code,
                )

            upload_url = response.headers.get("location")
            if not upload_url:
                raise _provider_error(
                    self.platform,
                    "provider_error",
                    "YouTube did not return an upload URL.",
                )

            upload = await client.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": upload_type,
                },
                content=path.read_bytes(),
            )
            if upload.status_code >= 400:
                raise _provider_error(
                    self.platform,
                    "provider_error",
                    upload.text[:1000],
                    upload.status_code,
                )
            return upload.json()

    async def reply(
        self,
        token: str,
        command: ReplyCommand,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "https://www.googleapis.com/youtube/v3/comments?part=snippet",
            token=token,
            json_body={
                "snippet": {
                    "parentId": command.item_id,
                    "textOriginal": command.text,
                }
            },
        )

    async def list_engagement(
        self,
        token: str,
        external_account_id: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "part": "snippet,replies",
            "allThreadsRelatedToChannelId": external_account_id,
            "maxResults": 100,
        }
        if cursor:
            params["pageToken"] = cursor
        return await self.request(
            "GET",
            "https://www.googleapis.com/youtube/v3/commentThreads",
            token=token,
            params=params,
        )

    async def analytics(
        self,
        token: str,
        external_account_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "https://youtubeanalytics.googleapis.com/v2/reports",
            token=token,
            params={
                "ids": f"channel=={external_account_id}",
                "startDate": start or "2000-01-01",
                "endDate": end or "2100-01-01",
                "metrics": (
                    "views,likes,comments,shares,"
                    "subscribersGained,subscribersLost"
                ),
                "dimensions": "day",
            },
        )