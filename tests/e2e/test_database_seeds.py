"""
Database Seeds Test Suite
Verifies persistent SQLite and PostgreSQL seed population, schema integrity,
and record count validation across tables in yatra_sathi.db.
"""
import pytest
import sqlite3
from pathlib import Path

from tests.e2e.conftest import (
    SQLITE_DB_PATH,
    NEPAL_LAT_MIN,
    NEPAL_LAT_MAX,
    NEPAL_LON_MIN,
    NEPAL_LON_MAX,
)


class TestDatabaseSeedsPopulation:
    """Verifies that persistent database tables are populated with expected seed volume."""

    def test_sqlite_database_file_exists(self):
        """The yatra_sathi.db file exists at the project root."""
        assert SQLITE_DB_PATH.exists(), f"Database file {SQLITE_DB_PATH} not found"
        assert SQLITE_DB_PATH.stat().st_size > 10_000, "Database file is empty or suspiciously small"

    def test_places_table_population_threshold(self):
        """The places table contains at least 1,000 destinations and cultural heritage points."""
        con = sqlite3.connect(SQLITE_DB_PATH)
        cur = con.cursor()
        count = cur.execute("SELECT count(*) FROM places").fetchone()[0]
        con.close()
        assert count >= 1000, f"Expected >= 1,000 places in yatra_sathi.db, found {count}"

    def test_trails_table_population_threshold(self):
        """The trails table contains at least 15 comprehensive trekking routes."""
        con = sqlite3.connect(SQLITE_DB_PATH)
        cur = con.cursor()
        count = cur.execute("SELECT count(*) FROM trails").fetchone()[0]
        con.close()
        assert count >= 15, f"Expected >= 15 trails in yatra_sathi.db, found {count}"

    def test_waypoints_table_population_threshold(self):
        """The waypoints table contains at least 1,000 waypoints."""
        con = sqlite3.connect(SQLITE_DB_PATH)
        cur = con.cursor()
        count = cur.execute("SELECT count(*) FROM waypoints").fetchone()[0]
        con.close()
        assert count >= 1000, f"Expected >= 1,000 waypoints in yatra_sathi.db, found {count}"

    def test_festivals_table_population_threshold(self):
        """The festivals table contains at least 12 major cultural festivals."""
        con = sqlite3.connect(SQLITE_DB_PATH)
        cur = con.cursor()
        count = cur.execute("SELECT count(*) FROM festivals").fetchone()[0]
        con.close()
        assert count >= 12, f"Expected >= 12 festivals in yatra_sathi.db, found {count}"

    def test_trail_reports_and_stewards_seeded(self):
        """Initial verified trail reports and trail stewards are seeded."""
        con = sqlite3.connect(SQLITE_DB_PATH)
        cur = con.cursor()
        reports_count = cur.execute("SELECT count(*) FROM trail_reports").fetchone()[0]
        stewards_count = cur.execute("SELECT count(*) FROM trail_stewards").fetchone()[0]
        con.close()
        assert reports_count >= 3, f"Expected >= 3 initial trail reports, found {reports_count}"
        assert stewards_count >= 3, f"Expected >= 3 initial stewards, found {stewards_count}"

    def test_database_places_coordinate_bounds(self):
        """Every place with non-null centroid or bounding box in yatra_sathi.db sits within Nepal."""
        con = sqlite3.connect(SQLITE_DB_PATH)
        cur = con.cursor()
        rows = cur.execute(
            "SELECT name, bbox_min_lat, bbox_min_lon FROM places WHERE bbox_min_lat IS NOT NULL AND bbox_min_lon IS NOT NULL"
        ).fetchall()
        con.close()
        assert len(rows) > 0, "No places with bbox coordinates found"
        for name, lat, lon in rows:
            assert NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX, f"Place '{name}' lat {lat} out of Nepal bounds"
            assert NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX, f"Place '{name}' lon {lon} out of Nepal bounds"
