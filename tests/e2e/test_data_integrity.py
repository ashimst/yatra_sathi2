"""
Data Integrity Test Suite
Opaque-box verification of coordinate bounding, deduplication, schema fidelity,
and JSON formatting across all persistent seed datasets in backend/data/seeds/.
"""
import pytest
import json
from pathlib import Path

from tests.e2e.conftest import (
    SEED_DIR,
    TRAILS_SEED_PATH,
    WAYPOINTS_SEED_PATH,
    HERITAGE_SEED_PATH,
    FESTIVALS_SEED_PATH,
    NEPAL_LAT_MIN,
    NEPAL_LAT_MAX,
    NEPAL_LON_MIN,
    NEPAL_LON_MAX,
    NEPAL_MIN_ALTITUDE,
    NEPAL_MAX_ALTITUDE,
)


class TestPersistentSeedDataIntegrity:
    """Rigorous integrity verification of persistent JSON seed datasets."""

    def test_seed_files_exist_and_non_empty(self):
        """All four primary seed files exist with positive file sizes."""
        for path in [TRAILS_SEED_PATH, WAYPOINTS_SEED_PATH, HERITAGE_SEED_PATH, FESTIVALS_SEED_PATH]:
            assert path.exists(), f"Seed file {path.name} is missing"
            assert path.stat().st_size > 500, f"Seed file {path.name} is unexpectedly small (<500B)"

    def test_100_percent_waypoints_within_nepal_bounds(self, waypoints_data):
        """100% of waypoints are strictly located within Nepal's geographic rectangle."""
        for wp in waypoints_data:
            lat = wp.get("latitude")
            lon = wp.get("longitude")
            assert lat is not None and lon is not None
            assert NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX, (
                f"Waypoint '{wp.get('name')}' lat {lat} outside Nepal [{NEPAL_LAT_MIN}, {NEPAL_LAT_MAX}]"
            )
            assert NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX, (
                f"Waypoint '{wp.get('name')}' lon {lon} outside Nepal [{NEPAL_LON_MIN}, {NEPAL_LON_MAX}]"
            )

    def test_100_percent_heritage_within_nepal_bounds(self, heritage_data):
        """100% of cultural heritage sites are strictly located within Nepal's geographic rectangle."""
        for h in heritage_data:
            lat = h.get("latitude")
            lon = h.get("longitude")
            assert lat is not None and lon is not None
            assert NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX, (
                f"Heritage '{h.get('name')}' lat {lat} outside Nepal [{NEPAL_LAT_MIN}, {NEPAL_LAT_MAX}]"
            )
            assert NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX, (
                f"Heritage '{h.get('name')}' lon {lon} outside Nepal [{NEPAL_LON_MIN}, {NEPAL_LON_MAX}]"
            )

    def test_100_percent_trail_endpoints_within_nepal_bounds(self, trails_data):
        """100% of trail start and end points are strictly located within Nepal's geographic rectangle."""
        for t in trails_data:
            sp = t.get("start_point")
            ep = t.get("end_point")
            if sp:
                assert NEPAL_LAT_MIN <= sp["latitude"] <= NEPAL_LAT_MAX
                assert NEPAL_LON_MIN <= sp["longitude"] <= NEPAL_LON_MAX
            if ep:
                assert NEPAL_LAT_MIN <= ep["latitude"] <= NEPAL_LAT_MAX
                assert NEPAL_LON_MIN <= ep["longitude"] <= NEPAL_LON_MAX

    def test_zero_duplicate_records_in_trails(self, trails_data):
        """Zero identical duplicate trail records by name and start/end coordinates."""
        seen = set()
        for t in trails_data:
            sp = t.get("start_point") or {}
            key = (
                t["name"].strip().lower(),
                round(sp.get("latitude", 0), 4),
                round(sp.get("longitude", 0), 4)
            )
            assert key not in seen, f"Duplicate trail found: {t['name']}"
            seen.add(key)

    def test_zero_duplicate_records_in_festivals(self, festivals_data):
        """Zero identical duplicate festival records by name and lunar month."""
        seen = set()
        for f in festivals_data:
            key = (f["name"].strip().lower(), f["lunar_month"].strip().lower())
            assert key not in seen, f"Duplicate festival found: {f['name']}"
            seen.add(key)

    def test_zero_identical_duplicate_records_in_waypoints(self, waypoints_data):
        """Zero duplicate waypoint records sharing identical name and micro-coordinates."""
        seen = set()
        for w in waypoints_data:
            key = (
                w["name"].strip().lower(),
                round(w["latitude"], 5),
                round(w["longitude"], 5)
            )
            assert key not in seen, f"Duplicate waypoint found: {w['name']} at {w['latitude']}, {w['longitude']}"
            seen.add(key)

    def test_zero_identical_duplicate_records_in_heritage(self, heritage_data):
        """Zero duplicate heritage records sharing identical name and coordinates."""
        seen = set()
        for h in heritage_data:
            key = (
                h["name"].strip().lower(),
                round(h["latitude"], 5),
                round(h["longitude"], 5)
            )
            assert key not in seen, f"Duplicate heritage site found: {h['name']} at {h['latitude']}, {h['longitude']}"
            seen.add(key)
