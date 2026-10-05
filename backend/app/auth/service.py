"""
PAMASMMA — Authentication persistence service.
Durable mode uses Postgres; memory mode uses the explicit ephemeral runtime store.
"""
import logging
from datetime import UTC, datetime

from app.auth.core import generate_totp_secret, verify_totp
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.user import User
from app.runtime import memory_store
from app.security.crypto import decrypt_secret, encrypt_secret

log = logging.getLogger(__name__)
settings = get_settings()


class TotpAlreadyConfiguredError(RuntimeError):
    """Raised when TOTP enrollment is attempted after activation."""


async def setup_totp(user_id: str, username: str) -> str:
    """Create a TOTP secret and store it encrypted in the configured repository."""
    secret = generate_totp_secret()

    if not settings.is_persistent:
        existing = memory_store.users.get(user_id)
        if existing and existing.get("totp_enabled"):
            raise TotpAlreadyConfiguredError("TOTP is already configured.")
        if existing and existing.get("username") != username:
            raise ValueError("Identity mismatch.")
        memory_store.users[user_id] = {
            "username": username,
            "totp_secret_enc": encrypt_secret(secret),
            "totp_enabled": False,
            "is_active": True,
            "last_login_at": None,
        }
        return secret

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(User.user_key == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(user_key=user_id, username=username)
            session.add(user)
        elif user.username != username:
            raise ValueError("Identity mismatch.")
        elif user.totp_enabled:
            raise TotpAlreadyConfiguredError("TOTP is already configured.")

        user.totp_secret_enc = encrypt_secret(secret)
        user.totp_enabled = False
        await session.commit()
        return secret


async def verify_totp_for_user(user_id: str, code: str) -> bool:
    """Verify the server-stored TOTP secret and activate the factor."""
    if not settings.is_persistent:
        user = memory_store.users.get(user_id)
        if not user or not user.get("is_active") or not user.get("totp_secret_enc"):
            return False
        try:
            secret = decrypt_secret(user["totp_secret_enc"])
        except Exception:
            log.exception("Unable to decrypt TOTP secret for user %s", user_id)
            return False
        if not await verify_totp(user_id, secret, code):
            return False
        user["totp_enabled"] = True
        user["last_login_at"] = datetime.now(UTC).isoformat()
        return True

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(
                User.user_key == user_id,
                User.is_active.is_(True),
            )
        )
        user = result.scalar_one_or_none()

        if user is None or not user.totp_secret_enc:
            return False

        try:
            secret = decrypt_secret(user.totp_secret_enc)
        except Exception:
            log.exception("Unable to decrypt TOTP secret for user %s", user_id)
            return False

        if not await verify_totp(user_id, secret, code):
            return False

        user.totp_enabled = True
        user.last_login_at = datetime.now(UTC)
        await session.commit()
        return True


async def mark_webauthn_registered(user_id: str) -> None:
    """Synchronize the persisted WebAuthn enrollment flag."""
    if not settings.is_persistent:
        user = memory_store.users.get(user_id)
        if user is not None:
            user["webauthn_registered"] = True
        return

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(User.user_key == user_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            user.webauthn_registered = True
            await session.commit()
