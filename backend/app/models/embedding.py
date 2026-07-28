"""
Embedding model for storing vector embeddings of places.
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from backend.app.db.database import Base
import uuid
from datetime import datetime, timezone


class Embedding(Base):
    """Model for storing place embeddings in pgvector."""
    
    __tablename__ = "embeddings"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to places table
    place_id = Column(UUID(as_uuid=True), ForeignKey('places.id', ondelete='CASCADE'), index=True)
    
    # Model information
    model_name = Column(String(100), index=True)  # e.g., "all-MiniLM-L6-v2"
    model_version = Column(String(50))  # e.g., "1.0"

    # Embedding data
    dimensions = Column(Integer)  # e.g., 384 for all-MiniLM-L6-v2
    # Vector stored as native pgvector type for indexing support
    vector = Column(Vector(384))
    
    # The text that was embedded (for reference and regeneration)
    embedding_text = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship to place
    place = relationship("Place", backref="embeddings")
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "place_id": str(self.place_id),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "dimensions": self.dimensions,
            "vector": self.vector,
            "embedding_text": self.embedding_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
