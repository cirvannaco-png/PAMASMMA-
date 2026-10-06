"""Knowledge Training unit tests."""
from pathlib import Path

from app.knowledge.contracts import KnowledgeSourceStatus, KnowledgeTrainingMode
from app.knowledge.extractor import _extract_subtitles
from app.knowledge.service import chunk_text


def test_chunk_text_preserves_order() -> None:
    source = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunk_text(source, max_chars=32, overlap=8)
    assert chunks
    assert "Paragraph one." in chunks[0]
    assert all(chunk.strip() for chunk in chunks)


def test_subtitle_extractor_removes_timing_markup(tmp_path: Path) -> None:
    path = tmp_path / "lecture.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello world.\n\n00:00:02.000 --> 00:00:04.000\nPAMASMMA learns from sources.",
        encoding="utf-8",
    )
    assert _extract_subtitles(path) == "Hello world.\n\nPAMASMMA learns from sources."


def test_training_modes_are_governed() -> None:
    assert KnowledgeTrainingMode.REFERENCE.value == "reference"
    assert KnowledgeTrainingMode.BEHAVIORAL.value == "behavioral"
    assert KnowledgeTrainingMode.DOMAIN_PLAYBOOK.value == "domain_playbook"
    assert KnowledgeSourceStatus.AWAITING_TRANSCRIPTION.value == "awaiting_transcription"
