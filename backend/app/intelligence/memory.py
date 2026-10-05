"""Local, deterministic embedding engine — no external API key required."""
import hashlib
import math
import re


class LocalEmbeddingProvider:
    """Hashing-based normalized embedding compatible with vector(1536)."""

    dimensions = 1536

    @staticmethod
    def embed(text: str) -> list[float]:
        vector = [0.0] * LocalEmbeddingProvider.dimensions
        tokens = re.findall(r"[a-z0-9_'-]{2,}", text.lower())

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            for offset in range(0, len(digest), 4):
                index = int.from_bytes(digest[offset:offset + 2], "big") % LocalEmbeddingProvider.dimensions
                sign = 1.0 if digest[offset + 2] & 1 else -1.0
                magnitude = 0.5 + (digest[offset + 3] / 255.0)
                vector[index] += sign * magnitude

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector

        return [value / norm for value in vector]
