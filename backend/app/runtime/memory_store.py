"""
Ephemeral runtime store used only when PERSISTENCE_MODE=memory.

This makes the application deployable as a zero-datastore intelligence demo
without conflating it with the durable Postgres/Redis production mode.
"""
from collections import defaultdict
from typing import Any

users: dict[str, dict[str, Any]] = {}
sessions: dict[str, dict[str, Any]] = {}
webauthn_challenges: dict[str, str] = {}
webauthn_credentials: dict[str, dict[str, Any]] = {}
totp_used: set[str] = set()

memories: list[dict[str, Any]] = []
action_log: list[dict[str, Any]] = []
overrides: list[dict[str, Any]] = []

rate_limits: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
