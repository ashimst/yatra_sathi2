# Project: YatraSathi Nepal Tourism, Trekking & Cultural Heritage Data Integration

## Architecture
YatraSathi is a Nepal travel and trekking exploration platform.
- **Backend Architecture**: FastAPI backend (`backend/app/main.py`), SQLAlchemy ORM (`backend/app/models/`), PostgreSQL 18 with PostGIS (`places.centroid` WKT `POINT(lon lat)`) and pgvector (`Vector(384)` embeddings), and SQLite fallback database (`yatra_sathi.db`).
- **Data Flow**:
  1. Open Data Sources (Offline OSM PBF `data/raw/nepal-260717.osm.pbf`, curated datasets, survey catalogs)
  2. Normalization & Deduplication Pipeline (`etl/`, seed generators)
  3. Persistent Seed Files (`backend/data/seeds/*.json`)
  4. Database Seeding Routines (Idempotent seeders for PostgreSQL `yatra_sathi` and SQLite `yatra_sathi.db`)
  5. FastAPI Service & Endpoints (`/places`, `/places/search`, `/places/nearby`, `/trail-watch`, `/itineraries`)
- **Shared Interfaces**:
  - `backend.app.models.place.Place`
  - `backend.app.models.trail_watch.TrailReport`, `TrailSteward`
  - `backend.app.models.itinerary.Itinerary`

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Trekking Trails & Passes | 10 major trekking routes (Annapurna Circuit/Sanctuary, EBC, Gokyo, Manaslu, Langtang, Mustang, Mardi Himal, Kanchenjunga) with elevation profiles, durations, difficulty, coordinates, and permit specifications | M1 | Survey (trails_survey_report.md) |
| F2 | Waypoints, Teahouses & Settlements | High-altitude settlements, acclimatization rest hubs, mountain lodges, teahouses, and checkposts along trail corridors | M1 | Survey (trails_survey_report.md) |
| F3 | Emergency & Medical Infrastructure | 10 high-altitude medical posts/clinics (HRA Pheriche, Manang, Kunde, Machhermo) and 19 emergency evacuation helipads with coordinates and rescue metadata | M1 | Survey (trails_survey_report.md) |
| F4 | Kathmandu Valley Cultural Heritage | All 7 UNESCO Monument Zones + 8 peripheral historical sites with coordinates, histories, and sub-monuments | M2 | Survey (heritage_survey_report.md) |
| F5 | Regional Heritage (Pokhara, Lumbini, Remote) | Pokhara natural/cultural sites, Lumbini Sacred Garden + 6 Greater Circuit sites, and remote Himalayan monasteries (Khumbu, Mustang, Dolpo, Manang) | M2 | Survey (heritage_survey_report.md) |
| F6 | Entry Fees, Regulations & Travel Guidelines | Tiered entry fee matrix (Non-SAARC, SAARC, Nepali), conservation area permits, restricted area permits (RAP), dress codes, photography and sacred site guidelines | M2 | Survey (heritage_survey_report.md) |
| F7 | Major Nepali Festivals Calendar | 13 major festivals with lunar calendar months, Gregorian windows, regional associations, and cultural rituals | M2 | Survey (heritage_survey_report.md) |
| F8 | Data Normalization & Nepal Bounding Integrity | 100% of location coordinates strictly validated within Nepal bounds (26.0°N–30.5°N, 80.0°E–88.5°E), multi-pass deduplication, schema alignment to backend models | M1, M2 | ORIGINAL_REQUEST §R2 |
| F9 | Persistent Seed Dataset Generation | Structured JSON seed files generated in `backend/data/seeds/` (`trekking_trails.json`, `waypoints.json`, `cultural_heritage.json`, `festivals.json`) for reproducible seeding | M1, M2 | ORIGINAL_REQUEST §R3.1 |
| F10 | Dual Database Seeding Engine | Idempotent seeder populating both active PostgreSQL (`yatra_sathi`) and SQLite (`yatra_sathi.db`) matching seed files with zero schema errors | M3 | ORIGINAL_REQUEST §R3.2 |
| F11 | End-to-End Test Suite & Endpoint Verification | Opaque-box 4-tier test suite verifying schema validation, coordinate integrity, deduplication, seed files, DB consistency, and FastAPI HTTP endpoints | E2E, M4 | ORIGINAL_REQUEST §Acceptance Criteria |
| F12 | Adversarial Coverage Hardening | White-box stress testing and gap coverage for edge coordinates, extreme elevations, pricing anomalies, and search filters | M4 (Phase 2) | Project Pattern §Dual Track |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Trekking Trails & Waypoint Data Curation | Curate 10 trekking trails, passes, waypoints, teahouses, emergency helipads, and medical posts; normalize coordinates; generate `backend/data/seeds/trekking_trails.json` and `backend/data/seeds/waypoints.json` | none | DONE |
| M2 | Cultural Heritage, Fees & Festivals Curation | Curate Kathmandu Valley 7 UNESCO + periphery, Pokhara, Lumbini + circuit, Himalayan monasteries, fee matrix, guidelines, and 13 festivals; normalize; generate `backend/data/seeds/cultural_heritage.json` and `backend/data/seeds/festivals.json` | none | DONE |
| M3 | Database Seeding & Integration Engine | Build idempotent seeding script populating both SQLite (`yatra_sathi.db`) and PostgreSQL (`yatra_sathi`); verify 100% coordinate compliance and schema compatibility | M1, M2 | DONE |
| M4 | Final Milestone: E2E Test Pass & Adversarial Hardening | Pass 100% of E2E tests (Tiers 1–4 from E2E Testing Track) across all endpoints and data models; conduct Tier 5 adversarial coverage hardening | M3, E2E Track | DONE |
| E2E | E2E Testing Track | Independent opaque-box test harness and test cases (Tiers 1–4) covering all features F1–F11; publish `TEST_READY.md` | none | DONE |

## Interface Contracts
### Data Curators (M1, M2) ↔ Seed Files (`backend/data/seeds/`)
- `trekking_trails.json`: List of trail objects with:
  - `id`: string (slug)
  - `name`: string
  - `region`: string (`Annapurna`, `Everest`, `Langtang`, `Manaslu`, `Mustang`, `Kanchenjunga`, etc.)
  - `difficulty`: string (`Easy`, `Moderate`, `Challenging`, `Strenuous`)
  - `duration_days`: int
  - `max_elevation_m`: float
  - `pass_elevation_m`: float (optional)
  - `permits_required`: list[string]
  - `start_point`: dict(`name`, `latitude`, `longitude`)
  - `end_point`: dict(`name`, `latitude`, `longitude`)
  - `route_geometry_wkt`: string (LINESTRING) or list of coordinates
  - `key_waypoints`: list[string]
- `waypoints.json`: List of waypoint objects with:
  - `name`: string
  - `trail_id` or `region`: string
  - `category`: string (`Mountain Pass`, `Emergency Helipad`, `Medical Post`, `Checkpost`, `Guest House`, `Settlement`, `Acclimatization Hub`)
  - `latitude`: float (`26.0 <= lat <= 30.5`)
  - `longitude`: float (`80.0 <= lon <= 88.5`)
  - `elevation_m`: float
  - `details`: dict (emergency capabilities, radio freq, amenities, permit check rules)
- `cultural_heritage.json`: List of place objects conforming to `backend.app.models.Place`:
  - `name`: string
  - `region`: string (`Kathmandu Valley`, `Pokhara`, `Lumbini`, `Himalaya`, etc.)
  - `category`: string (`Religious Site`, `Monument`, `Museum`, `Historic Site`)
  - `group`: string (`Religious`, `Historic`, `Culture`, `Heritage`)
  - `latitude`: float (`26.0 <= lat <= 30.5`)
  - `longitude`: float (`80.0 <= lon <= 88.5`)
  - `description`: string
  - `entry_fees`: dict(`foreign_npr`, `saarc_npr`, `nepali_npr`, `currency`)
  - `guidelines`: dict(`dress_code`, `photography`, `shoes_prohibited`, `sanctum_restrictions`)
  - `best_seasons`: list[string]
- `festivals.json`: List of festival objects:
  - `name`: string
  - `lunar_month`: string
  - `typical_gregorian_window`: string
  - `significance`: string
  - `primary_regions`: list[string]
  - `associated_places`: list[string]

### Seed Files ↔ Seeder Script (M3) ↔ Databases
- Script: `backend/scripts/seed_nepal_data.py` (or executable CLI)
- Inputs: `backend/data/seeds/*.json`
- Targets:
  1. `yatra_sathi.db` (SQLite): Created/updated with `places`, `trails`, `waypoints`, `festivals` tables matching model schemas.
  2. PostgreSQL `yatra_sathi`: Populated using SQLAlchemy session, generating PostGIS `centroid` WKT and pgvector embeddings.
- Invariants:
  - Zero duplicate records by `(name, round(lat, 4), round(lon, 4))`.
  - 100% coordinates within `[26.0, 30.5]` N and `[80.0, 88.5]` E.
  - Idempotent execution (running seeder multiple times does not create duplicates).

## Code Layout
- `backend/data/seeds/`:
  - `trekking_trails.json`
  - `waypoints.json`
  - `cultural_heritage.json`
  - `festivals.json`
- `backend/scripts/`:
  - `seed_nepal_data.py`: Main database seeding routine for PostgreSQL and SQLite.
  - `verify_data_integrity.py`: Automated programmatic validation script checking bounds, deduplication, schema, and DB counts.
- `backend/app/models/`:
  - `place.py`: Existing Place model.
  - `trail_watch.py`: Existing Trail Watch models.
  - `itinerary.py`: Existing Itinerary models.
- `tests/e2e/`:
  - `test_data_integrity.py`: Automated tests for coordinate bounds, deduplication, schema.
  - `test_database_seeds.py`: Tests verifying SQLite `yatra_sathi.db` and PostgreSQL consistency.
  - `test_api_endpoints.py`: Tests calling FastAPI endpoints `/places`, `/places/search`, `/places/nearby`, `/trail-watch`.
