"""
Automated Pytest & Standalone Validator for YatraSathi Cultural Heritage & Festivals Seed Data
Usage:
    pytest backend/data/seeds/validate_heritage_seeds.py -v
    python backend/data/seeds/validate_heritage_seeds.py
"""

import sys
import json
import math
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.place import Place

NEPAL_BOUNDS = {
    "min_lat": 26.0,
    "max_lat": 30.5,
    "min_lon": 80.0,
    "max_lon": 88.5,
}

REQUIRED_FESTIVALS = [
    "dashain", "tihar & chhath", "indra jatra", "bisket jatra",
    "rato machhindranath jatra", "buddha jayanti", "mani rimdu",
    "losar", "maha shivaratri", "holi", "tiji festival", "gai jatra",
    "vivah panchami"
]

def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2)**2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@pytest.fixture(scope="module")
def seed_data():
    seeds_dir = Path(__file__).resolve().parent
    heritage_file = seeds_dir / "cultural_heritage.json"
    festivals_file = seeds_dir / "festivals.json"

    assert heritage_file.exists(), f"Missing file: {heritage_file}"
    assert festivals_file.exists(), f"Missing file: {festivals_file}"

    with open(heritage_file, "r", encoding="utf-8") as f:
        places = json.load(f)
    with open(festivals_file, "r", encoding="utf-8") as f:
        festivals = json.load(f)

    return {"places": places, "festivals": festivals}

def test_files_exist(seed_data):
    """Test seed files exist and load valid non-empty JSON."""
    places = seed_data["places"]
    festivals = seed_data["festivals"]
    assert len(places) >= 60, f"Expected at least 60 places, found {len(places)}"
    assert len(festivals) >= 13, f"Expected at least 13 festivals, found {len(festivals)}"

def test_nepal_geographic_bounds(seed_data):
    """Test 100% of location coordinates fall strictly within Nepal bounding box."""
    for p in seed_data["places"]:
        lat, lon = p["latitude"], p["longitude"]
        assert NEPAL_BOUNDS["min_lat"] <= lat <= NEPAL_BOUNDS["max_lat"], (
            f"Latitude {lat} for '{p['name']}' out of bounds [26.0, 30.5]"
        )
        assert NEPAL_BOUNDS["min_lon"] <= lon <= NEPAL_BOUNDS["max_lon"], (
            f"Longitude {lon} for '{p['name']}' out of bounds [80.0, 88.5]"
        )

def test_centroid_wkt_format_and_sync(seed_data):
    """Test centroid WKT format POINT(lon lat) and exact lat/lon sync."""
    for p in seed_data["places"]:
        centroid = p["centroid"]
        assert centroid.startswith("POINT(") and centroid.endswith(")"), (
            f"Invalid centroid format for '{p['name']}': {centroid}"
        )
        coords = centroid[6:-1].split()
        assert len(coords) == 2, f"Centroid '{centroid}' does not have 2 coords"
        c_lon, c_lat = float(coords[0]), float(coords[1])
        assert abs(c_lon - p["longitude"]) < 1e-4, f"Longitude mismatch in {p['name']}"
        assert abs(c_lat - p["latitude"]) < 1e-4, f"Latitude mismatch in {p['name']}"

def test_deduplication_and_spatial_isolation(seed_data):
    """Test zero duplicates by name and zero collocated duplicates (<20m)."""
    places = seed_data["places"]
    names_seen = set()
    for p in places:
        norm = p["name"].strip().lower()
        assert norm not in names_seen, f"Duplicate place name: {p['name']}"
        names_seen.add(norm)

    for i in range(len(places)):
        for j in range(i + 1, len(places)):
            p1, p2 = places[i], places[j]
            dist = haversine_m(p1["latitude"], p1["longitude"], p2["latitude"], p2["longitude"])
            if dist < 20:
                assert p1["name"].lower() != p2["name"].lower(), (
                    f"Collocated duplicate places (<20m): {p1['name']} and {p2['name']}"
                )

def test_comparative_entry_fees_tiers(seed_data):
    """Test all places have valid comparative entry fee tiers in NPR."""
    for p in seed_data["places"]:
        fees = p.get("entry_fees")
        assert isinstance(fees, dict), f"Missing entry_fees dict in {p['name']}"
        for key in ["foreign_npr", "saarc_npr", "nepali_npr", "currency"]:
            assert key in fees, f"Missing '{key}' in entry_fees of {p['name']}"
        assert fees["currency"] == "NPR", f"Currency not NPR in {p['name']}"
        assert fees["foreign_npr"] >= 0, f"Negative foreign fee in {p['name']}"
        assert fees["saarc_npr"] >= 0, f"Negative saarc fee in {p['name']}"
        assert fees["nepali_npr"] >= 0, f"Negative nepali fee in {p['name']}"

def test_travel_guidelines_completeness(seed_data):
    """Test all places have required travel guidelines."""
    for p in seed_data["places"]:
        g = p.get("guidelines")
        assert isinstance(g, dict), f"Missing guidelines dict in {p['name']}"
        for key in ["dress_code", "photography", "shoes_prohibited", "sanctum_restrictions", "opening_hours"]:
            assert key in g and g[key] is not None, f"Missing '{key}' in guidelines of {p['name']}"

def test_13_major_nepali_festivals_catalog(seed_data):
    """Test 13 major festivals with lunar months, Gregorian windows, significance, rituals."""
    festivals = seed_data["festivals"]
    assert len(festivals) >= 13, f"Expected 13 festivals, found {len(festivals)}"

    fest_names = [f["name"].lower() for f in festivals]
    for rf in REQUIRED_FESTIVALS:
        assert any(rf in fn for fn in fest_names), f"Missing required festival: {rf}"

    for f in festivals:
        for key in ["name", "lunar_month", "typical_gregorian_window", "significance", "primary_regions", "associated_places", "rituals"]:
            assert key in f and f[key], f"Missing '{key}' in festival {f['name']}"
            if isinstance(f[key], list):
                assert len(f[key]) > 0, f"Empty list for '{key}' in {f['name']}"

def test_sqlalchemy_place_orm_instantiation(seed_data):
    """Test that all places instantiate clean SQLAlchemy Place models with matching properties."""
    for p in seed_data["places"]:
        place_obj = Place(
            name=p["name"],
            category=p["category"],
            group=p["group"],
            geometry=p["geometry"],
            centroid=p["centroid"],
            bbox_min_lat=p["bbox_min_lat"],
            bbox_min_lon=p["bbox_min_lon"],
            bbox_max_lat=p["bbox_max_lat"],
            bbox_max_lon=p["bbox_max_lon"],
            wikidata_id=p["wikidata_id"],
            wikipedia_url=p["wikipedia_url"],
            website=p["website"],
            raw_tags=p["raw_tags"],
            import_metadata=p["import_metadata"],
            semantic_tags=p["semantic_tags"],
            travel_styles=p["travel_styles"],
            best_seasons=p["best_seasons"],
            landscape=p["landscape"],
            image_url=p["image_url"],
            gallery=p["gallery"],
            price_level=p["price_level"],
            must_try=p["must_try"],
            is_hidden_gem=p["is_hidden_gem"],
            popularity=p["popularity"],
            rating=p["rating"],
            family_friendly=p["family_friendly"],
            accessibility=p["accessibility"],
        )
        assert place_obj.latitude == p["latitude"], f"ORM latitude mismatch for {p['name']}"
        assert place_obj.longitude == p["longitude"], f"ORM longitude mismatch for {p['name']}"
        d = place_obj.to_dict()
        assert d["name"] == p["name"]
        assert d["latitude"] == p["latitude"]
        assert d["longitude"] == p["longitude"]

if __name__ == "__main__":
    print("Running seed validation suite...")
    ret = pytest.main([__file__, "-v"])
    sys.exit(ret)
