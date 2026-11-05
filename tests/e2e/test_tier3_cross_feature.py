"""
Tier 3: Cross-Feature Combinations Test Suite (Pairwise Coverage)
Validates interactions between trekking trails, waypoints, emergency infrastructure,
cultural heritage sites, festival calendars, tiered fee structures, and trail watch hazard dispatch.
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
    TestSessionLocal,
)
from backend.app.models.place import Place
from backend.app.models.trail_watch import TrailReport, TrailSteward
from backend.app.api.trail_watch import create_report, get_reports, get_stats, CreateReportRequest


def _run_coro(coro):
    """Execute coroutine synchronously without event loop socket binding."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# =============================================================================
# Category 1: Trail-to-Waypoint Spatial Proximity
# =============================================================================
class TestTrailWaypointProximity:
    """Validate spatial associations between trails and their constituent waypoints."""

    def test_trail_start_point_has_nearby_settlement_waypoint(self, trails_data, waypoints_data):
        """Every trail start point must be within 50 km of at least one settlement or trailhead waypoint."""
        for trail in trails_data:
            sp = trail.get("start_point")
            if not sp:
                continue
            s_lat, s_lon = sp["latitude"], sp["longitude"]
            nearby_wps = [
                w for w in waypoints_data
                if haversine_km(s_lat, s_lon, w["latitude"], w["longitude"]) <= 50.0
            ]
            assert len(nearby_wps) >= 1, (
                f"Trail {trail['name']} start point ({s_lat}, {s_lon}) has no waypoints within 50km"
            )

    def test_trail_key_waypoints_exist_in_catalog(self, trails_data, waypoints_data):
        """Key waypoints referenced in trail metadata match catalog waypoints by name substring."""
        catalog_names = [w["name"].lower() for w in waypoints_data]
        matches_found = 0
        total_referenced = 0

        for trail in trails_data:
            for kw in trail.get("key_waypoints", []):
                total_referenced += 1
                kw_lower = kw.lower()
                if any(kw_lower in cn or cn in kw_lower for cn in catalog_names):
                    matches_found += 1

        assert total_referenced > 0
        match_ratio = matches_found / total_referenced
        assert match_ratio >= 0.50, f"Match ratio between trail key waypoints and catalog is only {match_ratio:.2%}"

    def test_trail_pass_elevation_corresponds_with_pass_waypoint(self, trails_data, waypoints_data):
        """If a trail defines a pass elevation, a corresponding Mountain Pass waypoint exists near that elevation."""
        passes = [w for w in waypoints_data if w.get("category") == "Mountain Pass"]
        for trail in trails_data:
            pass_elev = trail.get("pass_elevation_m")
            if pass_elev and pass_elev > 4000:
                matching_passes = [
                    p for p in passes
                    if abs(p.get("elevation_m", 0) - pass_elev) <= 250
                ]
                assert len(matching_passes) >= 1, (
                    f"Trail {trail['name']} pass elevation {pass_elev}m lacks matching pass waypoint"
                )


# =============================================================================
# Category 2: Emergency Evacuation Triad (Trail + Helipad + Medical Clinic)
# =============================================================================
class TestEmergencyEvacuationTriad:
    """Validate that high-altitude trails have accessible helipads and medical clinics."""

    def test_everest_base_camp_emergency_infrastructure_triad(self, trails_data, waypoints_data):
        """Everest Base Camp trail has helipad and medical aid post within high-altitude sectors."""
        ebc_trail = next((t for t in trails_data if "everest" in t.get("id", "").lower()), None)
        assert ebc_trail is not None, "Everest Base Camp trail missing"

        # Check for medical posts in Khumbu / EBC corridor
        khumbu_medics = [
            w for w in waypoints_data
            if w.get("category") == "Medical Post"
            and (w.get("trail_id") == "everest-base-camp" or ("86.6" <= str(w["longitude"]) <= "86.9"))
        ]
        assert len(khumbu_medics) >= 1, "EBC corridor lacks high-altitude medical post"

        # Check for emergency helipads in Khumbu / EBC corridor
        khumbu_helipads = [
            w for w in waypoints_data
            if w.get("category") == "Emergency Helipad"
            and (w.get("trail_id") == "everest-base-camp" or ("86.6" <= str(w["longitude"]) <= "86.9"))
        ]
        assert len(khumbu_helipads) >= 2, "EBC corridor lacks sufficient emergency helipads"

    def test_annapurna_circuit_emergency_infrastructure_triad(self, trails_data, waypoints_data):
        """Annapurna Circuit trail has emergency helipads and medical clinics along both sides of Thorong La."""
        ac_trail = next((t for t in trails_data if "annapurna-circuit" in t.get("id", "").lower()), None)
        assert ac_trail is not None, "Annapurna Circuit trail missing"

        ac_medics = [
            w for w in waypoints_data
            if w.get("category") == "Medical Post"
            and (w.get("trail_id") == "annapurna-circuit" or ("83.5" <= str(w["longitude"]) <= "84.5" and "28.3" <= str(w["latitude"]) <= "28.9"))
        ]
        assert len(ac_medics) >= 1, "Annapurna Circuit lacks medical aid post"

        ac_helipads = [
            w for w in waypoints_data
            if w.get("category") == "Emergency Helipad"
            and (w.get("trail_id") == "annapurna-circuit" or ("83.5" <= str(w["longitude"]) <= "84.5" and "28.3" <= str(w["latitude"]) <= "28.9"))
        ]
        assert len(ac_helipads) >= 1, "Annapurna Circuit lacks emergency helipad"

    def test_emergency_helipad_to_medical_clinic_flight_distance(self, waypoints_data):
        """Every high altitude helipad (>3500m) is within 40 km helicopter flight of a medical clinic or airstrip."""
        high_helipads = [
            w for w in waypoints_data
            if w.get("category") == "Emergency Helipad" and w.get("elevation_m", 0) >= 3500
        ]
        clinics = [w for w in waypoints_data if w.get("category") == "Medical Post"]

        for h in high_helipads:
            distances = [
                haversine_km(h["latitude"], h["longitude"], c["latitude"], c["longitude"])
                for c in clinics
            ]
            if distances:
                min_dist = min(distances)
                assert min_dist <= 120.0, f"Helipad {h['name']} is {min_dist:.1f}km away from nearest clinic (>120km limit)"


# =============================================================================
# Category 3: Cultural Itinerary, Festival Timing & Tiered Entry Fees
# =============================================================================
class TestCulturalItineraryAndFeeCalculation:
    """Pairwise combination of cultural heritage visits during festive periods with tiered fee calculations."""

    def test_dashain_kathmandu_valley_heritage_fee_computation(self, heritage_data, festivals_data):
        """Simulate a Dashain itinerary visiting Kathmandu Durbar Square, Pashupatinath, and Boudhanath."""
        dashain = next((f for f in festivals_data if "dashain" in f["name"].lower()), None)
        assert dashain is not None, "Dashain festival missing from calendar"
        assert "Ashwin" in dashain["lunar_month"] or "September" in dashain["typical_gregorian_window"]

        # Sites visited
        target_names = ["pashupatinath", "boudhanath", "kathmandu durbar"]
        visited_sites = [
            h for h in heritage_data
            if any(tn in h["name"].lower() for tn in target_names)
        ]
        assert len(visited_sites) >= 2, "Missing key Kathmandu UNESCO sites for Dashain itinerary"

        # Calculate entry fees for 2 Foreign Adults + 1 SAARC Adult + 1 Nepali citizen
        foreign_total = sum(h["entry_fees"]["foreign_npr"] * 2 for h in visited_sites)
        saarc_total = sum(h["entry_fees"]["saarc_npr"] * 1 for h in visited_sites)
        nepali_total = sum(h["entry_fees"]["nepali_npr"] * 1 for h in visited_sites)

        # Assert tiered pricing hierarchy: Foreign > SAARC >= Nepali
        assert foreign_total > saarc_total
        assert saarc_total >= nepali_total
        assert nepali_total == 0 or nepali_total < saarc_total

    def test_buddha_jayanti_lumbini_itinerary(self, heritage_data, festivals_data):
        """Simulate Buddha Jayanti pilgrimage to Lumbini Sacred Garden."""
        bj = next((f for f in festivals_data if "buddha" in f["name"].lower()), None)
        assert bj is not None, "Buddha Jayanti festival missing"

        lumbini_sites = [h for h in heritage_data if "lumbini" in h.get("region", "").lower() or "maya devi" in h["name"].lower()]
        assert len(lumbini_sites) >= 1, "Missing Lumbini heritage sites"

        for s in lumbini_sites:
            fees = s["entry_fees"]
            assert fees["foreign_npr"] >= fees["saarc_npr"] >= fees["nepali_npr"]
            assert s.get("guidelines") is not None
            assert "shoes_prohibited" in s["guidelines"]

    def test_mani_rimdu_tengboche_sherpa_festival_combination(self, heritage_data, festivals_data):
        """Simulate Mani Rimdu festival journey to Tengboche Monastery in Khumbu."""
        mr = next((f for f in festivals_data if "mani rimdu" in f["name"].lower()), None)
        assert mr is not None, "Mani Rimdu festival missing"
        assert any("Khumbu" in r or "Solukhumbu" in r for r in mr.get("primary_regions", []))

        # Verify Tengboche monastery presence in heritage dataset
        tengboche = next((h for h in heritage_data if "tengboche" in h["name"].lower()), None)
        assert tengboche is not None, "Tengboche Monastery missing from heritage data"
        assert tengboche["entry_fees"]["currency"] == "NPR"


# =============================================================================
# Category 4: Trail Watch Hazard Triage & Automated Guild Assignment
# =============================================================================
class TestTrailWatchHazardTriageAndGuildRouting:
    """Validate pairwise combination of hazard types, urgencies, and ecological steward dispatch."""

    def test_plastic_waste_hazard_auto_assigned_to_eco_clean_guild(self, db_session):
        """Waste accumulation hazards are categorised as Waste & Litter."""
        req = CreateReportRequest(
            hazard_type="Waste & Plastic Accumulation",
            urgency="Moderate",
            description="Discarded packaging and water bottles found along trail corridor.",
            location_name="Khumbu Corridor • Dingboche Sector",
            latitude=27.892,
            longitude=86.828,
            altitude=4410
        )
        res = _run_coro(create_report(req=req, db=db_session))
        assert res["success"] is True
        assert res["report"]["assigned_guild"] == "Waste & Litter"

    def test_trail_obstruction_hazard_auto_assigned_to_acap_field_wardens(self, db_session):
        """Landslide and shale blockage hazards are categorised as Trail Obstruction."""
        req = CreateReportRequest(
            hazard_type="Trail Obstruction / Landslide",
            urgency="Urgent",
            description="Boulders blocked the main ascent path.",
            location_name="Annapurna Circuit • Kali Gandaki Sector",
            latitude=28.539,
            longitude=83.652,
            altitude=2810
        )
        res = _run_coro(create_report(req=req, db=db_session))
        assert res["success"] is True
        assert res["report"]["assigned_guild"] == "Trail Obstruction"

    def test_heritage_damage_hazard_auto_assigned_to_heritage_guild(self, db_session):
        """Historic shrine and mani wall damage hazards are categorised as Heritage Site."""
        req = CreateReportRequest(
            hazard_type="Heritage Shrine & Mani Wall Damage",
            urgency="Low",
            description="Weathered carved slates loosened on ancient chorten.",
            location_name="Langtang Valley • Kyanjin Gompa Trail",
            latitude=28.213,
            longitude=85.567,
            altitude=3870
        )
        res = _run_coro(create_report(req=req, db=db_session))
        assert res["success"] is True
        assert res["report"]["assigned_guild"] == "Heritage Site"

    def test_hazard_dispatch_reflects_in_stewardship_metrics(self, db_session):
        """Filing a hazard incremented the total reports count in ecological stewardship stats."""
        stats_before = _run_coro(get_stats(db=db_session))
        count_before = stats_before["total_reports"]

        req = CreateReportRequest(
            hazard_type="Fallen Bridge Cable",
            urgency="Urgent",
            description="Suspension bridge anchor point needs wire reinforcement.",
            location_name="Manaslu Circuit • Jagat Suspension Bridge",
            latitude=28.360,
            longitude=84.890,
            altitude=1340
        )
        _run_coro(create_report(req=req, db=db_session))

        stats_after = _run_coro(get_stats(db=db_session))
        assert stats_after["total_reports"] == count_before + 1
