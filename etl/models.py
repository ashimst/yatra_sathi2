"""
ETL data models.

These are pure-Python dataclasses used only inside the ETL pipeline.
They are intentionally decoupled from the SQLAlchemy backend models.

Design rules
------------
* One canonical field name per concept — no dual aliases.
* centroid is always stored as tuple[float, float] = (lon, lat).
  After a JSONL round-trip it becomes list[float]; hydration.py
  normalises it back to a tuple on load.
* wikidata_id stores a Wikidata Q-ID string (e.g. "Q105124").
* wikipedia_url stores a full URL string.
* import_metadata is the single field name (no legacy `metadata` alias).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from etl.enums import OSMObjectType, Source


# ─────────────────────────────────────────────────────────────────────────────
# Import metadata
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ImportMetadata:
    source:      Source   = Source.OSM
    imported_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version:     int      = 1
    license:     str      = "ODbL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source":      self.source.value,
            "imported_at": self.imported_at.isoformat(),
            "version":     self.version,
            "license":     self.license,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Raw OSM object (extract stage output)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RawOSMObject:
    """Minimal representation of a single OSM node as it comes off the PBF."""

    id:              Optional[str]        = None
    osm_id:          int                  = 0
    osm_type:        OSMObjectType        = OSMObjectType.NODE
    geometry:        dict[str, Any]       = field(default_factory=dict)
    raw_tags:        dict[str, str]       = field(default_factory=dict)
    import_metadata: ImportMetadata       = field(default_factory=ImportMetadata)


# ─────────────────────────────────────────────────────────────────────────────
# Normalised Place (all stages after extract)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Place:
    """
    Normalised place record that flows through the entire ETL pipeline.

    Canonical field decisions
    ─────────────────────────
    centroid        : tuple[float, float] = (lon, lat)  — Shapely (x, y) order
    wikidata_id     : Optional[str]       — Wikidata Q-ID, e.g. "Q105124"
    wikipedia_url   : Optional[str]       — full URL, e.g. "https://en.wikipedia.org/wiki/…"
    import_metadata : ImportMetadata      — single field name, no `metadata` alias
    """

    # Core identity
    id:           Optional[str]      = None
    osm_id:       Optional[int]      = None
    osm_type:     Optional[OSMObjectType] = None
    name:         Optional[str]      = None
    category:     Optional[str]      = None
    group:        Optional[str]      = None

    # Geometry
    geometry:     Optional[dict]     = None
    centroid:     Optional[tuple]    = None   # (lon, lat)
    bbox_min_lat: Optional[float]    = None
    bbox_min_lon: Optional[float]    = None
    bbox_max_lat: Optional[float]    = None
    bbox_max_lon: Optional[float]    = None

    # External links  (single canonical names)
    wikidata_id:   Optional[str]     = None   # Q-ID string
    wikipedia_url: Optional[str]     = None   # full URL string
    website:       Optional[str]     = None

    # Raw OSM tags and import provenance
    raw_tags:        dict[str, Any]    = field(default_factory=dict)
    import_metadata: ImportMetadata    = field(default_factory=ImportMetadata)

    # Semantic metadata  (populated by semantic.py)
    semantic_tags:   list[str]         = field(default_factory=list)
    travel_styles:   list[str]         = field(default_factory=list)
    difficulty:      Optional[str]     = None
    visit_duration:  Optional[str]     = None
    family_friendly: Optional[bool]    = None
    accessibility:   Optional[str]     = None
    best_seasons:    list[str]         = field(default_factory=list)
    landscape:       list[str]         = field(default_factory=list)

    # Quality signals
    popularity: Optional[float] = None
    rating:     Optional[float] = None

    # ── serialisation ────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable dict.  Tuples → lists; enums → values."""
        out: dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if isinstance(v, ImportMetadata):
                out[k] = v.to_dict()
            elif isinstance(v, OSMObjectType):
                out[k] = v.value
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            elif isinstance(v, tuple):
                out[k] = list(v)
            else:
                out[k] = v
        return out
