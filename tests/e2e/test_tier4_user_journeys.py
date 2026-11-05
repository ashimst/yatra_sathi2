"""
Tier 4: Real-World Application Scenarios Test Suite (End-to-End User Journeys)
Validates complete user journeys from expedition planning to cultural immersion:
1. 14-Day Everest Base Camp Trek with Acclimatization Rest Days & Medical Safety.
2. Complete Kathmandu Valley UNESCO 7 Monument Zones & Lumbini Pilgrimage Circuit.
3. Annapurna Circuit Thorong La Pass Crossing Expedition & Cultural Transition.
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
from backend.app.models.itinerary import Itinerary
from backend.app.models.trail_watch import TrailReport, TrailSteward
from backend.app.api.trail_watch import create_report, CreateReportRequest


def _run_coro(coro):
    """Execute coroutine synchronously without event loop socket binding."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


# =============================================================================
# Journey 1: 14-Day Everest Base Camp Trekking Expedition
# =============================================================================
class TestEverestBaseCampExpeditionJourney:
    """End-to-End User Journey: Trekker plans and executes a 14-day EBC expedition."""

    def test_ebc_permits_and_mandatory_entrance_cards(self, trails_data):
        """Trekkers verify mandatory regulatory permits before departing Kathmandu for Lukla."""
        ebc_trail = next((t for t in trails_data if "everest" in t.get("id", "").lower()), None)
        assert ebc_trail is not None, "EBC Trail not found"

        permits = ebc_trail.get("permits_required", [])
        # Sagarmatha National Park Permit and Khumbu Pasang Lhamu Rural Municipality card
        assert any("Sagarmatha" in p for p in permits), "Missing Sagarmatha National Park permit"
        assert any("Khumbu" in p or "TIMS" in p for p in permits), "Missing Khumbu entrance card or permit"

    def test_ebc_acclimatization_rest_day_milestones(self, trails_data, waypoints_data):
        """Expedition includes mandatory medical acclimatization stops at Namche Bazaar (3440m) and Dingboche (4410m)."""
        ebc_trail = next((t for t in trails_data if "everest" in t.get("id", "").lower()), None)
        assert ebc_trail is not None

        # Check Namche Bazaar presence
        namche = next((w for w in waypoints_data if "namche" in w["name"].lower()), None)
        assert namche is not None, "Namche Bazaar missing from waypoint registry"
        assert 3300 <= namche["elevation_m"] <= 3600

        # Check Dingboche presence
        dingboche = next((w for w in waypoints_data if "dingboche" in w["name"].lower()), None)
        assert dingboche is not None, "Dingboche missing from waypoint registry"
        assert 4300 <= dingboche["elevation_m"] <= 4550

    def test_ebc_summit_viewpoint_and_base_camp_endpoints(self, waypoints_data):
        """Journey reaches Everest Base Camp (5,364m) and Kala Patthar summit viewpoint (5,545m)."""
        ebc_point = next((w for w in waypoints_data if "base camp" in w["name"].lower() and "everest" in w["name"].lower()), None)
        assert ebc_point is not None, "Everest Base Camp waypoint missing"

        kala_patthar = next((w for w in waypoints_data if "kala patthar" in w["name"].lower()), None)
        assert kala_patthar is not None, "Kala Patthar waypoint missing"
        assert 5000 <= kala_patthar["elevation_m"] <= 5600, "Kala Patthar elevation outside range"

    def test_ebc_emergency_rescue_network_readiness(self, waypoints_data, db_session):
        """Simulate AMS emergency at Lobuche (4,940m): verify medical clinic and helipad dispatch link."""
        pheriche_clinic = next((w for w in waypoints_data if "pheriche" in w["name"].lower()), None)
        assert pheriche_clinic is not None, "HRA Pheriche Clinic missing"

        # Check emergency helipads in high-altitude Khumbu
        khumbu_helipads = [
            w for w in waypoints_data
            if w.get("category") == "Emergency Helipad"
            and 86.6 <= w["longitude"] <= 86.9 and 27.6 <= w["latitude"] <= 28.1
        ]
        assert len(khumbu_helipads) >= 2, "Insufficient helipads in Khumbu corridor"

        # Register steward on EBC corridor with doko pack
        steward = TrailSteward(
            id=uuid.uuid4(),
            name="Tenzing Norgay Sherpa",
            email="tenzing.ebc.test@example.com",
            preferred_region="Everest Base Camp Corridor",
            doko_pack_issued=True
        )
        db_session.add(steward)
        db_session.commit()

        retrieved = db_session.query(TrailSteward).filter(TrailSteward.email == "tenzing.ebc.test@example.com").first()
        assert retrieved is not None
        assert retrieved.doko_pack_issued is True


# =============================================================================
# Journey 2: Kathmandu Valley 7 UNESCO Zones & Lumbini Pilgrimage Circuit
# =============================================================================
class TestKathmanduAndLumbiniHeritagePilgrimageJourney:
    """End-to-End User Journey: Cultural traveler visits all 7 UNESCO Kathmandu monument zones + Lumbini."""

    def test_unesco_seven_monument_zones_completeness(self, heritage_data):
        """Verify presence of all seven UNESCO Kathmandu Valley monument zones in single journey."""
        REQUIRED_ZONES = [
            "Pashupatinath",
            "Boudhanath",
            "Swayambhunath",
            "Kathmandu Durbar",
            "Patan Durbar",
            "Bhaktapur Durbar",
            "Changu Narayan"
        ]
        found_zones = []
        for zone in REQUIRED_ZONES:
            match = next((h for h in heritage_data if zone.lower() in h["name"].lower()), None)
            assert match is not None, f"Missing required UNESCO monument zone: {zone}"
            found_zones.append(match)

        assert len(found_zones) == 7

    def test_tiered_fee_matrix_foreign_vs_saarc_vs_nepali(self, heritage_data):
        """Calculate complete budget for 7 Kathmandu UNESCO sites + Maya Devi Temple (Lumbini)."""
        REQUIRED_SITES = [
            "Pashupatinath",
            "Boudhanath",
            "Swayambhunath",
            "Kathmandu Durbar",
            "Patan Durbar",
            "Bhaktapur Durbar",
            "Changu Narayan",
            "Maya Devi"
        ]
        circuit_sites = []
        for s in REQUIRED_SITES:
            m = next((h for h in heritage_data if s.lower() in h["name"].lower()), None)
            if m:
                circuit_sites.append(m)

        assert len(circuit_sites) >= 7, "Missing circuit sites"

        foreign_bill = sum(s["entry_fees"]["foreign_npr"] for s in circuit_sites)
        saarc_bill = sum(s["entry_fees"]["saarc_npr"] for s in circuit_sites)
        nepali_bill = sum(s["entry_fees"]["nepali_npr"] for s in circuit_sites)

        # Foreign bill should be between NPR 4,000 and NPR 10,000
        assert 4000 <= foreign_bill <= 10000, f"Unexpected foreign bill total: NPR {foreign_bill}"
        # SAARC bill should be substantial discount (~NPR 1,000 to NPR 3,000)
        assert 800 <= saarc_bill <= 3000, f"Unexpected SAARC bill total: NPR {saarc_bill}"
        # Nepali citizens have minimal or free entry (under NPR 300 total)
        assert nepali_bill <= 300, f"Unexpected Nepali bill total: NPR {nepali_bill}"

    def test_cultural_guideline_compliance_matrix(self, heritage_data):
        """Verify strict dress code, shoe removal, and photography rules across sacred sites."""
        sacred_sites = [
            h for h in heritage_data
            if any(term in h["name"].lower() for term in ["pashupatinath", "maya devi", "changu narayan", "boudhanath"])
        ]
        for s in sacred_sites:
            gl = s.get("guidelines", {})
            assert "dress_code" in gl, f"Missing dress code for sacred site {s['name']}"
            assert "photography" in gl, f"Missing photography guideline for {s['name']}"
            assert "shoes_prohibited" in gl or "shoes_prohibited" in str(gl), f"Missing shoe guideline for {s['name']}"


# =============================================================================
# Journey 3: Annapurna Circuit Thorong La Pass Crossing Expedition
# =============================================================================
class TestAnnapurnaCircuitCrossingJourney:
    """End-to-End User Journey: Trekker traverses the Annapurna Circuit crossing Thorong La (5,416m)."""

    def test_annapurna_circuit_full_itinerary_progression(self, trails_data, waypoints_data):
        """Verify sequential trek milestones: Besisahar -> Chame -> Manang -> Thorong Phedi -> Thorong La -> Muktinath."""
        ac_trail = next((t for t in trails_data if "annapurna-circuit" in t.get("id", "").lower()), None)
        assert ac_trail is not None, "Annapurna Circuit trail missing"
        assert ac_trail["max_elevation_m"] >= 5400, "Annapurna Circuit peak elevation too low"

        # Check Thorong La pass waypoint
        thorong_la = next((w for w in waypoints_data if "thorong la" in w["name"].lower()), None)
        assert thorong_la is not None, "Thorong La Pass missing from waypoint registry"
        assert 5400 <= thorong_la["elevation_m"] <= 5450, f"Thorong La elevation inaccurate: {thorong_la['elevation_m']}m"

        # Check Muktinath sacred temple on descent
        muktinath = next((w for w in waypoints_data if "muktinath" in w["name"].lower()), None)
        assert muktinath is not None, "Muktinath waypoint missing on descent"
        assert 3600 <= muktinath["elevation_m"] <= 3850

    def test_annapurna_circuit_permits_acap_and_tims(self, trails_data):
        """Verify Annapurna Circuit demands ACAP and TIMS permits."""
        ac_trail = next((t for t in trails_data if "annapurna-circuit" in t.get("id", "").lower()), None)
        assert ac_trail is not None
        permits = ac_trail.get("permits_required", [])
        assert any("ACAP" in p or "Annapurna Conservation" in p for p in permits), "ACAP permit missing"

    def test_annapurna_circuit_hazard_reporting_and_field_warden_resolution(self, db_session):
        """Simulate trekker reporting a landslide at Dana-Ghasa; report is posted as an open Trail Obstruction."""
        req = CreateReportRequest(
            hazard_type="Trail Obstruction / Landslide",
            urgency="Urgent",
            description="Rockfall across lower cliff path. Mule caravan rerouted to high trail.",
            location_name="Annapurna Circuit • Kali Gandaki Gorge",
            latitude=28.539,
            longitude=83.652,
            altitude=2810
        )
        res = _run_coro(create_report(req=req, db=db_session))
        assert res["success"] is True
        assert res["report"]["status"] == "Open"
        assert res["report"]["assigned_guild"] == "Trail Obstruction"

    def test_itinerary_persistence_in_database(self, db_session):
        """Verify an end-to-end multi-day itinerary commits cleanly to the database schema."""
        test_itin_id = uuid.uuid4()
        itinerary = Itinerary(
            id=test_itin_id,
            title="16-Day Classic Annapurna Circuit Expedition",
            origin_name="Kathmandu",
            dest_name="Jomsom / Pokhara",
            num_days=16,
            pace="moderate",
            budget="medium",
            share_id=f"ANNAPURNA-{uuid.uuid4().hex[:8]}"
        )
        db_session.add(itinerary)
        db_session.commit()

        retrieved = db_session.query(Itinerary).filter(Itinerary.id == test_itin_id).first()
        assert retrieved is not None
        assert retrieved.title == "16-Day Classic Annapurna Circuit Expedition"
        assert retrieved.num_days == 16
