"""Knowledge ingestion orchestration."""
from __future__ import annotations

import hashlib
import re
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings
from app.embeddings.service import embed_text
from app.knowledge.contracts import KnowledgeItem, KnowledgeSource, KnowledgeSourceStatus, KnowledgeTrainingMode
from app.knowledge.extractor import extract_content
from app.knowledge.repository import create_source, delete_source, find_source_by_hash, insert_chunks, list_sources, search_knowledge, update_source

settings = get_settings()


async def _write_upload(file: UploadFile, destination: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    maximum = settings.knowledge_max_upload_mb * 1024 * 1024
    with destination.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > maximum:
                raise ValueError(f"File exceeds the {settings.knowledge_max_upload_mb} MB upload limit.")
            digest.update(chunk)
            handle.write(chunk)
    return size, digest.hexdigest()


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text).strip()
    if not normalized:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
        else:
            tail = ""
        if len(paragraph) <= max_chars:
            current = f"{tail}\n{paragraph}".strip()
            continue
        start = 0
        while start < len(paragraph):
            end = min(len(paragraph), start + max_chars)
            piece = paragraph[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(paragraph):
                break
            start = max(start + 1, end - overlap)
        current = ""
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk.strip()]


async def ingest_upload(
    *, user_id: str, file: UploadFile, title: str | None,
    training_mode: KnowledgeTrainingMode, scope_system_id: str | None,
    transcript_override: str | None,
) -> KnowledgeSource:
    filename = Path(file.filename or "upload").name[:255]
    extension = Path(filename).suffix.lower()
    allowed = {
        ".pdf", ".docx", ".epub", ".txt", ".md", ".markdown", ".rst", ".log",
        ".srt", ".vtt", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
        ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v",
    }
    if extension not in allowed:
        raise ValueError(f"Unsupported knowledge file type: {extension or 'unknown'}")

    fd, temporary_name = tempfile.mkstemp(prefix="pamasmma-knowledge-", suffix=extension)
    temporary = Path(temporary_name)
    import os
    os.close(fd)
    try:
        size_bytes, content_hash = await _write_upload(file, temporary)
        duplicate = await find_source_by_hash(user_id, content_hash)
        if duplicate:
            return duplicate

        source = KnowledgeSource(
            id=str(uuid.uuid4()),
            title=(title or Path(filename).stem or "Untitled source").strip()[:255],
            filename=filename,
            media_type=file.content_type or "application/octet-stream",
            training_mode=training_mode,
            status=KnowledgeSourceStatus.PROCESSING,
            extraction_method="pending",
            size_bytes=size_bytes,
            content_hash=content_hash,
            scope_system_id=scope_system_id or None,
        )
        await create_source(user_id=user_id, source=source)

        extracted = await extract_content(temporary, filename, transcript_override=transcript_override)
        source = source.model_copy(update={
            "status": KnowledgeSourceStatus(extracted.status),
            "extraction_method": extracted.method,
            "error": extracted.error,
        })
        if extracted.status != KnowledgeSourceStatus.READY.value:
            await update_source(source, user_id)
            return source

        chunks = chunk_text(
            extracted.text[:settings.knowledge_max_extracted_chars],
            settings.knowledge_chunk_chars,
            settings.knowledge_chunk_overlap_chars,
        )
        if not chunks:
            source = source.model_copy(update={
                "status": KnowledgeSourceStatus.FAILED,
                "error": "No usable text was extracted from the uploaded source.",
            })
            await update_source(source, user_id)
            return source

        items: list[KnowledgeItem] = []
        embeddings: list[list[float]] = []
        for ordinal, content in enumerate(chunks, start=1):
            items.append(KnowledgeItem(
                source_id=source.id, title=source.title, source_name=source.filename,
                ordinal=ordinal, content=content, training_mode=training_mode,
                reliability=0.75, scope_system_id=source.scope_system_id,
                citation=f"{source.title} · chunk {ordinal}",
            ))
            embeddings.append(await embed_text(content))
        await insert_chunks(user_id, items, embeddings)
        source = source.model_copy(update={
            "status": KnowledgeSourceStatus.READY, "chunk_count": len(items), "error": None,
        })
        await update_source(source, user_id)
        return source
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    finally:
        temporary.unlink(missing_ok=True)


async def retrieve_knowledge(
    *, user_id: str, query: str, limit: int = 6,
    scope_system_id: str | None = None,
) -> list[KnowledgeItem]:
    if not query.strip():
        return []
    embedding = await embed_text(query)
    return await search_knowledge(
        user_id=user_id, query=query, embedding=embedding,
        limit=limit, scope_system_id=scope_system_id,
    )


__all__ = ["chunk_text", "delete_source", "ingest_upload", "list_sources", "retrieve_knowledge"]
