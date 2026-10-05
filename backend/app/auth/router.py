"""
PAMASMMA v4.0.1 — Authentication Router
TOTP enrollment/verification, WebAuthn/FIDO2 and JWT session lifecycle.
"""
import logging
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth.core import (
    begin_webauthn_authentication,
    begin_webauthn_registration,
    complete_webauthn_authentication,
    complete_webauthn_registration,
    create_auth_session,
    decode_token,
    issue_access_token,
    issue_refresh_token,
    revoke_auth_session,
)
from app.auth.dependencies import get_current_user
from app.auth.service import (
    TotpAlreadyConfiguredError,
    mark_webauthn_registered,
    setup_totp,
    verify_totp_for_user,
)
from app.config import get_settings
from app.redis_client import check_rate_limit, get_session

log = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


class TOTPVerifyRequest(BaseModel):
    user_id: str
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TOTPSetupRequest(BaseModel):
    user_id: str
    username: str


class WebAuthnRegistrationVerifyRequest(BaseModel):
    credential: dict


class WebAuthnAuthRequest(BaseModel):
    user_id: str


class WebAuthnAuthVerifyRequest(BaseModel):
    user_id: str
    credential: dict


class TokenRefreshRequest(BaseModel):
    refresh_token: str


async def _enforce_rate_limit(request: Request, key: str, limit: int) -> None:
    client_ip = request.client.host if request.client else "unknown"
    allowed, _remaining = await check_rate_limit(
        f"{key}:{client_ip}",
        limit,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again in 60 seconds.",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Remaining": "0",
            },
        )


def _enforce_bootstrap_token(provided_token: str) -> None:
    expected = settings.bootstrap_token.get_secret_value()
    if not expected or not secrets.compare_digest(provided_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bootstrap credentials.",
        )


def _enforce_founder_identity(user_id: str, username: str | None = None) -> None:
    if user_id != settings.founder_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found.")
    if username is not None and username != settings.founder_username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found.")


@router.post("/totp/setup")
async def totp_setup(
    body: TOTPSetupRequest,
    request: Request,
    x_bootstrap_token: str = Header(..., alias="X-Bootstrap-Token"),
) -> dict:
    """
    First-time founder enrollment.

    The server stores the generated secret encrypted at rest. The secret is
    returned exactly once for QR enrollment; verification never accepts it
    from the client.
    """
    await _enforce_rate_limit(request, "totp_setup", settings.rate_limit_auth_per_minute)
    _enforce_bootstrap_token(x_bootstrap_token)
    _enforce_founder_identity(body.user_id, body.username)

    try:
        secret = await setup_totp(body.user_id, body.username)
    except TotpAlreadyConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="TOTP is already configured. Use the authenticated recovery flow.",
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity configuration conflicts with the existing account.",
        ) from None

    from app.auth.core import get_totp_uri
    return {
        "secret": secret,
        "uri": get_totp_uri(secret, body.username),
        "issuer": settings.totp_issuer,
    }


@router.post("/totp/verify")
async def totp_verify(body: TOTPVerifyRequest, request: Request) -> dict:
    """Verify the backend-stored TOTP secret and issue a fresh session."""
    await _enforce_rate_limit(request, "totp_verify", settings.rate_limit_auth_per_minute)
    _enforce_founder_identity(body.user_id)

    valid = await verify_totp_for_user(body.user_id, body.code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired TOTP code.",
        )

    session_id = await create_auth_session(body.user_id, {"method": "totp"})
    return {
        "access_token": issue_access_token(body.user_id, session_id),
        "refresh_token": issue_refresh_token(body.user_id, session_id),
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.post("/webauthn/register/begin")
async def webauthn_register_begin(current_user: dict = Depends(get_current_user)) -> dict:
    """Begin passkey enrollment from an already authenticated session."""
    _enforce_founder_identity(current_user["user_id"])
    return await begin_webauthn_registration(
        current_user["user_id"],
        settings.founder_username,
    )


@router.post("/webauthn/register/complete")
async def webauthn_register_complete(
    body: WebAuthnRegistrationVerifyRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Complete passkey enrollment after authenticated TOTP/WebAuthn access."""
    _enforce_founder_identity(current_user["user_id"])
    success = await complete_webauthn_registration(
        current_user["user_id"],
        body.credential,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WebAuthn registration failed. Challenge expired or invalid.",
        )

    await mark_webauthn_registered(current_user["user_id"])
    return {"status": "registered"}


@router.post("/webauthn/authenticate/begin")
async def webauthn_auth_begin(
    body: WebAuthnAuthRequest,
    request: Request,
) -> dict:
    """Begin passkey authentication for the configured founder identity."""
    await _enforce_rate_limit(request, "webauthn_auth", settings.rate_limit_auth_per_minute)
    _enforce_founder_identity(body.user_id)

    options = await begin_webauthn_authentication(body.user_id)
    if not options:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No WebAuthn credential registered for this user.",
        )
    return options


@router.post("/webauthn/authenticate/complete")
async def webauthn_auth_complete(
    body: WebAuthnAuthVerifyRequest,
    request: Request,
) -> dict:
    """Complete passkey authentication and create a server-side session."""
    await _enforce_rate_limit(request, "webauthn_auth", settings.rate_limit_auth_per_minute)
    _enforce_founder_identity(body.user_id)

    success = await complete_webauthn_authentication(
        body.user_id,
        body.credential,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WebAuthn authentication failed.",
        )

    session_id = await create_auth_session(body.user_id, {"method": "webauthn"})
    return {
        "access_token": issue_access_token(body.user_id, session_id),
        "refresh_token": issue_refresh_token(body.user_id, session_id),
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.post("/token/refresh")
async def token_refresh(
    body: TokenRefreshRequest,
    request: Request,
) -> dict:
    """Validate, rotate and revoke the exact server-side refresh session."""
    await _enforce_rate_limit(request, "token_refresh", 10)

    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        user_id = str(payload["sub"])
        old_session_id = str(payload["sid"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from None

    session = await get_session(old_session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session is expired or revoked.",
        )

    await revoke_auth_session(old_session_id)
    new_session_id = await create_auth_session(
        user_id,
        {"method": "refresh", "rotated_from": old_session_id},
    )
    return {
        "access_token": issue_access_token(user_id, new_session_id),
        "refresh_token": issue_refresh_token(user_id, new_session_id),
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> dict:
    await revoke_auth_session(current_user["session_id"])
    return {"status": "logged_out"}
