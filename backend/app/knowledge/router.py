"""Authenticated API for PAMASMMA Knowledge Training."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.auth.dependencies import get_current_user
from app.knowledge.contracts import KnowledgeTrainingMode, KnowledgeUploadResponse
from app.knowledge.repository import delete_source, list_sources
from app.knowledge.service import ingest_upload

router = APIRouter(prefix="/knowledge", tags=["Knowledge Training"])


@router.get("")
async def get_sources(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
) -> dict:
    sources = await list_sources(current_user["user_id"], limit)
    return {"sources": [source.model_dump(mode="json") for source in sources], "count": len(sources)}


@router.post("/upload", response_model=KnowledgeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_source(
    file: UploadFile = File(...),
    title: str | None = Form(default=None, max_length=255),
    training_mode: KnowledgeTrainingMode = Form(default=KnowledgeTrainingMode.REFERENCE),
    scope_system_id: str | None = Form(default=None, pattern=r"^S([1-9]|10)$"),
    transcript: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
) -> KnowledgeUploadResponse:
    try:
        source = await ingest_upload(
            user_id=current_user["user_id"], file=file, title=title,
            training_mode=training_mode, scope_system_id=scope_system_id,
            transcript_override=transcript,
        )
    except ValueError as exc:
        message = str(exc)
        code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if "limit" in message.lower() or "exceeds" in message.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=message) from exc
    return KnowledgeUploadResponse(status=source.status.value, source=source)


@router.delete("/{source_id}")
async def remove_source(
    source_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        deleted = await delete_source(current_user["user_id"], source_id)
    except ValueError:
        deleted = False
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")
    return {"status": "deleted", "source_id": source_id}
