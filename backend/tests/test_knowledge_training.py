from app.intelligence.contracts import MemoryType
from app.knowledge.extractors import _subtitle_segments, _subtitle_text, supported_suffix
from app.knowledge.service import _chunk_segments, _memory_type_for_mode
from app.knowledge.extractors import ExtractedSegment


def test_supported_knowledge_formats():
    assert supported_suffix(".pdf")
    assert supported_suffix(".epub")
    assert supported_suffix(".mp4")
    assert supported_suffix(".docx")
    assert not supported_suffix(".exe")


def test_subtitle_extraction():
    text = (
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
        "Hello PAMASMMA.\n\n00:00:03.000 --> 00:00:04.000\n"
        "Knowledge training works."
    )
    assert "Hello PAMASMMA." in _subtitle_text(text)


def test_subtitle_locators_preserve_timestamps():
    text = (
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
        "First statement.\n\n00:00:05.000 --> 00:00:06.000\n"
        "Second statement."
    )
    segments = _subtitle_segments(text)
    assert len(segments) == 2
    assert segments[0].locator == "timestamp:00:00:01.000-->00:00:02.000"
    assert segments[1].locator == "timestamp:00:00:05.000-->00:00:06.000"


def test_chunking_preserves_source_locator():
    segments = [
        ExtractedSegment(
            "one two three four five six",
            "page:4",
        )
    ]
    chunks = _chunk_segments(segments, size=3, overlap=1)
    assert chunks[0][1] == "page:4#chunk:1"
    assert chunks[1][1] == "page:4#chunk:2"


def test_procedure_training_uses_procedural_memory_type():
    assert _memory_type_for_mode("procedure") == MemoryType.PROCEDURAL
    assert _memory_type_for_mode("knowledge") == MemoryType.SEMANTIC
