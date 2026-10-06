"""
Ephemeral runtime store used only when PERSISTENCE_MODE=memory.
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
decisions: list[dict[str, Any]] = []
outcomes: list[dict[str, Any]] = []
beliefs: list[dict[str, Any]] = []
world_entities: list[dict[str, Any]] = []
relationships: list[dict[str, Any]] = []
social_accounts: list[dict[str, Any]] = []
social_posts: list[dict[str, Any]] = []
social_engagement: list[dict[str, Any]] = []
social_campaigns: list[dict[str, Any]] = []
rate_limits: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
knowledge_sources: list[dict[str, Any]] = []
knowledge_chunks: list[dict[str, Any]] = []
