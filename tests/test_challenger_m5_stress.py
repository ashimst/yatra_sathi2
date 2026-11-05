"""
Empirical Integration Stress Test Suite for Milestone 5.
=========================================================
Adversarial & Empirical verification of core Yatra Sathi workflows on SQLite (yatra_sathi.db):
1. Place Photo Contribution Workflow (POST /places/{id}/photos, is_cover=True, DB update, static 200, GET /places/{id}/photos)
2. Spatial Engine Stress on SQLite (border coordinates, Himalayan elevation, zero radius, large radius, route buffers, zero PostGIS crashes)
3. Memory Creation & Deletion Lifecycle (Upload -> POST /memories -> GET /memories -> DELETE /memories/{id})
"""
import io
import math
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, List

import pytest
from fastapi import UploadFile, HTTPException
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Enforce SQLite yatra_sathi.db BEFORE any backend imports
SQLITE_DB_PATH = PROJECT_ROOT / "yatra_sathi.db"
SQLITE_DB_URL = f"sqlite:///{SQLITE_DB_PATH}"
os.environ["DATABASE_URL"] = SQLITE_DB_URL
os.environ["AI_ENABLED"] = "false"
os.environ["DEBUG"] = "false"

# SQLite compatibility compiler hooks
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"

try:
    from pgvector.sqlalchemy import Vector
    @compiles(Vector, "sqlite")
    def compile_vector_sqlite(type_, compiler, **kw):
        return "BLOB"
except ImportError:
    pass

from tests.auth_helpers import make_test_user
from backend.app.config.settings import settings
settings.DATABASE_URL = SQLITE_DB_URL

from backend.app.db.database import Base, SessionLocal, engine, init_db
from backend.app.models.place import Place
from backend.app.models.place_photo import PlacePhoto
from backend.app.models.memory import Memory
from backend.app.services.place_service import place_service
from backend.app.services.recommendation_service import recommendation_service
from backend.app.services.upload_service import upload_service
from backend.app.api.places import upload_place_photo, get_place_photos
from backend.app.api.uploads import upload_photo
from backend.app.api.memories import create_memory, list_memories, delete_memory, CreateMemoryRequest


def _run_coro(coro):
    """Execute coroutine synchronously matching repository test conventions."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    except Exception as ex:
        raise ex


class MockUploadFile(UploadFile):
    """Custom UploadFile providing deterministic binary reading."""
    def __init__(self, file: io.BytesIO, filename: str = "image.bin", content_type: str = "application/octet-stream"):
        super().__init__(file=file, filename=filename, headers={"content-type": content_type})

    async def read(self, size: int = -1) -> bytes:
        if hasattr(self.file, "seek"):
            self.file.seek(0)
        return self.file.read()


# Valid BMP payload (1x1 pixel 24bpp)
VALID_BMP_BYTES = (
    b"BM\x3e\x00\x00\x00\x00\x00\x00\x00\x36\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00"
    b"\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x08\x00\x00\x00\x13\x0b\x00\x00"
    b"\x13\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00"
)

# Valid JPEG payload
VALID_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    + b"\x00" * 200
    + b"\xff\xd9"
)


# =============================================================================
# 1. Place Photo Contribution Workflow Stress Tests
# =============================================================================
class TestPlacePhotoContributionWorkflow:
    """Empirical verification of Place Photo upload, DB persistence, cover update, and static serving."""

    def test_place_photo_contribution_full_lifecycle(self):
        """
        Select a real place from yatra_sathi.db, upload photo with is_cover=True,
        verify PlacePhoto DB record, verify place.image_url updated,
        verify static file retrieval returns 200 OK with identical payload,
        and fetch GET /places/{id}/photos to verify listing.
        """
        init_db()
        db = SessionLocal()
        
        # 1. Select a place from yatra_sathi.db
        place = db.query(Place).filter(Place.name.isnot(None)).first()
        assert place is not None, "yatra_sathi.db places table is empty!"
        place_id = str(place.id)
        original_image_url = place.image_url
        original_gallery = list(place.gallery or [])
        print(f"\n[STRESS TEST] Selected Place: {place.name} (ID: {place_id})")

        # 2. Upload valid photo via POST /places/{id}/photos with is_cover=True
        caption_text = f"Empirical Cover Contribution - {uuid.uuid4().hex[:8]}"
        file_obj = io.BytesIO(VALID_BMP_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="cover_himalaya.bmp", content_type="image/bmp")

        response_data = _run_coro(upload_place_photo(
            id=place_id,
            file=upload_file,
            caption=caption_text,
            is_cover=True,
            db=db, user=make_test_user(db, admin=True)))

        # Assert response schema
        assert response_data["place_id"] == place_id
        assert response_data["caption"] == caption_text
        assert response_data["is_cover"] is True
        assert response_data["image_url"].startswith("/uploads/places/")
        photo_id = response_data["id"]
        saved_url = response_data["image_url"]
        print(f"[STRESS TEST] Uploaded Photo ID: {photo_id}, URL: {saved_url}")

        # 3. Verify PlacePhoto DB record created
        photo_record = db.query(PlacePhoto).filter(PlacePhoto.id == uuid.UUID(photo_id)).first()
        assert photo_record is not None, "PlacePhoto record not found in database!"
        assert str(photo_record.place_id) == place_id
        assert photo_record.caption == caption_text
        assert photo_record.is_cover is True
        assert photo_record.image_url == saved_url

        # 4. Verify place.image_url updated and added to gallery
        db.refresh(place)
        assert place.image_url == saved_url, f"Expected place.image_url {saved_url}, got {place.image_url}"
        assert saved_url in place.gallery, f"Expected {saved_url} in gallery {place.gallery}"

        # 5. Verify static file HTTP retrieval returns 200 OK with identical content
        static_app = StaticFiles(directory=str(settings.UPLOAD_DIR))
        subpath = saved_url.replace("/uploads/", "")
        full_path, stat_result = static_app.lookup_path(subpath)
        assert full_path is not None, f"StaticFiles could not resolve subpath {subpath}"
        assert stat_result is not None
        assert stat_result.st_size == len(VALID_BMP_BYTES)

        file_resp = FileResponse(full_path, stat_result=stat_result)
        assert file_resp.status_code == 200
        assert Path(full_path).read_bytes() == VALID_BMP_BYTES
        print(f"[STRESS TEST] Static file verified: {full_path} (HTTP 200 OK, {stat_result.st_size} bytes)")

        # 6. Fetch GET /places/{id}/photos and verify returned list
        list_res = _run_coro(get_place_photos(id=place_id, db=db))
        assert "photos" in list_res
        assert isinstance(list_res["photos"], list)
        matching_photos = [p for p in list_res["photos"] if p["id"] == photo_id]
        assert len(matching_photos) == 1, f"Photo {photo_id} not found in photos list!"
        assert matching_photos[0]["is_cover"] is True
        assert matching_photos[0]["image_url"] == saved_url

        # Cleanup: Remove created photo to restore state
        db.delete(photo_record)
        place.image_url = original_image_url
        place.gallery = original_gallery
        db.commit()
        db.close()
        
        # Remove created file from disk
        try:
            if Path(full_path).exists():
                Path(full_path).unlink()
        except Exception:
            pass


# =============================================================================
# 2. Spatial Engine Stress on SQLite
# =============================================================================
class TestSpatialEngineStressSQLite:
    """Stress testing place_service and recommendation_service on SQLite without PostGIS."""

    @pytest.fixture(autouse=True, scope="class")
    def _corridor_places(self):
        """
        Seed one place on each tested corridor so these tests don't depend on
        whatever data happens to be in the bound database file.
        """
        db = SessionLocal()
        seeded = [
            Place(id=uuid.uuid4(), name="Test Mugling Viewpoint", category="Viewpoint",
                  centroid="POINT(84.4525 27.5341)", popularity=5.0, rating=4.0),
            Place(id=uuid.uuid4(), name="Test Namche Bazaar Lodge", category="Hotel",
                  centroid="POINT(86.7090 27.8051)", popularity=5.0, rating=4.0),
        ]
        db.add_all(seeded)
        db.commit()
        ids = [p.id for p in seeded]
        yield
        db.query(Place).filter(Place.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        db.close()

    @pytest.mark.parametrize("lat,lon,label", [
        (30.4, 81.5, "Extreme North Border (Humla / Tibet border)"),
        (26.1, 87.5, "Extreme South Border (Morang / Bihar border)"),
        (29.5, 80.1, "Extreme West Border (Mahakali / Uttarakhand border)"),
        (27.5, 88.3, "Extreme East Border (Taplejung / Sikkim border)"),
        (28.004, 86.856, "High Elevation Everest Base Camp (5364m)"),
        (28.530, 83.878, "High Elevation Annapurna Base Camp (4130m)"),
        (28.7937, 83.9355, "High Alpine Thorong La Pass (5416m)"),
        (27.7025, 88.1475, "Kangchenjunga Wilderness Border (5143m)")
    ])
    def test_border_and_himalayan_coordinates_nearby_places(self, lat, lon, label):
        """Stress get_nearby_places with extreme coordinates and assert zero PostGIS crashes."""
        res = place_service.get_nearby_places(lat=lat, lng=lon, radius=100.0, limit=20)
        assert isinstance(res, dict)
        assert "places" in res
        assert "count" in res
        assert "total_count" in res
        assert isinstance(res["places"], list)
        for p in res["places"]:
            assert "distance_km" in p
            assert p["distance_km"] <= 100.0
        print(f"\n[SPATIAL STRESS] {label} ({lat}, {lon}) -> Found: {res['count']} / {res['total_count']}")

    def test_zero_radius_nearby_places(self):
        """Verify zero radius (0.0 km) computes without division by zero or PostGIS crash."""
        res = place_service.get_nearby_places(lat=27.7172, lng=85.3240, radius=0.0, limit=10)
        assert isinstance(res, dict)
        assert res["count"] == 0
        assert res["places"] == []
        print(f"\n[SPATIAL STRESS] Zero radius test passed: {res}")

    def test_large_radius_nearby_places(self):
        """Verify large radius (100.0 km and 250.0 km) returns ordered places without SQL errors."""
        res_100 = place_service.get_nearby_places(lat=27.7172, lng=85.3240, radius=100.0, limit=50)
        assert isinstance(res_100, dict)
        assert res_100["count"] > 0
        # Check ascending distance order
        distances = [p["distance_km"] for p in res_100["places"]]
        assert distances == sorted(distances), "Results are not sorted by distance ascending!"

        res_250 = place_service.get_nearby_places(lat=28.0, lng=84.0, radius=250.0, limit=50)
        assert isinstance(res_250, dict)
        assert res_250["count"] > 0
        print(f"\n[SPATIAL STRESS] Large radius 100km count: {res_100['count']} (total: {res_100['total_count']}), 250km count: {res_250['count']} (total: {res_250['total_count']})")

    def test_route_buffer_kathmandu_to_pokhara_sqlite(self):
        """Stress _get_pois_in_route_buffer on SQLite for Kathmandu -> Pokhara corridor."""
        ktm_to_pkr_coords = [
            [85.324, 27.7172],   # Kathmandu
            [84.7, 27.9],        # Dhading / Trishuli corridor
            [84.4525, 27.5341],  # Mugling / Narayanghat junction
            [83.9856, 28.2096]   # Pokhara
        ]
        pois = recommendation_service._get_pois_in_route_buffer(
            route_coordinates=ktm_to_pkr_coords,
            buffer_km=15.0,
            origin_lat=27.7172,
            origin_lng=85.324,
            dest_lat=28.2096,
            dest_lng=83.9856,
            destination_buffer_km=25.0
        )
        assert isinstance(pois, list)
        assert len(pois) > 0, "Expected POIs along Kathmandu to Pokhara route buffer"
        for poi in pois:
            assert "_in_route_buffer" in poi or "_in_dest_buffer" in poi
        print(f"\n[SPATIAL STRESS] KTM to Pokhara POIs in route buffer: {len(pois)}")

    def test_route_buffer_lukla_to_ebc_sqlite(self):
        """Stress _get_pois_in_route_buffer on SQLite for high-altitude Lukla -> EBC route."""
        lukla_to_ebc_coords = [
            [86.7314, 27.6869],  # Lukla (2840m)
            [86.7247, 27.7719],  # Monjo
            [86.7090, 27.8051],  # Namche Bazaar (3440m)
            [86.7646, 27.8364],  # Tengboche (3860m)
            [86.8287, 27.8923],  # Dingboche (4410m)
            [86.8290, 27.9810],  # Gorak Shep (5140m)
            [86.8525, 28.0044]   # Everest Base Camp (5364m)
        ]
        pois = recommendation_service._get_pois_in_route_buffer(
            route_coordinates=lukla_to_ebc_coords,
            buffer_km=10.0,
            origin_lat=27.6869,
            origin_lng=86.7314,
            dest_lat=28.0044,
            dest_lng=86.8525,
            destination_buffer_km=15.0
        )
        assert isinstance(pois, list)
        assert len(pois) > 0, "Expected high altitude POIs along Lukla to EBC route buffer"
        print(f"\n[SPATIAL STRESS] Lukla to EBC POIs in route buffer: {len(pois)}")

    def test_recommendations_corridor_sqlite(self):
        """Verify place_service.get_recommendations runs cleanly on SQLite without PostGIS crashes."""
        res = place_service.get_recommendations(
            origin_lat=27.7172,
            origin_lng=85.3240,
            dest_lat=28.2096,
            dest_lng=83.9856,
            corridor_km=25.0,
            limit=15
        )
        assert isinstance(res, dict)
        assert "places" in res
        assert res["count"] > 0
        for p in res["places"]:
            assert "distance_to_route_km" in p
            assert p["distance_to_route_km"] <= 25.0
        print(f"\n[SPATIAL STRESS] Recommendations corridor count: {res['count']}")


# =============================================================================
# 3. Memory Creation & Deletion Lifecycle Stress Tests
# =============================================================================
class TestMemoryLifecycleStress:
    """Empirical verification of photo upload, memory creation, retrieval, and deletion lifecycle."""

    def test_memory_creation_default_header_attribute_error(self):
        """
        EMPIRICAL DEFECT RESOLUTION VERIFIED:
        In backend/app/api/memories.py, create_memory specifies:
          authorization: Optional[str] = Header(None)
        With isinstance(authorization, str) guard, calling create_memory with default
        Header(None) argument succeeds without raising AttributeError.
        """
        db = SessionLocal()
        mem_req = CreateMemoryRequest(
            place_name="Pashupatinath Temple",
            image_url="/uploads/memories/test.jpg"
        )
        res = _run_coro(create_memory(req=mem_req, db=db, user=make_test_user(db)))
        assert res["success"] is True
        assert res["memory"]["place_name"] == "Pashupatinath Temple"
        print(f"\n[DEFECT RESOLVED] Successfully created memory with default Header(None): {res['memory']['id']}")
        
        # Clean up created record
        created_id = uuid.UUID(res["memory"]["id"])
        db.query(Memory).filter(Memory.id == created_id).delete()
        db.commit()
        db.close()

    def test_memory_creation_and_deletion_lifecycle(self):
        """
        1. Upload photo to /uploads/photo (category: "memories")
        2. POST /memories linking returned relative URL (passing authorization=None)
        3. Verify memory is retrieved via GET /memories and in DB
        4. DELETE /memories/{id} and verify record deleted from DB and subsequent listings.
        """
        db = SessionLocal()

        # Step 1: Upload photo to /uploads/photo (category: "memories")
        file_obj = io.BytesIO(VALID_JPEG_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="test_memory_photo.jpg", content_type="image/jpeg")

        upload_res = _run_coro(upload_photo(
            file=upload_file,
            category="memories",
            caption="Sunrise over Everest"
        ))
        assert "url" in upload_res
        assert upload_res["url"].startswith("/uploads/memories/")
        assert upload_res["category"] == "memories"
        relative_url = upload_res["url"]
        print(f"\n[MEMORY LIFECYCLE] Uploaded memory photo URL: {relative_url}")

        # Step 2: Call POST /memories linking returned relative URL
        mem_req = CreateMemoryRequest(
            place_name="Pashupatinath Temple",
            latitude=27.7105,
            longitude=85.3487,
            image_url=relative_url,
            caption="Sacred evening aarti by Bagmati river"
        )
        owner = make_test_user(db)
        create_res = _run_coro(create_memory(req=mem_req, db=db, user=owner))
        assert create_res["success"] is True
        assert "memory" in create_res
        created_mem = create_res["memory"]
        memory_id = created_mem["id"]
        assert created_mem["place_name"] == "Pashupatinath Temple"
        assert created_mem["image_url"] == relative_url
        assert created_mem["ai_reflection"] is not None
        print(f"[MEMORY LIFECYCLE] Created memory ID: {memory_id}, Reflection: {created_mem['ai_reflection']}")

        # Step 3: Verify memory is retrieved via GET /memories
        list_res = _run_coro(list_memories(place_name=None, place_id=None, itinerary_id=None, mine=False, limit=50, user=None, db=db))
        assert "memories" in list_res
        assert isinstance(list_res["memories"], list)
        found_in_list = any(m["id"] == memory_id for m in list_res["memories"])
        assert found_in_list is True, f"Created memory ID {memory_id} not found in GET /memories response!"

        # Verify direct DB query in SQLite
        db_mem = db.query(Memory).filter(Memory.id == uuid.UUID(memory_id)).first()
        assert db_mem is not None, "Memory not persisted in SQLite database!"
        assert db_mem.place_name == "Pashupatinath Temple"
        assert db_mem.image_url == relative_url
        print(f"[MEMORY LIFECYCLE] Verified Memory in DB: ID={db_mem.id}")

        # Step 4: Call DELETE /memories/{id} and verify record deleted
        delete_res = _run_coro(delete_memory(memory_id=memory_id, user=owner, db=db))
        assert delete_res["success"] is True
        assert delete_res["deleted_id"] == memory_id
        print(f"[MEMORY LIFECYCLE] Deleted memory ID: {memory_id}")

        # Verify DB record is deleted
        db_after = db.query(Memory).filter(Memory.id == uuid.UUID(memory_id)).first()
        assert db_after is None, "Memory record still exists in DB after deletion!"

        # Verify GET /memories no longer returns deleted record
        list_after = _run_coro(list_memories(place_name=None, place_id=None, itinerary_id=None, mine=False, limit=50, user=None, db=db))
        assert not any(m["id"] == memory_id for m in list_after["memories"]), "Deleted memory still returned in GET /memories!"
        print(f"[MEMORY LIFECYCLE] Memory deletion confirmed: zero dangling references.")

        db.close()

        # Clean up uploaded physical file
        try:
            static_app = StaticFiles(directory=str(settings.UPLOAD_DIR))
            subpath = relative_url.replace("/uploads/", "")
            full_path, _ = static_app.lookup_path(subpath)
            if full_path and Path(full_path).exists():
                Path(full_path).unlink()
        except Exception:
            pass


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING CHALLENGER EMPIRICAL INTEGRATION STRESS TEST SUITE")
    print("=" * 80)
    sys.exit(pytest.main(["-v", "-s", "--tb=short", str(Path(__file__).resolve())]))
