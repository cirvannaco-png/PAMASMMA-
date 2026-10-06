"""Telegram Bot API adapter."""
from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand
from app.social.providers.base import SocialProvider
from app.social.providers.http import HttpProvider
class TelegramProvider(SocialProvider):
    def __init__(self): self.platform=Platform.TELEGRAM; self.http=HttpProvider(self.platform); self.capabilities=frozenset({Capability.PUBLISH,Capability.COMMENTS_READ,Capability.COMMENTS_WRITE})
    def authorization_url(self,state): raise NotImplementedError("Telegram bots use bot-token configuration, not OAuth.")
    async def exchange_code(self,code): raise NotImplementedError("Telegram bots use bot-token configuration, not OAuth.")
    async def publish(self,token,command,external_account_id): return await self.http.request("POST",f"https://api.telegram.org/bot{token}/sendMessage",json_body={"chat_id":external_account_id,"text":command.text,"disable_web_page_preview":True})
    async def reply(self,token,command): return await self.http.request("POST",f"https://api.telegram.org/bot{token}/sendMessage",json_body={"chat_id":command.platform_options.get("chat_id"),"text":command.text,"reply_parameters":{"message_id":int(command.item_id)}})
    async def list_engagement(self,token,external_account_id,cursor=None): raise NotImplementedError("Telegram engagement should arrive through Bot API webhooks/updates.")
    async def analytics(self,token,external_account_id,start=None,end=None): raise NotImplementedError("Telegram Bot API does not expose native post analytics.")
