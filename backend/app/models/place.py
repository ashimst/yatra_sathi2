"""
Place model for the places table.
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from backend.app.db.database import Base
import uuid
from datetime import datetime, timezone


class Place(Base):
    """Place model matching the main database schema."""
    
    __tablename__ = "places"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # OSM identifiers
    osm_id = Column(BigInteger, index=True)
    osm_type = Column(String(50))
    
    # Name and categorization
    name = Column(String(500), index=True)
    category = Column(String(100), index=True)
    group = Column(String(100), index=True)
    
    # Geometry (PostGIS) - stored as WKT strings for now
    geometry = Column(Text)
    centroid = Column(Text)
    
    # Bounding box
    bbox_min_lat = Column(Float)
    bbox_min_lon = Column(Float)
    bbox_max_lat = Column(Float)
    bbox_max_lon = Column(Float)
    
    # External identifiers
    wikidata_id = Column(String(50), index=True)
    wikipedia_url = Column(Text)
    website = Column(Text)
    
    # Rich metadata (JSONB)
    raw_tags = Column(JSONB, default=dict)
    import_metadata = Column(JSONB, default=dict)
    
    # Semantic metadata
    semantic_tags = Column(JSONB, default=list)
    travel_styles = Column(JSONB, default=list)
    difficulty = Column(String(50))
    visit_duration = Column(String(100))
    family_friendly = Column(Boolean)
    accessibility = Column(String(200))
    best_seasons = Column(JSONB, default=list)
    landscape = Column(JSONB, default=list)
    
    # Popularity and quality metrics
    popularity = Column(Float, index=True)
    rating = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @property
    def latitude(self):
        """Parse latitude from PostGIS centroid geometry."""
        if self.centroid:
            try:
                # Try to parse as WKT first
                if isinstance(self.centroid, str) and self.centroid.startswith("POINT("):
                    coords = self.centroid.replace("POINT(", "").replace(")", "").split()
                    return float(coords[1])
                # If it's binary PostGIS geometry, we'd need to use ST_Y
                # For now, return None for binary geometries
            except (ValueError, IndexError, AttributeError):
                pass
        return None
    
    @property
    def longitude(self):
        """Parse longitude from PostGIS centroid geometry."""
        if self.centroid:
            try:
                # Try to parse as WKT first
                if isinstance(self.centroid, str) and self.centroid.startswith("POINT("):
                    coords = self.centroid.replace("POINT(", "").replace(")", "").split()
                    return float(coords[0])
                # If it's binary PostGIS geometry, we'd need to use ST_X
                # For now, return None for binary geometries
            except (ValueError, IndexError, AttributeError):
                pass
        return None
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        # Parse centroid WKT to lat/lng
        lat = lng = None
        if self.centroid:
            try:
                # Parse POINT(lng lat) format
                if self.centroid.startswith("POINT("):
                    coords = self.centroid.replace("POINT(", "").replace(")", "").split()
                    lng, lat = float(coords[0]), float(coords[1])
            except (ValueError, IndexError):
                pass
        
        # If coordinates are still null, try to extract from bbox as fallback
        if lat is None or lng is None:
            if self.bbox_min_lat and self.bbox_min_lon and self.bbox_max_lat and self.bbox_max_lon:
                lat = (self.bbox_min_lat + self.bbox_max_lat) / 2
                lng = (self.bbox_min_lon + self.bbox_max_lon) / 2
        
        return {
            "id": str(self.id),
            "osm_id": self.osm_id,
            "osm_type": self.osm_type,
            "name": self.name,
            "category": self.category,
            "group": self.group,
            "latitude": lat,
            "longitude": lng,
            "wikidata_id": self.wikidata_id,
            "wikipedia_url": self.wikipedia_url,
            "website": self.website,
            "raw_tags": self.raw_tags or {},
            "semantic_tags": self.semantic_tags or [],
            "travel_styles": self.travel_styles or [],
            "difficulty": self.difficulty,
            "visit_duration": self.visit_duration,
            "family_friendly": self.family_friendly,
            "accessibility": self.accessibility,
            "best_seasons": self.best_seasons or [],
            "landscape": self.landscape or [],
            "popularity": self.popularity,
            "rating": self.rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
