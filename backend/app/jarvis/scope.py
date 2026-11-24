"""Stable namespace helpers for JARVIS-owned cognitive memory."""
import hashlib


def jarvis_memory_scope(user_id: str) -> str:
    """Return a bounded, opaque per-user namespace isolated from other systems."""
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return f"jarvis:{digest}"
