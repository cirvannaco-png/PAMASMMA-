"""Hugging Face text-embedding endpoint adapter.

Configure HF_EMBEDDING_API_URL as a trusted, private or HTTPS endpoint that
accepts {"inputs": "..."} and returns a sentence embedding vector or a
single-item batch of vectors. For Text Embeddings Inference, use its /embed
endpoint. Never point this at an untrusted URL.

The PostgreSQL schema currently uses vector(1536). Smaller vectors are zero
padded, which preserves cosine similarity within that model's vector space.
This does NOT make vectors from different embedding models comparable: reindex
all memory and knowledge records before switching providers in production.
"""
from __future__ import annotations

import asyncio
import math
import os
from urllib.parse import urlparse

import httpx

DATABASE_DIMENSIONS = 1536
DEFAULT_TIMEOUT_SECONDS = 20.0


def _endpoint() -> str:
    value = os.getenv("HF_EMBEDDING_API_URL", "").strip()
    if not value:
        raise RuntimeError("HF_EMBEDDING_API_URL is required for Hugging Face embeddings.")
    parsed = urlparse(value)
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("HF_EMBEDDING_API_URL must use HTTPS outside localhost.")
    if not parsed.netloc:
        raise RuntimeError("HF_EMBEDDING_API_URL must be an absolute URL.")
    return value


def _normalize_vector(value: object) -> list[float]:
    # TEI /embed commonly returns [[...]] for a one-item batch.
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, list) or not value:
        raise ValueError("Hugging Face endpoint returned no embedding vector.")
    if any(isinstance(item, (list, dict)) or not isinstance(item, (int, float)) for item in value):
        raise ValueError("Expected a flat numeric embedding vector; configure a sentence-embedding endpoint.")
    vector = [float(item) for item in value]
    if any(not math.isfinite(item) for item in vector):
        raise ValueError("Embedding contains non-finite values.")
    if len(vector) > DATABASE_DIMENSIONS:
        raise ValueError(
            f"Embedding has {len(vector)} dimensions; database supports at most {DATABASE_DIMENSIONS}."
        )
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0:
        raise ValueError("Embedding vector has zero norm.")
    normalized = [item / norm for item in vector]
    # The database schema is vector(1536); padding with zeros preserves cosine
    # similarity within this embedding model's space.
    return normalized + [0.0] * (DATABASE_DIMENSIONS - len(normalized))


async def embed_text_huggingface(content: str) -> list[float]:
    if not content or not content.strip():
        raise ValueError("Cannot embed empty text.")
    endpoint = _endpoint()
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is required for the configured Hugging Face endpoint.")
    try:
        timeout = max(1.0, min(float(os.getenv("HF_EMBEDDING_TIMEOUT_SECONDS", "20")), 120.0))
    except ValueError:
        timeout = DEFAULT_TIMEOUT_SECONDS
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response = await client.post(endpoint, json={"inputs": content[:8000]}, headers=headers)
        response.raise_for_status()
        payload = response.json()
    # TEI's /embed returns [[float, ...]]; also accept a direct vector.
    if isinstance(payload, dict) and "embedding" in payload:
        payload = payload["embedding"]
    return _normalize_vector(payload)
