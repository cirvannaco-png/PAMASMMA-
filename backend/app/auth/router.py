"""
PAMASMMA v4 — Auth Router
Endpoints: TOTP setup, TOTP verify, WebAuthn register/auth, token refresh, logout.
Rate-limited at the middleware layer. All responses are constant-time safe.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.core import (
    generate_totp_secret,
    get_totp_uri,
    verify_totp,
    issue_access_token,
    issue_refresh_token,
    decode_token,
    begin_webauthn_registration,
    complete_webauthn_registration,
    begin_webauthn_authentication,
    complete_webauthn_authentication,
    create_auth_session,
    revoke_auth_session,
)
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.redis_client import check_rate_limit
from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class TOTPVerifyRequest(BaseModel):
    user_id: str
    secret: str
    code: str = Field(..., min_length=6, max_length=8)


class TOTPSetupRequest(BaseModel):
    user_id: str
    username: str


class WebAuthnRegistrationRequest(BaseModel):
    user_id: str
    username: str


class WebAuthnRegistrationVerifyRequest(BaseModel):
    user_id: str
    credential: dict


class WebAuthnAuthRequest(BaseModel):
    user_id: str


class WebAuthnAuthVerifyRequest(BaseModel):
    user_id: str
    credential: dict


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _enforce_rate_limit(request: Request, key: str, limit: int) -> None:
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining = await check_rate_limit(
        f"{key}:{client_ip}", limit, window_seconds=60
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again in 60 seconds.",
            headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
        )


# ── TOTP Endpoints ────────────────────────────────────────────────────────────

@router.post("/totp/setup")
async def totp_setup(body: TOTPSetupRequest, request: Request) -> dict:
    """
    Generate a TOTP secret and provisioning URI for a new user.
    The secret must be stored (encrypted) by the caller.
    """
    await _enforce_rate_limit(request, "totp_setup", settings.rate_limit_auth_per_minute)
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, body.username)
    return {"secret": secret, "uri": uri, "issuer": settings.totp_issuer}


@router.post("/totp/verify")
async def totp_verify(body: TOTPVerifyRequest, request: Request) -> dict:
    """
    Verify a TOTP code and issue JWT tokens on success.
    Replay-attack prevention is enforced via Redis.
    """
    await _enforce_rate_limit(request, "totp_verify", settings.rate_limit_auth_per_minute)
    valid = await verify_totp(body.user_id, body.secret, body.code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired TOTP code.",
        )
    session_id = await create_auth_session(body.user_id)
    return {
        "access_token": issue_access_token(body.user_id, session_id),
        "refresh_token": issue_refresh_token(body.user_id, session_id),
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


# ── WebAuthn Endpoints ────────────────────────────────────────────────────────

@router.post("/webauthn/register/begin")
async def webauthn_register_begin(body: WebAuthnRegistrationRequest, request: Request) -> dict:
    await _enforce_rate_limit(request, "webauthn_register", settings.rate_limit_auth_per_minute)
    options = await begin_webauthn_registration(body.user_id, body.username)
    return options


@router.post("/webauthn/register/complete")
async def webauthn_register_complete(
    body: WebAuthnRegistrationVerifyRequest,
    request: Request,
) -> dict:
    await _enforce_rate_limit(request, "webauthn_register", settings.rate_limit_auth_per_minute)
    success = await complete_webauthn_registration(body.user_id, body.credential)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WebAuthn registration failed. Challenge expired or invalid.",
        )
    return {"status": "registered"}


@router.post("/webauthn/authenticate/begin")
async def webauthn_auth_begin(body: WebAuthnAuthRequest, request: Request) -> dict:
    await _enforce_rate_limit(request, "webauthn_auth", settings.rate_limit_auth_per_minute)
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
    await _enforce_rate_limit(request, "webauthn_auth", settings.rate_limit_auth_per_minute)
    success = await complete_webauthn_authentication(body.user_id, body.credential)
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


# ── Token Refresh ─────────────────────────────────────────────────────────────

@router.post("/token/refresh")
async def token_refresh(body: TokenRefreshRequest, request: Request) -> dict:
    await _enforce_rate_limit(request, "token_refresh", 10)
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    user_id = payload["sub"]
    old_session_id = payload["sid"]
    await revoke_auth_session(old_session_id)
    new_session_id = await create_auth_session(user_id)
    return {
        "access_token": issue_access_token(user_id, new_session_id),
        "refresh_token": issue_refresh_token(user_id, new_session_id),
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


# ── Logout ─────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> dict:
    await revoke_auth_session(current_user["session_id"])
    return {"status": "logged_out"}
