"""
Security primitives: password hashing and JWT access tokens.

- Passwords are hashed with bcrypt (per-user salt, adaptive cost).
- Legacy SHA-256 hashes (pre-2026-11 accounts) are still accepted once on
  login and transparently upgraded to bcrypt by the caller.
- Access tokens are signed JWTs (HS256 by default) carrying the user id in
  ``sub`` and an ``is_guest`` flag. The signature and expiry are always
  verified; nothing is trusted from an unsigned token.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from backend.app.config.settings import settings

# Salt used by the legacy SHA-256 scheme. Only needed to verify old hashes
# so they can be upgraded; never used to create new hashes.
_LEGACY_SALT = "yatrasathi_nepal_secret_salt_2026"

# bcrypt only uses the first 72 bytes of input; we reject longer passwords
# instead of silently truncating them.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8

TOKEN_TYPE_ACCESS = "access"


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a bcrypt hash for ``password``."""
    pw = password.encode("utf-8")
    if len(pw) > MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long.")
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def _is_legacy_hash(hashed: str) -> bool:
    return len(hashed) == 64 and all(c in "0123456789abcdef" for c in hashed)


def verify_password(password: str, hashed: Optional[str]) -> tuple[bool, bool]:
    """
    Check ``password`` against ``hashed``.

    Returns ``(is_valid, needs_rehash)``. ``needs_rehash`` is True when the
    stored hash uses the legacy SHA-256 scheme and should be replaced.
    """
    if not hashed:
        return False, False

    if _is_legacy_hash(hashed):
        candidate = hashlib.sha256(f"{password}{_LEGACY_SALT}".encode()).hexdigest()
        ok = hmac.compare_digest(candidate, hashed)
        return ok, ok

    pw = password.encode("utf-8")
    if len(pw) > MAX_PASSWORD_BYTES:
        return False, False
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8")), False
    except ValueError:
        # Malformed stored hash
        return False, False


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TokenData:
    user_id: uuid.UUID
    is_guest: bool


def create_access_token(user_id: uuid.UUID | str, is_guest: bool = False) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_ACCESS,
        "guest": bool(is_guest),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.JWT_EXPIRE_HOURS)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenData]:
    """Verify signature + expiry and return the token data, or None if invalid."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError:
        return None

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError, TypeError):
        return None
    return TokenData(user_id=user_id, is_guest=bool(payload.get("guest", False)))


GUEST_EMAIL_DOMAIN = "@yatrasathi.local"


def is_guest_email(email: Optional[str]) -> bool:
    return bool(email) and email.endswith(GUEST_EMAIL_DOMAIN)
