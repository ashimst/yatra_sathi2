"""
Semantic stage — adds structured travel metadata to every Place.

Input:  curated/places.jsonl
Output: curated/semantic_places.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path

from tqdm import tqdm

from etl.config import CURATED_FILE, SEMANTIC_FILE
from etl.hydration import stream_places
from etl.models import Place


# ─────────────────────────────────────────────────────────────────────────────
# Lookup tables  (category → semantic attributes)
# ─────────────────────────────────────────────────────────────────────────────

_TRAVEL_STYLES: dict[str, list[str]] = {
    "Mountain Peak":      ["Hiking", "Adventure", "Photography", "Nature"],
    "Waterfall":          ["Nature", "Photography", "Adventure"],
    "Lake":               ["Nature", "Photography", "Relaxation"],
    "Viewpoint":          ["Photography", "Nature", "Sightseeing"],
    "Museum":             ["Culture", "History", "Education"],
    "Gallery":            ["Culture", "Art"],
    "Castle":             ["History", "Architecture", "Photography"],
    "Fort":               ["History", "Architecture"],
    "Ruins":              ["History", "Archaeology", "Photography"],
    "Monument":           ["History", "Culture", "Photography"],
    "Memorial":           ["History", "Culture"],
    "Archaeological Site":["History", "Archaeology"],
    "Religious Site":     ["Culture", "Religion", "Spirituality"],
    "Park":               ["Nature", "Relaxation", "Family"],
    "Garden":             ["Nature", "Relaxation", "Photography"],
    "Nature Reserve":     ["Nature", "Wildlife", "Hiking"],
    "Forest":             ["Nature", "Hiking", "Wildlife"],
    "Cave":               ["Adventure", "Exploration"],
    "Hot Spring":         ["Relaxation", "Nature", "Wellness"],
    "Beach":              ["Nature", "Relaxation", "Swimming"],
    "Spring":             ["Nature", "Photography"],
    "Glacier":            ["Adventure", "Photography", "Nature"],
    "Restaurant":         ["Food", "Culture"],
    "Cafe":               ["Food", "Relaxation"],
    "Bar":                ["Food", "Social"],
    "Pub":                ["Food", "Social"],
    "Fast Food":          ["Food"],
    "Hotel":              ["Accommodation"],
    "Hostel":             ["Accommodation", "Budget"],
    "Guest House":        ["Accommodation", "Local Experience"],
    "Campground":         ["Adventure", "Nature", "Budget"],
    "Hospital":           ["Utilities"],
    "Pharmacy":           ["Utilities"],
    "ATM":                ["Utilities"],
    "Bus Station":        ["Transport"],
    "Airport":            ["Transport"],
    "Fuel Station":       ["Transport"],
}

_DIFFICULTY: dict[str, str] = {
    "Mountain Peak": "Hard",  "Cave": "Hard",
    "Waterfall": "Moderate",  "Fort": "Moderate",  "Ruins": "Moderate",
    "Nature Reserve": "Moderate", "Forest": "Moderate", "Viewpoint": "Moderate",
    "Glacier": "Hard",
}

_DURATION: dict[str, str] = {
    "Mountain Peak": "4-8 hours",  "Waterfall": "1-3 hours",
    "Lake": "2-4 hours",           "Viewpoint": "1-2 hours",
    "Museum": "2-3 hours",         "Gallery": "1-2 hours",
    "Castle": "2-4 hours",         "Fort": "2-3 hours",
    "Ruins": "1-2 hours",          "Monument": "30 minutes - 1 hour",
    "Religious Site": "1-2 hours", "Park": "1-3 hours",
    "Garden": "1-2 hours",         "Nature Reserve": "3-6 hours",
    "Forest": "2-4 hours",         "Cave": "2-3 hours",
    "Hot Spring": "1-2 hours",     "Beach": "2-4 hours",
    "Restaurant": "1-2 hours",     "Cafe": "1 hour",
    "Hotel": "Overnight",          "Guest House": "Overnight",
    "Campground": "Overnight",
}

_FAMILY: dict[str, bool] = {
    "Mountain Peak": False, "Cave": False, "Glacier": False,
}

_ACCESSIBILITY: dict[str, str] = {
    "Mountain Peak": "Requires hiking",   "Forest": "Requires hiking",
    "Waterfall": "Short hike required",   "Cave": "Not accessible",
    "Viewpoint": "Short hike or vehicle", "Glacier": "Requires hiking",
    "Ruins": "Uneven terrain",            "Fort": "Some stairs",
    "Castle": "Some stairs",              "Religious Site": "Varies",
    "Nature Reserve": "Variable",         "Hot Spring": "Short walk",
}

_SEASONS: dict[str, list[str]] = {
    "Mountain Peak":  ["Spring", "Autumn"],
    "Waterfall":      ["Monsoon", "Spring"],
    "Lake":           ["Spring", "Summer", "Autumn"],
    "Viewpoint":      ["Spring", "Autumn", "Winter"],
    "Hot Spring":     ["Winter", "Spring"],
    "Beach":          ["Summer", "Winter"],
    "Campground":     ["Spring", "Autumn"],
    "Nature Reserve": ["Spring", "Autumn"],
    "Forest":         ["Spring", "Autumn"],
    "Glacier":        ["Spring", "Summer"],
}

_LANDSCAPE: dict[str, list[str]] = {
    "Mountain Peak":  ["Mountain", "High Altitude"],
    "Waterfall":      ["Water", "Forest", "Mountain"],
    "Lake":           ["Water", "Mountain", "Valley"],
    "Viewpoint":      ["Mountain", "Valley", "Panoramic"],
    "Cave":           ["Underground", "Rock"],
    "Hot Spring":     ["Mountain", "Water"],
    "Beach":          ["Water", "Coastal"],
    "Forest":         ["Forest", "Wilderness"],
    "Nature Reserve": ["Forest", "Wilderness", "Protected"],
    "Glacier":        ["Mountain", "Ice", "High Altitude"],
    "Museum":         ["Urban", "Indoor"],
    "Gallery":        ["Urban", "Indoor"],
    "Restaurant":     ["Urban", "Indoor"],
    "Cafe":           ["Urban", "Indoor"],
    "Hotel":          ["Urban", "Indoor"],
}


def _compute_popularity(place: Place) -> float:
    """
    Compute a synthetic popularity score (0–100) from OSM signals alone.

    No external API needed — everything is derived from fields already
    present after the enrich stage.

    Signal                                  Points
    ──────────────────────────────────────  ──────
    Has wikidata_id                           40
    Has wikipedia_url                         30
    Has wikipedia_extract in raw_tags         20
    Has wikidata_description in raw_tags      10
    Has website                               10
    merge_count in raw_tags  (+5 each, ≤20)   0–20
    name:en AND name:ne both filled            5
    Has ele tag (notable peak)                 5
    tourism = attraction/heritage/museum      10
    historic tag present                      10
    natural tag = peak/lake/waterfall/cave    10
    Has official_name or alt_name             3
    ──────────────────────────────────────  ──────
    Max raw                                 ~173  → capped at 100
    """
    rt = place.raw_tags or {}
    score = 0.0

    # Wiki linkage — the strongest signal that a place is well-known
    if place.wikidata_id:
        score += 40
    if place.wikipedia_url:
        score += 30
    if rt.get("wikipedia_extract"):
        score += 20
    if rt.get("wikidata_description"):
        score += 10

    # Web presence
    if place.website or rt.get("website") or rt.get("contact:website"):
        score += 10

    # OSM merge count — more merges means more editors noticed it
    try:
        merge_count = int(rt.get("merge_count", 0) or 0)
        score += min(merge_count * 5, 20)
    except (ValueError, TypeError):
        pass

    # Internationally known — has both English and Nepali names
    has_en = bool((rt.get("name:en") or "").strip())
    has_ne = bool((rt.get("name:ne") or rt.get("name:nep") or "").strip())
    if has_en and has_ne:
        score += 5

    # Notable physical feature
    if rt.get("ele") or rt.get("elevation"):
        score += 5

    # High-value OSM tourism/historic tags
    tourism_val = (rt.get("tourism") or "").lower()
    if tourism_val in ("attraction", "museum", "artwork", "viewpoint",
                       "theme_park", "zoo", "aquarium", "gallery",
                       "heritage", "information"):
        score += 10

    if rt.get("historic"):
        score += 10

    natural_val = (rt.get("natural") or "").lower()
    if natural_val in ("peak", "volcano", "glacier", "cave_entrance",
                       "water", "waterfall", "lake", "wetland", "geyser"):
        score += 10

    # Alt name / official name — somebody cared enough to add one
    if rt.get("official_name") or rt.get("alt_name"):
        score += 3

    return min(100.0, score)


def _generate(place: Place) -> None:
    """Populate semantic fields and synthetic popularity on a Place in-place."""
    cat = place.category or ""
    place.travel_styles   = _TRAVEL_STYLES.get(cat, ["Sightseeing"])
    place.difficulty      = _DIFFICULTY.get(cat)
    place.visit_duration  = _DURATION.get(cat)
    place.family_friendly = _FAMILY.get(cat, True)
    place.accessibility   = _ACCESSIBILITY.get(cat, "Fully accessible")
    place.best_seasons    = _SEASONS.get(cat, ["All year"])
    place.landscape       = _LANDSCAPE.get(cat, ["General"])
    place.semantic_tags   = (
        [cat, place.group or ""]
        + place.travel_styles
        + (["Wikidata linked"] if place.wikidata_id else [])
        + (["Wikipedia linked"] if place.wikipedia_url else [])
    )

    # Synthetic popularity — only set if not already enriched with a real value
    if place.popularity is None:
        place.popularity = _compute_popularity(place)


class SemanticPipeline:

    def __init__(
        self,
        input_file:  Path = CURATED_FILE,
        output_file: Path = SEMANTIC_FILE,
    ) -> None:
        self.input_file  = input_file
        self.output_file = output_file
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats = {"total": 0, "ok": 0, "failed": 0}

    def run(self) -> None:
        print(f"[semantic] {self.input_file} → {self.output_file}")
        pop_nonzero = 0
        with open(self.output_file, "w", encoding="utf-8") as out:
            for place in tqdm(stream_places(self.input_file), desc="Semantic", unit=" places"):
                self.stats["total"] += 1
                try:
                    _generate(place)
                    if place.popularity and place.popularity > 0:
                        pop_nonzero += 1
                    out.write(json.dumps(place.to_dict()) + "\n")
                    self.stats["ok"] += 1
                except Exception as e:
                    print(f"[semantic] error on {place.id}: {e}")
                    self.stats["failed"] += 1
        total = max(self.stats["total"], 1)
        print(
            f"\nSemantic complete: {self.stats['ok']:,} processed, "
            f"{self.stats['failed']} failed, "
            f"{pop_nonzero:,} places with popularity > 0 "
            f"({100 * pop_nonzero // total}%)"
        )


def main() -> None:
    SemanticPipeline().run()


if __name__ == "__main__":
    main()
