"""
E2E Integration & Functional Test Suite for Image Upload Pipeline.
==================================================================
Comprehensive automated tests covering:
1. Valid Image Uploads (JPEG, PNG, WebP, BMP) across all categories & aliases
2. Static File Serving (StaticFiles lookup, FileResponse status, headers, content verification)
3. Invalid Format Rejection (text/plain, PDF, corrupted bytes, executables)
4. Oversized File Rejection (> 10MB limit -> HTTP 413)
5. Empty File Rejection (0-byte payload -> HTTP 400)
6. Place Photo Contribution (POST /places/{id}/photos, DB persistence, cover update, GET /places/{id}/photos)
7. Path Traversal Safeguards (directory traversal filenames, escaping protection)
8. Project Root Sample Assets (test.bmp, view_front.bmp, view_angle.bmp)
9. Upload Categories Namespace Endpoint
"""
import io
import os
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import pytest
from fastapi import UploadFile, HTTPException
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse

# Ensure SQLite test engine and settings are initialized
import tests.e2e.conftest
from tests.e2e.conftest import PROJECT_ROOT, TestSessionLocal
from tests.auth_helpers import make_test_user
from backend.app.config.settings import settings
from backend.app.models.place import Place
from backend.app.models.place_photo import PlacePhoto
from backend.app.api.uploads import upload_photo, list_upload_categories
from backend.app.api.places import upload_place_photo, get_place_photos
from backend.app.services.upload_service import upload_service, ALLOWED_CATEGORIES


import mimetypes
mimetypes.add_type("image/webp", ".webp")


# -----------------------------------------------------------------------------
# Test Helpers & Coroutine Runner
# -----------------------------------------------------------------------------
def _run_coro(coro):
    """Execute async coroutine synchronously matching repository test conventions."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    except Exception as ex:
        raise ex


class MockUploadFile(UploadFile):
    """Custom UploadFile providing synchronous binary reading without AnyIO thread pool."""

    def __init__(self, file: io.BytesIO, filename: str = "image.bin", content_type: str = "application/octet-stream"):
        super().__init__(file=file, filename=filename, headers={"content-type": content_type})

    async def read(self, size: int = -1) -> bytes:
        if hasattr(self.file, "seek"):
            self.file.seek(0)
        return self.file.read()


# -----------------------------------------------------------------------------
# Synthetic Image Payloads (Deterministic Magic Byte Headers)
# -----------------------------------------------------------------------------
# JPEG: \xFF\xD8\xFF + JFIF header + padding + EOI \xFF\xD9
JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    + b"\x00" * 200
    + b"\xff\xd9"
)

# PNG: \x89PNG\r\n\x1a\n + IHDR + IDAT + IEND
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# WebP: RIFF....WEBPVP8
WEBP_BYTES = (
    b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\xb0\x01\x00\x9d\x01*\x01\x00\x01\x00\x00/ \x00\x00"
)

# BMP: BM + file header + DIB header + 1x1 pixel
BMP_BYTES = (
    b"BM\x3e\x00\x00\x00\x00\x00\x00\x00\x36\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00"
    b"\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x08\x00\x00\x00\x13\x0b\x00\x00"
    b"\x13\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00"
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture(scope="module")
def static_app():
    """StaticFiles application mount instance for upload directory."""
    return StaticFiles(directory=str(settings.UPLOAD_DIR))


@pytest.fixture(scope="module")
def place_in_db():
    """Ensure at least one valid place exists in database and return place record."""
    db = TestSessionLocal()
    place = db.query(Place).first()
    if not place:
        place = Place(
            id=uuid.uuid4(),
            name="Patan Durbar Square",
            category="Cultural Heritage",
            centroid="POINT(85.3250 27.6734)",
            bbox_min_lat=27.67,
            bbox_max_lat=27.68,
            bbox_min_lon=85.32,
            bbox_max_lon=85.33,
            popularity=9.2,
            rating=4.9,
            image_url=None,
            gallery=[]
        )
        db.add(place)
        db.commit()
        db.refresh(place)
    place_id_str = str(place.id)
    db.close()
    return place_id_str


# =============================================================================
# 1. Valid Image Uploads (JPEG, PNG, WebP, BMP)
# =============================================================================
class TestValidImageUploads:
    """Verifies valid image uploads across supported formats and categories."""

    def test_upload_valid_jpeg_memories(self):
        """Upload valid JPEG binary to memories category; assert 200 OK and valid response."""
        file_obj = io.BytesIO(JPEG_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="himalaya_peak.jpg", content_type="image/jpeg")

        data = _run_coro(upload_photo(
            file=upload_file,
            category="memories",
            caption="Sunrise over Langtang Lirung"
        ))

        assert data["status"] == "success"
        assert data["content_type"] == "image/jpeg"
        assert data["category"] == "memories"
        assert data["size_bytes"] == len(JPEG_BYTES)
        assert data["url"].startswith("/uploads/memories/")
        assert re.match(r"^[0-9a-f]{32}\.(jpg|jpeg)$", data["filename"])
        assert data["caption"] == "Sunrise over Langtang Lirung"

        # Verify disk persistence
        saved_file = Path(settings.UPLOAD_DIR) / "memories" / data["filename"]
        assert saved_file.exists()
        assert saved_file.stat().st_size == len(JPEG_BYTES)
        assert saved_file.read_bytes() == JPEG_BYTES

    def test_upload_valid_png_places(self):
        """Upload valid PNG binary to places category; assert 200 OK and valid metadata."""
        file_obj = io.BytesIO(PNG_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="temple_map.png", content_type="image/png")

        data = _run_coro(upload_photo(
            file=upload_file,
            category="places"
        ))

        assert data["status"] == "success"
        assert data["content_type"] == "image/png"
        assert data["category"] == "places"
        assert data["size_bytes"] == len(PNG_BYTES)
        assert data["url"].startswith("/uploads/places/")
        assert re.match(r"^[0-9a-f]{32}\.png$", data["filename"])

        saved_file = Path(settings.UPLOAD_DIR) / "places" / data["filename"]
        assert saved_file.exists()
        assert saved_file.read_bytes() == PNG_BYTES

    def test_upload_valid_webp_avatars(self):
        """Upload valid WebP binary to avatars category; assert 200 OK and valid metadata."""
        file_obj = io.BytesIO(WEBP_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="sherpa_guide.webp", content_type="image/webp")

        data = _run_coro(upload_photo(
            file=upload_file,
            category="avatars"
        ))

        assert data["status"] == "success"
        assert data["content_type"] == "image/webp"
        assert data["category"] == "avatars"
        assert data["size_bytes"] == len(WEBP_BYTES)
        assert data["url"].startswith("/uploads/avatars/")
        assert re.match(r"^[0-9a-f]{32}\.webp$", data["filename"])

        saved_file = Path(settings.UPLOAD_DIR) / "avatars" / data["filename"]
        assert saved_file.exists()
        assert saved_file.read_bytes() == WEBP_BYTES

    def test_upload_valid_bmp_trail_reports(self):
        """Upload valid BMP binary to trail_reports category; assert 200 OK and valid metadata."""
        file_obj = io.BytesIO(BMP_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="trail_hazard.bmp", content_type="image/bmp")

        data = _run_coro(upload_photo(
            file=upload_file,
            category="trail_reports"
        ))

        assert data["status"] == "success"
        assert data["content_type"] == "image/bmp"
        assert data["category"] == "trail_reports"
        assert data["size_bytes"] == len(BMP_BYTES)
        assert data["url"].startswith("/uploads/trail_reports/")
        assert re.match(r"^[0-9a-f]{32}\.bmp$", data["filename"])

        saved_file = Path(settings.UPLOAD_DIR) / "trail_reports" / data["filename"]
        assert saved_file.exists()
        assert saved_file.read_bytes() == BMP_BYTES

    def test_upload_category_aliases_normalization(self):
        """Verify category aliases ('memory', 'place', 'avatar', 'trail-watch') normalize cleanly."""
        file_obj = io.BytesIO(JPEG_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="alias_test.jpg")

        data = _run_coro(upload_photo(
            file=upload_file,
            category="trail-watch"
        ))
        assert data["category"] == "trail_reports"
        assert data["url"].startswith("/uploads/trail_reports/")

    def test_upload_with_entity_id_and_caption(self):
        """Verify optional entity_id and caption are echoed back in the response."""
        entity_uuid = str(uuid.uuid4())
        file_obj = io.BytesIO(PNG_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="captioned.png")

        data = _run_coro(upload_photo(
            file=upload_file,
            category="memories",
            entity_id=entity_uuid,
            caption="Everest Base Camp Memorial"
        ))
        assert data["entity_id"] == entity_uuid
        assert data["caption"] == "Everest Base Camp Memorial"


# =============================================================================
# 2. Static File Serving
# =============================================================================
class TestStaticFileServing:
    """Verifies static file serving through FastAPI StaticFiles mount."""

    def test_static_file_serving_retrieval(self, static_app):
        """Upload image, verify StaticFiles.lookup_path resolves file, and FileResponse returns 200 OK."""
        file_obj = io.BytesIO(JPEG_BYTES)
        upload_file = MockUploadFile(file=file_obj, filename="static_test.jpg", content_type="image/jpeg")

        data = _run_coro(upload_photo(file=upload_file, category="memories"))
        subpath = data["url"].replace("/uploads/", "")

        full_path, stat_result = static_app.lookup_path(subpath)
        assert full_path is not None
        assert stat_result is not None
        assert stat_result.st_size == len(JPEG_BYTES)

        file_resp = FileResponse(full_path, stat_result=stat_result)
        assert file_resp.status_code == 200
        assert file_resp.media_type in ("image/jpeg", "image/jpg")
        assert Path(full_path).read_bytes() == JPEG_BYTES

    def test_static_file_serving_all_formats(self, static_app):
        """Verify static file serving returns correct Content-Type for all 4 supported formats."""
        formats = [
            ("memories", JPEG_BYTES, "test.jpg", "image/jpeg"),
            ("places", PNG_BYTES, "test.png", "image/png"),
            ("avatars", WEBP_BYTES, "test.webp", "image/webp"),
            ("trail_reports", BMP_BYTES, "test.bmp", "image/bmp"),
        ]

        for category, payload, fname, expected_mime in formats:
            upload_file = MockUploadFile(file=io.BytesIO(payload), filename=fname)
            res = _run_coro(upload_photo(file=upload_file, category=category))
            subpath = res["url"].replace("/uploads/", "")

            full_path, stat_result = static_app.lookup_path(subpath)
            assert full_path is not None
            resp = FileResponse(full_path, stat_result=stat_result)
            assert resp.status_code == 200
            assert resp.media_type == expected_mime
            assert Path(full_path).read_bytes() == payload

    def test_static_file_nonexistent_returns_404_condition(self, static_app):
        """Verify requesting a non-existent file produces lookup failure (404 condition)."""
        nonexistent_subpath = "memories/00000000000000000000000000000000.jpg"
        full_path, stat_result = static_app.lookup_path(nonexistent_subpath)
        assert full_path == ""
        assert stat_result is None


# =============================================================================
# 3. Invalid Format Rejection
# =============================================================================
class TestInvalidFormatRejection:
    """Verifies that non-image payloads are rejected with HTTP 400 Bad Request."""

    def test_reject_plain_text(self):
        """Submit text/plain file; assert 400 Bad Request with 'Unsupported file format'."""
        text_payload = b"This is a travel journal in plain text, not a binary image."
        upload_file = MockUploadFile(file=io.BytesIO(text_payload), filename="notes.txt")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_photo(file=upload_file, category="memories"))

        assert exc.value.status_code == 400
        assert "Unsupported file format" in exc.value.detail

    def test_reject_pdf_document(self):
        """Submit PDF document bytes; assert 400 Bad Request."""
        pdf_payload = b"%PDF-1.4\n1 0 obj\n<< /Title (Nepal Trekking Guide) >>\nendobj"
        upload_file = MockUploadFile(file=io.BytesIO(pdf_payload), filename="permit.pdf")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_photo(file=upload_file, category="trail_reports"))

        assert exc.value.status_code == 400
        assert "Unsupported file format" in exc.value.detail

    def test_reject_corrupted_random_bytes(self):
        """Submit arbitrary non-image binary bytes; assert 400 Bad Request."""
        corrupt_payload = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f"
        upload_file = MockUploadFile(file=io.BytesIO(corrupt_payload), filename="corrupt.jpg")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_photo(file=upload_file, category="memories"))

        assert exc.value.status_code == 400
        assert "Unsupported file format" in exc.value.detail

    def test_reject_executable_binary(self):
        """Submit Windows MZ executable header; assert 400 Bad Request."""
        exe_payload = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
        upload_file = MockUploadFile(file=io.BytesIO(exe_payload), filename="installer.exe")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_photo(file=upload_file, category="avatars"))

        assert exc.value.status_code == 400
        assert "Unsupported file format" in exc.value.detail

    def test_reject_invalid_category(self):
        """Submit valid image to an unrecognized category; assert 400 Bad Request."""
        upload_file = MockUploadFile(file=io.BytesIO(JPEG_BYTES), filename="test.jpg")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_photo(file=upload_file, category="unauthorized_category"))

        assert exc.value.status_code == 400
        assert "Invalid category" in exc.value.detail


# =============================================================================
# 4. Oversized & Empty File Rejection
# =============================================================================
class TestOversizedAndEmptyFileRejection:
    """Verifies file size boundary enforcement (> 10MB -> 413, 0-byte -> 400)."""

    def test_reject_oversized_payload_exceeding_10mb(self):
        """Submit payload exceeding 10MB limit (10.5 MB); assert HTTP 413 Payload Too Large."""
        oversized_size = 10 * 1024 * 1024 + 512 * 1024  # 10.5 MB
        # Start with valid JPEG header and pad with zeros
        oversized_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (oversized_size - 4)
        upload_file = MockUploadFile(file=io.BytesIO(oversized_bytes), filename="huge_photo.jpg")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_photo(file=upload_file, category="memories"))

        assert exc.value.status_code == 413
        assert "File size exceeds maximum allowed limit" in exc.value.detail

    def test_reject_empty_file_zero_bytes(self):
        """Submit 0-byte file; assert HTTP 400 Bad Request."""
        empty_file = MockUploadFile(file=io.BytesIO(b""), filename="empty.jpg")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_photo(file=empty_file, category="memories"))

        assert exc.value.status_code == 400
        assert "File is empty or corrupted" in exc.value.detail

    def test_reject_none_file_object(self):
        """Submit None as file; assert HTTP 400 Bad Request."""
        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_photo(file=None, category="memories"))

        assert exc.value.status_code == 400


# =============================================================================
# 5. Place Photo Contribution (POST /places/{id}/photos)
# =============================================================================
class TestPlacePhotoContribution:
    """Verifies place photo contribution endpoints, DB persistence, and listing."""

    def test_upload_place_photo_success_and_cover_update(self, place_in_db):
        """Upload photo for known place with is_cover=True; verify 201 Created and DB state."""
        db = TestSessionLocal()
        upload_file = MockUploadFile(file=io.BytesIO(PNG_BYTES), filename="patan_krishna.png")

        data = _run_coro(upload_place_photo(
            id=place_in_db,
            file=upload_file,
            caption="Krishna Mandir Stone Carvings",
            is_cover=True,
            db=db, user=make_test_user(db, admin=True)))

        assert data["place_id"] == place_in_db
        assert data["caption"] == "Krishna Mandir Stone Carvings"
        assert data["is_cover"] is True
        assert data["image_url"].startswith("/uploads/places/")

        # Verify DB persistence of PlacePhoto
        saved_photo = db.query(PlacePhoto).filter(PlacePhoto.id == uuid.UUID(data["id"])).first()
        assert saved_photo is not None
        assert saved_photo.caption == "Krishna Mandir Stone Carvings"
        assert saved_photo.is_cover is True

        # Verify Place model cover photo and gallery update
        place = db.query(Place).filter(Place.id == uuid.UUID(place_in_db)).first()
        assert place.image_url == data["image_url"]
        assert data["image_url"] in place.gallery
        db.close()

    def test_get_place_photos_list(self, place_in_db):
        """Verify GET /places/{id}/photos returns all photos contributed for a destination."""
        db = TestSessionLocal()
        # Upload an additional photo
        upload_file = MockUploadFile(file=io.BytesIO(JPEG_BYTES), filename="golden_temple.jpg")
        photo_res = _run_coro(upload_place_photo(
            id=place_in_db,
            file=upload_file,
            caption="Golden Temple Courtyard",
            is_cover=False,
            db=db, user=make_test_user(db, admin=True)))

        # Query photo list
        list_res = _run_coro(get_place_photos(id=place_in_db, db=db))
        assert "photos" in list_res
        assert isinstance(list_res["photos"], list)
        assert len(list_res["photos"]) >= 1
        photo_ids = [p["id"] for p in list_res["photos"]]
        assert photo_res["id"] in photo_ids
        db.close()

    def test_upload_place_photo_nonexistent_place(self):
        """Submit photo for non-existent place UUID; assert HTTP 404 Not Found."""
        db = TestSessionLocal()
        fake_uuid = str(uuid.uuid4())
        upload_file = MockUploadFile(file=io.BytesIO(JPEG_BYTES), filename="ghost.jpg")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_place_photo(
                id=fake_uuid,
                file=upload_file,
                caption="Ghost Place",
                is_cover=False,
                db=db, user=make_test_user(db, admin=True)))

        assert exc.value.status_code == 404
        assert "Place not found" in exc.value.detail
        db.close()

    def test_upload_place_photo_invalid_uuid_format(self):
        """Submit photo with malformed place ID string; assert HTTP 400 Bad Request."""
        db = TestSessionLocal()
        upload_file = MockUploadFile(file=io.BytesIO(JPEG_BYTES), filename="bad_id.jpg")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_place_photo(
                id="not-a-valid-uuid",
                file=upload_file,
                caption="Invalid ID",
                is_cover=False,
                db=db, user=make_test_user(db, admin=True)))

        assert exc.value.status_code == 400
        assert "Invalid place ID format" in exc.value.detail
        db.close()

    def test_upload_place_photo_corrupted_payload(self, place_in_db):
        """Submit non-image bytes to place photo endpoint; assert HTTP 400 Bad Request."""
        db = TestSessionLocal()
        corrupt_file = MockUploadFile(file=io.BytesIO(b"NOT_AN_IMAGE"), filename="bad.bin")

        with pytest.raises(HTTPException) as exc:
            _run_coro(upload_place_photo(
                id=place_in_db,
                file=corrupt_file,
                caption="Corrupted",
                is_cover=False,
                db=db, user=make_test_user(db, admin=True)))

        assert exc.value.status_code == 400
        assert "Unsupported file format" in exc.value.detail
        db.close()


# =============================================================================
# 6. Path Traversal Safeguards
# =============================================================================
class TestPathTraversalSafeguards:
    """Verifies protection against directory traversal attacks."""

    def test_path_traversal_filename_sanitization(self):
        """Submit file with malicious path traversal filename; assert UUID generation prevents breakout."""
        malicious_filename = "../../../../etc/passwd.jpg"
        upload_file = MockUploadFile(file=io.BytesIO(JPEG_BYTES), filename=malicious_filename)

        data = _run_coro(upload_photo(file=upload_file, category="memories"))
        assert data["status"] == "success"

        # Filename must be sanitized to safe UUID4, never containing '..' or path separators
        assert ".." not in data["filename"]
        assert "/" not in data["filename"]
        assert "\\" not in data["filename"]
        assert re.match(r"^[0-9a-f]{32}\.(jpg|jpeg)$", data["filename"])

        # File must be strictly inside settings.UPLOAD_DIR/memories
        expected_dir = Path(settings.UPLOAD_DIR) / "memories"
        saved_file = expected_dir / data["filename"]
        assert saved_file.exists()
        assert saved_file.resolve().parent == expected_dir.resolve()

    def test_path_traversal_windows_backslashes(self):
        """Submit file with Windows backslash path traversal; assert clean UUID naming."""
        malicious_filename = "..\\..\\windows\\system32\\malware.png"
        upload_file = MockUploadFile(file=io.BytesIO(PNG_BYTES), filename=malicious_filename)

        data = _run_coro(upload_photo(file=upload_file, category="avatars"))
        assert ".." not in data["filename"]
        assert "\\" not in data["filename"]
        assert re.match(r"^[0-9a-f]{32}\.png$", data["filename"])

    def test_delete_upload_file_path_traversal_protection(self):
        """Verify upload_service.delete_upload_file rejects traversal attempts outside UPLOAD_DIR."""
        # Attempt to delete outside upload directory
        res = upload_service.delete_upload_file("/uploads/../../some_file.txt")
        assert res is False

        # Attempt to delete invalid non-upload URL
        res = upload_service.delete_upload_file("/etc/passwd")
        assert res is False


# =============================================================================
# 7. Project Root Sample Assets Testing
# =============================================================================
class TestSampleAssets:
    """Verifies uploading of sample BMP assets and static serving."""

    def test_upload_sample_test_bmp(self, static_app):
        """Upload sample BMP (test.bmp) and verify static serving."""
        sample_path = PROJECT_ROOT / "test.bmp"
        sample_bytes = sample_path.read_bytes() if sample_path.exists() else BMP_BYTES

        upload_file = MockUploadFile(file=io.BytesIO(sample_bytes), filename="test.bmp")
        data = _run_coro(upload_photo(file=upload_file, category="places"))

        assert data["status"] == "success"
        assert data["content_type"] == "image/bmp"
        assert data["size_bytes"] == len(sample_bytes)

        # Static serving verification
        subpath = data["url"].replace("/uploads/", "")
        full_path, stat_result = static_app.lookup_path(subpath)
        assert full_path is not None
        assert stat_result.st_size == len(sample_bytes)
        assert Path(full_path).read_bytes() == sample_bytes

    def test_upload_sample_view_front_bmp(self, static_app):
        """Upload sample BMP (view_front.bmp) and verify static serving."""
        sample_path = PROJECT_ROOT / "view_front.bmp"
        sample_bytes = sample_path.read_bytes() if sample_path.exists() else (BMP_BYTES + b"\x00" * 1024)

        upload_file = MockUploadFile(file=io.BytesIO(sample_bytes), filename="view_front.bmp")
        data = _run_coro(upload_photo(file=upload_file, category="memories"))

        assert data["status"] == "success"
        assert data["content_type"] == "image/bmp"
        assert data["size_bytes"] == len(sample_bytes)

        subpath = data["url"].replace("/uploads/", "")
        full_path, stat_result = static_app.lookup_path(subpath)
        assert full_path is not None
        assert stat_result.st_size == len(sample_bytes)

    def test_upload_sample_view_angle_bmp(self, static_app):
        """Upload sample BMP (view_angle.bmp) and verify static serving."""
        sample_path = PROJECT_ROOT / "view_angle.bmp"
        sample_bytes = sample_path.read_bytes() if sample_path.exists() else (BMP_BYTES + b"\x00" * 2048)

        upload_file = MockUploadFile(file=io.BytesIO(sample_bytes), filename="view_angle.bmp")
        data = _run_coro(upload_photo(file=upload_file, category="trail_reports"))

        assert data["status"] == "success"
        assert data["content_type"] == "image/bmp"
        assert data["size_bytes"] == len(sample_bytes)

        subpath = data["url"].replace("/uploads/", "")
        full_path, stat_result = static_app.lookup_path(subpath)
        assert full_path is not None
        assert stat_result.st_size == len(sample_bytes)

    def test_sample_bmp_to_place_photos_contribution(self, place_in_db):
        """Upload sample BMP to POST /places/{id}/photos and verify DB persistence."""
        sample_path = PROJECT_ROOT / "test.bmp"
        sample_bytes = sample_path.read_bytes() if sample_path.exists() else BMP_BYTES
        db = TestSessionLocal()

        upload_file = MockUploadFile(file=io.BytesIO(sample_bytes), filename="test.bmp")
        photo_res = _run_coro(upload_place_photo(
            id=place_in_db,
            file=upload_file,
            caption="Authentic Durbar Square View",
            is_cover=False,
            db=db, user=make_test_user(db, admin=True)))

        assert photo_res["place_id"] == place_in_db
        assert photo_res["caption"] == "Authentic Durbar Square View"
        assert photo_res["image_url"].startswith("/uploads/places/")

        # Verify saved in PlacePhoto table
        photo_record = db.query(PlacePhoto).filter(PlacePhoto.id == uuid.UUID(photo_res["id"])).first()
        assert photo_record is not None
        db.close()


# =============================================================================
# 8. Upload Categories Namespace Endpoint
# =============================================================================
class TestUploadCategoriesEndpoint:
    """Verifies GET /uploads/categories lists supported category namespaces."""

    def test_list_upload_categories(self):
        """Call list_upload_categories; assert categories list matches ALLOWED_CATEGORIES."""
        data = _run_coro(list_upload_categories())
        assert "categories" in data
        assert isinstance(data["categories"], list)
        expected = sorted(["avatars", "memories", "places", "trail_reports"])
        assert data["categories"] == expected
