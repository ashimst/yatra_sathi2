"""
Itinerary model for trip planning.
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from backend.app.db.database import Base
import uuid
from datetime import datetime, timezone


class Itinerary(Base):
    """Itinerary model for trip planning."""
    
    __tablename__ = "itineraries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    share_id = Column(String(50), unique=True, index=True, nullable=True)
    title = Column(String(255))
    description = Column(Text, nullable=True)
    origin_name = Column(String(100), nullable=True)
    dest_name = Column(String(100), nullable=True)
    num_days = Column(Integer, default=3)
    pace = Column(String(50), default="balanced")
    budget = Column(String(50), default="medium")
    destinations = Column(JSON, default=list)
    route_data = Column(JSON, nullable=True)
    itinerary_data = Column(JSON, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
