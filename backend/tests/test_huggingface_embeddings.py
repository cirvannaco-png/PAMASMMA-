import math

import pytest

from app.embeddings.huggingface import _normalize_vector, _endpoint


def test_normalize_vector_pads_to_database_dimension():
    vector = _normalize_vector([3.0, 4.0])
    assert len(vector) == 1536
    assert vector[0] == pytest.approx(0.6)
    assert vector[1] == pytest.approx(0.8)
    assert all(value == 0.0 for value in vector[2:])


def test_normalize_vector_accepts_single_item_batch():
    vector = _normalize_vector([[1.0, 0.0]])
    assert len(vector) == 1536
    assert vector[0] == pytest.approx(1.0)


@pytest.mark.parametrize("value", [[], [0.0, 0.0], [float("nan")], [float("inf")], [[1.0], [2.0]], ["bad"]])
def test_normalize_vector_rejects_invalid_vectors(value):
    with pytest.raises(ValueError):
        _normalize_vector(value)


def test_normalize_vector_rejects_more_than_schema_dimension():
    with pytest.raises(ValueError, match="at most 1536"):
        _normalize_vector([1.0] * 1537)


def test_endpoint_requires_configuration(monkeypatch):
    monkeypatch.delenv("HF_EMBEDDING_API_URL", raising=False)
    with pytest.raises(RuntimeError, match="HF_EMBEDDING_API_URL is required"):
        _endpoint()


def test_endpoint_requires_https_off_localhost(monkeypatch):
    monkeypatch.setenv("HF_EMBEDDING_API_URL", "http://example.com/embed")
    with pytest.raises(RuntimeError, match="must use HTTPS"):
        _endpoint()


def test_endpoint_allows_local_development(monkeypatch):
    monkeypatch.setenv("HF_EMBEDDING_API_URL", "http://localhost:8080/embed")
    assert _endpoint() == "http://localhost:8080/embed"
