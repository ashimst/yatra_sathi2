"""
Trail Watch & Ecological Stewardship Models
Community-reported trail hazards and volunteer steward sign-ups.
"""
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from backend.app.db.database import Base
import uuid
from datetime import datetime, timezone


class TrailReport(Base):
    """Trail hazard report filed by a traveler."""
    __tablename__ = "trail_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hazard_type = Column(String(100), nullable=False)
    urgency = Column(String(50), default="Moderate")  # Low, Moderate, Urgent
    description = Column(Text, nullable=False)
    location_name = Column(String(200), default="Himalayan Corridor")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Integer, default=2400)
    image_url = Column(Text, nullable=True)
    status = Column(String(50), default="Open")  # Open | Resolved (legacy: "Resolved & Cleared")
    # Legacy column name: holds the report's topic category, not an assignee.
    assigned_guild = Column(String(100), default="General Trail Condition")
    resolved_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TrailSteward(Base):
    """Volunteer community steward sign-up."""
    __tablename__ = "trail_stewards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    email = Column(String(200), nullable=False)
    preferred_region = Column(String(100), default="Annapurna Circuit")
    doko_pack_issued = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
