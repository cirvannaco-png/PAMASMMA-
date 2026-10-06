"""Content extraction adapters for books, notes, audio and video."""
from __future__ import annotations

import re
import subprocess
import tempfile
import zipfile
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


def _clean(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _subtitle_text(value: str) -> str:
    lines = []
    for line in value.replace("\r", "").split("\n"):
        item = line.strip()
        if not item or item.upper() == "WEBVTT" or item.isdigit():
            continue
        if "-->" in item:
            continue
        lines.append(item)
    return _clean(" ".join(lines))


def extract_document(path: Path) -> tuple[str, list[str]]:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return _clean(path.read_text(encoding="utf-8", errors="replace")), []
    if suffix in SUBTITLE_EXTENSIONS:
        return _subtitle_text(path.read_text(encoding="utf-8", errors="replace")), []
    if suffix in PDF_EXTENSIONS:
        from pypdf import PdfReader

        pages = [
            _clean(page.extract_text() or "")
            for page in PdfReader(str(path)).pages
        ]
        return _clean("\n\n".join(pages)), [
            f"page:{index}" for index, value in enumerate(pages, 1) if value
        ]
    if suffix in DOCX_EXTENSIONS:
        from docx import Document

        document = Document(str(path))
        return _clean("\n".join(p.text for p in document.paragraphs)), []
    if suffix in EPUB_EXTENSIONS:
        return _extract_epub(path)
    if suffix in AUDIO_EXTENSIONS or suffix in VIDEO_EXTENSIONS:
        return _transcribe_media(path)
    raise ValueError(f"Unsupported knowledge file type: {suffix or 'unknown'}")


def _extract_epub(path: Path) -> tuple[str, list[str]]:
    parts = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith((".xhtml", ".html", ".htm")):
                continue
            try:
                root = ElementTree.fromstring(archive.read(name))
            except (ElementTree.ParseError, UnicodeDecodeError):
                continue
            value = " ".join(" ".join(root.itertext()).split())
            if value:
                parts.append(value)
    return _clean("\n\n".join(parts)), []


def _transcribe_media(path: Path) -> tuple[str, list[str]]:
    if settings.knowledge_transcription_provider.lower() == "disabled":
        raise ValueError("Media transcription is disabled by configuration.")
    if not settings.openai_api_key:
        raise RuntimeError(
            "Media training requires OPENAI_API_KEY for the configured transcription adapter."
        )
    return _transcribe_with_openai(path)


def _transcribe_with_openai(path: Path) -> tuple[str, list[str]]:
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
        return _clean(str(result)), []


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
