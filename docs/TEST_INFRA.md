# YatraSathi E2E Testing Infrastructure & Architectural Specification

## Executive Overview
The **YatraSathi End-to-End (E2E) Test Suite** is an opaque-box test framework engineered to validate Nepal destination data integrity, trekking trails, waypoint infrastructure, emergency response networks, cultural heritage sites, festival calendars, tiered fee calculations, and FastAPI backend endpoints without coupling to internal implementation quirks.

The test infrastructure enforces a strict **4-Tier Test Design Methodology** designed specifically for the geographical, logistical, and cultural topology of Nepal.

---

## Directory & Package Structure

```
tests/
├── __init__.py
└── e2e/
    ├── __init__.py
    ├── conftest.py                     # Global fixtures, SQLite compilers (JSONB/pgvector), seed loaders
    ├── test_runner.py                  # Standalone automated test runner script
    ├── test_data_integrity.py          # Coordinate bounding (100% in Nepal), deduplication, seed JSON schema
    ├── test_database_seeds.py          # SQLite yatra_sathi.db and PostgreSQL seed population verification
    ├── test_tier1_feature_coverage.py  # Tier 1: Isolated feature coverage (F1–F11, >=5 test cases/feature)
    ├── test_tier2_boundary_corner.py   # Tier 2: Nepal borders, elevation bounds, missing fields, fuzzing
    ├── test_tier3_cross_feature.py     # Tier 3: Pairwise cross-feature interactions & emergency triads
    └── test_tier4_user_journeys.py     # Tier 4: Real-world multi-day expeditions and pilgrimage circuits
```

---

## 4-Tier Opaque-Box Test Hierarchy

### Tier 1: Isolated Feature Coverage (`test_tier1_feature_coverage.py`)
Provides >=5 isolated opaque-box test cases for every functional capability defined in `PROJECT.md` (Features F1 through F11):
- **Feature 1 (F1): Trekking Trails Catalog**: Trail inventory, elevation profiles, duration/difficulty ratings, permits, endpoints, route WKT geometry.
- **Feature 2 (F2): Trekking Waypoints**: Standardized waypoint categories (`Mountain Pass`, `Medical Post`, `Emergency Helipad`, `Checkpost`, `Settlement`), coordinates, and elevations.
- **Feature 3 (F3): Emergency Infrastructure**: High-altitude clinics (HRA Pheriche, HRA Manang, Kunde), emergency helipads, medical facilities (Gamow bags, oxygen).
- **Feature 4 (F4): Kathmandu Valley UNESCO Heritage**: 7 World Heritage monument zones (Pashupatinath, Boudhanath, Swayambhunath, Kathmandu Durbar, Patan Durbar, Bhaktapur Durbar, Changu Narayan) and peripheral sites.
- **Feature 5 (F5): Regional Heritage**: Pokhara cultural/natural sites, Lumbini Sacred Garden circuit, remote Himalayan monasteries (Tengboche, Chiwong, Shey Gompa).
- **Feature 6 (F6): Tiered Entry Fees & Cultural Guidelines**: Multi-tier fee matrix (Foreign / SAARC / Nepali), dress code restrictions, footwear rules, and photography bans.
- **Feature 7 (F7): Living Cultural Festival Calendar**: Lunar calendar mappings (Bikram Sambat / Tibetan lunar), Gregorian seasonal windows, and regional rituals.
- **Feature 8 (F8): Data Normalization & Nepal Bounding Integrity**: Micro-coordinate types, WKT centroid format compliance, and strict bounding box limits.
- **Feature 9 (F9): Persistent Seed Dataset Generation**: Schema verification for JSON seed files (`trekking_trails.json`, `waypoints.json`, `cultural_heritage.json`, `festivals.json`).
- **Feature 10 (F10): Dual Database Seeding Engine**: Schema compatibility with PostgreSQL and SQLite dialects, UUID primary keys, and idempotent seed ingestion.
- **Feature 11 (F11): End-to-End API Endpoints**: Response verification for `/places`, `/places/search`, `/places/geocode`, `/trail-watch/reports`, `/trail-watch/stats`, and `/health`.

### Tier 2: Boundary & Corner Cases (`test_tier2_boundary_corner.py`)
Stresses boundary limits, error resilience, and edge conditions:
- **Nepal Border Coords**: Border limits (26.0°N, 30.5°N, 80.0°E, 88.5°E) vs strictly external coordinates (25.99°N, 30.51°N, 79.99°E, 88.51°E rejected).
- **Elevation Bounds**: Sea level and negative altitudes rejected (minimum 60m Kechana Kawal); summit elevations capped at Mt. Everest (8848.86m); pass elevations verified (3,000m–6,000m); helipad density ceilings (<6,000m).
- **Data Completeness**: Non-null checks for mandatory attributes, valid nested dictionaries for entry fees and guidelines.
- **Deduplication**: Zero exact name+coordinate duplicates; micro-coordinate proximity validation (<1m coincidence rejection).
- **Adversarial Query Inputs**: Empty queries `q=""`, whitespace queries `q="   "`, Devanagari script queries (`"काठमाडौँ"`), extreme limits (`limit=1`, `limit=200`), and special character escaping (`' " < > &`).

### Tier 3: Cross-Feature Combinations (`test_tier3_cross_feature.py`)
Pairwise cross-module interactions:
- **Trail-to-Waypoint Proximity**: Validates that all trailheads sit within 50 km of catalog settlements/waypoints and trail pass elevations align with catalog mountain passes.
- **Emergency Evacuation Triad**: Verifies that high-altitude trekking corridors (Everest, Annapurna) possess the critical triad: Trail + Nearby Helipad + Medical Clinic within operational flight radius.
- **Cultural Itineraries & Festive Fee Computation**: Pairs cultural heritage visits with active festival windows (e.g. Dashain, Buddha Jayanti, Mani Rimdu) and computes aggregate tiered family admission costs.
- **Trail Watch Hazard Triage**: Verifies automated guild dispatch (Plastic Waste -> SPCC & ACAP Eco-Clean Guild; Landslides -> ACAP Field Wardens; Heritage Shrines -> Heritage Trust Guild).

### Tier 4: Real-World Scenarios (`test_tier4_user_journeys.py`)
Full end-to-end user journeys:
- **14-Day Everest Base Camp Trek**: Planning regulatory permits (Sagarmatha NP + Khumbu Card), acclimatization rest milestones (Namche Bazaar 3,440m, Dingboche 4,410m), Kala Patthar viewpoint (5,164m–5,545m), and emergency rescue link.
- **Kathmandu Valley 7 UNESCO Zones & Lumbini**: Complete pilgrimage circuit with multi-tier fee budgeting (Foreign vs SAARC vs Nepali) and cultural guideline compliance (shoe/leather prohibitions, photography limits).
- **Annapurna Circuit Crossing**: Full expedition traversing Besisahar to Muktinath via Thorong La Pass (5,416m), permit inspection, field hazard reporting, and database itinerary persistence.

### Data Integrity & Database Seed Suites
- `test_data_integrity.py`: 100% coordinate compliance in Nepal bounds, zero name+coord duplicates across all 4 seed datasets.
- `test_database_seeds.py`: Direct SQLite verification of `yatra_sathi.db` (validating >=1,000 places, >=15 trails, >=1,000 waypoints, >=12 festivals, and active trail stewards).

---

## Environmental Isolation & Sandboxed Execution

### Dual-Database Dialect Abstraction
To support testing in constrained environments without live PostgreSQL/PostGIS daemons:
1. **JSONB Compilation**: In SQLite mode, PostgreSQL `JSONB` columns automatically compile to SQLite `JSON` text.
2. **pgvector Compilation**: `pgvector.sqlalchemy.Vector` compiles to SQLite `BLOB`.
3. **Synchronous Coroutine Execution (`_run_coro`)**: In Windows sandboxed environments where loopback socket creation (AnyIO/Proactor loop) is restricted by OS security policy, FastAPI router endpoint coroutines are executed via direct generator iteration (`coro.send(None)`), delivering sub-millisecond execution times without network socket binding.

---

## Test Execution Commands

### Run Full Test Suite via Pytest
```powershell
python -m pytest tests/e2e/ -v
```

### Run Standalone E2E Test Runner
```powershell
python tests/e2e/test_runner.py
```

### Run Individual Tiers
```powershell
# Tier 1: Feature Coverage (F1-F11)
python -m pytest tests/e2e/test_tier1_feature_coverage.py -v

# Tier 2: Boundary & Corner Cases
python -m pytest tests/e2e/test_tier2_boundary_corner.py -v

# Tier 3: Cross-Feature Combinations
python -m pytest tests/e2e/test_tier3_cross_feature.py -v

# Tier 4: Real-World Application Scenarios
python -m pytest tests/e2e/test_tier4_user_journeys.py -v

# Data Integrity & Database Seeds
python -m pytest tests/e2e/test_data_integrity.py tests/e2e/test_database_seeds.py -v
```
