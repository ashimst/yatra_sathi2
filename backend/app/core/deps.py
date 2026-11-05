"""
Shared FastAPI dependencies for authentication.

Use ``get_current_user`` on endpoints that require a signed-in traveler
(guest accounts count), and ``get_optional_user`` on public endpoints that
can personalise their response when a valid token is present.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.core.security import decode_access_token
from backend.app.db.database import get_db
from backend.app.models.user import User


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated user, or None if no/invalid token was supplied."""
    token = _extract_bearer(authorization)
    if not token:
        return None
    data = decode_access_token(token)
    if not data:
        return None
    return db.query(User).filter(User.id == data.user_id).first()


def is_admin(user: Optional[User]) -> bool:
    """Admins are configured via the ADMIN_EMAILS setting (comma-separated)."""
    if user is None or not user.email:
        return False
    return user.email.lower() in settings.ADMIN_EMAILS


def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    """Require a valid access token."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
