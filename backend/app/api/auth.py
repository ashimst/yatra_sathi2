"""
Authentication & Traveler Profile API Endpoints
Provides Register, Login, Guest Explorer, Guest Upgrade, and User Profile.
"""
from datetime import datetime, timezone
import secrets
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.core.rate_limit import rate_limit
from backend.app.core.deps import get_current_user, get_optional_user
from backend.app.core.security import (
    GUEST_EMAIL_DOMAIN,
    MAX_PASSWORD_BYTES,
    MIN_PASSWORD_LENGTH,
    create_access_token,
    hash_password,
    is_guest_email,
    verify_password,
)
from backend.app.db.database import get_db
from backend.app.models.itinerary import Itinerary
from backend.app.models.memory import Memory
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _validate_password(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
    return value


class _CredentialsBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str
    full_name: Optional[str] = Field(default=None, max_length=255)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("email")
    @classmethod
    def _no_reserved_domain(cls, v: str) -> str:
        if v.lower().endswith(GUEST_EMAIL_DOMAIN):
            raise ValueError("This email domain is reserved.")
        return v


class RegisterRequest(_CredentialsBase):
    pass


class UpgradeGuestRequest(_CredentialsBase):
    pass


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=256)


def _user_payload(user: User, db: Session, with_stats: bool = False) -> dict:
    payload = {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email,
        "is_guest": is_guest_email(user.email),
    }
    if with_stats:
        payload["trip_count"] = db.query(Itinerary).filter(Itinerary.user_id == user.id).count()
        payload["memory_count"] = db.query(Memory).filter(Memory.user_id == user.id).count()
    return payload


def _auth_response(user: User, db: Session, with_stats: bool = False) -> dict:
    token = create_access_token(user.id, is_guest=is_guest_email(user.email))
    return {
        "success": True,
        "token": token,          # web client
        "access_token": token,   # mobile client / OAuth2 convention
        "token_type": "bearer",
        "user": _user_payload(user, db, with_stats=with_stats),
    }


def _ensure_unique(db: Session, email: str, username: str, exclude_id: Optional[uuid.UUID] = None) -> None:
    q_email = db.query(User).filter(User.email == email)
    q_user = db.query(User).filter(User.username == username)
    if exclude_id is not None:
        q_email = q_email.filter(User.id != exclude_id)
        q_user = q_user.filter(User.id != exclude_id)
    if q_email.first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    if q_user.first():
        raise HTTPException(status_code=400, detail="This username is already taken.")


@router.post("/register", dependencies=[rate_limit("auth", settings.RATE_LIMIT_AUTH)])
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new traveler account."""
    _ensure_unique(db, req.email, req.username)

    user = User(
        id=uuid.uuid4(),
        email=req.email,
        username=req.username,
        full_name=req.full_name or req.username,
        hashed_password=hash_password(req.password),
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user, db)


@router.post("/login", dependencies=[rate_limit("auth", settings.RATE_LIMIT_AUTH)])
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Log in with username or email."""
    user = db.query(User).filter(
        (User.username == req.username_or_email) | (User.email == req.username_or_email)
    ).first()

    ok, needs_rehash = verify_password(req.password, user.hashed_password if user else None)
    if not user or not ok or is_guest_email(user.email):
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    if needs_rehash:
        user.hashed_password = hash_password(req.password)
        db.commit()

    return _auth_response(user, db)


@router.post("/upgrade", dependencies=[rate_limit("auth", settings.RATE_LIMIT_AUTH)])
async def upgrade_guest(
    req: UpgradeGuestRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upgrade the signed-in guest explorer account to a permanent traveler profile."""
    if not is_guest_email(user.email):
        raise HTTPException(status_code=400, detail="This account is already a registered traveler.")

    _ensure_unique(db, req.email, req.username, exclude_id=user.id)

    user.email = req.email
    user.username = req.username
    if req.full_name:
        user.full_name = req.full_name
    user.hashed_password = hash_password(req.password)
    db.commit()
    db.refresh(user)

    return _auth_response(user, db, with_stats=True)


@router.post("/guest", dependencies=[rate_limit("auth", settings.RATE_LIMIT_AUTH)])
async def guest_login(db: Session = Depends(get_db)):
    """1-Click Guest Explorer mode for instant, friction-free access."""
    suffix = secrets.token_hex(4)
    user = User(
        id=uuid.uuid4(),
        email=f"guest_{suffix}{GUEST_EMAIL_DOMAIN}",
        username=f"Explorer_{suffix}",
        full_name="Guest Explorer",
        # Guests cannot log in with a password; store an unusable random hash.
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user, db)


@router.get("/me")
async def get_profile(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get current traveler profile and travel statistics."""
    if user is None:
        return {"is_authenticated": False, "user": None}
    return {"is_authenticated": True, "user": _user_payload(user, db, with_stats=True)}
