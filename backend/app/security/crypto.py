"""
PAMASMMA — Application-layer secret encryption.

TOTP secrets are encrypted before persistence. The encryption key is derived
from SECRET_KEY, so rotating SECRET_KEY requires TOTP re-enrollment.
"""
import base64
import hashlib
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


def _encryption_key() -> bytes:
    """Derive a stable 256-bit AES key from the application secret."""
    return hashlib.sha256(get_settings().secret_key.encode("utf-8")).digest()


def encrypt_secret(value: str) -> str:
    """Encrypt a UTF-8 secret with AES-256-GCM and return URL-safe text."""
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_encryption_key()).encrypt(
        nonce,
        value.encode("utf-8"),
        None,
    )
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_secret(token: str) -> str:
    """Decrypt an AES-256-GCM secret previously produced by encrypt_secret."""
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(raw) < 13:
        raise ValueError("Encrypted secret is malformed.")
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(_encryption_key()).decrypt(nonce, ciphertext, None).decode("utf-8")
