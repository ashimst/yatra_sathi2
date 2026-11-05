"""
PlacePhoto model for community destination photos and gallery contributions.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from backend.app.db.database import Base


class PlacePhoto(Base):
    """PlacePhoto model linked to places and optionally users."""

    __tablename__ = "place_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    place_id = Column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    image_url = Column(Text, nullable=False)
    caption = Column(String(500), nullable=True)
    is_cover = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "place_id": str(self.place_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "image_url": self.image_url,
            "caption": self.caption,
            "is_cover": bool(self.is_cover),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
