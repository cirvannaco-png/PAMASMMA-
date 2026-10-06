"""Persistence and governance services for the social subsystem."""
from datetime import UTC, datetime
import uuid
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.runtime import memory_store
from app.security.crypto import decrypt_secret, encrypt_secret
from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand
from app.social.providers.adapters import get_provider

settings = get_settings()


def _now() -> datetime:
    return datetime.now(UTC)


def _token_value(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    return None


def _capabilities(platform: Platform) -> list[str]:
    return [cap.value for cap in get_provider(platform).capabilities]


async def create_account(user_id: str, platform: Platform, token_data: dict[str, Any], external_account_id: str | None = None, display_name: str | None = None) -> dict[str, Any]:
    access = _token_value(token_data, "access_token", "token")
    if not access:
        raise ValueError("OAuth response did not contain an access token.")
    refresh = _token_value(token_data, "refresh_token")
    expires_in = token_data.get("expires_in")
    expiry = datetime.fromtimestamp(_now().timestamp() + int(expires_in), UTC) if expires_in else None
    external_id = external_account_id or _token_value(token_data, "user_id", "id", "sub")
    if not external_id:
        raise ValueError("An external account id is required for this provider.")
    scopes = str(token_data.get("scope", "")).split()
    provider = get_provider(platform)
    record = {"id": uuid.uuid4(), "user_id": user_id, "platform": platform.value, "external_account_id": external_id, "display_name": display_name or token_data.get("name") or token_data.get("username"), "access_token_enc": encrypt_secret(access), "refresh_token_enc": encrypt_secret(refresh) if refresh else None, "token_expires_at": expiry, "scopes": scopes, "metadata": token_data.get("metadata", {}), "status": "active", "created_at": _now(), "updated_at": _now()}
    if not settings.is_persistent:
        memory_store.social_accounts[:] = [a for a in memory_store.social_accounts if not (a["user_id"] == user_id and a["platform"] == platform.value and a["external_account_id"] == external_id)]
        memory_store.social_accounts.append(record)
    else:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            await session.execute(text("""INSERT INTO pamasmma_social_accounts (id,user_id,platform,external_account_id,display_name,access_token_enc,refresh_token_enc,token_expires_at,scopes,metadata,status) VALUES (:id,:user_id,:platform,:external_account_id,:display_name,:access_token_enc,:refresh_token_enc,:token_expires_at,:scopes,:metadata,:status) ON CONFLICT DO NOTHING"""), record)
            await session.commit()
    return public_account(record, provider.capabilities)


def public_account(record: dict[str, Any], capabilities=None) -> dict[str, Any]:
    provider_caps = capabilities if capabilities is not None else _capabilities(Platform(record["platform"]))
    return {"id": str(record["id"]), "platform": record["platform"], "external_account_id": record["external_account_id"], "display_name": record.get("display_name"), "status": record.get("status", "active"), "scopes": record.get("scopes", []), "capabilities": [c.value if hasattr(c, "value") else c for c in provider_caps]}


async def list_accounts(user_id: str) -> list[dict[str, Any]]:
    if not settings.is_persistent:
        return [public_account(a) for a in memory_store.social_accounts if a["user_id"] == user_id]
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(text("SELECT id,platform,external_account_id,display_name,status,scopes FROM pamasmma_social_accounts WHERE user_id=:u ORDER BY created_at DESC"), {"u": user_id})).mappings().all()
    return [{"id": str(r["id"]), "platform": r["platform"], "external_account_id": r["external_account_id"], "display_name": r["display_name"], "status": r["status"], "scopes": r["scopes"] or [], "capabilities": _capabilities(Platform(r["platform"]))} for r in rows]


async def get_account(user_id: str, account_id: str) -> dict[str, Any] | None:
    if not settings.is_persistent:
        return next((a for a in memory_store.social_accounts if str(a["id"]) == account_id and a["user_id"] == user_id), None)
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        row = (await session.execute(text("SELECT * FROM pamasmma_social_accounts WHERE id=:id AND user_id=:u"), {"id": account_id, "u": user_id})).mappings().first()
    return dict(row) if row else None


async def delete_account(user_id: str, account_id: str) -> bool:
    account = await get_account(user_id, account_id)
    if not account:
        return False
    if not settings.is_persistent:
        memory_store.social_accounts[:] = [a for a in memory_store.social_accounts if str(a["id"]) != account_id]
    else:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            await session.execute(text("DELETE FROM pamasmma_social_accounts WHERE id=:id AND user_id=:u"), {"id": account_id, "u": user_id})
            await session.commit()
    return True


async def _persist_post(post: dict[str, Any]) -> None:
    if not settings.is_persistent:
        memory_store.social_posts.append(post)
        return
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(text("INSERT INTO pamasmma_social_posts (id,account_id,platform_post_id,status,content,scheduled_at,published_at,metrics,error) VALUES (:id,:account_id,:platform_post_id,:status,:content,:scheduled_at,:published_at,:metrics,:error)"), post)
        await session.commit()


async def publish_now(user_id: str, command: PublishCommand) -> dict[str, Any]:
    account = await get_account(user_id, command.account_id)
    if not account:
        raise ValueError("Social account not found.")
    platform = Platform(account["platform"])
    result = await get_provider(platform).publish(decrypt_secret(account["access_token_enc"]), command, account["external_account_id"])
    post = {"id": uuid.uuid4(), "account_id": account["id"], "platform_post_id": _token_value(result, "id", "post_id", "uri"), "status": "published", "content": command.model_dump(mode="json"), "scheduled_at": None, "published_at": _now(), "metrics": {}, "error": None, "created_at": _now()}
    await _persist_post(post)
    return {"status": "published", "post_id": str(post["id"]), "platform_post_id": post["platform_post_id"], "provider_response": result}


async def queue_post(user_id: str, command: PublishCommand, scheduled_at: datetime) -> dict[str, Any]:
    account = await get_account(user_id, command.account_id)
    if not account:
        raise ValueError("Social account not found.")
    post = {"id": uuid.uuid4(), "account_id": account["id"], "platform_post_id": None, "status": "queued", "content": command.model_dump(mode="json"), "scheduled_at": scheduled_at, "published_at": None, "metrics": {}, "error": None, "created_at": _now()}
    await _persist_post(post)
    return {"status": "queued", "post_id": str(post["id"]), "scheduled_at": scheduled_at.isoformat()}


async def process_due_posts() -> int:
    if not settings.is_persistent:
        due = [p for p in memory_store.social_posts if p["status"] == "queued" and p.get("scheduled_at") and p["scheduled_at"] <= _now()]
    else:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            due = [dict(r) for r in (await session.execute(text("SELECT * FROM pamasmma_social_posts WHERE status='queued' AND scheduled_at <= now() ORDER BY scheduled_at LIMIT 50"))).mappings().all()]
    count = 0
    for post in due:
        try:
            if settings.is_persistent:
                assert AsyncSessionLocal is not None
                async with AsyncSessionLocal() as session:
                    row = (await session.execute(text("SELECT a.*, p.content FROM pamasmma_social_accounts a JOIN pamasmma_social_posts p ON p.account_id=a.id WHERE p.id=:id"), {"id": post["id"]})).mappings().first()
                account = dict(row) if row else None
            else:
                account = next((a for a in memory_store.social_accounts if a["id"] == post["account_id"]), None)
            if not account:
                continue
            command = PublishCommand.model_validate(post["content"])
            result = await get_provider(Platform(account["platform"])).publish(decrypt_secret(account["access_token_enc"]), command, account["external_account_id"])
            pid = _token_value(result, "id", "post_id", "uri")
            if settings.is_persistent:
                assert AsyncSessionLocal is not None
                async with AsyncSessionLocal() as session:
                    await session.execute(text("UPDATE pamasmma_social_posts SET status='published', platform_post_id=:pid, published_at=now(), error=NULL WHERE id=:id"), {"pid": pid, "id": post["id"]})
                    await session.commit()
            else:
                post.update({"status":"published","platform_post_id":pid,"published_at":_now(),"error":None})
            count += 1
        except Exception as exc:
            if settings.is_persistent:
                assert AsyncSessionLocal is not None
                async with AsyncSessionLocal() as session:
                    await session.execute(text("UPDATE pamasmma_social_posts SET status='failed', error=:e WHERE id=:id"), {"e": str(exc)[:2000], "id": post["id"]})
                    await session.commit()
            else:
                post.update({"status":"failed","error":str(exc)[:2000]})
    return count


def classify_engagement(text_value: str | None) -> tuple[str, str, str]:
    value = (text_value or "").lower()
    if any(x in value for x in ("price", "cost", "buy", "order", "available", "how much")): return "lead", "neutral", "high"
    if any(x in value for x in ("refund", "charged", "broken", "complaint", "angry", "scam", "problem")): return "complaint", "negative", "urgent"
    if any(x in value for x in ("love", "great", "amazing", "thanks", "beautiful")): return "praise", "positive", "normal"
    if any(x in value for x in ("how", "what", "when", "where", "can i")): return "question", "neutral", "normal"
    return "conversation", "neutral", "normal"


async def sync_engagement(user_id: str, account_id: str) -> dict[str, Any]:
    account = await get_account(user_id, account_id)
    if not account: raise ValueError("Social account not found.")
    data = await get_provider(Platform(account["platform"])).list_engagement(decrypt_secret(account["access_token_enc"]), account["external_account_id"])
    raw_items = data.get("items") or data.get("data") or []
    created=[]
    for item in raw_items:
        item_id=str(item.get("id") or item.get("comment_id") or item.get("tweet_id") or "")
        if not item_id: continue
        txt=item.get("text") or item.get("message") or (((item.get("snippet") or {}).get("topLevelComment") or {}).get("snippet") or {}).get("textOriginal")
        intent,sentiment,priority=classify_engagement(txt)
        record={"id":uuid.uuid4(),"account_id":account["id"],"item_id":item_id,"kind":"comment_or_mention","author_name":(item.get("author_name") or (item.get("from") or {}).get("name")),"text":txt,"intent":intent,"sentiment":sentiment,"priority":priority,"responded_at":None,"metadata":item,"created_at":_now()}
        if settings.is_persistent:
            assert AsyncSessionLocal is not None
            async with AsyncSessionLocal() as session:
                await session.execute(text("""INSERT INTO pamasmma_social_engagement (id,account_id,item_id,kind,author_name,text,intent,sentiment,priority,metadata) VALUES (:id,:account_id,:item_id,:kind,:author_name,:text,:intent,:sentiment,:priority,:metadata) ON CONFLICT DO NOTHING"""),record); await session.commit()
        else: memory_store.social_engagement.append(record)
        created.append({"id":str(record["id"]),"item_id":item_id,"intent":intent,"sentiment":sentiment,"priority":priority,"text":txt})
    return {"count":len(created),"items":created}


async def reply_to_engagement(user_id: str, command: ReplyCommand) -> dict[str, Any]:
    account = await get_account(user_id, command.account_id)
    if not account: raise ValueError("Social account not found.")
    result=await get_provider(Platform(account["platform"])).reply(decrypt_secret(account["access_token_enc"]),command)
    return {"status":"replied","provider_response":result}


async def list_engagement(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    if not settings.is_persistent:
        account_ids={a["id"] for a in memory_store.social_accounts if a["user_id"]==user_id}
        rows=[e for e in reversed(memory_store.social_engagement) if e["account_id"] in account_ids][:limit]
        return [{k:(str(v) if k in {"id","account_id"} else (v.isoformat() if hasattr(v,"isoformat") else v)) for k,v in e.items()} for e in rows]
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        rows=(await session.execute(text("SELECT e.*,a.platform FROM pamasmma_social_engagement e JOIN pamasmma_social_accounts a ON a.id=e.account_id WHERE a.user_id=:u ORDER BY e.created_at DESC LIMIT :l"),{"u":user_id,"l":limit})).mappings().all()
    return [{k:(str(v) if k in {"id","account_id"} else (v.isoformat() if hasattr(v,"isoformat") else v)) for k,v in dict(r).items()} for r in rows]


async def plan_campaign(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    account=await get_account(user_id,payload["account_id"])
    if not account: raise ValueError("Social account not found.")
    campaign={"id":uuid.uuid4(),"account_id":uuid.UUID(payload["account_id"]),"ad_account_id":payload.get("ad_account_id"),"external_campaign_id":None,"name":payload["name"],"objective":payload["objective"],"budget":payload.get("daily_budget") or payload.get("lifetime_budget"),"currency":payload.get("currency","USD"),"status":"planned","config":payload,"metrics":{},"approved_at":None,"created_at":_now()}
    if not settings.is_persistent: memory_store.social_campaigns.append(campaign)
    else:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            await session.execute(text("INSERT INTO pamasmma_social_campaigns (id,account_id,ad_account_id,name,objective,budget,currency,status,config,metrics) VALUES (:id,:account_id,:ad_account_id,:name,:objective,:budget,:currency,:status,:config,:metrics)"),campaign); await session.commit()
    return {"campaign_id":str(campaign["id"]),"status":"planned","approval_required":True}


async def approve_campaign(user_id: str, campaign_id: str) -> dict[str, Any]:
    if settings.is_persistent:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            row=(await session.execute(text("SELECT c.*,a.user_id,a.platform,a.access_token_enc FROM pamasmma_social_campaigns c JOIN pamasmma_social_accounts a ON a.id=c.account_id WHERE c.id=:id AND a.user_id=:u"),{"id":campaign_id,"u":user_id})).mappings().first(); campaign=dict(row) if row else None
    else: campaign=next((c for c in memory_store.social_campaigns if str(c["id"])==campaign_id),None)
    if not campaign: raise ValueError("Campaign not found.")
    provider=get_provider(Platform(campaign["platform"])); provider.require(Capability.ADS_WRITE)
    config=dict(campaign["config"]); config.setdefault("name",campaign["name"]); config.setdefault("objective",campaign["objective"]); config.setdefault("status","PAUSED")
    result=await provider.create_campaign(decrypt_secret(campaign["access_token_enc"]),campaign.get("ad_account_id") or "",config)
    external=_token_value(result,"id","campaign_id")
    if settings.is_persistent:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            await session.execute(text("UPDATE pamasmma_social_campaigns SET status='created',external_campaign_id=:e,approved_at=now() WHERE id=:id"),{"e":external,"id":campaign_id}); await session.commit()
    else: campaign.update({"status":"created","external_campaign_id":external,"approved_at":_now()})
    return {"status":"created","campaign_id":campaign_id,"external_campaign_id":external,"provider_response":result}
