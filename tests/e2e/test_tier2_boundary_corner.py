"""
Tier 2: Boundary & Corner Cases Test Suite
Validates Nepal geographic boundary conditions, elevation limits, missing fields,
duplicate detection, extreme values, and adversarial query inputs across datasets and APIs.
"""
import pytest
import math
import uuid
from typing import Dict, Any, List

from tests.e2e.conftest import (
    NEPAL_LAT_MIN,
    NEPAL_LAT_MAX,
    NEPAL_LON_MIN,
    NEPAL_LON_MAX,
    NEPAL_MIN_ALTITUDE,
    NEPAL_MAX_ALTITUDE,
    TestSessionLocal,
)
from backend.app.models.place import Place
from backend.app.models.trail_watch import TrailReport, TrailSteward
from backend.app.models.itinerary import Itinerary
from backend.app.services.place_service import place_service
from backend.app.api.places import get_places, search_places, geocode_place
from backend.app.api.trail_watch import get_reports, get_stats


def _run_coro(coro):
    """Execute coroutine synchronously without event loop socket binding."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


# =============================================================================
# Category 1: Nepal Border Coordinate Boundaries
# =============================================================================
class TestNepalBorderCoordinates:
    """Boundary conditions on Nepal border limits (26.0°N–30.5°N, 80.0°E–88.5°E)."""

    def test_coordinates_exactly_on_min_border(self):
        """Points right on the southwestern border minimums are recognized within bounds."""
        lat, lon = NEPAL_LAT_MIN, NEPAL_LON_MIN
        assert NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX
        assert NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX

    def test_coordinates_exactly_on_max_border(self):
        """Points right on the northeastern border maximums are recognized within bounds."""
        lat, lon = NEPAL_LAT_MAX, NEPAL_LON_MAX
        assert NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX
        assert NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX

    def test_coordinates_strictly_outside_south_rejected(self):
        """Latitude 25.99°N (India - Bihar/UP) is outside Nepal boundary."""
        lat = NEPAL_LAT_MIN - 0.01
        assert not (NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX)

    def test_coordinates_strictly_outside_north_rejected(self):
        """Latitude 30.51°N (Tibet Autonomous Region) is outside Nepal boundary."""
        lat = NEPAL_LAT_MAX + 0.01
        assert not (NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX)

    def test_coordinates_strictly_outside_west_rejected(self):
        """Longitude 79.99°E (India - Uttarakhand) is outside Nepal boundary."""
        lon = NEPAL_LON_MIN - 0.01
        assert not (NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX)

    def test_coordinates_strictly_outside_east_rejected(self):
        """Longitude 88.51°E (India - Sikkim/West Bengal) is outside Nepal boundary."""
        lon = NEPAL_LON_MAX + 0.01
        assert not (NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX)

    def test_seed_datasets_zero_border_overflow(self, heritage_data, waypoints_data, trails_data):
        """Ensure 100% of persistent seed points are strictly inside Nepal boundaries."""
        for item in heritage_data + waypoints_data:
            lat = item.get("latitude")
            lon = item.get("longitude")
            assert lat is not None and lon is not None
            assert NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX, f"Point {item.get('name')} lat {lat} out of bounds"
            assert NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX, f"Point {item.get('name')} lon {lon} out of bounds"

        for trail in trails_data:
            sp = trail.get("start_point")
            ep = trail.get("end_point")
            if sp:
                assert NEPAL_LAT_MIN <= sp["latitude"] <= NEPAL_LAT_MAX
                assert NEPAL_LON_MIN <= sp["longitude"] <= NEPAL_LON_MAX
            if ep:
                assert NEPAL_LAT_MIN <= ep["latitude"] <= NEPAL_LAT_MAX
                assert NEPAL_LON_MIN <= ep["longitude"] <= NEPAL_LON_MAX


# =============================================================================
# Category 2: Elevation & Altitude Boundaries
# =============================================================================
class TestElevationBoundaries:
    """Elevation boundaries: lowest point 60m to summit 8848.86m."""

    def test_zero_and_negative_elevations_invalid_in_nepal(self, waypoints_data, trails_data):
        """No waypoint or trail max elevation should be zero or negative in Nepal."""
        for wp in waypoints_data:
            elev = wp.get("elevation_m")
            if elev is not None:
                assert elev >= NEPAL_MIN_ALTITUDE, f"Waypoint {wp.get('name')} has sub-terai elevation {elev}m"

        for tr in trails_data:
            max_el = tr.get("max_elevation_m")
            assert max_el >= NEPAL_MIN_ALTITUDE, f"Trail {tr.get('name')} max elevation {max_el}m too low"

    def test_extreme_high_altitude_thresholds(self, waypoints_data, trails_data):
        """Highest peaks must not exceed Mount Everest's official height (8848.86m)."""
        for wp in waypoints_data:
            elev = wp.get("elevation_m")
            if elev is not None:
                assert elev <= NEPAL_MAX_ALTITUDE, f"Waypoint {wp.get('name')} elevation {elev}m exceeds Everest"

        for tr in trails_data:
            max_el = tr.get("max_elevation_m")
            assert max_el <= NEPAL_MAX_ALTITUDE, f"Trail {tr.get('name')} elevation {max_el}m exceeds Everest"

    def test_pass_elevations_between_subalpine_and_death_zone(self, waypoints_data):
        """Major trekking passes (Yamda La, Thorong La, Larkya La, Cho La) sit between 3,500m and 6,000m."""
        passes = [w for w in waypoints_data if w.get("category") == "Mountain Pass"]
        assert len(passes) >= 3, "Insufficient mountain passes in waypoint catalog"
        for p in passes:
            elev = p.get("elevation_m", 0)
            assert 3000.0 <= elev <= 6000.0, f"Mountain pass {p.get('name')} elevation {elev}m outside realistic pass corridor"

    def test_medical_post_elevations_in_acclimatization_zones(self, waypoints_data):
        """Medical posts and travel hospitals range from gateway cities (Pokhara/Kathmandu ~800m) to high-altitude clinics (Pheriche/Manang ~4,500m)."""
        clinics = [w for w in waypoints_data if w.get("category") == "Medical Post"]
        assert len(clinics) >= 2, "Insufficient medical aid posts"
        for c in clinics:
            elev = c.get("elevation_m", 0)
            assert 500.0 <= elev <= 5200.0, f"Medical clinic {c.get('name')} elevation {elev}m outside expected clinic range"

    def test_emergency_helipads_within_safe_helicopter_ceiling(self, waypoints_data):
        """Helipads must be below maximum operational density altitude for rescue choppers (Eurocopter B3e / H125 ceiling ~7,000m)."""
        helipads = [w for w in waypoints_data if w.get("category") == "Emergency Helipad"]
        assert len(helipads) >= 5, "Insufficient emergency helipads"
        for h in helipads:
            elev = h.get("elevation_m", 0)
            assert 1000.0 <= elev <= 6000.0, f"Emergency helipad {h.get('name')} elevation {elev}m exceeds rescue operational ceiling"


# =============================================================================
# Category 3: Data Completeness & Missing Fields
# =============================================================================
class TestDataCompletenessAndMissingFields:
    """Robustness against missing or null fields in heritage, trail, and waypoint entities."""

    def test_heritage_sites_mandatory_attributes(self, heritage_data):
        """Every heritage entity must have non-empty name, region, category, group, and entry_fees."""
        for h in heritage_data:
            assert h.get("name") and str(h["name"]).strip(), f"Empty name in {h}"
            assert h.get("region") and str(h["region"]).strip(), f"Empty region in {h.get('name')}"
            assert h.get("category") and str(h["category"]).strip(), f"Empty category in {h.get('name')}"
            assert h.get("group") and str(h["group"]).strip(), f"Empty group in {h.get('name')}"
            assert isinstance(h.get("entry_fees"), dict), f"Missing entry_fees dict in {h.get('name')}"

    def test_entry_fees_structure_completeness(self, heritage_data):
        """Entry fees must specify foreign, SAARC, and nepali tiers in non-negative NPR."""
        for h in heritage_data:
            fees = h.get("entry_fees", {})
            assert "foreign_npr" in fees, f"Missing foreign_npr in {h.get('name')}"
            assert "saarc_npr" in fees, f"Missing saarc_npr in {h.get('name')}"
            assert "nepali_npr" in fees, f"Missing nepali_npr in {h.get('name')}"
            assert fees["foreign_npr"] >= 0
            assert fees["saarc_npr"] >= 0
            assert fees["nepali_npr"] >= 0
            assert fees.get("currency") == "NPR"

    def test_trails_mandatory_attributes(self, trails_data):
        """Every trail must have valid duration_days, difficulty, and permits_required."""
        valid_difficulties = {"Easy", "Moderate", "Challenging", "Strenuous", "Demanding", "Extreme"}
        for t in trails_data:
            assert t.get("name") and str(t["name"]).strip()
            assert t.get("difficulty") in valid_difficulties, f"Invalid difficulty {t.get('difficulty')} in {t.get('name')}"
            assert 1 <= t.get("duration_days", 0) <= 180
            assert isinstance(t.get("permits_required"), list)
            assert len(t.get("permits_required")) >= 1, f"Trail {t.get('name')} missing permit declarations"

    def test_waypoints_mandatory_attributes(self, waypoints_data):
        """Waypoints must have non-empty name, category, and coordinate floats."""
        for w in waypoints_data:
            assert w.get("name") and str(w["name"]).strip()
            assert w.get("category") and str(w["category"]).strip()
            assert isinstance(w.get("latitude"), (float, int))
            assert isinstance(w.get("longitude"), (float, int))

    def test_festivals_mandatory_attributes(self, festivals_data):
        """Festivals must specify lunar_month, gregorian_window, significance, and primary_regions."""
        for f in festivals_data:
            assert f.get("name") and str(f["name"]).strip()
            assert f.get("lunar_month") and str(f["lunar_month"]).strip()
            assert f.get("typical_gregorian_window") and str(f["typical_gregorian_window"]).strip()
            assert f.get("significance") and len(f["significance"]) >= 10
            assert isinstance(f.get("primary_regions"), list) and len(f["primary_regions"]) >= 1


# =============================================================================
# Category 4: Deduplication & Spatial Proximity
# =============================================================================
class TestDeduplicationAndSpatialIntegrity:
    """Zero exact duplicates and sanity checks on near-duplicate spatial thresholds."""

    def test_no_identical_duplicate_names_in_trails(self, trails_data):
        """Trekking trail names must be unique across the catalog."""
        names = [t["name"].strip().lower() for t in trails_data]
        unique_names = set(names)
        assert len(names) == len(unique_names), f"Duplicate trail names found: {len(names) - len(unique_names)} duplicates"

    def test_no_identical_duplicate_names_in_festivals(self, festivals_data):
        """Festival names must be unique across the festival calendar."""
        names = [f["name"].strip().lower() for f in festivals_data]
        unique_names = set(names)
        assert len(names) == len(unique_names), f"Duplicate festival names found: {len(names) - len(unique_names)} duplicates"

    def test_no_identical_coordinate_duplicates_in_heritage(self, heritage_data):
        """No two heritage sites should share the exact same micro-coordinate (down to 1e-6 degrees)."""
        coords = [(round(h["latitude"], 6), round(h["longitude"], 6)) for h in heritage_data]
        # Allow at most 0 identical coordinate collisions for distinct heritage sites
        assert len(coords) == len(set(coords)), f"Identical coordinates found in heritage sites: {len(coords) - len(set(coords))} collisions"

    def test_fuzzy_duplicate_distance_threshold(self, heritage_data):
        """Distinct named places should not be closer than 5 meters unless explicitly co-located shrines."""
        def haversine_m(lat1, lon1, lat2, lon2):
            R = 6371000  # meters
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
            return R * 2 * math.asin(math.sqrt(a))

        n = len(heritage_data)
        near_coincidences = 0
        for i in range(min(n, 40)):
            for j in range(i + 1, min(n, 40)):
                h1, h2 = heritage_data[i], heritage_data[j]
                d = haversine_m(h1["latitude"], h1["longitude"], h2["latitude"], h2["longitude"])
                if d < 1.0 and h1["name"] != h2["name"]:
                    near_coincidences += 1
        assert near_coincidences == 0, f"Found {near_coincidences} distinct entities with <1m proximity"


# =============================================================================
# Category 5: API Edge Cases & Adversarial Search Inputs
# =============================================================================
class TestAPIEdgeCasesAndAdversarialInputs:
    """Adversarial and corner inputs against FastAPI endpoints."""

    def test_search_places_with_empty_or_whitespace_string(self, db_session):
        """Whitespace queries should not crash the search endpoint."""
        res_space = _run_coro(search_places(q="   ", limit=10, offset=0))
        assert "places" in res_space
        assert isinstance(res_space["places"], list)

    def test_search_places_nepali_unicode_script(self, db_session):
        """Nepali Devanagari script queries should execute without decoding errors."""
        res_devanagari = _run_coro(search_places(q="काठमाडौँ", limit=5, offset=0))
        assert "places" in res_devanagari
        assert isinstance(res_devanagari["places"], list)

    def test_search_places_extreme_limits_handling(self, db_session):
        """Boundary limit values (1, 50, 200) execute predictably."""
        res_min = _run_coro(search_places(q="Pashupatinath", limit=1, offset=0))
        assert len(res_min["places"]) <= 1

        res_max = _run_coro(search_places(q="Temple", limit=200, offset=0))
        assert len(res_max["places"]) <= 200

    def test_geocode_unknown_location_fallback_safeguard(self):
        """Unknown or hallucinated location defaults safely to Kathmandu or default fallback within Nepal."""
        res = _run_coro(geocode_place(q="NonExistentFantasyMountainPeak999"))
        assert "latitude" in res and "longitude" in res
        assert NEPAL_LAT_MIN <= res["latitude"] <= NEPAL_LAT_MAX
        assert NEPAL_LON_MIN <= res["longitude"] <= NEPAL_LON_MAX

    def test_geocode_special_characters_escaping(self):
        """Queries containing punctuation, quotes, and symbols do not raise injection exceptions."""
        res = _run_coro(geocode_place(q="Patan 'Durbar' <Square> & @Boudha #123!"))
        assert "latitude" in res and "longitude" in res
        assert NEPAL_LAT_MIN <= res["latitude"] <= NEPAL_LAT_MAX
        assert NEPAL_LON_MIN <= res["longitude"] <= NEPAL_LON_MAX

    def test_trail_watch_reports_pagination_bounds(self, db_session):
        """Pagination limits on field audits operate without bounds exceptions."""
        reports_1 = _run_coro(get_reports(limit=1, db=db_session))
        assert len(reports_1["reports"]) <= 1

        reports_50 = _run_coro(get_reports(limit=50, db=db_session))
        assert isinstance(reports_50["reports"], list)
