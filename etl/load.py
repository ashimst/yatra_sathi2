"""
Load stage — upserts curated/semantic_places.jsonl into PostgreSQL.

Key changes from the old load.py
---------------------------------
* Does NOT drop tables on every run.  Tables are created if they don't
  exist; existing rows are updated in-place.  User tables (users,
  itineraries, sessions) are never touched.
* centroid stored as WKT POINT(lon lat) string.
* geometry stored as WKT string.
* Single canonical field names — no dual-alias fallbacks needed because
  Place now has only one name per concept.
"""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import shape
from tqdm import tqdm

from etl.config import SEMANTIC_FILE
from etl.hydration import serialize_metadata, stream_places
from etl.models import Place
from backend.app.db.database import SessionLocal, create_tables, init_database
from backend.app.models.place import Place as PlaceDB


# ─────────────────────────────────────────────────────────────────────────────
# Conversion helper
# ─────────────────────────────────────────────────────────────────────────────

def place_to_db(place: Place) -> PlaceDB:
    """Convert ETL Place dataclass → SQLAlchemy PlaceDB row."""
    rt = place.raw_tags or {}

    # Geometry → WKT
    geom_wkt = None
    bbox_min_lat = bbox_min_lon = bbox_max_lat = bbox_max_lon = None
    if place.geometry:
        try:
            geom = shape(place.geometry)
            geom_wkt = geom.wkt
            bx = geom.bounds          # (min_lon, min_lat, max_lon, max_lat)
            bbox_min_lon, bbox_min_lat, bbox_max_lon, bbox_max_lat = bx
        except Exception:
            pass

    # Centroid (lon, lat) tuple → WKT
    centroid_wkt = None
    if place.centroid and len(place.centroid) == 2:
        lon, lat = place.centroid
        centroid_wkt = f"POINT({lon} {lat})"

    # OSM type
    osm_type_val = place.osm_type.value if place.osm_type else None

    # Import metadata
    meta_dict = serialize_metadata(place.import_metadata) if place.import_metadata else {}

    # family_friendly coercion (may arrive as string from raw_tags)
    ff = place.family_friendly
    if isinstance(ff, str):
        ff = ff.lower() in ("yes", "true", "1")

    return PlaceDB(
        id=place.id,
        osm_id=place.osm_id,
        osm_type=osm_type_val,
        name=place.name,
        category=place.category,
        group=place.group,
        geometry=geom_wkt,
        centroid=centroid_wkt,
        bbox_min_lat=bbox_min_lat,
        bbox_min_lon=bbox_min_lon,
        bbox_max_lat=bbox_max_lat,
        bbox_max_lon=bbox_max_lon,
        wikidata_id=place.wikidata_id,
        wikipedia_url=place.wikipedia_url,
        website=place.website,
        raw_tags=rt,
        import_metadata=meta_dict,
        semantic_tags=place.semantic_tags or [],
        travel_styles=place.travel_styles or [],
        difficulty=place.difficulty,
        visit_duration=place.visit_duration,
        family_friendly=ff,
        accessibility=place.accessibility,
        best_seasons=place.best_seasons or [],
        landscape=place.landscape or [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseLoader:

    def __init__(
        self,
        input_file: Path = SEMANTIC_FILE,
        batch_size: int  = 50,
    ) -> None:
        self.input_file = input_file
        self.batch_size = batch_size
        self.stats = {"read": 0, "inserted": 0, "updated": 0, "failed": 0}

    def _load_batch(self, places: list[Place], session) -> tuple[int, int]:
        ins = upd = 0
        for place in places:
            try:
                session.begin_nested()
                existing = session.query(PlaceDB).filter(PlaceDB.id == place.id).first()
                if not existing and place.osm_id:
                    existing = session.query(PlaceDB).filter(PlaceDB.osm_id == place.osm_id).first()

                new = place_to_db(place)

                if existing:
                    for col in (
                        "name", "category", "group", "geometry", "centroid",
                        "bbox_min_lat", "bbox_min_lon", "bbox_max_lat", "bbox_max_lon",
                        "wikidata_id", "wikipedia_url", "website", "raw_tags",
                        "import_metadata", "semantic_tags", "travel_styles",
                        "difficulty", "visit_duration", "family_friendly",
                        "accessibility", "best_seasons", "landscape",
                    ):
                        setattr(existing, col, getattr(new, col))
                    upd += 1
                else:
                    session.add(new)
                    ins += 1

                session.commit()
            except Exception as e:
                session.rollback()
                print(f"[load] error place {place.id}: {str(e)[:100]}")
                self.stats["failed"] += 1
        return ins, upd

    def run(self) -> None:
        print(f"[load] {self.input_file} → DB")

        # Ensure tables exist (CREATE IF NOT EXISTS — does not touch existing data)
        init_database()
        create_tables()
        print("[load] Tables ready")

        session = SessionLocal()
        batch: list[Place] = []
        progress = tqdm(desc="Load", unit=" places")

        try:
            for place in stream_places(self.input_file):
                self.stats["read"] += 1
                batch.append(place)
                progress.update()
                if len(batch) >= self.batch_size:
                    ins, upd = self._load_batch(batch, session)
                    self.stats["inserted"] += ins
                    self.stats["updated"]  += upd
                    batch = []
                    progress.set_postfix(ins=self.stats["inserted"], upd=self.stats["updated"])

            if batch:
                ins, upd = self._load_batch(batch, session)
                self.stats["inserted"] += ins
                self.stats["updated"]  += upd
        finally:
            session.close()
            progress.close()

        print(f"\nLoad complete:")
        print(f"  Read:     {self.stats['read']:,}")
        print(f"  Inserted: {self.stats['inserted']:,}")
        print(f"  Updated:  {self.stats['updated']:,}")
        print(f"  Failed:   {self.stats['failed']:,}")


def main() -> None:
    DatabaseLoader().run()


if __name__ == "__main__":
    main()
