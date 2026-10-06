"""Protected Knowledge Training API."""
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.knowledge.extractors import supported_suffix
from app.knowledge.service import (
    delete_source,
    ingest_file,
    list_source_chunks,
    list_sources,
)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Training"])
CurrentUser = Annotated[dict, Depends(get_current_user)]
settings = get_settings()


@router.get("/sources")
async def sources(
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=200),
) -> dict:
    items = await list_sources(current_user["user_id"], limit)
    return {"sources": items, "count": len(items)}


@router.get("/sources/{source_id}/chunks")
async def chunks(
    source_id: str,
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=200),
) -> dict:
    items = await list_source_chunks(
        current_user["user_id"],
        source_id,
        limit,
    )
    if not items:
        sources_for_user = await list_sources(current_user["user_id"], 200)
        if not any(str(item["id"]) == source_id for item in sources_for_user):
            raise HTTPException(404, "Knowledge source not found.")
    return {"chunks": items, "count": len(items), "source_id": source_id}


@router.post("/upload")
async def upload(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    training_mode: str = Query("knowledge", pattern="^(knowledge|procedure)$"),
) -> dict:
    filename = Path(file.filename or "upload").name
    if not supported_suffix(Path(filename).suffix):
        raise HTTPException(415, "Unsupported knowledge file type.")

    data = await file.read(settings.knowledge_max_upload_bytes + 1)
    if len(data) > settings.knowledge_max_upload_bytes:
        raise HTTPException(
            413,
            f"Upload exceeds {settings.knowledge_max_upload_mb} MB.",
        )

    try:
        return await ingest_file(
            user_id=current_user["user_id"],
            filename=filename,
            data=data,
            mode=training_mode,
            content_type=file.content_type,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.delete("/sources/{source_id}")
async def remove(source_id: str, current_user: CurrentUser) -> dict:
    deleted = await delete_source(current_user["user_id"], source_id)
    if not deleted:
        raise HTTPException(404, "Knowledge source not found.")
    return {"status": "deleted", "source_id": source_id}
