"""Concrete REST adapters. No provider SDK is required; OAuth and API boundaries stay isolated here."""
import base64
import os
from urllib.parse import urlencode
from typing import Any

from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand, SocialProviderError
from app.social.providers.base import SocialProvider
from app.social.providers.http import HttpProvider


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


class OAuthRestProvider(SocialProvider, HttpProvider):
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
            raise SocialProviderError(self.platform, "oauth_not_configured", f"{self.platform.value} OAuth is not configured.", 503)
        scopes = _env(self.scope_env)
        params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "state": state}
        if scopes:
            params["scope"] = scopes
        return self.auth_url + ("&" if "?" in self.auth_url else "?") + urlencode(params)

    async def exchange_code(self, code: str) -> dict[str, Any]:
        client_id, secret, redirect_uri = _env(self.client_id_env), _env(self.client_secret_env), _env(self.redirect_env)
        if not all((client_id, secret, redirect_uri)):
            raise SocialProviderError(self.platform, "oauth_not_configured", f"{self.platform.value} OAuth is not configured.", 503)
        return await self.request("POST", self.token_url, data={"code": code, "client_id": client_id, "client_secret": secret, "redirect_uri": redirect_uri, "grant_type": "authorization_code"}, headers={"Content-Type":"application/x-www-form-urlencoded"})

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        client_id, secret = _env(self.client_id_env), _env(self.client_secret_env)
        return await self.request("POST", self.token_url, data={"refresh_token": refresh_token, "client_id": client_id, "client_secret": secret, "grant_type": "refresh_token"}, headers={"Content-Type":"application/x-www-form-urlencoded"})


class XProvider(OAuthRestProvider):
    platform=Platform.X; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_WRITE,Capability.COMMENTS_READ,Capability.MENTIONS_READ,Capability.ANALYTICS})
    auth_url="https://x.com/i/oauth2/authorize"; token_url="https://api.x.com/2/oauth2/token"
    client_id_env="SOCIAL_X_CLIENT_ID"; client_secret_env="SOCIAL_X_CLIENT_SECRET"; redirect_env="SOCIAL_X_REDIRECT_URI"; scope_env="SOCIAL_X_SCOPES"
    async def publish(self, token, command, external_account_id):
        self.require(Capability.PUBLISH)
        body={"text":command.text}
        if command.reply_to_id: body["reply"]={"in_reply_to_tweet_id":command.reply_to_id}
        return await self.request("POST","https://api.x.com/2/tweets",token=token,json_body=body)
    async def reply(self, token, command):
        return await self.publish(token, PublishCommand(account_id="", text=command.text, reply_to_id=command.item_id), "")
    async def list_engagement(self, token, external_account_id, cursor=None):
        query=f"to:{external_account_id} OR @{external_account_id}"
        return await self.request("GET","https://api.x.com/2/tweets/search/recent",token=token,params={"query":query,"tweet.fields":"created_at,author_id,public_metrics","max_results":100,**({"next_token":cursor} if cursor else {})})


class LinkedInProvider(OAuthRestProvider):
    platform=Platform.LINKEDIN; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE,Capability.ANALYTICS,Capability.ADS_READ})
    auth_url="https://www.linkedin.com/oauth/v2/authorization"; token_url="https://www.linkedin.com/oauth/v2/accessToken"
    client_id_env="SOCIAL_LINKEDIN_CLIENT_ID"; client_secret_env="SOCIAL_LINKEDIN_CLIENT_SECRET"; redirect_env="SOCIAL_LINKEDIN_REDIRECT_URI"; scope_env="SOCIAL_LINKEDIN_SCOPES"
    def _headers(self): return {"Linkedin-Version":_env("SOCIAL_LINKEDIN_VERSION") or "202603","X-Restli-Protocol-Version":"2.0.0"}
    async def publish(self, token, command, external_account_id):
        body={"author":external_account_id,"commentary":command.text,"visibility":"PUBLIC","distribution":{"feedDistribution":"MAIN_FEED"},"lifecycleState":"PUBLISHED","isReshareDisabledByAuthor":False}
        return await self.request("POST","https://api.linkedin.com/rest/posts",token=token,json_body=body,headers=self._headers())
    async def reply(self, token, command):
        body={"actor":"","object":command.item_id,"message":{"text":command.text}}
        return await self.request("POST",f"https://api.linkedin.com/rest/socialActions/{command.item_id}/comments",token=token,json_body=body,headers=self._headers())
    async def list_engagement(self, token, external_account_id, cursor=None):
        return await self.request("GET",f"https://api.linkedin.com/rest/socialActions/{external_account_id}/comments",token=token,headers=self._headers())


class YouTubeProvider(OAuthRestProvider):
    platform=Platform.YOUTUBE; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE,Capability.ANALYTICS})
    auth_url="https://accounts.google.com/o/oauth2/v2/auth"; token_url="https://oauth2.googleapis.com/token"
    client_id_env="SOCIAL_YOUTUBE_CLIENT_ID"; client_secret_env="SOCIAL_YOUTUBE_CLIENT_SECRET"; redirect_env="SOCIAL_YOUTUBE_REDIRECT_URI"; scope_env="SOCIAL_YOUTUBE_SCOPES"
    async def publish(self, token, command, external_account_id):
        video_path=command.platform_options.get("video_path")
        if not video_path:
            raise SocialProviderError(self.platform,"media_required","YouTube publishing requires platform_options.video_path for videos.",422)
        import pathlib
        path=pathlib.Path(str(video_path))
        if not path.is_file(): raise SocialProviderError(self.platform,"media_not_found","Video file was not found on the server.",422)
        metadata={"snippet":{"title":command.title or command.text[:100],"description":command.text},"status":{"privacyStatus":command.platform_options.get("privacy_status","private")}}
        headers={"Authorization":f"Bearer {token}","X-Upload-Content-Type":command.media_type or "video/mp4","Content-Type":"application/json; charset=UTF-8"}
        async with __import__("httpx").AsyncClient(timeout=120) as client:
            init=await client.post("https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=resumable",headers=headers,json=metadata)
            if init.status_code>=400: raise SocialProviderError(self.platform,"provider_error",init.text[:1000],init.status_code)
            upload_url=init.headers.get("location")
            if not upload_url: raise SocialProviderError(self.platform,"provider_error","YouTube did not return an upload URL.",502)
            response=await client.put(upload_url,headers={"Authorization":f"Bearer {token}","Content-Type":command.media_type or "video/mp4"},content=path.read_bytes())
            if response.status_code>=400: raise SocialProviderError(self.platform,"provider_error",response.text[:1000],response.status_code)
            return response.json()
    async def reply(self, token, command):
        return await self.request("POST","https://www.googleapis.com/youtube/v3/comments?part=snippet",token=token,json_body={"snippet":{"parentId":command.item_id,"textOriginal":command.text}})
    async def list_engagement(self, token, external_account_id, cursor=None):
        return await self.request("GET","https://www.googleapis.com/youtube/v3/commentThreads",token=token,params={"part":"snippet,replies","allThreadsRelatedToChannelId":external_account_id,"maxResults":100,**({"pageToken":cursor} if cursor else {})})
    async def analytics(self, token, external_account_id, start=None, end=None):
        return await self.request("GET","https://youtubeanalytics.googleapis.com/v2/reports",token=token,params={"ids":f"channel=={external_account_id}","startDate":start or "2000-01-01","endDate":end or "2100-01-01","metrics":"views,likes,comments,shares,subscribersGained,subscribersLost","dimensions":"day"})


class PinterestProvider(OAuthRestProvider):
    platform=Platform.PINTEREST; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.ANALYTICS,Capability.ADS_READ,Capability.ADS_WRITE})
    auth_url="https://www.pinterest.com/oauth/"; token_url="https://api.pinterest.com/v5/oauth/token"
    client_id_env="SOCIAL_PINTEREST_APP_ID"; client_secret_env="SOCIAL_PINTEREST_APP_SECRET"; redirect_env="SOCIAL_PINTEREST_REDIRECT_URI"; scope_env="SOCIAL_PINTEREST_SCOPES"
    async def publish(self, token, command, external_account_id):
        if not command.media_url: raise SocialProviderError(self.platform,"media_required","Pinterest Pins require media_url.",422)
        return await self.request("POST","https://api.pinterest.com/v5/pins",token=token,json_body={"board_id":command.platform_options.get("board_id"),"title":command.title,"description":command.text,"alt_text":command.platform_options.get("alt_text"),"link":str(command.link_url) if command.link_url else None,"media_source":{"source_type":"image_url","url":str(command.media_url)}})


class MetaProvider(OAuthRestProvider):
    platform=Platform.FACEBOOK; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE,Capability.MENTIONS_READ,Capability.ANALYTICS,Capability.ADS_READ,Capability.ADS_WRITE})
    auth_url="https://www.facebook.com/v{version}/dialog/oauth"; token_url="https://graph.facebook.com/v{version}/oauth/access_token"
    client_id_env="SOCIAL_META_CLIENT_ID"; client_secret_env="SOCIAL_META_CLIENT_SECRET"; redirect_env="SOCIAL_META_REDIRECT_URI"; scope_env="SOCIAL_META_SCOPES"
    def _base(self): return f"https://graph.facebook.com/{_env('SOCIAL_META_GRAPH_VERSION') or 'v23.0'}"
    def authorization_url(self,state):
        self.auth_url=f"https://www.facebook.com/{_env('SOCIAL_META_GRAPH_VERSION') or 'v23.0'}/dialog/oauth"; return super().authorization_url(state)
    async def exchange_code(self,code):
        self.token_url=f"{self._base()}/oauth/access_token"; return await super().exchange_code(code)
    async def publish(self, token, command, external_account_id):
        body={"message":command.text}
        if command.link_url: body["link"]=str(command.link_url)
        return await self.request("POST",f"{self._base()}/{external_account_id}/feed",token=token,data=body,headers={"Content-Type":"application/x-www-form-urlencoded"})
    async def reply(self, token, command): return await self.request("POST",f"{self._base()}/{command.item_id}/comments",token=token,data={"message":command.text},headers={"Content-Type":"application/x-www-form-urlencoded"})
    async def list_engagement(self, token, external_account_id, cursor=None): return await self.request("GET",f"{self._base()}/{external_account_id}/feed",token=token,params={"fields":"id,message,comments.limit(100){message,from,created_time}","limit":100,**({"after":cursor} if cursor else {})})
    async def analytics(self, token, external_account_id, start=None, end=None): return await self.request("GET",f"{self._base()}/{external_account_id}/insights",token=token,params={"metric":"page_impressions,page_engaged_users,page_post_engagements"})
    async def create_campaign(self, token, account_id, payload): return await self.request("POST",f"{self._base()}/act_{account_id}/campaigns",token=token,data={k:str(v).lower() if isinstance(v,bool) else str(v) for k,v in payload.items()},headers={"Content-Type":"application/x-www-form-urlencoded"})


class InstagramProvider(MetaProvider):
    platform=Platform.INSTAGRAM; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE,Capability.MENTIONS_READ,Capability.ANALYTICS})
    async def publish(self, token, command, external_account_id):
        if not command.media_url: raise SocialProviderError(self.platform,"media_required","Instagram publishing requires media_url.",422)
        container={"image_url":str(command.media_url),"caption":command.text}
        if (command.media_type or "").startswith("video"): container={"video_url":str(command.media_url),"caption":command.text,"media_type":"REELS"}
        created=await self.request("POST",f"{self._base()}/{external_account_id}/media",token=token,data=container,headers={"Content-Type":"application/x-www-form-urlencoded"})
        return await self.request("POST",f"{self._base()}/{external_account_id}/media_publish",token=token,data={"creation_id":created.get("id","")},headers={"Content-Type":"application/x-www-form-urlencoded"})


class ThreadsProvider(OAuthRestProvider):
    platform=Platform.THREADS; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE,Capability.ANALYTICS})
    auth_url="https://threads.net/oauth/authorize"; token_url="https://graph.threads.net/oauth/access_token"
    client_id_env="SOCIAL_THREADS_CLIENT_ID"; client_secret_env="SOCIAL_THREADS_CLIENT_SECRET"; redirect_env="SOCIAL_THREADS_REDIRECT_URI"; scope_env="SOCIAL_THREADS_SCOPES"
    async def publish(self, token, command, external_account_id):
        created=await self.request("POST",f"https://graph.threads.net/v1.0/{external_account_id}/threads",token=token,data={"media_type":"TEXT","text":command.text},headers={"Content-Type":"application/x-www-form-urlencoded"})
        return await self.request("POST",f"https://graph.threads.net/v1.0/{external_account_id}/threads_publish",token=token,data={"creation_id":created.get("id","")},headers={"Content-Type":"application/x-www-form-urlencoded"})
    async def reply(self, token, command): return await self.request("POST",f"https://graph.threads.net/v1.0/{command.item_id}/replies",token=token,data={"text":command.text},headers={"Content-Type":"application/x-www-form-urlencoded"})


class TikTokProvider(OAuthRestProvider):
    platform=Platform.TIKTOK; capabilities=frozenset({Capability.PUBLISH})
    auth_url="https://www.tiktok.com/v2/auth/authorize/"; token_url="https://open.tiktokapis.com/v2/oauth/token/"
    client_id_env="SOCIAL_TIKTOK_CLIENT_KEY"; client_secret_env="SOCIAL_TIKTOK_CLIENT_SECRET"; redirect_env="SOCIAL_TIKTOK_REDIRECT_URI"; scope_env="SOCIAL_TIKTOK_SCOPES"
    async def publish(self, token, command, external_account_id):
        if not command.media_url: raise SocialProviderError(self.platform,"media_required","TikTok publishing requires media_url.",422)
        is_photo=(command.media_type or "").startswith("image")
        endpoint="https://open.tiktokapis.com/v2/post/publish/content/init/" if is_photo else "https://open.tiktokapis.com/v2/post/publish/video/init/"
        body={"post_info":{"title":command.text,"privacy_level":command.platform_options.get("privacy_level","SELF_ONLY")}}
        body["source_info"]={"source":"PULL_FROM_URL","photo_cover_index":0,"photo_images":[str(command.media_url)]} if is_photo else {"source":"PULL_FROM_URL","video_url":str(command.media_url)}
        return await self.request("POST",endpoint,token=token,json_body=body)


class RedditProvider(OAuthRestProvider):
    platform=Platform.REDDIT; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE,Capability.MENTIONS_READ})
    auth_url="https://www.reddit.com/api/v1/authorize"; token_url="https://www.reddit.com/api/v1/access_token"
    client_id_env="SOCIAL_REDDIT_CLIENT_ID"; client_secret_env="SOCIAL_REDDIT_CLIENT_SECRET"; redirect_env="SOCIAL_REDDIT_REDIRECT_URI"; scope_env="SOCIAL_REDDIT_SCOPES"
    async def exchange_code(self,code):
        client_id,secret,redirect_uri=_env(self.client_id_env),_env(self.client_secret_env),_env(self.redirect_env)
        basic=base64.b64encode(f"{client_id}:{secret}".encode()).decode()
        return await self.request("POST",self.token_url,data={"code":code,"redirect_uri":redirect_uri,"grant_type":"authorization_code"},headers={"Authorization":f"Basic {basic}","Content-Type":"application/x-www-form-urlencoded","User-Agent":"PAMASMMA/1.0"})
    async def publish(self,token,command,external_account_id): return await self.request("POST","https://oauth.reddit.com/api/submit",token=token,data={"sr":command.platform_options["subreddit"],"title":command.title or command.text[:300],"text":command.text,"kind":"self"},headers={"Content-Type":"application/x-www-form-urlencoded","User-Agent":"PAMASMMA/1.0"})
    async def reply(self,token,command): return await self.request("POST","https://oauth.reddit.com/api/comment",token=token,data={"thing_id":command.item_id,"text":command.text},headers={"Content-Type":"application/x-www-form-urlencoded","User-Agent":"PAMASMMA/1.0"})
    async def list_engagement(self,token,external_account_id,cursor=None): return await self.request("GET",f"https://oauth.reddit.com/user/{external_account_id}/comments",token=token,params={"limit":100,"after":cursor} if cursor else {"limit":100},headers={"User-Agent":"PAMASMMA/1.0"})


class TelegramProvider(SocialProvider):
    platform=Platform.TELEGRAM; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE,Capability.ANALYTICS})
    def authorization_url(self,state): raise SocialProviderError(self.platform,"oauth_not_applicable","Telegram uses a bot token rather than user OAuth.",422)
    async def exchange_code(self,code): raise SocialProviderError(self.platform,"oauth_not_applicable","Telegram uses a bot token rather than user OAuth.",422)
    async def publish(self,token,command,external_account_id): return await HttpProvider.request(self, "POST", f"https://api.telegram.org/bot{token}/sendMessage", json_body={"chat_id":external_account_id,"text":command.text})


class WhatsAppProvider(SocialProvider):
    platform=Platform.WHATSAPP; capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE})
    def authorization_url(self,state): raise SocialProviderError(self.platform,"oauth_not_applicable","WhatsApp Business uses Meta business credentials/configuration.",422)
    async def exchange_code(self,code): raise SocialProviderError(self.platform,"oauth_not_applicable","Use Meta Business configuration for WhatsApp.",422)
    async def publish(self,token,command,external_account_id):
        phone_id=external_account_id; version=_env("SOCIAL_META_GRAPH_VERSION") or "v23.0"; return await self.request("POST",f"https://graph.facebook.com/{version}/{phone_id}/messages",token=token,json_body={"messaging_product":"whatsapp","to":command.platform_options["to"],"type":"text","text":{"body":command.text}})


PROVIDERS: dict[Platform, SocialProvider]= {p: c() for p,c in {
    Platform.FACEBOOK:MetaProvider,Platform.INSTAGRAM:InstagramProvider,Platform.TIKTOK:TikTokProvider,Platform.YOUTUBE:YouTubeProvider,Platform.LINKEDIN:LinkedInProvider,Platform.X:XProvider,Platform.THREADS:ThreadsProvider,Platform.PINTEREST:PinterestProvider,Platform.REDDIT:RedditProvider,Platform.TELEGRAM:TelegramProvider,Platform.WHATSAPP:WhatsAppProvider}.items()}

def get_provider(platform: Platform) -> SocialProvider: return PROVIDERS[platform]
