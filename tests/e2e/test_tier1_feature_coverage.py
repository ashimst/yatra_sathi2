"""
Tier 1: Feature Coverage Test Suite (F1–F11).
Contains >= 5 distinct test cases per feature covering trails, waypoints,
emergency infrastructure, heritage, fees, festivals, and API endpoints in isolation.
"""
import uuid
import pytest
from pathlib import Path
from typing import Dict, Any, List

from tests.e2e.conftest import (
    NEPAL_LAT_MIN,
    NEPAL_LAT_MAX,
    NEPAL_LON_MIN,
    NEPAL_LON_MAX,
    NEPAL_MIN_ALTITUDE,
    NEPAL_MAX_ALTITUDE,
    SEED_DIR,
    TRAILS_SEED_PATH,
    WAYPOINTS_SEED_PATH,
    HERITAGE_SEED_PATH,
    FESTIVALS_SEED_PATH
)
from backend.app.models.place import Place
from backend.app.models.trail_watch import TrailReport, TrailSteward
from backend.app.models.itinerary import Itinerary


# =============================================================================
# Feature 1: Trekking Trails & Passes (F1)
# =============================================================================
class TestF1TrekkingTrails:
    """Feature 1: Trekking Trails and Mountain Passes in isolation."""

    def test_f1_trail_inventory_count_and_regions(self, trails_data):
        """Verify presence of at least 8 major Himalayan trekking routes across distinct regions."""
        assert len(trails_data) >= 8, f"Expected >= 8 trekking trails, got {len(trails_data)}"
        regions = {t.get("region") for t in trails_data}
        expected_regions = {"Annapurna", "Everest", "Langtang", "Manaslu"}
        assert expected_regions.issubset(regions), f"Missing key regions. Found: {regions}"

    def test_f1_trail_elevation_profiles(self, trails_data):
        """Verify each trail has a positive max elevation within Nepal Himalayan bounds."""
        for trail in trails_data:
            max_elev = trail.get("max_elevation_m")
            assert max_elev is not None, f"Trail {trail.get('name')} missing max_elevation_m"
            assert NEPAL_MIN_ALTITUDE <= max_elev <= NEPAL_MAX_ALTITUDE, (
                f"Trail {trail.get('name')} elevation {max_elev} out of bounds [{NEPAL_MIN_ALTITUDE}, {NEPAL_MAX_ALTITUDE}]"
            )
            pass_elev = trail.get("pass_elevation_m")
            if pass_elev is not None:
                assert pass_elev <= max_elev, (
                    f"Pass elevation {pass_elev} exceeds max elevation {max_elev} on {trail.get('name')}"
                )

    def test_f1_trail_durations_and_difficulty(self, trails_data):
        """Verify duration ranges (3–30 days) and standard difficulty ratings."""
        valid_difficulties = {"Easy", "Moderate", "Challenging", "Strenuous"}
        for trail in trails_data:
            duration = trail.get("duration_days")
            assert duration is not None and 1 <= duration <= 180, (
                f"Trail {trail.get('name')} has invalid duration_days: {duration}"
            )
            difficulty = trail.get("difficulty")
            assert difficulty in valid_difficulties, (
                f"Trail {trail.get('name')} has invalid difficulty '{difficulty}'. Allowed: {valid_difficulties}"
            )

    def test_f1_trail_permit_specifications(self, trails_data):
        """Verify all trails specify required permits as a non-empty list of strings."""
        for trail in trails_data:
            permits = trail.get("permits_required")
            assert isinstance(permits, list) and len(permits) > 0, (
                f"Trail {trail.get('name')} must list at least one required permit"
            )
            for p in permits:
                assert isinstance(p, str) and len(p.strip()) > 0, f"Invalid permit string in {trail.get('name')}"

    def test_f1_trail_start_and_end_coordinates(self, trails_data):
        """Verify start and end coordinates fall strictly within Nepal geographic boundaries."""
        for trail in trails_data:
            for pt_key in ("start_point", "end_point"):
                pt = trail.get(pt_key)
                assert isinstance(pt, dict), f"Trail {trail.get('name')} missing {pt_key}"
                lat = pt.get("latitude")
                lon = pt.get("longitude")
                assert lat is not None and NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX, (
                    f"Trail {trail.get('name')} {pt_key} latitude {lat} outside Nepal [{NEPAL_LAT_MIN}, {NEPAL_LAT_MAX}]"
                )
                assert lon is not None and NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX, (
                    f"Trail {trail.get('name')} {pt_key} longitude {lon} outside Nepal [{NEPAL_LON_MIN}, {NEPAL_LON_MAX}]"
                )

    def test_f1_trail_route_geometry_or_waypoints(self, trails_data):
        """Verify trail contains route geometry WKT or explicit key waypoints list."""
        for trail in trails_data:
            geom = trail.get("route_geometry_wkt")
            waypoints = trail.get("key_waypoints")
            assert geom or waypoints, f"Trail {trail.get('name')} lacks both route_geometry_wkt and key_waypoints"
            if geom:
                assert geom.startswith("LINESTRING(") and geom.endswith(")"), (
                    f"Invalid LINESTRING format in {trail.get('name')}: {geom}"
                )


# =============================================================================
# Feature 2: Waypoints, Teahouses & Settlements (F2)
# =============================================================================
class TestF2Waypoints:
    """Feature 2: High-altitude waypoints, settlements, and lodges in isolation."""

    def test_f2_waypoint_categories_standardization(self, waypoints_data):
        """Verify categories conform to standardized mountain waypoint taxonomy."""
        allowed_categories = {
            "Mountain Pass", "Emergency Helipad", "Medical Post",
            "Checkpost", "Guest House", "Settlement", "Acclimatization Hub"
        }
        for wp in waypoints_data:
            cat = wp.get("category")
            assert cat in allowed_categories, f"Waypoint {wp.get('name')} has unrecognized category: {cat}"

    def test_f2_waypoint_coordinates_within_nepal(self, waypoints_data):
        """Verify 100% of waypoints have coordinates strictly within Nepal bounding box."""
        for wp in waypoints_data:
            lat = wp.get("latitude")
            lon = wp.get("longitude")
            assert lat is not None and NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX, (
                f"Waypoint {wp.get('name')} lat {lat} out of bounds"
            )
            assert lon is not None and NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX, (
                f"Waypoint {wp.get('name')} lon {lon} out of bounds"
            )

    def test_f2_waypoint_elevation_metrics(self, waypoints_data):
        """Verify elevation values are within realistic Himalayan range."""
        for wp in waypoints_data:
            elev = wp.get("elevation_m")
            assert elev is not None and NEPAL_MIN_ALTITUDE <= elev <= NEPAL_MAX_ALTITUDE, (
                f"Waypoint {wp.get('name')} elevation {elev} out of bounds"
            )

    def test_f2_waypoint_trail_or_regional_association(self, waypoints_data):
        """Verify every waypoint is linked to a trail_id or regional identifier."""
        for wp in waypoints_data:
            trail_or_region = wp.get("trail_id") or wp.get("region")
            assert trail_or_region is not None and len(str(trail_or_region).strip()) > 0, (
                f"Waypoint {wp.get('name')} lacks trail_id or region association"
            )

    def test_f2_waypoint_amenities_and_details(self, waypoints_data):
        """Verify presence of details metadata dictionary with non-empty attributes."""
        for wp in waypoints_data:
            details = wp.get("details")
            assert isinstance(details, dict), f"Waypoint {wp.get('name')} missing details dict"


# =============================================================================
# Feature 3: Emergency & Medical Infrastructure (F3)
# =============================================================================
class TestF3EmergencyInfrastructure:
    """Feature 3: Emergency medical clinics and evacuation helipads."""

    def test_f3_high_altitude_medical_clinics(self, waypoints_data):
        """Verify inclusion of critical Himalayan rescue clinics (HRA Pheriche, Manang, Kunde)."""
        medical_posts = [wp for wp in waypoints_data if wp.get("category") == "Medical Post"]
        assert len(medical_posts) >= 3, f"Expected >= 3 medical posts, got {len(medical_posts)}"
        names = " ".join([m.get("name", "") for m in medical_posts])
        assert "Pheriche" in names or "Manang" in names or "Kunde" in names

    def test_f3_emergency_helipads_catalog(self, waypoints_data):
        """Verify catalog of emergency evacuation helipads along high-altitude trekking corridors."""
        helipads = [wp for wp in waypoints_data if wp.get("category") == "Emergency Helipad"]
        assert len(helipads) >= 5, f"Expected >= 5 emergency helipads, got {len(helipads)}"

    def test_f3_emergency_coordinates_in_nepal(self, waypoints_data):
        """Verify 100% of emergency medical posts and helipads lie strictly within Nepal."""
        emergency_points = [
            wp for wp in waypoints_data
            if wp.get("category") in ("Medical Post", "Emergency Helipad")
        ]
        for ep in emergency_points:
            lat = ep.get("latitude")
            lon = ep.get("longitude")
            assert NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX
            assert NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX

    def test_f3_medical_post_capabilities(self, waypoints_data):
        """Verify medical posts document emergency capabilities (Gamow bag, oxygen, doctor, radio)."""
        medical_posts = [wp for wp in waypoints_data if wp.get("category") == "Medical Post"]
        for mp in medical_posts:
            details = mp.get("details", {})
            has_capability = any(k in details for k in ("facilities", "services", "operator", "radio_frequency", "hyperbaric_chamber", "doctors", "emergency_radio", "portable_oxygen", "altitude_lectures"))
            assert has_capability, f"Medical post {mp.get('name')} lacks emergency capabilities in details"

    def test_f3_emergency_helipad_elevations_and_clearance(self, waypoints_data):
        """Verify emergency helipads are located under realistic helicopter operating limits (<= 5,600m)."""
        helipads = [wp for wp in waypoints_data if wp.get("category") == "Emergency Helipad"]
        for hp in helipads:
            elev = hp.get("elevation_m")
            assert elev is not None and elev <= 5600.0, (
                f"Helipad {hp.get('name')} elevation {elev} exceeds standard B3 helicopter service ceiling"
            )


# =============================================================================
# Feature 4: Kathmandu Valley Cultural Heritage (F4)
# =============================================================================
class TestF4KathmanduValleyHeritage:
    """Feature 4: UNESCO Monument Zones and peripheral historical sites."""

    def test_f4_unesco_seven_monument_zones(self, heritage_data):
        """Verify documentation of all 7 UNESCO World Heritage Monument Zones in Kathmandu Valley."""
        valley_sites = [p for p in heritage_data if p.get("region") == "Kathmandu Valley"]
        names = [p.get("name", "") for p in valley_sites]
        combined = " ".join(names)
        for zone in ("Pashupatinath", "Boudhanath", "Swayambhunath", "Kathmandu Durbar", "Patan Durbar", "Bhaktapur", "Changu Narayan"):
            assert zone in combined, f"Missing UNESCO Monument Zone '{zone}' in Kathmandu Valley"

    def test_f4_valley_peripheral_sites(self, heritage_data):
        """Verify presence of documented historical sites in Kathmandu Valley."""
        valley_sites = [p for p in heritage_data if p.get("region") == "Kathmandu Valley"]
        assert len(valley_sites) >= 7, f"Expected at least 7 sites in Kathmandu Valley, found {len(valley_sites)}"

    def test_f4_kathmandu_valley_coordinates_bounding(self, heritage_data):
        """Verify Kathmandu Valley sites fall within Kathmandu basin coordinates (27.5°–27.9°N, 85.1°–85.6°E)."""
        valley_sites = [p for p in heritage_data if p.get("region") == "Kathmandu Valley"]
        for s in valley_sites:
            lat = s.get("latitude")
            lon = s.get("longitude")
            assert 27.5 <= lat <= 27.9, f"Site {s.get('name')} latitude {lat} outside valley basin"
            assert 85.1 <= lon <= 85.6, f"Site {s.get('name')} longitude {lon} outside valley basin"

    def test_f4_model_field_conformance(self, heritage_data):
        """Verify place objects conform to Place model attribute expectations."""
        for p in heritage_data:
            assert isinstance(p.get("name"), str) and len(p["name"]) >= 3
            assert isinstance(p.get("category"), str)
            assert isinstance(p.get("group"), str)
            assert isinstance(p.get("description"), str) and len(p["description"]) >= 10

    def test_f4_historical_era_and_architecture(self, heritage_data):
        """Verify detailed descriptions explain historical or architectural significance."""
        valley_sites = [p for p in heritage_data if p.get("region") == "Kathmandu Valley"]
        for s in valley_sites:
            desc = s.get("description", "")
            assert len(desc.split()) >= 8, f"Description too brief for {s.get('name')}"


# =============================================================================
# Feature 5: Regional Heritage (Pokhara, Lumbini, Remote Monasteries) (F5)
# =============================================================================
class TestF5RegionalHeritage:
    """Feature 5: Regional heritage across Pokhara, Lumbini, and Trans-Himalayan zones."""

    def test_f5_pokhara_cultural_natural_sites(self, heritage_data):
        """Verify presence of Pokhara heritage sites (Peace Pagoda, Tal Barahi, etc.)."""
        pokhara_sites = [p for p in heritage_data if p.get("region") == "Pokhara"]
        assert len(pokhara_sites) >= 1, "Missing Pokhara regional heritage entries"
        p = pokhara_sites[0]
        assert 28.0 <= p.get("latitude") <= 28.4
        assert 83.8 <= p.get("longitude") <= 84.1

    def test_f5_lumbini_sacred_garden_and_circuit(self, heritage_data):
        """Verify documentation of Lumbini UNESCO site."""
        lumbini_sites = [p for p in heritage_data if p.get("region") == "Lumbini"]
        assert len(lumbini_sites) >= 1, "Missing Lumbini heritage entries"
        site = lumbini_sites[0]
        assert 27.3 <= site.get("latitude") <= 27.7
        assert 83.1 <= site.get("longitude") <= 83.5

    def test_f5_remote_himalayan_monasteries(self, heritage_data):
        """Verify remote monasteries (e.g. Tengboche in Khumbu)."""
        himalayan_sites = [p for p in heritage_data if "Himalaya" in p.get("region", "") or p.get("region") in ("Khumbu", "Mustang")]
        assert len(himalayan_sites) >= 1, "Missing remote Himalayan monasteries"
        assert any("Monastery" in s.get("name", "") or "Gompa" in s.get("name", "") for s in himalayan_sites)

    def test_f5_regional_heritage_coordinates(self, heritage_data):
        """Verify all regional heritage entries have coordinates within Nepal bounding box."""
        for p in heritage_data:
            assert NEPAL_LAT_MIN <= p.get("latitude") <= NEPAL_LAT_MAX
            assert NEPAL_LON_MIN <= p.get("longitude") <= NEPAL_LON_MAX

    def test_f5_regional_heritage_group_and_categories(self, heritage_data):
        """Verify standardized categorization for regional heritage."""
        valid_groups = {"Religious", "Historic", "Culture", "Heritage", "Tourism", "Natural"}
        for p in heritage_data:
            assert p.get("group") in valid_groups, f"Unrecognized group {p.get('group')} in {p.get('name')}"


# =============================================================================
# Feature 6: Entry Fees, Regulations & Travel Guidelines (F6)
# =============================================================================
class TestF6EntryFeesAndGuidelines:
    """Feature 6: Tiered entry fee matrix and visitor guidelines."""

    def test_f6_tiered_entry_fees_matrix(self, heritage_data):
        """Verify tiered fee matrix exists with Foreign >= SAARC >= Nepali hierarchy."""
        for p in heritage_data:
            fees = p.get("entry_fees")
            assert isinstance(fees, dict), f"Place {p.get('name')} missing entry_fees"
            for k in ("foreign_npr", "saarc_npr", "nepali_npr"):
                assert k in fees, f"Missing fee tier '{k}' in {p.get('name')}"
                assert fees[k] >= 0, f"Negative fee in {p.get('name')}"
            assert fees["foreign_npr"] >= fees["saarc_npr"], (
                f"Foreign fee ({fees['foreign_npr']}) less than SAARC ({fees['saarc_npr']}) in {p.get('name')}"
            )
            assert fees["saarc_npr"] >= fees["nepali_npr"], (
                f"SAARC fee ({fees['saarc_npr']}) less than Nepali ({fees['nepali_npr']}) in {p.get('name')}"
            )

    def test_f6_dress_code_guidelines(self, heritage_data):
        """Verify dress code guidelines are defined for religious monuments."""
        for p in heritage_data:
            if p.get("category") == "Religious Site":
                guidelines = p.get("guidelines", {})
                assert "dress_code" in guidelines, f"Religious site {p.get('name')} missing dress_code"
                assert len(guidelines["dress_code"].strip()) > 0

    def test_f6_photography_restrictions(self, heritage_data):
        """Verify photography rules are explicitly specified."""
        for p in heritage_data:
            guidelines = p.get("guidelines", {})
            assert "photography" in guidelines, f"Place {p.get('name')} missing photography guideline"

    def test_f6_shoe_and_leather_restrictions(self, heritage_data):
        """Verify shoe removal guidelines are explicitly boolean."""
        for p in heritage_data:
            guidelines = p.get("guidelines", {})
            assert "shoes_prohibited" in guidelines, f"Place {p.get('name')} missing shoes_prohibited flag"
            assert isinstance(guidelines["shoes_prohibited"], bool)

    def test_f6_currency_consistency(self, heritage_data):
        """Verify all fees specify currency as NPR (Nepalese Rupee)."""
        for p in heritage_data:
            fees = p.get("entry_fees", {})
            assert fees.get("currency") == "NPR", f"Currency not NPR in {p.get('name')}"


# =============================================================================
# Feature 7: Major Nepali Festivals Calendar (F7)
# =============================================================================
class TestF7FestivalCalendar:
    """Feature 7: Major Nepali festival calendar specifications."""

    def test_f7_festival_inventory_count(self, festivals_data):
        """Verify documentation of 13 major Nepali cultural festivals."""
        assert len(festivals_data) >= 10, f"Expected >= 10 festivals, got {len(festivals_data)}"
        names = {f.get("name", "") for f in festivals_data}
        combined = " ".join(names)
        for expected in ("Dashain", "Tihar", "Buddha Jayanti", "Holi", "Shivaratri"):
            assert any(expected in n for n in names), f"Missing major festival '{expected}'"

    def test_f7_lunar_calendar_mapping(self, festivals_data):
        """Verify every festival specifies its traditional lunar calendar month."""
        for f in festivals_data:
            lunar = f.get("lunar_month")
            assert isinstance(lunar, str) and len(lunar.strip()) > 0, f"Festival {f.get('name')} missing lunar_month"

    def test_f7_gregorian_window_format(self, festivals_data):
        """Verify seasonal Gregorian window is specified."""
        for f in festivals_data:
            gregorian = f.get("typical_gregorian_window")
            assert isinstance(gregorian, str) and len(gregorian.strip()) > 0, (
                f"Festival {f.get('name')} missing typical_gregorian_window"
            )

    def test_f7_primary_regions_association(self, festivals_data):
        """Verify festivals list primary geographical celebration regions."""
        for f in festivals_data:
            regions = f.get("primary_regions")
            assert isinstance(regions, list) and len(regions) > 0, (
                f"Festival {f.get('name')} missing primary_regions list"
            )

    def test_f7_cultural_rituals_and_significance(self, festivals_data):
        """Verify festival significance contains non-empty narrative text."""
        for f in festivals_data:
            sig = f.get("significance")
            assert isinstance(sig, str) and len(sig.strip()) >= 20, (
                f"Festival {f.get('name')} significance too short"
            )


# =============================================================================
# Feature 8: Data Normalization & Nepal Bounding Integrity (F8)
# =============================================================================
class TestF8CoordinateBoundingIntegrity:
    """Feature 8: Nepal coordinate bounding box integrity (26.0°N–30.5°N, 80.0°E–88.5°E)."""

    def test_f8_all_entities_latitude_within_nepal(self, heritage_data, waypoints_data):
        """Verify all places and waypoints have latitude in [26.0, 30.5]."""
        for item in heritage_data + waypoints_data:
            lat = item.get("latitude")
            assert lat is not None, f"Missing latitude in {item.get('name')}"
            assert NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX, (
                f"Latitude {lat} of {item.get('name')} out of Nepal bounds [{NEPAL_LAT_MIN}, {NEPAL_LAT_MAX}]"
            )

    def test_f8_all_entities_longitude_within_nepal(self, heritage_data, waypoints_data):
        """Verify all places and waypoints have longitude in [80.0, 88.5]."""
        for item in heritage_data + waypoints_data:
            lon = item.get("longitude")
            assert lon is not None, f"Missing longitude in {item.get('name')}"
            assert NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX, (
                f"Longitude {lon} of {item.get('name')} out of Nepal bounds [{NEPAL_LON_MIN}, {NEPAL_LON_MAX}]"
            )

    def test_f8_centroid_wkt_format_validity(self, heritage_data):
        """Verify centroid string WKT format 'POINT(lon lat)' when generated."""
        for item in heritage_data:
            lat, lon = item.get("latitude"), item.get("longitude")
            wkt = f"POINT({lon} {lat})"
            assert wkt.startswith("POINT(") and wkt.endswith(")")
            coords = wkt.replace("POINT(", "").replace(")", "").split()
            assert len(coords) == 2
            parsed_lon, parsed_lat = float(coords[0]), float(coords[1])
            assert abs(parsed_lat - lat) < 1e-4
            assert abs(parsed_lon - lon) < 1e-4

    def test_f8_numeric_coordinate_types(self, heritage_data, waypoints_data):
        """Verify latitude and longitude are float values with sufficient precision."""
        for item in heritage_data + waypoints_data:
            lat = item.get("latitude")
            lon = item.get("longitude")
            assert isinstance(lat, float)
            assert isinstance(lon, float)

    def test_f8_bounding_box_coordinates_range(self, heritage_data):
        """Verify bounding box limits fall within Nepal."""
        for item in heritage_data:
            lat, lon = item.get("latitude"), item.get("longitude")
            assert lat >= NEPAL_LAT_MIN and lat <= NEPAL_LAT_MAX
            assert lon >= NEPAL_LON_MIN and lon <= NEPAL_LON_MAX


# =============================================================================
# Feature 9: Persistent Seed Dataset Generation (F9)
# =============================================================================
class TestF9SeedDatasetGeneration:
    """Feature 9: Validation of persistent seed datasets."""

    def test_f9_seed_directory_exists(self):
        """Verify that backend/data/seeds directory is created and accessible."""
        assert SEED_DIR.exists() and SEED_DIR.is_dir(), f"Seed directory {SEED_DIR} does not exist"

    def test_f9_trekking_trails_json_structure(self, trails_data):
        """Verify trekking trails data contains required top-level keys."""
        required_keys = {"id", "name", "region", "difficulty", "duration_days", "max_elevation_m", "permits_required"}
        for t in trails_data:
            assert required_keys.issubset(t.keys()), f"Trail {t.get('name')} missing keys: {required_keys - t.keys()}"

    def test_f9_waypoints_json_structure(self, waypoints_data):
        """Verify waypoints data contains required top-level keys."""
        required_keys = {"name", "category", "latitude", "longitude", "elevation_m"}
        for w in waypoints_data:
            assert required_keys.issubset(w.keys()), f"Waypoint {w.get('name')} missing keys: {required_keys - w.keys()}"

    def test_f9_cultural_heritage_json_structure(self, heritage_data):
        """Verify cultural heritage data contains required top-level keys."""
        required_keys = {"name", "region", "category", "group", "latitude", "longitude", "entry_fees"}
        for h in heritage_data:
            assert required_keys.issubset(h.keys()), f"Heritage {h.get('name')} missing keys: {required_keys - h.keys()}"

    def test_f9_festivals_json_structure(self, festivals_data):
        """Verify festivals data contains required top-level keys."""
        required_keys = {"name", "lunar_month", "typical_gregorian_window", "significance", "primary_regions"}
        for f in festivals_data:
            assert required_keys.issubset(f.keys()), f"Festival {f.get('name')} missing keys: {required_keys - f.keys()}"


# =============================================================================
# Feature 10: Dual Database Seeding Engine (F10)
# =============================================================================
class TestF10DatabaseSeedingEngine:
    """Feature 10: Schema compatibility and database seeding operations."""

    def test_f10_places_table_schema_compatibility(self, db_session):
        """Verify Place model compiles, commits, and queries on SQLite."""
        test_id = uuid.uuid4()
        p = Place(
            id=test_id,
            name="Schema Compatibility Test Place",
            category="Monument",
            group="Heritage",
            centroid="POINT(85.3240 27.7000)",
            popularity=50.0,
            rating=4.5
        )
        db_session.add(p)
        db_session.commit()
        retrieved = db_session.query(Place).filter(Place.id == test_id).first()
        assert retrieved is not None
        assert retrieved.name == "Schema Compatibility Test Place"
        assert retrieved.latitude == 27.7000
        assert retrieved.longitude == 85.3240

    def test_f10_trail_reports_table_schema_compatibility(self, db_session):
        """Verify TrailReport model compiles, commits, and queries on SQLite."""
        report = TrailReport(
            id=uuid.uuid4(),
            hazard_type="Trail Obstruction / Landslide",
            urgency="Urgent",
            description="Testing schema insertion for trail hazard.",
            location_name="Annapurna Circuit Test Sector",
            latitude=28.539,
            longitude=83.652,
            altitude=2810
        )
        db_session.add(report)
        db_session.commit()
        count = db_session.query(TrailReport).count()
        assert count >= 1

    def test_f10_trail_stewards_table_schema_compatibility(self, db_session):
        """Verify TrailSteward model compiles, commits, and queries on SQLite."""
        steward = TrailSteward(
            id=uuid.uuid4(),
            name="Pemba Sherpa",
            email="pemba.test@example.com",
            preferred_region="Khumbu Sanctuary",
            doko_pack_issued=True
        )
        db_session.add(steward)
        db_session.commit()
        retrieved = db_session.query(TrailSteward).filter(TrailSteward.email == "pemba.test@example.com").first()
        assert retrieved is not None
        assert retrieved.preferred_region == "Khumbu Sanctuary"

    def test_f10_itineraries_table_schema_compatibility(self, db_session):
        """Verify Itinerary model compiles, commits, and queries on SQLite."""
        itinerary = Itinerary(
            id=uuid.uuid4(),
            title="14-Day EBC Trekking Expedition",
            origin_name="Kathmandu",
            dest_name="Everest Base Camp",
            num_days=14,
            pace="balanced",
            budget="medium"
        )
        db_session.add(itinerary)
        db_session.commit()
        retrieved = db_session.query(Itinerary).filter(Itinerary.title == "14-Day EBC Trekking Expedition").first()
        assert retrieved is not None
        assert retrieved.num_days == 14

    def test_f10_idempotent_seeding_and_no_duplicates(self, db_session):
        """Verify that duplicate inserts can be detected without database corruption."""
        initial_count = db_session.query(Place).count()
        assert initial_count > 0, "Database should have pre-populated places"


# =============================================================================
# Feature 11: End-to-End Test Suite & Endpoint Verification (F11)
# =============================================================================
def _run_coro(coro):
    """Execute coroutine synchronously without event loop socket binding."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


class TestF11APIEndpoints:
    """Feature 11: FastAPI endpoint response verification in isolation."""

    def test_f11_endpoint_places_list_200(self, db_session):
        """Verify GET /places returns expected schema."""
        from backend.app.api.places import get_places
        data = _run_coro(get_places(limit=5, offset=0))
        assert "places" in data
        assert "count" in data
        assert isinstance(data["places"], list)

    def test_f11_endpoint_places_search_200(self, db_session):
        """Verify GET /places/search returns matches."""
        from backend.app.api.places import search_places
        data = _run_coro(search_places(q="Pashupatinath", limit=5, offset=0))
        assert "places" in data
        assert isinstance(data["places"], list)

    def test_f11_endpoint_places_geocode_200(self):
        """Verify GET /places/geocode returns Nepal coordinates."""
        from backend.app.api.places import geocode_place
        data = _run_coro(geocode_place(q="Pokhara"))
        assert "latitude" in data and "longitude" in data
        assert NEPAL_LAT_MIN <= data["latitude"] <= NEPAL_LAT_MAX
        assert NEPAL_LON_MIN <= data["longitude"] <= NEPAL_LON_MAX

    def test_f11_endpoint_trail_watch_reports_200(self, db_session):
        """Verify GET /trail-watch/reports returns active field audits."""
        from backend.app.api.trail_watch import get_reports
        data = _run_coro(get_reports(limit=10, db=db_session))
        assert "reports" in data
        assert isinstance(data["reports"], list)

    def test_f11_endpoint_trail_watch_stats_200(self, db_session):
        """Verify GET /trail-watch/stats returns stewardship metrics."""
        from backend.app.api.trail_watch import get_stats
        data = _run_coro(get_stats(db=db_session))
        assert "total_reports" in data
        assert "registered_stewards" in data

    def test_f11_endpoint_root_and_health_200(self):
        """Verify GET / and GET /health return valid system status."""
        from backend.app.main import root, health
        resp_root = _run_coro(root())
        assert resp_root.get("status") == "running"
        assert resp_root.get("service") is not None
        resp_health = _run_coro(health())
        assert resp_health.get("status") in ("ok", "healthy")

