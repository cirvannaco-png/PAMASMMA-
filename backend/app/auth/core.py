"""
PAMASMMA v4.0.1 — Authentication primitives
TOTP + WebAuthn/FIDO2 + JWT session issuance.
"""
import base64
import json
import logging
import secrets
from typing import Any, cast
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pyotp
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.config import get_settings
from app.redis_client import (
    delete_session,
    get_webauthn_credential,
    mark_totp_used,
    pop_webauthn_challenge,
    set_session,
    store_webauthn_challenge,
    store_webauthn_credential,
)

log = logging.getLogger(__name__)
settings = get_settings()


def generate_totp_secret() -> str:
    """Generate a fresh base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    """Build an otpauth:// provisioning URI."""
    totp = pyotp.TOTP(
        secret,
        digits=settings.totp_digits,
        interval=settings.totp_interval,
    )
    return totp.provisioning_uri(
        name=username,
        issuer_name=settings.totp_issuer,
    )


async def verify_totp(user_id: str, secret: str, code: str) -> bool:
    """
    Verify a TOTP code and reject reuse.

    The secret argument is an internal value loaded by the authentication
    persistence service; API clients never supply it.
    """
    code = code.strip()
    if not code.isdigit() or len(code) != settings.totp_digits:
        return False

    totp = pyotp.TOTP(
        secret,
        digits=settings.totp_digits,
        interval=settings.totp_interval,
    )
    if not totp.verify(code, valid_window=1):
        return False

    fresh = await mark_totp_used(user_id, code)
    if not fresh:
        log.warning("TOTP replay attempt blocked for user %s", user_id)
        return False

    return True


def _utc_now() -> datetime:
    return datetime.now(UTC)


def issue_access_token(user_id: str, session_id: str) -> str:
    now = _utc_now()
    payload = {
        "sub": user_id,
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "type": "access",
        "jti": secrets.token_hex(16),
    }
    return pyjwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def issue_refresh_token(user_id: str, session_id: str) -> str:
    now = _utc_now()
    payload = {
        "sub": user_id,
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
        "type": "refresh",
        "jti": secrets.token_hex(16),
    }
    return pyjwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return cast(
        dict[str, Any],
        pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        ),
    )


async def begin_webauthn_registration(user_id: str, username: str) -> dict:
    """Generate a registration challenge and store it in Redis."""
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
    challenge_b64 = base64.b64encode(options.challenge).decode("ascii")
    await store_webauthn_challenge(user_id, challenge_b64)
    return cast(dict[str, Any], json.loads(options_to_json(options)))


async def complete_webauthn_registration(
    user_id: str,
    credential_response: dict,
) -> bool:
    """Verify registration response and persist the credential."""
    challenge_b64 = await pop_webauthn_challenge(user_id)
    if not challenge_b64:
        log.warning("WebAuthn registration: no challenge for user %s", user_id)
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
            "credential_id": base64.b64encode(verification.credential_id).decode("ascii"),
            "public_key": base64.b64encode(
                verification.credential_public_key
            ).decode("ascii"),
            "sign_count": verification.sign_count,
            "registered_at": _utc_now().isoformat(),
        }
        await store_webauthn_credential(user_id, credential_data)
        log.info("WebAuthn credential registered for user %s", user_id)
        return True
    except Exception:
        log.exception("WebAuthn registration failed for user %s", user_id)
        return False


async def begin_webauthn_authentication(user_id: str) -> dict | None:
    """Generate an authentication challenge for the stored credential."""
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
    challenge_b64 = base64.b64encode(options.challenge).decode("ascii")
    await store_webauthn_challenge(user_id, challenge_b64)
    return options_to_json(options)


async def complete_webauthn_authentication(
    user_id: str,
    credential_response: dict,
) -> bool:
    """Verify a WebAuthn authentication assertion."""
    stored_credential = await get_webauthn_credential(user_id)
    challenge_b64 = await pop_webauthn_challenge(user_id)
    if not stored_credential or not challenge_b64:
        return False

    challenge = base64.b64decode(challenge_b64)
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
        stored_credential["sign_count"] = verification.new_sign_count
        await store_webauthn_credential(user_id, stored_credential)
        return True
    except Exception:
        log.exception("WebAuthn authentication failed for user %s", user_id)
        return False


async def create_auth_session(
    user_id: str,
    metadata: dict | None = None,
) -> str:
    """Create an active server-side session."""
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
