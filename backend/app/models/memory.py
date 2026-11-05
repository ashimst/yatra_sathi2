"""
Memory model for traveler photo uploads, journal reflections, and place memories.
"""
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from backend.app.db.database import Base
import uuid
from datetime import datetime, timezone


class Memory(Base):
    """Memory model for photo uploads and travel reflections."""
    
    __tablename__ = "memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    itinerary_id = Column(UUID(as_uuid=True), ForeignKey("itineraries.id"), nullable=True, index=True)
    place_id = Column(String(100), nullable=True, index=True)
    place_name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    image_url = Column(Text, nullable=False)  # Stores base64 data URI or asset URI
    caption = Column(Text, nullable=True)
    ai_reflection = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
