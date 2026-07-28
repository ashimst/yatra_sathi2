"""
Extract stage — nodes only.

Reads a .osm.pbf file and writes every travel-relevant OSM *node*
as a newline-delimited JSON record to EXTRACTED_FILE.

Why nodes only
--------------
Ways and relations require a two-pass location cache that adds ~28 min
of runtime and produces polygon / linestring geometries that the rest of
the pipeline immediately reduces to centroids anyway.  For Nepal POI data
virtually all meaningful places (peaks, temples, hotels, restaurants, …)
are mapped as nodes.  Ways/relations that represent the same feature are
deduplicated later by the spatial deduplication stage.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import osmium
from tqdm import tqdm

from etl.category_mapper import get_category, get_name
from etl.config import EXTRACTED_FILE, OSM_FILE
from etl.enums import OSMObjectType, Source
from etl.models import ImportMetadata, RawOSMObject


# ─────────────────────────────────────────────────────────────────────────────
# OSM tag filter — only extract nodes that map to a known travel category
# ─────────────────────────────────────────────────────────────────────────────

def _is_travel_node(tags: dict[str, str]) -> bool:
    """Return True if these OSM tags map to a known travel category."""
    return get_category(tags) is not None


# ─────────────────────────────────────────────────────────────────────────────
# Handler
# ─────────────────────────────────────────────────────────────────────────────

class NodeHandler(osmium.SimpleHandler):
    """
    Streams OSM nodes from a PBF file.

    Only nodes that:
      1. have a valid lat/lon
      2. map to a known travel category  (via category_mapper)
      3. have at least one usable name

    are written to the output JSONL file.
    """

    def __init__(self, output_path: Path) -> None:
        super().__init__()
        self._out = open(output_path, "w", encoding="utf-8")
        self._progress = tqdm(desc="Reading nodes", unit=" nodes")

        self.stats = {
            "total_seen":        0,
            "no_location":       0,
            "no_category":       0,
            "no_name":           0,
            "written":           0,
        }

    # ── osmium callback ──────────────────────────────────────────────────────

    def node(self, n: osmium.osm.Node) -> None:
        self.stats["total_seen"] += 1
        self._progress.update()

        # Guard: osmium marks nodes without stored coordinates as invalid
        if not n.location.valid():
            self.stats["no_location"] += 1
            return

        tags: dict[str, str] = dict(n.tags)

        if not _is_travel_node(tags):
            self.stats["no_category"] += 1
            return

        name = get_name(tags)
        if not name:
            self.stats["no_name"] += 1
            return

        obj = RawOSMObject(
            id=str(uuid.uuid4()),
            osm_id=n.id,
            osm_type=OSMObjectType.NODE,
            geometry={
                "type":        "Point",
                "coordinates": [n.location.lon, n.location.lat],
            },
            raw_tags=tags,
            import_metadata=ImportMetadata(
                source=Source.OSM,
                imported_at=datetime.now(UTC),
            ),
        )

        self._out.write(json.dumps(obj.__dict__, default=_json_default) + "\n")
        self.stats["written"] += 1

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        self._out.close()
        self._progress.close()
        self._print_summary()

    def _print_summary(self) -> None:
        s = self.stats
        print(f"\nExtraction complete:")
        print(f"  Total nodes seen:     {s['total_seen']:,}")
        print(f"  No location:          {s['no_location']:,}")
        print(f"  No category:          {s['no_category']:,}")
        print(f"  No name:              {s['no_name']:,}")
        print(f"  Written:              {s['written']:,}")
        print(f"\n  Output: {EXTRACTED_FILE}")


# ─────────────────────────────────────────────────────────────────────────────
# JSON serialisation helper
# ─────────────────────────────────────────────────────────────────────────────

def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value"):          # enums
        return obj.value
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"[extract] Reading: {OSM_FILE}")
    print(f"[extract] Output:  {EXTRACTED_FILE}")

    if not OSM_FILE.exists():
        raise FileNotFoundError(
            f"OSM PBF not found: {OSM_FILE}\n"
            "Place the Nepal PBF at data/raw/nepal-260717.osm.pbf"
        )

    handler = NodeHandler(EXTRACTED_FILE)
    try:
        # locations=False — nodes carry their own lat/lon; no cache needed
        handler.apply_file(str(OSM_FILE), locations=False)
    finally:
        handler.close()


if __name__ == "__main__":
    main()
