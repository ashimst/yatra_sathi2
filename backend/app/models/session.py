"""
AI Session model for chat history.
"""
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from backend.app.db.database import Base
import uuid
from datetime import datetime, timezone


class AISession(Base):
    """AI Session model for chat history."""
    
    __tablename__ = "ai_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), unique=True, index=True)
    messages = Column(JSON, default=list)
    session_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
