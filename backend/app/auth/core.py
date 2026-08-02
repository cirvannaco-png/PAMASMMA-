"""
PAMASMMA v4 — Authentication
TOTP (primary) + WebAuthn/FIDO2 (hardware key) + JWT sessions.
Replay-attack prevention via Redis. Rate-limited on all auth endpoints.
"""
import base64
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone

import pyotp
import jwt as pyjwt
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier

from app.config import get_settings
from app.redis_client import (
    mark_totp_used,
    store_webauthn_challenge,
    pop_webauthn_challenge,
    store_webauthn_credential,
    get_webauthn_credential,
    set_session,
    delete_session,
)

log = logging.getLogger(__name__)
settings = get_settings()

# ── TOTP ──────────────────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a fresh base32 TOTP secret for a new user."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    """Return the otpauth:// URI for QR code generation."""
    totp = pyotp.TOTP(secret, digits=settings.totp_digits, interval=settings.totp_interval)
    return totp.provisioning_uri(name=username, issuer_name=settings.totp_issuer)


async def verify_totp(user_id: str, secret: str, code: str) -> bool:
    """
    Verify a TOTP code with:
    - ±1 window tolerance for clock skew
    - Redis-backed replay-attack prevention
    """
    totp = pyotp.TOTP(secret, digits=settings.totp_digits, interval=settings.totp_interval)
    valid = totp.verify(code, valid_window=1)
    if not valid:
        return False
    fresh = await mark_totp_used(user_id, code)
    if not fresh:
        log.warning(f"TOTP replay attempt blocked for user {user_id}")
        return False
    return True


# ── JWT ───────────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def issue_access_token(user_id: str, session_id: str) -> str:
    payload = {
        "sub": user_id,
        "sid": session_id,
        "iat": _utc_now(),
        "exp": _utc_now() + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    return pyjwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def issue_refresh_token(user_id: str, session_id: str) -> str:
    payload = {
        "sub": user_id,
        "sid": session_id,
        "iat": _utc_now(),
        "exp": _utc_now() + timedelta(days=settings.jwt_refresh_token_expire_days),
        "type": "refresh",
    }
    return pyjwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return pyjwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )


# ── WebAuthn ──────────────────────────────────────────────────────────────────

async def begin_webauthn_registration(user_id: str, username: str) -> dict:
    """Generate registration challenge and store it in Redis."""
    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_id=user_id.encode(),
        user_name=username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        supported_pub_key_algs=[
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ],
    )
    challenge_b64 = base64.b64encode(options.challenge).decode()
    await store_webauthn_challenge(user_id, challenge_b64)
    return options_to_json(options)


async def complete_webauthn_registration(
    user_id: str,
    credential_response: dict,
) -> bool:
    """Verify registration response and store credential in Redis."""
    challenge_b64 = await pop_webauthn_challenge(user_id)
    if not challenge_b64:
        log.warning(f"WebAuthn registration: no challenge for user {user_id}")
        return False

    challenge = base64.b64decode(challenge_b64)
    try:
        verification = verify_registration_response(
            credential=credential_response,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
        )
        credential_data = {
            "credential_id": base64.b64encode(verification.credential_id).decode(),
            "public_key": base64.b64encode(verification.credential_public_key).decode(),
            "sign_count": verification.sign_count,
            "registered_at": _utc_now().isoformat(),
        }
        await store_webauthn_credential(user_id, credential_data)
        log.info(f"WebAuthn credential registered for user {user_id}")
        return True
    except Exception as exc:
        log.error(f"WebAuthn registration failed for {user_id}: {exc}")
        return False


async def begin_webauthn_authentication(user_id: str) -> dict | None:
    """Generate authentication challenge. Returns None if no credential registered."""
    credential = await get_webauthn_credential(user_id)
    if not credential:
        return None

    credential_id = base64.b64decode(credential["credential_id"])
    options = generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=credential_id)
        ],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    challenge_b64 = base64.b64encode(options.challenge).decode()
    await store_webauthn_challenge(user_id, challenge_b64)
    return options_to_json(options)


async def complete_webauthn_authentication(
    user_id: str,
    credential_response: dict,
) -> bool:
    """Verify authentication response. Returns True on success."""
    stored_credential = await get_webauthn_credential(user_id)
    challenge_b64 = await pop_webauthn_challenge(user_id)
    if not stored_credential or not challenge_b64:
        return False

    challenge = base64.b64decode(challenge_b64)
    credential_id = base64.b64decode(stored_credential["credential_id"])
    public_key = base64.b64decode(stored_credential["public_key"])

    try:
        verification = verify_authentication_response(
            credential=credential_response,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
            credential_public_key=public_key,
            credential_current_sign_count=stored_credential["sign_count"],
        )
        # Update sign count to prevent cloning attacks
        stored_credential["sign_count"] = verification.new_sign_count
        await store_webauthn_credential(user_id, stored_credential)
        return True
    except Exception as exc:
        log.error(f"WebAuthn authentication failed for {user_id}: {exc}")
        return False


# ── Session Management ────────────────────────────────────────────────────────

async def create_auth_session(user_id: str, metadata: dict | None = None) -> str:
    """Create a new authenticated session. Returns session_id."""
    session_id = secrets.token_hex(32)
    session_data = {
        "user_id": user_id,
        "created_at": _utc_now().isoformat(),
        "metadata": metadata or {},
    }
    await set_session(session_id, session_data)
    return session_id


async def revoke_auth_session(session_id: str) -> None:
    await delete_session(session_id)
