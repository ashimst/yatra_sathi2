"""
Helpers for tests that call API endpoint functions directly (bypassing
FastAPI dependency injection) and therefore must pass ``user=`` explicitly.
"""
import uuid

from backend.app.config.settings import settings
from backend.app.models.user import User


def make_test_user(db, admin: bool = False) -> User:
    """Create and persist a throwaway user in the given session's database."""
    suffix = uuid.uuid4().hex[:10]
    email = f"test_{suffix}@example.com"
    user = User(id=uuid.uuid4(), email=email, username=f"test_{suffix}", hashed_password="!")
    db.add(user)
    db.commit()
    if admin and email not in settings.ADMIN_EMAILS:
        settings.ADMIN_EMAILS.append(email)
    return user
