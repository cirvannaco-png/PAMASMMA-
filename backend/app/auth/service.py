"""
PAMASMMA — Authentication persistence service.

Keeps database state out of the authentication router and cryptographic
primitives. This is the application boundary for founder identity state.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.auth.core import generate_totp_secret, verify_totp
from app.database import AsyncSessionLocal
from app.models.user import User
from app.security.crypto import decrypt_secret, encrypt_secret

log = logging.getLogger(__name__)


class TotpAlreadyConfiguredError(RuntimeError):
    """Raised when TOTP enrollment is attempted after activation."""


async def setup_totp(user_id: str, username: str) -> str:
    """
    Create or refresh the founder's pending TOTP enrollment.

    A configured-but-unverified secret may be replaced. Once TOTP is enabled,
    re-enrollment must use a separate authenticated recovery flow.
    """
    async with AsyncSessionLocal() as session:
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

        secret = generate_totp_secret()
        user.totp_secret_enc = encrypt_secret(secret)
        user.totp_enabled = False
        await session.commit()
        return secret


async def verify_totp_for_user(user_id: str, code: str) -> bool:
    """Verify the server-stored TOTP secret and activate the factor."""
    async with AsyncSessionLocal() as session:
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

        valid = await verify_totp(user_id, secret, code)
        if not valid:
            return False

        user.totp_enabled = True
        user.last_login_at = datetime.now(timezone.utc)
        await session.commit()
        return True


async def mark_webauthn_registered(user_id: str) -> None:
    """Synchronize the persisted founder identity flag after registration."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.user_key == user_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            user.webauthn_registered = True
            await session.commit()
