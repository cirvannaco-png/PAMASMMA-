"""
PAMASMMA v4 — Auth Dependencies
FastAPI dependency injection for protected routes.
"""
import logging

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.core import decode_token
from app.redis_client import get_session

log = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Validate JWT and confirm session is active in Redis.
    Returns user context dict injected into route handlers.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Not an access token")
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except Exception:
        raise credentials_exception from None

    user_id: str = payload.get("sub")
    session_id: str = payload.get("sid")
    if not user_id or not session_id:
        raise credentials_exception from None

    session = await get_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_id,
        "session_id": session_id,
        "session": session,
    }
