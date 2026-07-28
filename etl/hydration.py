"""
Hydration utilities — deserialise JSONL records back into ETL dataclasses.

Rules
-----
* centroid is always normalised to tuple[float, float] = (lon, lat).
  JSON round-trips turn tuples into lists; we fix that here.
* import_metadata is the one canonical field name — no `metadata` alias.
* osm_type is always coerced to OSMObjectType enum.
* Streaming readers never load an entire file into memory.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator

from etl.enums import OSMObjectType, Source
from etl.models import ImportMetadata, Place, RawOSMObject


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _coerce_osm_type(value: Any) -> OSMObjectType:
    if isinstance(value, OSMObjectType):
        return value
    try:
        return OSMObjectType(str(value))
    except (ValueError, KeyError):
        return OSMObjectType.NODE


def _coerce_metadata(value: Any) -> ImportMetadata:
    if isinstance(value, ImportMetadata):
        return value
    if not isinstance(value, dict):
        return ImportMetadata()

    source_raw = value.get("source", "osm")
    try:
        source = Source(source_raw) if isinstance(source_raw, str) else Source.OSM
    except ValueError:
        source = Source.OSM

    imported_raw = value.get("imported_at")
    if isinstance(imported_raw, datetime):
        imported_at = imported_raw
    elif isinstance(imported_raw, str):
        try:
            imported_at = datetime.fromisoformat(imported_raw)
        except ValueError:
            imported_at = datetime.now(UTC)
    else:
        imported_at = datetime.now(UTC)

    return ImportMetadata(
        source=source,
        imported_at=imported_at,
        version=value.get("version", 1),
        license=value.get("license", "ODbL"),
    )


def _coerce_centroid(value: Any) -> tuple[float, float] | None:
    """Normalise centroid to (lon, lat) tuple regardless of source type."""
    if value is None:
        return None
    if isinstance(value, tuple) and len(value) == 2:
        return value
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (float(value[0]), float(value[1]))
    return None


# ─────────────────────────────────────────────────────────────────────────────
# RawOSMObject hydration
# ─────────────────────────────────────────────────────────────────────────────

def hydrate_raw_osm_object(data: dict[str, Any]) -> RawOSMObject:
    """
    Deserialise a JSON dict (from extract stage JSONL) into a RawOSMObject.

    Handles the nested ImportMetadata dict that _json_default serialised.
    """
    meta_raw = data.get("import_metadata") or data.get("metadata") or {}

    return RawOSMObject(
        id=data.get("id"),
        osm_id=data.get("osm_id", 0),
        osm_type=_coerce_osm_type(data.get("osm_type", "node")),
        geometry=data.get("geometry") or {},
        raw_tags=data.get("raw_tags") or {},
        import_metadata=_coerce_metadata(meta_raw),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Place hydration
# ─────────────────────────────────────────────────────────────────────────────

def hydrate_place(data: dict[str, Any]) -> Place:
    """
    Deserialise a JSON dict (from any post-extract stage JSONL) into a Place.

    Normalises:
      * centroid list → tuple
      * osm_type string → OSMObjectType
      * import_metadata dict → ImportMetadata  (accepts both field-name variants)
    """
    # Normalise metadata field name  (old runs may have written "metadata")
    if "metadata" in data and "import_metadata" not in data:
        data["import_metadata"] = data.pop("metadata")

    return Place(
        id=data.get("id"),
        osm_id=data.get("osm_id"),
        osm_type=_coerce_osm_type(data.get("osm_type")) if data.get("osm_type") else None,
        name=data.get("name"),
        category=data.get("category"),
        group=data.get("group"),
        geometry=data.get("geometry"),
        centroid=_coerce_centroid(data.get("centroid")),
        bbox_min_lat=data.get("bbox_min_lat"),
        bbox_min_lon=data.get("bbox_min_lon"),
        bbox_max_lat=data.get("bbox_max_lat"),
        bbox_max_lon=data.get("bbox_max_lon"),
        wikidata_id=data.get("wikidata_id"),
        wikipedia_url=data.get("wikipedia_url"),
        website=data.get("website"),
        raw_tags=data.get("raw_tags") or {},
        import_metadata=_coerce_metadata(data.get("import_metadata") or {}),
        semantic_tags=data.get("semantic_tags") or [],
        travel_styles=data.get("travel_styles") or [],
        difficulty=data.get("difficulty"),
        visit_duration=data.get("visit_duration"),
        family_friendly=data.get("family_friendly"),
        accessibility=data.get("accessibility"),
        best_seasons=data.get("best_seasons") or [],
        landscape=data.get("landscape") or [],
        popularity=data.get("popularity"),
        rating=data.get("rating"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Streaming readers
# ─────────────────────────────────────────────────────────────────────────────

def stream_raw_objects(path: Path) -> Generator[RawOSMObject, None, None]:
    """Yield RawOSMObjects from a JSONL file one at a time."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield hydrate_raw_osm_object(json.loads(line))


def stream_places(path: Path) -> Generator[Place, None, None]:
    """Yield Places from a JSONL file one at a time."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield hydrate_place(json.loads(line))


def load_all_places(path: Path) -> list[Place]:
    """Load all Places into memory (use only when random access is required)."""
    return list(stream_places(path))


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def serialize_metadata(metadata: ImportMetadata | dict) -> dict[str, Any]:
    """Serialise an ImportMetadata to a plain dict (safe for JSON/JSONB)."""
    if isinstance(metadata, dict):
        return metadata
    return metadata.to_dict()
