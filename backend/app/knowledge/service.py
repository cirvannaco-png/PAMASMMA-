"""Governed knowledge ingestion, storage and retrieval."""
from __future__ import annotations
import hashlib,json,logging,re,tempfile,uuid
from datetime import UTC,datetime
from pathlib import Path
from sqlalchemy import text
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.embeddings.service import embed_text
from app.intelligence.contracts import MemoryItem,MemoryType
from app.runtime import memory_store
from app.knowledge.extractors import extract_document
settings=get_settings(); log=logging.getLogger(__name__)
def _chunks(content:str,size:int,overlap:int)->list[str]:
    words=re.findall(r"\S+",content)
    if not words:return []
    step=max(1,size-overlap)
    return [" ".join(words[i:i+size]) for i in range(0,len(words),step)]
def _hash(data:bytes)->str:return hashlib.sha256(data).hexdigest()
async def ingest_file(*,user_id:str,filename:str,data:bytes,mode:str="knowledge")->dict:
    if len(data)>settings.knowledge_max_upload_bytes: raise ValueError(f"Upload exceeds the {settings.knowledge_max_upload_mb} MB knowledge limit.")
    source_id=str(uuid.uuid4()); digest=_hash(data)
    if settings.is_persistent:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            await session.execute(text("""INSERT INTO pamasmma_knowledge_sources
                (id,user_id,filename,media_type,status,content_hash,size_bytes,training_mode,metadata,created_at,updated_at)
                VALUES (:id,:user_id,:filename,:media_type,'processing',:hash,:size,:mode,'{}',NOW(),NOW())"""),
                {"id":source_id,"user_id":user_id,"filename":filename,"media_type":Path(filename).suffix.lower().lstrip("."),"hash":digest,"size":len(data),"mode":mode})
            await session.commit()
    else:
        memory_store.knowledge_sources.append({"id":source_id,"user_id":user_id,"filename":filename,"status":"processing","training_mode":mode})
    try:
        with tempfile.TemporaryDirectory(prefix="pamasmma-knowledge-") as tmp:
            path=Path(tmp)/Path(filename).name; path.write_bytes(data)
            content,locators=extract_document(path)
        if not content.strip(): raise ValueError("No readable text was extracted from the upload.")
        chunks=_chunks(content,settings.knowledge_chunk_size,settings.knowledge_chunk_overlap)
        for ordinal,chunk in enumerate(chunks):
            metadata={"knowledge_source_id":source_id,"source_filename":filename,"training_mode":mode,"importance":0.7,"reliability":0.75,"memory_type":MemoryType.SEMANTIC.value}
            embedding=await embed_text(chunk); locator=locators[ordinal] if ordinal<len(locators) else f"chunk:{ordinal+1}"
            if settings.is_persistent:
                assert AsyncSessionLocal is not None
                async with AsyncSessionLocal() as session:
                    await session.execute(text("""INSERT INTO pamasmma_knowledge_chunks
                      (id,source_id,user_id,ordinal,content,locator,embedding,metadata,created_at)
                      VALUES (:id,:source_id,:user_id,:ordinal,:content,:locator,CAST(:embedding AS vector),:metadata,NOW())"""),
                      {"id":str(uuid.uuid4()),"source_id":source_id,"user_id":user_id,"ordinal":ordinal,"content":chunk,"locator":locator,"embedding":str(embedding),"metadata":json.dumps(metadata)})
                    await session.commit()
            else:
                memory_store.knowledge_chunks.append({"source_id":source_id,"user_id":user_id,"content":chunk,"embedding":embedding,"metadata":metadata,"created_at":datetime.now(UTC),"locator":locator})
        if settings.is_persistent:
            assert AsyncSessionLocal is not None
            async with AsyncSessionLocal() as session:
                await session.execute(text("UPDATE pamasmma_knowledge_sources SET status='ready',chunk_count=:count,updated_at=NOW() WHERE id=:id AND user_id=:user_id"),{"count":len(chunks),"id":source_id,"user_id":user_id}); await session.commit()
        return {"source_id":source_id,"status":"ready","filename":filename,"chunks":len(chunks),"mode":mode,"content_hash":digest}
    except Exception as exc:
        log.exception("Knowledge ingestion failed")
        if settings.is_persistent:
            assert AsyncSessionLocal is not None
            async with AsyncSessionLocal() as session:
                await session.execute(text("UPDATE pamasmma_knowledge_sources SET status='failed',error=:error,updated_at=NOW() WHERE id=:id AND user_id=:user_id"),{"error":str(exc)[:2000],"id":source_id,"user_id":user_id}); await session.commit()
        raise
async def list_sources(user_id:str,limit:int=100)->list[dict]:
    if not settings.is_persistent:return [x for x in memory_store.knowledge_sources if x["user_id"]==user_id][-limit:][::-1]
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result=await session.execute(text("SELECT id,filename,media_type,status,content_hash,size_bytes,chunk_count,training_mode,metadata,error,created_at,updated_at FROM pamasmma_knowledge_sources WHERE user_id=:user_id ORDER BY created_at DESC LIMIT :limit"),{"user_id":user_id,"limit":limit})
        return [dict(row._mapping) for row in result.fetchall()]
async def delete_source(user_id:str,source_id:str)->bool:
    if not settings.is_persistent:
        before=len(memory_store.knowledge_chunks); memory_store.knowledge_chunks[:]=[x for x in memory_store.knowledge_chunks if not(x["user_id"]==user_id and x["source_id"]==source_id)]
        memory_store.knowledge_sources[:]=[x for x in memory_store.knowledge_sources if not(x["user_id"]==user_id and x["id"]==source_id)]
        return len(memory_store.knowledge_chunks)!=before
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result=await session.execute(text("DELETE FROM pamasmma_knowledge_sources WHERE id=:id AND user_id=:user_id"),{"id":source_id,"user_id":user_id}); await session.commit(); return bool(result.rowcount)
async def retrieve_knowledge_items(query:str,user_id:str,limit:int=5)->list[MemoryItem]:
    if not query.strip():return []
    query_embedding=await embed_text(query); rows=[]
    if not settings.is_persistent:
        for item in memory_store.knowledge_chunks:
            if item["user_id"]!=user_id:continue
            rows.append((item["content"],item["created_at"],_cosine(query_embedding,item["embedding"]),item["metadata"],item["locator"],item["source_id"],item["metadata"].get("source_filename","")))
    else:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            result=await session.execute(text("""SELECT c.content,c.created_at,1-(c.embedding <=> CAST(:vec AS vector)) AS similarity,c.metadata,c.locator,c.source_id,s.filename
                FROM pamasmma_knowledge_chunks c JOIN pamasmma_knowledge_sources s ON s.id=c.source_id
                WHERE c.user_id=:user_id AND s.status='ready'
                ORDER BY c.embedding <=> CAST(:vec AS vector) LIMIT :limit"""),{"vec":str(query_embedding),"user_id":user_id,"limit":max(limit*5,25)})
            rows=[(r.content,r.created_at,float(r.similarity or 0),json.loads(r.metadata or "{}") if isinstance(r.metadata,str) else(r.metadata or {}),r.locator,str(r.source_id),r.filename) for r in result.fetchall()]
    results=[]
    for content,created,similarity,metadata,locator,source_id,filename in rows:
        if similarity<settings.knowledge_similarity_threshold:continue
        results.append(MemoryItem(content=f"[{filename} · {locator}]\n{content}",memory_type=MemoryType.SEMANTIC,similarity=similarity,recency=.5,importance=float(metadata.get("importance",.7)),reliability=float(metadata.get("reliability",.75)),outcome_relevance=.5,contextual_fit=0.0,score=similarity,created_at=created,metadata={**metadata,"knowledge_source_id":source_id,"locator":locator}))
    results.sort(key=lambda x:x.score,reverse=True); return results[:limit]
def _cosine(a:list[float],b:list[float])->float:
    numerator=sum(x*y for x,y in zip(a,b,strict=False)); na=sum(x*x for x in a)**.5; nb=sum(y*y for y in b)**.5
    return float(numerator/(na*nb)) if na and nb else 0.0
