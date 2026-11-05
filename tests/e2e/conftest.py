"""
Global pytest configuration and fixtures for YatraSathi E2E test suite.
Provides database fixtures, mock data, bounding box constants, and test utilities.
"""
import os
import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set test environment variables BEFORE importing backend settings
TEST_DB_FILE = PROJECT_ROOT / "test_e2e_yatra.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["AI_ENABLED"] = "false"
os.environ["DEBUG"] = "false"

# SQLAlchemy & SQLite compatibility for PostgreSQL JSONB and pgvector Vector
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

try:
    from pgvector.sqlalchemy import Vector
    @compiles(Vector, "sqlite")
    def compile_vector_sqlite(type_, compiler, **kw):
        return "BLOB"
except ImportError:
    pass

import pytest
from backend.app.config.settings import settings
settings.DATABASE_URL = TEST_DB_URL

import backend.app.db.database as db_mod
import backend.app.services.place_service as ps_mod
from backend.app.db.database import Base, get_db
from backend.app.models.place import Place
from backend.app.models.trail_watch import TrailReport, TrailSteward
from backend.app.models.itinerary import Itinerary

# Configure shared SQLite test engine and sessionmaker
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False
)
Base.metadata.create_all(bind=test_engine)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Re-bind global backend db references to SQLite test engine
db_mod.engine = test_engine
db_mod.SessionLocal = TestSessionLocal
ps_mod.SessionLocal = TestSessionLocal

# -----------------------------------------------------------------------------
# Geographic Constants for Nepal
# -----------------------------------------------------------------------------
NEPAL_LAT_MIN = 26.0
NEPAL_LAT_MAX = 30.5
NEPAL_LON_MIN = 80.0
NEPAL_LON_MAX = 88.5
NEPAL_MIN_ALTITUDE = 60.0       # Kechana Kawal, Jhapa
NEPAL_MAX_ALTITUDE = 8848.86    # Mt. Everest (Sagarmatha)

# Seed File Paths
SEED_DIR = PROJECT_ROOT / "backend" / "data" / "seeds"
TRAILS_SEED_PATH = SEED_DIR / "trekking_trails.json"
WAYPOINTS_SEED_PATH = SEED_DIR / "waypoints.json"
HERITAGE_SEED_PATH = SEED_DIR / "cultural_heritage.json"
FESTIVALS_SEED_PATH = SEED_DIR / "festivals.json"
SQLITE_DB_PATH = PROJECT_ROOT / "yatra_sathi.db"

# -----------------------------------------------------------------------------
# Reference Datasets (Fallback / Opaque-box Oracle)
# -----------------------------------------------------------------------------
REFERENCE_TRAILS = [
    {
        "id": "annapurna-circuit",
        "name": "Annapurna Circuit Trek",
        "region": "Annapurna",
        "difficulty": "Challenging",
        "duration_days": 16,
        "max_elevation_m": 5416.0,
        "pass_elevation_m": 5416.0,
        "permits_required": ["ACAP", "TIMS"],
        "start_point": {"name": "Besisahar", "latitude": 28.2300, "longitude": 84.3750},
        "end_point": {"name": "Jomsom", "latitude": 28.7844, "longitude": 83.7231},
        "route_geometry_wkt": "LINESTRING(84.3750 28.2300, 84.2403 28.5539, 84.0256 28.6638, 83.9355 28.7937, 83.8714 28.8169, 83.7231 28.7844)",
        "key_waypoints": ["Chame", "Manang", "Thorong Phedi", "Thorong La Pass", "Muktinath"]
    },
    {
        "id": "annapurna-base-camp",
        "name": "Annapurna Sanctuary Trek (ABC)",
        "region": "Annapurna",
        "difficulty": "Moderate",
        "duration_days": 10,
        "max_elevation_m": 4130.0,
        "pass_elevation_m": None,
        "permits_required": ["ACAP", "TIMS"],
        "start_point": {"name": "Nayapul", "latitude": 28.3006, "longitude": 83.7744},
        "end_point": {"name": "Nayapul", "latitude": 28.3006, "longitude": 83.7744},
        "route_geometry_wkt": "LINESTRING(83.7744 28.3006, 83.8206 28.4217, 83.8710 28.5240, 83.8780 28.5300)",
        "key_waypoints": ["Ghandruk", "Chhomrong", "Dovan", "Deurali", "Machapuchare Base Camp", "Annapurna Base Camp"]
    },
    {
        "id": "everest-base-camp",
        "name": "Everest Base Camp Trek",
        "region": "Everest",
        "difficulty": "Strenuous",
        "duration_days": 14,
        "max_elevation_m": 5545.0,
        "pass_elevation_m": 4830.0,
        "permits_required": ["Sagarmatha National Park Permit", "Khumbu Pasang Lhamu Entrance Card"],
        "start_point": {"name": "Lukla", "latitude": 27.6869, "longitude": 86.7314},
        "end_point": {"name": "Lukla", "latitude": 27.6869, "longitude": 86.7314},
        "route_geometry_wkt": "LINESTRING(86.7314 27.6869, 86.7247 27.7719, 86.7090 27.8051, 86.7646 27.8364, 86.8287 27.8923, 86.8290 27.9810, 86.8525 28.0044)",
        "key_waypoints": ["Phakding", "Namche Bazaar", "Tengboche", "Dingboche", "Lobuche", "Gorak Shep", "Everest Base Camp", "Kala Patthar"]
    },
    {
        "id": "gokyo-lakes-three-passes",
        "name": "Gokyo Lakes & Three Passes Trek",
        "region": "Everest",
        "difficulty": "Strenuous",
        "duration_days": 18,
        "max_elevation_m": 5535.0,
        "pass_elevation_m": 5420.0,
        "permits_required": ["Sagarmatha National Park Permit", "Khumbu Pasang Lhamu Entrance Card"],
        "start_point": {"name": "Lukla", "latitude": 27.6869, "longitude": 86.7314},
        "end_point": {"name": "Lukla", "latitude": 27.6869, "longitude": 86.7314},
        "route_geometry_wkt": "LINESTRING(86.7314 27.6869, 86.7090 27.8051, 86.6947 27.9538, 86.7516 27.9617, 86.8290 27.9810)",
        "key_waypoints": ["Namche Bazaar", "Dole", "Gokyo", "Cho La Pass", "Renjo La Pass", "Kongma La Pass"]
    },
    {
        "id": "manaslu-circuit",
        "name": "Manaslu Circuit Trek",
        "region": "Manaslu",
        "difficulty": "Strenuous",
        "duration_days": 14,
        "max_elevation_m": 5106.0,
        "pass_elevation_m": 5106.0,
        "permits_required": ["Manaslu Restricted Area Permit (RAP)", "MCAP", "ACAP"],
        "start_point": {"name": "Soti Khola", "latitude": 28.1833, "longitude": 84.8667},
        "end_point": {"name": "Dharapani", "latitude": 28.5200, "longitude": 84.3600},
        "route_geometry_wkt": "LINESTRING(84.8667 28.1833, 84.8833 28.4000, 84.6333 28.5833, 84.4500 28.6667, 84.3600 28.5200)",
        "key_waypoints": ["Machha Khola", "Jagat", "Deng", "Namrung", "Samagaon", "Samdo", "Larkya La Pass", "Bhimthang"]
    },
    {
        "id": "langtang-valley",
        "name": "Langtang Valley Trek",
        "region": "Langtang",
        "difficulty": "Moderate",
        "duration_days": 8,
        "max_elevation_m": 4984.0,
        "pass_elevation_m": None,
        "permits_required": ["Langtang National Park Permit", "TIMS"],
        "start_point": {"name": "Syabrubesi", "latitude": 28.1567, "longitude": 85.3378},
        "end_point": {"name": "Syabrubesi", "latitude": 28.1567, "longitude": 85.3378},
        "route_geometry_wkt": "LINESTRING(85.3378 28.1567, 85.4200 28.1800, 85.5600 28.2100, 85.6200 28.2200)",
        "key_waypoints": ["Lama Hotel", "Langtang Village", "Kyanjin Gompa", "Kyanjin Ri", "Tserko Ri"]
    },
    {
        "id": "upper-mustang",
        "name": "Upper Mustang Trek",
        "region": "Mustang",
        "difficulty": "Moderate",
        "duration_days": 12,
        "max_elevation_m": 4230.0,
        "pass_elevation_m": 3820.0,
        "permits_required": ["Upper Mustang Restricted Area Permit (RAP)", "ACAP"],
        "start_point": {"name": "Jomsom", "latitude": 28.7844, "longitude": 83.7231},
        "end_point": {"name": "Jomsom", "latitude": 28.7844, "longitude": 83.7231},
        "route_geometry_wkt": "LINESTRING(83.7231 28.7844, 83.7500 28.8700, 83.8300 29.0800, 83.9500 29.1800)",
        "key_waypoints": ["Kagbeni", "Chele", "Syangboche", "Ghami", "Charang", "Lo Manthang"]
    },
    {
        "id": "mardi-himal",
        "name": "Mardi Himal Trek",
        "region": "Annapurna",
        "difficulty": "Moderate",
        "duration_days": 6,
        "max_elevation_m": 4500.0,
        "pass_elevation_m": None,
        "permits_required": ["ACAP", "TIMS"],
        "start_point": {"name": "Kande", "latitude": 28.2917, "longitude": 83.8417},
        "end_point": {"name": "Siding", "latitude": 28.3667, "longitude": 83.9000},
        "route_geometry_wkt": "LINESTRING(83.8417 28.2917, 83.8500 28.3200, 83.8800 28.4000, 83.9100 28.4500)",
        "key_waypoints": ["Australian Camp", "Forest Camp", "Low Camp", "High Camp", "Mardi Himal Base Camp"]
    },
    {
        "id": "kanchenjunga-base-camp",
        "name": "Kanchenjunga Base Camp Trek",
        "region": "Kanchenjunga",
        "difficulty": "Strenuous",
        "duration_days": 21,
        "max_elevation_m": 5143.0,
        "pass_elevation_m": 4640.0,
        "permits_required": ["Kanchenjunga Restricted Area Permit (RAP)", "KCAP"],
        "start_point": {"name": "Taplejung", "latitude": 27.3500, "longitude": 87.6700},
        "end_point": {"name": "Taplejung", "latitude": 27.3500, "longitude": 87.6700},
        "route_geometry_wkt": "LINESTRING(87.6700 27.3500, 87.8000 27.5500, 88.0200 27.7500, 88.1500 27.8000)",
        "key_waypoints": ["Mitke", "Ghunsa", "Kambachen", "Lhonak", "Pangpema (North BC)", "Sele Le Pass", "Ramche (South BC)"]
    },
    {
        "id": "gosaikunda-helambu",
        "name": "Gosaikunda & Helambu Sacred Lakes Trek",
        "region": "Langtang",
        "difficulty": "Moderate",
        "duration_days": 7,
        "max_elevation_m": 4610.0,
        "pass_elevation_m": 4610.0,
        "permits_required": ["Langtang National Park Permit", "Shivapuri National Park Permit", "TIMS"],
        "start_point": {"name": "Dhunche", "latitude": 28.1120, "longitude": 85.3000},
        "end_point": {"name": "Sundarijal", "latitude": 27.7600, "longitude": 85.4200},
        "route_geometry_wkt": "LINESTRING(85.3000 28.1120, 85.3500 28.1000, 85.4200 28.0800, 85.4500 27.9500, 85.4200 27.7600)",
        "key_waypoints": ["Deurali", "Chandanbari", "Laurebina", "Gosaikunda Lake", "Laurebina Pass", "Ghopte", "Melamchigaon", "Tarkeghyang"]
    }
]

REFERENCE_WAYPOINTS = [
    {"name": "Thorong La Pass", "category": "Mountain Pass", "latitude": 28.7937, "longitude": 83.9355, "elevation_m": 5416.0, "trail_id": "annapurna-circuit", "details": {"pass_name": "Thorong La", "prayer_flags": True}},
    {"name": "Kala Patthar", "category": "Mountain Pass", "latitude": 27.9958, "longitude": 86.8284, "elevation_m": 5545.0, "trail_id": "everest-base-camp", "details": {"viewpoint": "Mt. Everest View"}},
    {"name": "Cho La Pass", "category": "Mountain Pass", "latitude": 27.9617, "longitude": 86.7516, "elevation_m": 5420.0, "trail_id": "gokyo-lakes-three-passes", "details": {"glacier_crossing": True}},
    {"name": "Larkya La Pass", "category": "Mountain Pass", "latitude": 28.6667, "longitude": 84.4500, "elevation_m": 5106.0, "trail_id": "manaslu-circuit", "details": {"pass_name": "Larkya La"}},
    {"name": "HRA Pheriche Clinic", "category": "Medical Post", "latitude": 27.8920, "longitude": 86.8210, "elevation_m": 4240.0, "trail_id": "everest-base-camp", "details": {"facilities": ["Gamow hyperbaric chamber", "Oxygen concentrators"], "doctors": 2, "radio_frequency": "144.120 MHz"}},
    {"name": "HRA Manang Clinic", "category": "Medical Post", "latitude": 28.6638, "longitude": 84.0256, "elevation_m": 3540.0, "trail_id": "annapurna-circuit", "details": {"facilities": ["Altitude lectures"], "radio_frequency": "144.150 MHz"}},
    {"name": "Kunde Hospital", "category": "Medical Post", "latitude": 27.8180, "longitude": 86.7120, "elevation_m": 3840.0, "trail_id": "everest-base-camp", "details": {"facilities": ["Inpatient ward", "X-ray"]}},
    {"name": "Machhermo Rescue Clinic", "category": "Medical Post", "latitude": 27.9080, "longitude": 86.7110, "elevation_m": 4470.0, "trail_id": "gokyo-lakes-three-passes", "details": {"facilities": ["Portable oxygen", "PAC chamber"]}},
    {"name": "Lukla Helipad", "category": "Emergency Helipad", "latitude": 27.6875, "longitude": 86.7320, "elevation_m": 2846.0, "trail_id": "everest-base-camp", "details": {"paved": True, "icao": "VNLK"}},
    {"name": "Namche Army Helipad", "category": "Emergency Helipad", "latitude": 27.8060, "longitude": 86.7130, "elevation_m": 3450.0, "trail_id": "everest-base-camp", "details": {"army_controlled": True}},
    {"name": "Tengboche Helipad", "category": "Emergency Helipad", "latitude": 27.8360, "longitude": 86.7640, "elevation_m": 3867.0, "trail_id": "everest-base-camp", "details": {"open_field": True}},
    {"name": "Pheriche Helipad", "category": "Emergency Helipad", "latitude": 27.8930, "longitude": 86.8200, "elevation_m": 4240.0, "trail_id": "everest-base-camp", "details": {"clinic_adjacent": True}},
    {"name": "Gorak Shep Helipad", "category": "Emergency Helipad", "latitude": 27.9815, "longitude": 86.8285, "elevation_m": 5164.0, "trail_id": "everest-base-camp", "details": {"high_altitude_rescue": True}},
    {"name": "Annapurna Base Camp Helipad", "category": "Emergency Helipad", "latitude": 28.5305, "longitude": 83.8785, "elevation_m": 4130.0, "trail_id": "annapurna-base-camp", "details": {"sanctuary_clearing": True}},
    {"name": "Manang Humde Helipad", "category": "Emergency Helipad", "latitude": 28.6400, "longitude": 84.1400, "elevation_m": 3350.0, "trail_id": "annapurna-circuit", "details": {"airstrip_adjacent": True}},
    {"name": "Thorong Phedi Base Helipad", "category": "Emergency Helipad", "latitude": 28.7750, "longitude": 83.9550, "elevation_m": 4540.0, "trail_id": "annapurna-circuit", "details": {"evac_point": True}},
    {"name": "Monjo Checkpost", "category": "Checkpost", "latitude": 27.7719, "longitude": 86.7247, "elevation_m": 2835.0, "trail_id": "everest-base-camp", "details": {"permit_inspection": "Sagarmatha NP"}},
    {"name": "Bhotekoshi ACAP Checkpost", "category": "Checkpost", "latitude": 28.2320, "longitude": 84.3760, "elevation_m": 820.0, "trail_id": "annapurna-circuit", "details": {"permit_inspection": "ACAP + TIMS"}},
    {"name": "Namche Bazaar Settlement", "category": "Settlement", "latitude": 27.8051, "longitude": 86.7090, "elevation_m": 3440.0, "trail_id": "everest-base-camp", "details": {"acclimatization_hub": True, "lodges": 50, "banks": True, "bakeries": True}},
    {"name": "Dingboche Acclimatization Hub", "category": "Acclimatization Hub", "latitude": 27.8923, "longitude": 86.8287, "elevation_m": 4410.0, "trail_id": "everest-base-camp", "details": {"day_hike": "Nagarjun Hill 5100m"}}
]

REFERENCE_HERITAGE = [
    {
        "name": "Pashupatinath Temple Complex",
        "region": "Kathmandu Valley",
        "category": "Religious Site",
        "group": "Religious",
        "latitude": 27.7105,
        "longitude": 85.3487,
        "description": "Sacred Hindu temple dedicated to Lord Shiva situated along the Bagmati River; UNESCO World Heritage Monument Zone.",
        "entry_fees": {"foreign_npr": 1000, "saarc_npr": 1000, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Cover shoulders and knees", "shoes_prohibited": True, "photography": "Courtyard allowed, main sanctum forbidden", "sanctum_restrictions": "Hindus only in inner sanctum"},
        "best_seasons": ["Autumn", "Winter", "Spring"]
    },
    {
        "name": "Boudhanath Stupa",
        "region": "Kathmandu Valley",
        "category": "Religious Site",
        "group": "Heritage",
        "latitude": 27.7215,
        "longitude": 85.3620,
        "description": "One of the largest spherical stupas in the world and center of Tibetan Buddhism in Nepal; UNESCO Monument Zone.",
        "entry_fees": {"foreign_npr": 400, "saarc_npr": 100, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Modest attire", "shoes_prohibited": False, "photography": "Permitted", "sanctum_restrictions": "Circumambulate clockwise (kora)"},
        "best_seasons": ["Autumn", "Winter", "Spring"]
    },
    {
        "name": "Swayambhunath Stupa (Monkey Temple)",
        "region": "Kathmandu Valley",
        "category": "Religious Site",
        "group": "Heritage",
        "latitude": 27.7148,
        "longitude": 85.2903,
        "description": "Ancient hilltop religious complex housing sacred white dome, all-seeing eyes of Buddha, and tantric shrines.",
        "entry_fees": {"foreign_npr": 200, "saarc_npr": 50, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Modest clothing", "shoes_prohibited": False, "photography": "Permitted", "sanctum_restrictions": "Clockwise circumambulation"},
        "best_seasons": ["Autumn", "Spring"]
    },
    {
        "name": "Kathmandu Durbar Square (Hanuman Dhoka)",
        "region": "Kathmandu Valley",
        "category": "Historic Site",
        "group": "Historic",
        "latitude": 27.7042,
        "longitude": 85.3076,
        "description": "Historic royal palace plaza featuring Kumari Ghar, Taleju Temple, Kasthamandap, and Newar pagoda architecture.",
        "entry_fees": {"foreign_npr": 1000, "saarc_npr": 150, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Modest attire", "shoes_prohibited": False, "photography": "Permitted outside; restricted inside Kumari Ghar", "sanctum_restrictions": "No photography of Living Goddess"},
        "best_seasons": ["Autumn", "Spring"]
    },
    {
        "name": "Patan Durbar Square",
        "region": "Kathmandu Valley",
        "category": "Historic Site",
        "group": "Historic",
        "latitude": 27.6738,
        "longitude": 85.3253,
        "description": "Center of fine arts and Malla architecture, including Krishna Mandir, Golden Temple, and Patan Museum.",
        "entry_fees": {"foreign_npr": 1000, "saarc_npr": 250, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Modest attire", "shoes_prohibited": False, "photography": "Allowed; separate museum tickets may apply", "sanctum_restrictions": "None"},
        "best_seasons": ["Autumn", "Spring"]
    },
    {
        "name": "Bhaktapur Durbar Square",
        "region": "Kathmandu Valley",
        "category": "Historic Site",
        "group": "Historic",
        "latitude": 27.6722,
        "longitude": 85.4284,
        "description": "Preserved medieval royal city featuring 55-Window Palace, Nyatapola 5-story pagoda, and Pottery Square.",
        "entry_fees": {"foreign_npr": 1800, "saarc_npr": 500, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Modest attire", "shoes_prohibited": False, "photography": "Permitted throughout", "sanctum_restrictions": "None"},
        "best_seasons": ["Autumn", "Winter", "Spring"]
    },
    {
        "name": "Changu Narayan Temple",
        "region": "Kathmandu Valley",
        "category": "Religious Site",
        "group": "Historic",
        "latitude": 27.7161,
        "longitude": 85.4277,
        "description": "Oldest intact Hindu pagoda temple in Nepal with 5th century Licchavi stone inscriptions and master carvings.",
        "entry_fees": {"foreign_npr": 300, "saarc_npr": 100, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Modest attire", "shoes_prohibited": True, "photography": "Permitted outside", "sanctum_restrictions": "Inner sanctum restricted"},
        "best_seasons": ["Autumn", "Spring"]
    },
    {
        "name": "Maya Devi Temple & Sacred Garden",
        "region": "Lumbini",
        "category": "Religious Site",
        "group": "Heritage",
        "latitude": 27.4840,
        "longitude": 83.2760,
        "description": "UNESCO World Heritage birthplace of Siddhartha Gautama (Lord Buddha), Marker Stone, and Ashoka Pillar.",
        "entry_fees": {"foreign_npr": 500, "saarc_npr": 200, "nepali_npr": 50, "currency": "NPR"},
        "guidelines": {"dress_code": "White or modest clothing", "shoes_prohibited": True, "photography": "Forbidden inside sanctum, allowed in garden", "sanctum_restrictions": "Silence required"},
        "best_seasons": ["Autumn", "Winter"]
    },
    {
        "name": "World Peace Pagoda (Shanti Stupa)",
        "region": "Pokhara",
        "category": "Monument",
        "group": "Tourism",
        "latitude": 28.2008,
        "longitude": 83.9443,
        "description": "Brilliant white stupa situated atop Anadu Hill overlooking Phewa Lake and the Annapurna Mountain range.",
        "entry_fees": {"foreign_npr": 0, "saarc_npr": 0, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Modest clothing", "shoes_prohibited": True, "photography": "Permitted", "sanctum_restrictions": "Silence maintained on upper deck"},
        "best_seasons": ["Autumn", "Winter", "Spring"]
    },
    {
        "name": "Tengboche Monastery",
        "region": "Himalaya",
        "category": "Religious Site",
        "group": "Religious",
        "latitude": 27.8364,
        "longitude": 86.7646,
        "description": "Premier Tibetan Buddhist monastery in Khumbu, hosting the annual sacred masked dance festival Mani Rimdu.",
        "entry_fees": {"foreign_npr": 300, "saarc_npr": 300, "nepali_npr": 0, "currency": "NPR"},
        "guidelines": {"dress_code": "Hats and shoes removed inside", "shoes_prohibited": True, "photography": "Prohibited inside prayer hall", "sanctum_restrictions": "Quiet prayer observed"},
        "best_seasons": ["Spring", "Autumn"]
    }
]

REFERENCE_FESTIVALS = [
    {
        "name": "Dashain (Bijaya Dashami)",
        "lunar_month": "Ashwin (September - October)",
        "typical_gregorian_window": "September - October",
        "significance": "Nepal's longest and most auspicious national festival celebrating the victory of Goddess Durga over Mahishasura; family reunions, tika, jamara, and blessing of elders.",
        "primary_regions": ["Nationwide", "Kathmandu Valley", "Pokhara"],
        "associated_places": ["Taleju Temple", "Dakshinkali Temple", "Hanuman Dhoka"]
    },
    {
        "name": "Tihar (Deepawali & Bhai Tika)",
        "lunar_month": "Kartik (October - November)",
        "typical_gregorian_window": "October - November",
        "significance": "Five-day Festival of Lights worshipping cows, dogs, Goddess Laxmi, and the bond between brothers and sisters.",
        "primary_regions": ["Nationwide"],
        "associated_places": ["Kathmandu Durbar Square", "Patan Durbar Square", "Rani Pokhari"]
    },
    {
        "name": "Chhath Parva",
        "lunar_month": "Kartik Shukla Shashthi",
        "typical_gregorian_window": "October - November",
        "significance": "Ancient Vedic sun worship celebrated by offering Arghya to the setting and rising Sun God Surya at sacred rivers and ponds.",
        "primary_regions": ["Terai", "Janakpur", "Kathmandu"],
        "associated_places": ["Janaki Mandir", "Ganga Sagar", "Bagmati River"]
    },
    {
        "name": "Holi (Fagu Purnima)",
        "lunar_month": "Phalguna Purnima",
        "typical_gregorian_window": "March",
        "significance": "Spring festival of colors celebrating the victory of devotee Prahlada over Holika.",
        "primary_regions": ["Nationwide", "Kathmandu Valley", "Terai"],
        "associated_places": ["Basantapur Dabali", "Patan Durbar Square", "Lakeside Pokhara"]
    },
    {
        "name": "Bisket Jatra",
        "lunar_month": "Chaitra - Baisakh (Nepali New Year)",
        "typical_gregorian_window": "Mid-April",
        "significance": "Ancient Newar chariot festival of Bhaktapur with dramatic tug-of-war pulling of Lord Bhairav's chariot and erection of the sacred lingam pole.",
        "primary_regions": ["Bhaktapur", "Thimi", "Kathmandu Valley"],
        "associated_places": ["Taumadhi Square", "Nyatapola Temple", "Bhairavnath Temple"]
    },
    {
        "name": "Rato Machhindranath Jatra (Boto Jatra)",
        "lunar_month": "Baisakh - Jestha",
        "typical_gregorian_window": "April - June",
        "significance": "Longest chariot festival in Nepal; pulling of the 60-foot chariot of Avalokiteshvara across Patan.",
        "primary_regions": ["Patan", "Jawalakhel", "Bungamati"],
        "associated_places": ["Rato Machhindranath Temple", "Sundari Chowk", "Jawalakhel Ground"]
    },
    {
        "name": "Indra Jatra (Yenya)",
        "lunar_month": "Bhadra Shukla Dwadashi",
        "typical_gregorian_window": "September",
        "significance": "Eight-day festival honoring Indra and the Living Goddess Kumari; masked dances in Hanuman Dhoka.",
        "primary_regions": ["Kathmandu Durbar Square", "Basantapur"],
        "associated_places": ["Kumari Ghar", "Hanuman Dhoka", "Kal Bhairav"]
    },
    {
        "name": "Buddha Jayanti",
        "lunar_month": "Baisakh Purnima",
        "typical_gregorian_window": "May",
        "significance": "Full moon celebrating the birth, enlightenment, and Mahaparinirvana of Gautama Buddha.",
        "primary_regions": ["Lumbini", "Boudhanath", "Swayambhunath"],
        "associated_places": ["Maya Devi Temple", "Boudhanath Stupa", "Swayambhunath Stupa"]
    },
    {
        "name": "Maha Shivaratri",
        "lunar_month": "Magha - Phalguna Krishna Chaturdashi",
        "typical_gregorian_window": "February - March",
        "significance": "Night of Lord Shiva drawing over one million pilgrims and sadhus to Pashupatinath.",
        "primary_regions": ["Kathmandu Valley", "Pashupatinath"],
        "associated_places": ["Pashupatinath Temple Complex", "Guhyeshwari", "Kirateshwar Mahadev"]
    },
    {
        "name": "Teej (Haritalika Teej)",
        "lunar_month": "Bhadra Shukla Tritiya",
        "typical_gregorian_window": "August - September",
        "significance": "Women's festival with fasting for marital bliss, devotional songs and dances at Shiva shrines.",
        "primary_regions": ["Nationwide", "Pashupatinath"],
        "associated_places": ["Pashupatinath Temple Complex", "Gokarneshwor Mahadev"]
    },
    {
        "name": "Janai Purnima & Rakshabandhan",
        "lunar_month": "Shrawan Purnima",
        "typical_gregorian_window": "August",
        "significance": "Sacred thread renewal and high-altitude pilgrimage to holy glacial lakes like Gosaikunda.",
        "primary_regions": ["Gosaikunda", "Patan", "Pashupatinath"],
        "associated_places": ["Gosaikunda Lake", "Kumbheshwar Temple", "Pashupatinath"]
    },
    {
        "name": "Lhosar (Sonam, Gyalpo, Tamu Lhosar)",
        "lunar_month": "Tibetan Lunar 1st Month",
        "typical_gregorian_window": "January - March",
        "significance": "Tibetan and Himalayan Buddhist New Year celebrated by Sherpa, Tamang, and Gurung communities.",
        "primary_regions": ["Solukhumbu", "Kathmandu", "Pokhara", "Manang"],
        "associated_places": ["Boudhanath Stupa", "Tengboche Monastery", "Kopan Monastery"]
    },
    {
        "name": "Mani Rimdu",
        "lunar_month": "Tibetan 9th Lunar Month",
        "typical_gregorian_window": "October - November",
        "significance": "Nineteen-day Sherpa Buddhist monastic festival at Tengboche and Chiwong monasteries.",
        "primary_regions": ["Khumbu", "Solukhumbu"],
        "associated_places": ["Tengboche Monastery", "Chiwong Monastery", "Thame Monastery"]
    }
]

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def get_seed_data(filename: str, fallback_data: list) -> list:
    """Load JSON from seed file if present; otherwise return authoritative reference fallback."""
    target_path = SEED_DIR / filename
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
    return fallback_data


# -----------------------------------------------------------------------------
# Pytest Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture(scope="session")
def trails_data() -> List[Dict[str, Any]]:
    """Fixture providing trekking trails seed data."""
    return get_seed_data("trekking_trails.json", REFERENCE_TRAILS)


@pytest.fixture(scope="session")
def waypoints_data() -> List[Dict[str, Any]]:
    """Fixture providing waypoints seed data."""
    return get_seed_data("waypoints.json", REFERENCE_WAYPOINTS)


@pytest.fixture(scope="session")
def heritage_data() -> List[Dict[str, Any]]:
    """Fixture providing cultural heritage seed data."""
    return get_seed_data("cultural_heritage.json", REFERENCE_HERITAGE)


@pytest.fixture(scope="session")
def festivals_data() -> List[Dict[str, Any]]:
    """Fixture providing festivals seed data."""
    return get_seed_data("festivals.json", REFERENCE_FESTIVALS)


@pytest.fixture(scope="function")
def db_session(heritage_data):
    """Provide clean database session pre-populated with reference places."""
    session = TestSessionLocal()
    
    # Populate places table if empty
    if session.query(Place).count() == 0:
        for item in heritage_data:
            lat = item.get("latitude")
            lon = item.get("longitude")
            centroid_wkt = f"POINT({lon} {lat})" if lat is not None and lon is not None else None
            p = Place(
                id=uuid.uuid4(),
                name=item["name"],
                category=item.get("category", "Heritage"),
                group=item.get("group", "Historic"),
                centroid=centroid_wkt,
                bbox_min_lat=lat,
                bbox_max_lat=lat,
                bbox_min_lon=lon,
                bbox_max_lon=lon,
                raw_tags={"entry_fees": item.get("entry_fees"), "guidelines": item.get("guidelines")},
                popularity=85.0,
                rating=4.8,
                is_hidden_gem=False
            )
            session.add(p)
        session.commit()
    
    yield session
    session.close()
