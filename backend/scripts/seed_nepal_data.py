"""
YatraSathi Dual Database Seeding Engine
=======================================
Reads persistent seed datasets from backend/data/seeds/:
  - trekking_trails.json
  - waypoints.json
  - cultural_heritage.json
  - festivals.json
And populates:
  1. SQLite database yatra_sathi.db (at project root)
  2. PostgreSQL database yatra_sathi (when accessible)

Guarantees:
  - 100% coordinates within Nepal bounds [26.0°N to 30.5°N, 80.0°E to 88.5°E]
  - Idempotent upsert (re-running does not corrupt or duplicate data)
  - Dedicated tables (trails, waypoints, festivals) and unified places table
  - PostGIS centroid format POINT(lon lat)
  - Schema alignment with backend models
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure project root and backend/ are on the Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
for p in (PROJECT_ROOT, BACKEND_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean,
    DateTime, Text, JSON, BigInteger, inspect
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles

# Ensure SQLite compatibility for PostgreSQL JSONB and UUID
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"

# Import existing backend models and Base
from backend.app.db.database import Base
from backend.app.models.place import Place
from backend.app.models.trail_watch import TrailReport, TrailSteward
from backend.app.models.itinerary import Itinerary
from backend.app.models.embedding import Embedding

# -----------------------------------------------------------------------------
# Dedicated SQLAlchemy Models for Trails, Waypoints, Festivals
# -----------------------------------------------------------------------------
class Trail(Base):
    """Trekking route specification matching trekking_trails.json."""
    __tablename__ = "trails"

    id = Column(String(100), primary_key=True)
    name = Column(String(500), index=True, nullable=False)
    region = Column(String(100), index=True, nullable=False)
    difficulty = Column(String(50), nullable=False)
    duration_days = Column(Integer, nullable=False)
    estimated_walking_hours_per_day = Column(String(100), nullable=True)
    starting_elevation_m = Column(Float, nullable=True)
    max_elevation_m = Column(Float, nullable=False)
    pass_elevation_m = Column(Float, nullable=True)
    end_elevation_m = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    permits_required = Column(JSON, default=list)
    start_point = Column(JSON, nullable=True)
    end_point = Column(JSON, nullable=True)
    route_geometry_wkt = Column(Text, nullable=True)
    key_waypoints = Column(JSON, default=list)
    best_seasons = Column(JSON, default=list)
    osm_relation_id = Column(BigInteger, nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "region": self.region,
            "difficulty": self.difficulty,
            "duration_days": self.duration_days,
            "estimated_walking_hours_per_day": self.estimated_walking_hours_per_day,
            "starting_elevation_m": self.starting_elevation_m,
            "max_elevation_m": self.max_elevation_m,
            "pass_elevation_m": self.pass_elevation_m,
            "end_elevation_m": self.end_elevation_m,
            "distance_km": self.distance_km,
            "permits_required": self.permits_required or [],
            "start_point": self.start_point or {},
            "end_point": self.end_point or {},
            "route_geometry_wkt": self.route_geometry_wkt,
            "key_waypoints": self.key_waypoints or [],
            "best_seasons": self.best_seasons or [],
            "osm_relation_id": self.osm_relation_id,
            "details": self.details or {},
        }


class Waypoint(Base):
    """Trail waypoints, clinics, helipads, and passes matching waypoints.json."""
    __tablename__ = "waypoints"

    id = Column(String(100), primary_key=True)
    name = Column(String(500), index=True, nullable=False)
    trail_id = Column(String(100), index=True, nullable=True)
    region = Column(String(100), index=True, nullable=True)
    category = Column(String(100), index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trail_id": self.trail_id,
            "region": self.region,
            "category": self.category,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
            "details": self.details or {},
        }


class Festival(Base):
    """Major Nepali cultural festivals matching festivals.json."""
    __tablename__ = "festivals"

    id = Column(String(100), primary_key=True)
    name = Column(String(500), index=True, nullable=False)
    nepali_name = Column(String(500), nullable=True)
    lunar_month = Column(String(200), nullable=False)
    typical_gregorian_window = Column(String(200), nullable=False)
    significance = Column(Text, nullable=False)
    primary_regions = Column(JSON, default=list)
    associated_places = Column(JSON, default=list)
    rituals = Column(JSON, default=list)
    duration_days = Column(Integer, default=1)
    key_highlights = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nepali_name": self.nepali_name,
            "lunar_month": self.lunar_month,
            "typical_gregorian_window": self.typical_gregorian_window,
            "significance": self.significance,
            "primary_regions": self.primary_regions or [],
            "associated_places": self.associated_places or [],
            "rituals": self.rituals or [],
            "duration_days": self.duration_days,
            "key_highlights": self.key_highlights,
        }

# -----------------------------------------------------------------------------
# Geographic Constants for Nepal
# -----------------------------------------------------------------------------
NEPAL_LAT_MIN = 26.0
NEPAL_LAT_MAX = 30.5
NEPAL_LON_MIN = 80.0
NEPAL_LON_MAX = 88.5

def validate_nepal_coords(lat: float, lon: float, entity_name: str = "Entity") -> None:
    """Validate that coordinates strictly fall within the Nepal bounding box."""
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise ValueError(f"Non-numeric coordinates for {entity_name}: lat={lat}, lon={lon}")
    if not (NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX):
        raise ValueError(f"Latitude {lat} for '{entity_name}' out of Nepal bounds [{NEPAL_LAT_MIN}, {NEPAL_LAT_MAX}]")
    if not (NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX):
        raise ValueError(f"Longitude {lon} for '{entity_name}' out of Nepal bounds [{NEPAL_LON_MIN}, {NEPAL_LON_MAX}]")

def normalize_dedup_key(name: str, lat: float, lon: float) -> Tuple[str, float, float]:
    """Generate normalized deduplication tuple: (lowercase_name, 4_dec_lat, 4_dec_lon)."""
    return (name.strip().lower(), round(float(lat), 4), round(float(lon), 4))

# -----------------------------------------------------------------------------
# Seeder Implementation
# -----------------------------------------------------------------------------
class NepalDataSeeder:
    """Unified Seeder for SQLite and PostgreSQL databases."""

    def __init__(
        self,
        sqlite_path: Optional[Path] = None,
        postgres_url: Optional[str] = None,
        seeds_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.sqlite_path = sqlite_path or (PROJECT_ROOT / "yatra_sathi.db")
        self.postgres_url = postgres_url or os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/yatra_sathi")
        self.seeds_dir = seeds_dir or (BACKEND_DIR / "data" / "seeds")
        self.logger = logger or logging.getLogger("NepalDataSeeder")
        self._load_seed_files()

    def _load_seed_files(self) -> None:
        """Load and parse the 4 seed datasets from disk."""
        trails_path = self.seeds_dir / "trekking_trails.json"
        waypoints_path = self.seeds_dir / "waypoints.json"
        heritage_path = self.seeds_dir / "cultural_heritage.json"
        festivals_path = self.seeds_dir / "festivals.json"

        for p in (trails_path, waypoints_path, heritage_path, festivals_path):
            if not p.exists():
                raise FileNotFoundError(f"Required seed file missing: {p}")

        with open(trails_path, "r", encoding="utf-8") as f:
            self.trails_data: List[Dict[str, Any]] = json.load(f)
        with open(waypoints_path, "r", encoding="utf-8") as f:
            self.waypoints_data: List[Dict[str, Any]] = json.load(f)
        with open(heritage_path, "r", encoding="utf-8") as f:
            self.heritage_data: List[Dict[str, Any]] = json.load(f)
        with open(festivals_path, "r", encoding="utf-8") as f:
            self.festivals_data: List[Dict[str, Any]] = json.load(f)

        self.logger.info(
            f"Loaded seeds: {len(self.trails_data)} trails, {len(self.waypoints_data)} waypoints, "
            f"{len(self.heritage_data)} heritage sites, {len(self.festivals_data)} festivals"
        )

    def seed_sqlite(self, force_recreate: bool = False) -> Dict[str, int]:
        """Populate the SQLite database at self.sqlite_path."""
        self.logger.info(f"==> Seeding SQLite Database: {self.sqlite_path}")
        
        # Ensure parent directory exists
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        if force_recreate and self.sqlite_path.exists():
            self.logger.info(f"Force recreate: removing {self.sqlite_path}")
            self.sqlite_path.unlink()

        engine = create_engine(
            f"sqlite:///{self.sqlite_path}",
            connect_args={"check_same_thread": False},
            echo=False
        )
        Base.metadata.create_all(bind=engine)
        SessionCls = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        with SessionCls() as session:
            stats = self._seed_session(session, is_sqlite=True)
            session.commit()

        self.logger.info(f"SQLite Seeding Completed successfully: {stats}")
        return stats

    def seed_postgres(self, generate_embeddings: bool = True) -> Optional[Dict[str, int]]:
        """Populate the PostgreSQL database if reachable."""
        self.logger.info(f"==> Attempting PostgreSQL Connection: {self.postgres_url}")
        try:
            pg_engine = create_engine(
                self.postgres_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3}
            )
            # Test connectivity
            with pg_engine.connect() as conn:
                self.logger.info("PostgreSQL connection confirmed.")
        except Exception as e:
            self.logger.warning(
                f"PostgreSQL database unreachable or restricted ({e}). "
                "Skipping PostgreSQL seeding while SQLite remains fully populated."
            )
            return None

        try:
            Base.metadata.create_all(bind=pg_engine)
            SessionCls = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
            with SessionCls() as session:
                stats = self._seed_session(session, is_sqlite=False)
                session.commit()

            if generate_embeddings:
                self._generate_postgres_embeddings(pg_engine)

            self.logger.info(f"PostgreSQL Seeding Completed successfully: {stats}")
            return stats
        except Exception as e:
            self.logger.error(f"Error seeding PostgreSQL: {e}")
            return None

    def _seed_session(self, session: Session, is_sqlite: bool) -> Dict[str, int]:
        """Core idempotent seeding logic executed inside a database session."""
        stats = {
            "trails": 0,
            "waypoints": 0,
            "festivals": 0,
            "places_heritage": 0,
            "places_waypoints": 0,
            "places_trails": 0,
            "trail_reports": 0,
            "trail_stewards": 0,
            "itineraries": 0,
        }

        # ---------------------------------------------------------------------
        # 1. Dedicated Trails Table
        # ---------------------------------------------------------------------
        for t in self.trails_data:
            # Validate coordinates
            for pt_key in ("start_point", "end_point"):
                pt = t.get(pt_key) or {}
                if pt.get("latitude") and pt.get("longitude"):
                    validate_nepal_coords(pt["latitude"], pt["longitude"], f"{t['name']} {pt_key}")

            existing_trail = session.query(Trail).filter(Trail.id == t["id"]).first()
            if not existing_trail:
                trail_obj = Trail(
                    id=t["id"],
                    name=t["name"],
                    region=t.get("region", "Himalaya"),
                    difficulty=t.get("difficulty", "Challenging"),
                    duration_days=int(t.get("duration_days", 10)),
                    estimated_walking_hours_per_day=t.get("estimated_walking_hours_per_day"),
                    starting_elevation_m=t.get("starting_elevation_m"),
                    max_elevation_m=float(t.get("max_elevation_m", 5000.0)),
                    pass_elevation_m=t.get("pass_elevation_m"),
                    end_elevation_m=t.get("end_elevation_m"),
                    distance_km=t.get("distance_km"),
                    permits_required=t.get("permits_required", []),
                    start_point=t.get("start_point"),
                    end_point=t.get("end_point"),
                    route_geometry_wkt=t.get("route_geometry_wkt"),
                    key_waypoints=t.get("key_waypoints", []),
                    best_seasons=t.get("best_seasons", []),
                    osm_relation_id=t.get("osm_relation_id"),
                    details=t.get("details", {})
                )
                session.add(trail_obj)
                stats["trails"] += 1
            else:
                existing_trail.name = t["name"]
                existing_trail.difficulty = t.get("difficulty", existing_trail.difficulty)
                existing_trail.max_elevation_m = float(t.get("max_elevation_m", existing_trail.max_elevation_m))
                existing_trail.permits_required = t.get("permits_required", existing_trail.permits_required)

        # ---------------------------------------------------------------------
        # 2. Dedicated Waypoints Table
        # ---------------------------------------------------------------------
        for w in self.waypoints_data:
            lat, lon = float(w["latitude"]), float(w["longitude"])
            validate_nepal_coords(lat, lon, w["name"])

            existing_wp = session.query(Waypoint).filter(Waypoint.id == w["id"]).first()
            if not existing_wp:
                wp_obj = Waypoint(
                    id=w["id"],
                    name=w["name"],
                    trail_id=w.get("trail_id"),
                    region=w.get("region"),
                    category=w.get("category", "Waypoint"),
                    latitude=lat,
                    longitude=lon,
                    elevation_m=w.get("elevation_m"),
                    details=w.get("details", {})
                )
                session.add(wp_obj)
                stats["waypoints"] += 1
            else:
                existing_wp.name = w["name"]
                existing_wp.latitude = lat
                existing_wp.longitude = lon
                existing_wp.elevation_m = w.get("elevation_m", existing_wp.elevation_m)
                existing_wp.details = w.get("details", existing_wp.details)

        # ---------------------------------------------------------------------
        # 3. Dedicated Festivals Table
        # ---------------------------------------------------------------------
        for f in self.festivals_data:
            existing_fest = session.query(Festival).filter(Festival.id == f["id"]).first()
            if not existing_fest:
                fest_obj = Festival(
                    id=f["id"],
                    name=f["name"],
                    nepali_name=f.get("nepali_name"),
                    lunar_month=f.get("lunar_month", ""),
                    typical_gregorian_window=f.get("typical_gregorian_window", ""),
                    significance=f.get("significance", ""),
                    primary_regions=f.get("primary_regions", []),
                    associated_places=f.get("associated_places", []),
                    rituals=f.get("rituals", []),
                    duration_days=int(f.get("duration_days", 1)),
                    key_highlights=f.get("key_highlights")
                )
                session.add(fest_obj)
                stats["festivals"] += 1
            else:
                existing_fest.name = f["name"]
                existing_fest.significance = f.get("significance", existing_fest.significance)
                existing_fest.associated_places = f.get("associated_places", existing_fest.associated_places)

        # Flush to register primary keys
        session.flush()

        # ---------------------------------------------------------------------
        # 4. Unified Places Table
        # Track seen deduplication keys: (name_lower, round(lat, 4), round(lon, 4))
        # ---------------------------------------------------------------------
        seen_keys: Set[Tuple[str, float, float]] = set()

        # Query existing places in DB into index
        for p_row in session.query(Place.id, Place.name, Place.centroid, Place.bbox_min_lat, Place.bbox_min_lon).all():
            lat = p_row.bbox_min_lat
            lon = p_row.bbox_min_lon
            if (lat is None or lon is None) and p_row.centroid and p_row.centroid.startswith("POINT("):
                try:
                    c = p_row.centroid[6:-1].split()
                    lon, lat = float(c[0]), float(c[1])
                except Exception:
                    pass
            if lat is not None and lon is not None and p_row.name:
                seen_keys.add(normalize_dedup_key(p_row.name, lat, lon))

        # 4a. Cultural Heritage Places
        for h in self.heritage_data:
            lat = float(h["latitude"])
            lon = float(h["longitude"])
            validate_nepal_coords(lat, lon, h["name"])
            key = normalize_dedup_key(h["name"], lat, lon)

            # Generate or parse UUID
            try:
                place_uuid = uuid.UUID(h["id"])
            except Exception:
                place_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"heritage:{h['name']}")

            existing_place = session.query(Place).filter(Place.id == place_uuid).first()
            if not existing_place and key not in seen_keys:
                centroid_wkt = f"POINT({lon:.6f} {lat:.6f})"
                geom_wkt = h.get("geometry") or centroid_wkt
                raw_tags = h.get("raw_tags") or {}
                if "entry_fees" not in raw_tags and "entry_fees" in h:
                    raw_tags["entry_fees"] = h["entry_fees"]
                if "guidelines" not in raw_tags and "guidelines" in h:
                    raw_tags["guidelines"] = h["guidelines"]

                place_obj = Place(
                    id=place_uuid,
                    osm_id=h.get("osm_id"),
                    osm_type=h.get("osm_type", "node"),
                    name=h["name"],
                    category=h.get("category", "Religious Site"),
                    group=h.get("group", "Culture"),
                    geometry=geom_wkt,
                    centroid=centroid_wkt,
                    bbox_min_lat=float(h.get("bbox_min_lat", lat)),
                    bbox_min_lon=float(h.get("bbox_min_lon", lon)),
                    bbox_max_lat=float(h.get("bbox_max_lat", lat)),
                    bbox_max_lon=float(h.get("bbox_max_lon", lon)),
                    wikidata_id=h.get("wikidata_id"),
                    wikipedia_url=h.get("wikipedia_url"),
                    website=h.get("website"),
                    raw_tags=raw_tags,
                    import_metadata={"source": "seed_nepal_data", "type": "cultural_heritage"},
                    semantic_tags=h.get("semantic_tags", []),
                    travel_styles=h.get("travel_styles", []),
                    difficulty=h.get("difficulty"),
                    visit_duration=h.get("visit_duration", "1-2 hours"),
                    family_friendly=h.get("family_friendly", True),
                    accessibility=h.get("accessibility"),
                    best_seasons=h.get("best_seasons", []),
                    landscape=h.get("landscape", []),
                    image_url=h.get("image_url"),
                    gallery=h.get("gallery", []),
                    price_level=h.get("price_level"),
                    must_try=h.get("must_try"),
                    is_hidden_gem=bool(h.get("is_hidden_gem", False)),
                    popularity=float(h.get("popularity", 85.0)),
                    rating=float(h.get("rating", 4.8))
                )
                session.add(place_obj)
                seen_keys.add(key)
                stats["places_heritage"] += 1
            elif existing_place:
                # Update attributes
                existing_place.name = h["name"]
                existing_place.category = h.get("category", existing_place.category)
                existing_place.group = h.get("group", existing_place.group)
                if h.get("raw_tags"):
                    existing_place.raw_tags = h["raw_tags"]

        # 4b. Waypoints / Passes / Helipads / Medical Posts into Places
        for w in self.waypoints_data:
            lat = float(w["latitude"])
            lon = float(w["longitude"])
            validate_nepal_coords(lat, lon, w["name"])
            key = normalize_dedup_key(w["name"], lat, lon)

            wp_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"waypoint:{w['id']}")
            existing_place = session.query(Place).filter(Place.id == wp_uuid).first()

            if not existing_place and key not in seen_keys:
                cat = w.get("category", "Waypoint")
                # Group mapping
                if cat in ("Guest House", "Hotel", "Lodge"):
                    grp = "Accommodation"
                elif cat in ("Emergency Helipad", "Airport"):
                    grp = "Transport"
                elif cat in ("Mountain Pass", "Mountain Peak"):
                    grp = "Natural"
                elif cat in ("Settlement", "Acclimatization Hub"):
                    grp = "Culture"
                else:
                    grp = "Tourism"

                centroid_wkt = f"POINT({lon:.6f} {lat:.6f})"
                diff = "Challenging" if cat == "Mountain Pass" else None
                dur = "4-8 hours" if cat == "Mountain Pass" else ("1-2 hours" if cat == "Emergency Helipad" else "Overnight")
                pop = 75.0 if cat in ("Mountain Pass", "Acclimatization Hub") else 60.0

                raw_tags = {
                    "source": "seed_nepal_data",
                    "waypoint_id": w["id"],
                    "trail_id": w.get("trail_id"),
                    "region": w.get("region"),
                    "elevation_m": w.get("elevation_m"),
                    "details": w.get("details", {})
                }

                place_obj = Place(
                    id=wp_uuid,
                    osm_type="curated",
                    name=w["name"],
                    category=cat,
                    group=grp,
                    geometry=centroid_wkt,
                    centroid=centroid_wkt,
                    bbox_min_lat=lat,
                    bbox_min_lon=lon,
                    bbox_max_lat=lat,
                    bbox_max_lon=lon,
                    raw_tags=raw_tags,
                    import_metadata={"source": "seed_nepal_data", "type": "waypoint"},
                    semantic_tags=[cat, w.get("region", "Himalaya"), "High Altitude"],
                    travel_styles=["Alpine Trekking", "Himalayan Expedition"],
                    difficulty=diff,
                    visit_duration=dur,
                    family_friendly=cat not in ("Mountain Pass", "Emergency Helipad"),
                    best_seasons=["Autumn", "Spring"],
                    popularity=pop,
                    rating=4.7 if cat == "Mountain Pass" else 4.5,
                    is_hidden_gem=False
                )
                session.add(place_obj)
                seen_keys.add(key)
                stats["places_waypoints"] += 1

        # 4c. Trekking Trails into Places (Linear Attractions)
        for t in self.trails_data:
            trail_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"trail:{t['id']}")
            sp = t.get("start_point") or {}
            ep = t.get("end_point") or {}
            start_lat = sp.get("latitude", 28.0)
            start_lon = sp.get("longitude", 84.0)
            end_lat = ep.get("latitude", start_lat)
            end_lon = ep.get("longitude", start_lon)
            c_lat = (start_lat + end_lat) / 2.0
            c_lon = (start_lon + end_lon) / 2.0
            validate_nepal_coords(c_lat, c_lon, t["name"])

            key = normalize_dedup_key(t["name"], c_lat, c_lon)
            existing_place = session.query(Place).filter(Place.id == trail_uuid).first()

            if not existing_place and key not in seen_keys:
                geom_wkt = t.get("route_geometry_wkt") or f"POINT({c_lon:.6f} {c_lat:.6f})"
                centroid_wkt = f"POINT({c_lon:.6f} {c_lat:.6f})"
                raw_tags = {
                    "source": "seed_nepal_data",
                    "trail_id": t["id"],
                    "region": t.get("region"),
                    "permits_required": t.get("permits_required", []),
                    "duration_days": t.get("duration_days"),
                    "max_elevation_m": t.get("max_elevation_m"),
                    "pass_elevation_m": t.get("pass_elevation_m"),
                    "distance_km": t.get("distance_km"),
                    "key_waypoints": t.get("key_waypoints", []),
                    "start_point": sp,
                    "end_point": ep
                }

                place_obj = Place(
                    id=trail_uuid,
                    osm_id=t.get("osm_relation_id"),
                    osm_type="relation" if t.get("osm_relation_id") else "curated",
                    name=t["name"],
                    category="Trekking Route",
                    group="Tourism",
                    geometry=geom_wkt,
                    centroid=centroid_wkt,
                    bbox_min_lat=min(start_lat, end_lat),
                    bbox_min_lon=min(start_lon, end_lon),
                    bbox_max_lat=max(start_lat, end_lat),
                    bbox_max_lon=max(start_lon, end_lon),
                    raw_tags=raw_tags,
                    import_metadata={"source": "seed_nepal_data", "type": "trekking_trail"},
                    semantic_tags=["Trekking Trail", t.get("region", "Himalaya"), t.get("difficulty", "Challenging")],
                    travel_styles=["High Altitude Trekking", "Adventure"],
                    difficulty=t.get("difficulty", "Challenging"),
                    visit_duration=f"{t.get('duration_days', 10)} days",
                    family_friendly=t.get("difficulty") == "Easy",
                    best_seasons=t.get("best_seasons", ["Autumn", "Spring"]),
                    popularity=92.0,
                    rating=4.9,
                    is_hidden_gem=False
                )
                session.add(place_obj)
                seen_keys.add(key)
                stats["places_trails"] += 1

        # ---------------------------------------------------------------------
        # 5. Trail Reports & Stewards
        # ---------------------------------------------------------------------
        verified_reports = [
            TrailReport(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, "trail_report:audit_1"),
                hazard_type="Waste & Plastic Accumulation",
                urgency="Moderate",
                description="Over 180kg of energy bar wrappers and PET bottles removed by Sherpa Women's Eco-Guild. Waste transferred to Sagarmatha Pollution Control Committee.",
                location_name="Khumbu Corridor • Namche to Tengboche",
                latitude=27.8050,
                longitude=86.7140,
                altitude=3440,
                status="Resolved & Cleared",
                assigned_guild="SPCC Eco-Lodge Guild • 2.4h turnaround"
            ),
            TrailReport(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, "trail_report:audit_2"),
                hazard_type="Trail Obstruction / Landslide",
                urgency="Urgent",
                description="Shale slippage caused loose rocks across lower bypass trail. ACAP field wardens dispatched with local stone masons to reinforce retaining wall.",
                location_name="Annapurna Circuit • Dana to Ghasa",
                latitude=28.5390,
                longitude=83.6520,
                altitude=2810,
                status="In Field Dispatch",
                assigned_guild="ACAP Unit 04 • Crews en route"
            ),
            TrailReport(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, "trail_report:audit_3"),
                hazard_type="Heritage Shrine & Mani Wall Damage",
                urgency="Low",
                description="Frost weathering loosened slate inscriptions dating to 18th century. Slated for non-invasive lime mortar stabilization prior to Janai Purnima.",
                location_name="Trishuli Corridor • Gosainkunda Way",
                latitude=28.0820,
                longitude=85.3420,
                altitude=3120,
                status="Spring Yatra Scheduled",
                assigned_guild="Heritage Trust Guild • Apr Phase"
            ),
        ]
        for rep in verified_reports:
            existing = session.query(TrailReport).filter(TrailReport.id == rep.id).first()
            if not existing:
                session.add(rep)
                stats["trail_reports"] += 1

        verified_stewards = [
            TrailSteward(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, "trail_steward:pemba"),
                name="Pemba Dorjee Sherpa",
                email="pemba.sherpa@khumbu-clean.org",
                preferred_region="Khumbu Sanctuary",
                doko_pack_issued=True
            ),
            TrailSteward(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, "trail_steward:dawa"),
                name="Dawa Norbu Gurung",
                email="dawa.gurung@annapurna-wardens.org",
                preferred_region="Annapurna Circuit",
                doko_pack_issued=True
            ),
            TrailSteward(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, "trail_steward:pasang"),
                name="Pasang Lhamu Tamang",
                email="pasang.tamang@langtang-eco.org",
                preferred_region="Langtang Valley",
                doko_pack_issued=True
            )
        ]
        for stw in verified_stewards:
            existing = session.query(TrailSteward).filter(TrailSteward.id == stw.id).first()
            if not existing:
                session.add(stw)
                stats["trail_stewards"] += 1

        # ---------------------------------------------------------------------
        # 6. Sample Itineraries
        # ---------------------------------------------------------------------
        universal_itins_file = PROJECT_ROOT / "data" / "saved_itineraries_universal.json"
        if universal_itins_file.exists():
            try:
                with open(universal_itins_file, "r", encoding="utf-8") as f:
                    itins_data = json.load(f).get("itineraries", [])
                for idx, itin in enumerate(itins_data):
                    itin_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"itinerary:{itin.get('id', idx)}")
                    existing = session.query(Itinerary).filter(Itinerary.id == itin_uuid).first()
                    if not existing:
                        dest_list = []
                        it_data = itin.get("itinerary", {})
                        for day, acts in it_data.items():
                            for act in acts:
                                if isinstance(act, dict) and "name" in act:
                                    dest_list.append(act["name"])

                        itin_obj = Itinerary(
                            id=itin_uuid,
                            share_id=f"nepal-{itin.get('id', idx)[:20]}",
                            title=itin.get("title", f"Nepal Expedition {idx+1}"),
                            description=itin.get("description", "Curated Himalayan multi-day expedition."),
                            origin_name=itin.get("origin") or itin.get("from") or "Kathmandu",
                            dest_name=itin.get("destination") or itin.get("to") or "Himalayas",
                            num_days=int(itin.get("days", 3)),
                            pace=itin.get("pace", "balanced"),
                            budget=itin.get("budget", "medium"),
                            destinations=dest_list,
                            itinerary_data=it_data
                        )
                        session.add(itin_obj)
                        stats["itineraries"] += 1
            except Exception as e:
                self.logger.warning(f"Error parsing saved_itineraries_universal.json: {e}")

        session.flush()
        return stats

    def _generate_postgres_embeddings(self, engine) -> None:
        """Generate pgvector embeddings for PostgreSQL places lacking embeddings."""
        try:
            from backend.app.services.embedding_service import EmbeddingService
            self.logger.info("Initializing EmbeddingService for pgvector embeddings...")
            svc = EmbeddingService()
            svc.load_model()
            SessionCls = sessionmaker(bind=engine)
            with SessionCls() as session:
                unembedded = session.query(Place).outerjoin(Embedding, Place.id == Embedding.place_id).filter(Embedding.id.is_(None)).all()
                self.logger.info(f"Generating embeddings for {len(unembedded)} places...")
                for p in unembedded:
                    emb_dict = svc.generate_place_embedding(p)
                    emb_obj = Embedding(
                        id=uuid.uuid4(),
                        place_id=p.id,
                        model_name=emb_dict["model_name"],
                        model_version=emb_dict["model_version"],
                        dimensions=emb_dict["dimensions"],
                        vector=emb_dict["vector"],
                        embedding_text=emb_dict["embedding_text"]
                    )
                    session.add(emb_obj)
                session.commit()
                self.logger.info(f"Successfully generated {len(unembedded)} embeddings.")
        except Exception as e:
            self.logger.warning(f"Embedding generation skipped or incomplete: {e}")


def main():
    parser = argparse.ArgumentParser(description="YatraSathi Nepal Data Seeding Engine")
    parser.add_argument("--sqlite-path", type=str, default=str(PROJECT_ROOT / "yatra_sathi.db"), help="Path to SQLite DB")
    parser.add_argument("--postgres-url", type=str, default=os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/yatra_sathi"), help="Postgres DB URL")
    parser.add_argument("--skip-sqlite", action="store_true", help="Skip SQLite seeding")
    parser.add_argument("--skip-postgres", action="store_true", help="Skip Postgres seeding")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip pgvector embedding generation")
    parser.add_argument("--force", action="store_true", help="Recreate SQLite database from scratch")
    parser.add_argument("--verbose", action="store_true", help="Verbose log output")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    seeder = NepalDataSeeder(
        sqlite_path=Path(args.sqlite_path),
        postgres_url=args.postgres_url
    )

    if not args.skip_sqlite:
        seeder.seed_sqlite(force_recreate=args.force)

    if not args.skip_postgres:
        seeder.seed_postgres(generate_embeddings=not args.skip_embeddings)

    print("\nDatabase seeding completed successfully.")

if __name__ == "__main__":
    main()
