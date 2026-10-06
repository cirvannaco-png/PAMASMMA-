"""Content extraction adapters for books, notes, audio and video."""
from __future__ import annotations

import re
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from app.config import get_settings

settings = get_settings()

TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".csv", ".log"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
EPUB_EXTENSIONS = {".epub"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


@dataclass(frozen=True)
class ExtractedSegment:
    content: str
    locator: str


def _clean(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _subtitle_segments(value: str) -> list[ExtractedSegment]:
    segments: list[ExtractedSegment] = []
    blocks = re.split(r"\n\s*\n", value.replace("\r", "").strip())
    for block_index, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines or lines[0].upper() == "WEBVTT":
            continue

        timestamp = next((line for line in lines if "-->" in line), None)
        if timestamp:
            text_lines = [
                line
                for line in lines
                if "-->" not in line
                and not line.isdigit()
                and not line.upper().startswith(("NOTE", "STYLE", "REGION"))
            ]
            locator = "timestamp:" + timestamp.replace(" ", "")
        else:
            text_lines = [
                line
                for line in lines
                if not line.isdigit()
                and not line.upper().startswith(("NOTE", "STYLE", "REGION"))
            ]
            locator = f"subtitle:{block_index}"

        content = _clean(" ".join(text_lines))
        if content:
            segments.append(ExtractedSegment(content=content, locator=locator))
    return segments


def _subtitle_text(value: str) -> str:
    return _clean(" ".join(segment.content for segment in _subtitle_segments(value)))


def extract_document(path: Path) -> list[ExtractedSegment]:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        content = _clean(path.read_text(encoding="utf-8", errors="replace"))
        return [ExtractedSegment(content, "document")] if content else []

    if suffix in SUBTITLE_EXTENSIONS:
        return _subtitle_segments(path.read_text(encoding="utf-8", errors="replace"))

    if suffix in PDF_EXTENSIONS:
        from pypdf import PdfReader

        segments: list[ExtractedSegment] = []
        for index, page in enumerate(PdfReader(str(path)).pages, 1):
            content = _clean(page.extract_text() or "")
            if content:
                segments.append(ExtractedSegment(content, f"page:{index}"))
        return segments

    if suffix in DOCX_EXTENSIONS:
        from docx import Document

        document = Document(str(path))
        content = _clean("\n".join(p.text for p in document.paragraphs))
        return [ExtractedSegment(content, "document")] if content else []

    if suffix in EPUB_EXTENSIONS:
        return _extract_epub(path)

    if suffix in AUDIO_EXTENSIONS or suffix in VIDEO_EXTENSIONS:
        content, locator = _transcribe_media(path)
        return [ExtractedSegment(content, locator)] if content else []

    raise ValueError(f"Unsupported knowledge file type: {suffix or 'unknown'}")


def _extract_epub(path: Path) -> list[ExtractedSegment]:
    parts: list[ExtractedSegment] = []
    max_bytes = settings.knowledge_max_archive_extract_mb * 1024 * 1024
    total_bytes = 0

    with zipfile.ZipFile(path) as archive:
        members = [
            item
            for item in archive.infolist()
            if item.filename.lower().endswith((".xhtml", ".html", ".htm"))
            and not item.is_dir()
        ]
        if len(members) > settings.knowledge_max_archive_files:
            raise ValueError("EPUB contains too many archive members.")

        for item in members:
            total_bytes += item.file_size
            if total_bytes > max_bytes:
                raise ValueError("EPUB extracted content exceeds the safety limit.")

            try:
                root = ElementTree.fromstring(archive.read(item))
            except (ElementTree.ParseError, UnicodeDecodeError):
                continue

            value = _clean(" ".join(" ".join(root.itertext()).split()))
            if value:
                parts.append(
                    ExtractedSegment(
                        value,
                        "section:" + Path(item.filename).as_posix(),
                    )
                )
    return parts


def _transcribe_media(path: Path) -> tuple[str, str]:
    if settings.knowledge_transcription_provider.lower() == "disabled":
        raise ValueError("Media transcription is disabled by configuration.")
    if not settings.openai_api_key:
        raise RuntimeError(
            "Media training requires OPENAI_API_KEY for the configured transcription adapter."
        )
    return _transcribe_with_openai(path)


def _transcribe_with_openai(path: Path) -> tuple[str, str]:
    from openai import OpenAI

    with tempfile.TemporaryDirectory(prefix="pamasmma-media-") as directory:
        audio = Path(directory) / "audio.mp3"
        source = path
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(path),
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        str(audio),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=settings.knowledge_media_timeout_seconds,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "ffmpeg is required to extract audio from video uploads."
                ) from exc
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    "Unable to extract audio from the uploaded video."
                ) from exc
            source = audio

        client = OpenAI(api_key=settings.openai_api_key)
        with source.open("rb") as handle:
            result = client.audio.transcriptions.create(
                model=settings.knowledge_transcription_model,
                file=handle,
                response_format="text",
            )
        return _clean(str(result)), "transcript"


def supported_suffix(suffix: str) -> bool:
    supported = (
        TEXT_EXTENSIONS
        | PDF_EXTENSIONS
        | DOCX_EXTENSIONS
        | EPUB_EXTENSIONS
        | SUBTITLE_EXTENSIONS
        | AUDIO_EXTENSIONS
        | VIDEO_EXTENSIONS
    )
    return suffix.lower() in supported
