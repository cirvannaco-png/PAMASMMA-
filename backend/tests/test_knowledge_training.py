from app.knowledge.extractors import _subtitle_text, supported_suffix


def test_supported_knowledge_formats():
    assert supported_suffix(".pdf")
    assert supported_suffix(".epub")
    assert supported_suffix(".mp4")
    assert not supported_suffix(".exe")


def test_subtitle_extraction():
    text = (
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
        "Hello PAMASMMA.\n\n00:00:03.000 --> 00:00:04.000\n"
        "Knowledge training works."
    )
    assert "Hello PAMASMMA." in _subtitle_text(text)
