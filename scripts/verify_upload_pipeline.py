"""
YatraSathi Automated Image Upload & Storage Verification Script
==============================================================
Standalone verification script validating the complete image uploading,
local filesystem storage, static file serving, and place photo database
persistence pipelines.

Usage:
    python scripts/verify_upload_pipeline.py

Verifies:
1. Valid Image Uploads (JPEG, PNG, WebP, BMP) across multiple categories
2. Project Root Sample Assets (test.bmp, view_front.bmp, view_angle.bmp)
3. Static File Serving (lookup_path, Content-Type headers, exact byte fidelity)
4. Invalid Format Rejection (text/plain, PDF, corrupted binary -> HTTP 400)
5. Oversized File Rejection (> 10MB limit -> HTTP 413)
6. Empty File Rejection (0 bytes -> HTTP 400)
7. Place Photo Contribution (POST /places/{id}/photos, DB persistence, cover update)
8. Path Traversal Safeguards (directory escape prevention, safe UUID naming)
9. Upload Categories Namespace Endpoint
"""
import io
import os
import sys
import time
import uuid
import re
import mimetypes
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure SQLite local database and non-blocking LLM settings
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = f"sqlite:///{PROJECT_ROOT / 'yatra_sathi.db'}"
os.environ["AI_ENABLED"] = "false"
os.environ["DEBUG"] = "false"

# Register webp mimetype for Windows compatibility
mimetypes.add_type("image/webp", ".webp")

from fastapi import UploadFile, HTTPException
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse

from backend.app.config.settings import settings
settings.DATABASE_URL = os.environ["DATABASE_URL"]

from backend.app.db.database import SessionLocal, init_db, engine
from backend.app.models.place import Place
from backend.app.models.place_photo import PlacePhoto
from backend.app.api.uploads import upload_photo, list_upload_categories
from backend.app.api.places import upload_place_photo, get_place_photos
from backend.app.services.upload_service import upload_service, ALLOWED_CATEGORIES


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def run_coro(coro):
    """Execute async coroutine synchronously without event loop socket binding."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    except Exception as ex:
        raise ex


class MockUploadFile(UploadFile):
    """UploadFile implementation allowing synchronous binary reading."""

    def __init__(self, file: io.BytesIO, filename: str = "image.bin", content_type: str = "application/octet-stream"):
        super().__init__(file=file, filename=filename, headers={"content-type": content_type})

    async def read(self, size: int = -1) -> bytes:
        if hasattr(self.file, "seek"):
            self.file.seek(0)
        return self.file.read()


# Synthetic binary payloads
JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    + b"\x00" * 200
    + b"\xff\xd9"
)

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

WEBP_BYTES = (
    b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\xb0\x01\x00\x9d\x01*\x01\x00\x01\x00\x00/ \x00\x00"
)

BMP_BYTES = (
    b"BM\x3e\x00\x00\x00\x00\x00\x00\x00\x36\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00"
    b"\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x08\x00\x00\x00\x13\x0b\x00\x00"
    b"\x13\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x00"
)


# -----------------------------------------------------------------------------
# Test Suite Runner
# -----------------------------------------------------------------------------
class UploadPipelineVerifier:
    def __init__(self):
        self.passes = 0
        self.failures = 0
        self.static_app = StaticFiles(directory=str(settings.UPLOAD_DIR))

    def log_pass(self, test_num: int, name: str, detail: str = ""):
        self.passes += 1
        suffix = f" -- {detail}" if detail else ""
        print(f"  [PASS] Test {test_num}: {name}{suffix}")

    def log_fail(self, test_num: int, name: str, reason: str):
        self.failures += 1
        print(f"  [FAIL] Test {test_num}: {name} -> {reason}")

    def run_all(self):
        print("=" * 80)
        print("YATRASATHI PHOTO UPLOAD & STORAGE PIPELINE VERIFICATION")
        print("=" * 80)
        start_time = time.time()

        # Initialize DB and ensure tables exist
        init_db()

        self.test_1_valid_image_uploads()
        self.test_2_project_root_sample_assets()
        self.test_3_static_file_serving()
        self.test_4_invalid_format_rejection()
        self.test_5_oversized_file_rejection()
        self.test_6_empty_file_rejection()
        self.test_7_place_photo_contribution()
        self.test_8_path_traversal_safeguards()
        self.test_9_upload_categories_endpoint()

        duration = time.time() - start_time
        print("=" * 80)
        print(f"VERIFICATION SUMMARY: {self.passes} PASSED, {self.failures} FAILED in {duration:.2f}s")
        print("=" * 80)

        if self.failures > 0:
            print("Status: [FAIL] VERIFICATION FAILED")
            return 1
        else:
            print("Status: [OK] ALL PIPELINE TESTS PASSED (100% SUCCESS)")
            return 0

    def test_1_valid_image_uploads(self):
        """Test valid JPEG, PNG, WebP, BMP uploads across categories."""
        test_cases = [
            ("JPEG in memories", JPEG_BYTES, "test_peak.jpg", "memories", "image/jpeg"),
            ("PNG in places", PNG_BYTES, "monastery.png", "places", "image/png"),
            ("WebP in avatars", WEBP_BYTES, "avatar.webp", "avatars", "image/webp"),
            ("BMP in trail_reports", BMP_BYTES, "landslide.bmp", "trail_reports", "image/bmp"),
        ]

        for desc, payload, fname, category, mime in test_cases:
            try:
                uf = MockUploadFile(file=io.BytesIO(payload), filename=fname)
                res = run_coro(upload_photo(file=uf, category=category))

                assert res["status"] == "success", "status not success"
                assert res["content_type"] == mime, f"content_type {res['content_type']} != {mime}"
                assert res["category"] == category, f"category {res['category']} != {category}"
                assert res["url"].startswith(f"/uploads/{category}/"), "URL missing prefix"
                assert res["size_bytes"] == len(payload), "size_bytes mismatch"

                # Check on disk
                saved_path = PROJECT_ROOT / res["url"].lstrip("/")
                assert saved_path.exists(), f"File not written to {saved_path}"
                assert saved_path.read_bytes() == payload, "Bytes on disk do not match payload"

                self.log_pass(1, f"Valid {desc}", f"Saved to {res['url']}")
            except Exception as e:
                self.log_fail(1, f"Valid {desc}", str(e))

    def test_2_project_root_sample_assets(self):
        """Test uploading sample BMP assets from project root."""
        samples = [
            ("test.bmp", 30054, "places"),
            ("view_front.bmp", 460854, "memories"),
            ("view_angle.bmp", 460854, "trail_reports"),
        ]

        for fname, expected_size, category in samples:
            sample_path = PROJECT_ROOT / fname
            if not sample_path.exists():
                self.log_fail(2, f"Sample asset {fname}", "File does not exist in project root")
                continue

            try:
                raw_bytes = sample_path.read_bytes()
                assert len(raw_bytes) == expected_size, f"Size {len(raw_bytes)} != {expected_size}"

                uf = MockUploadFile(file=io.BytesIO(raw_bytes), filename=fname)
                res = run_coro(upload_photo(file=uf, category=category))

                assert res["status"] == "success"
                assert res["content_type"] == "image/bmp"
                assert res["size_bytes"] == expected_size
                assert res["url"].startswith(f"/uploads/{category}/")

                # Verify file on disk
                saved_path = PROJECT_ROOT / res["url"].lstrip("/")
                assert saved_path.exists()
                assert saved_path.read_bytes() == raw_bytes

                self.log_pass(2, f"Sample asset '{fname}' ({expected_size:,} bytes)", f"Uploaded to {res['url']}")
            except Exception as e:
                self.log_fail(2, f"Sample asset '{fname}'", str(e))

    def test_3_static_file_serving(self):
        """Test static file serving and MIME header resolution via StaticFiles."""
        try:
            # Upload sample image
            uf = MockUploadFile(file=io.BytesIO(JPEG_BYTES), filename="static_test.jpg")
            res = run_coro(upload_photo(file=uf, category="memories"))

            subpath = res["url"].replace("/uploads/", "")
            full_path, stat_result = self.static_app.lookup_path(subpath)
            assert full_path is not None and full_path != "", "StaticFiles failed to locate file"
            assert stat_result.st_size == len(JPEG_BYTES), "stat size mismatch"

            file_resp = FileResponse(full_path, stat_result=stat_result)
            assert file_resp.status_code == 200, f"Status code {file_resp.status_code} != 200"
            assert file_resp.media_type in ("image/jpeg", "image/jpg")
            assert Path(full_path).read_bytes() == JPEG_BYTES

            # Test 404 condition for non-existent file
            fake_path, fake_stat = self.static_app.lookup_path("memories/nonexistent_file_99999.jpg")
            assert fake_path == "" and fake_stat is None, "Non-existent file did not return empty path"

            self.log_pass(3, "Static File Serving", f"Verified HTTP 200 & Content-Type for {res['url']}")
        except Exception as e:
            self.log_fail(3, "Static File Serving", str(e))

    def test_4_invalid_format_rejection(self):
        """Test that text/plain, PDF, and corrupt payloads are rejected with HTTP 400."""
        invalid_payloads = [
            ("Plain text", b"Text journal notes only", "notes.txt"),
            ("PDF document", b"%PDF-1.4\nSome PDF content\n%%EOF", "doc.pdf"),
            ("Random corrupt bytes", b"\x00\x01\x02\x03\x04\x05\x06\x07", "corrupt.bin"),
            ("Executable header", b"MZ\x90\x00\x03\x00\x00\x00", "installer.exe"),
        ]

        for label, payload, fname in invalid_payloads:
            try:
                uf = MockUploadFile(file=io.BytesIO(payload), filename=fname)
                try:
                    run_coro(upload_photo(file=uf, category="memories"))
                    self.log_fail(4, f"Reject {label}", "Did not raise HTTPException")
                except HTTPException as exc:
                    assert exc.status_code == 400, f"Expected 400, got {exc.status_code}"
                    assert "Unsupported file format" in exc.detail, f"Unexpected detail: {exc.detail}"
                    self.log_pass(4, f"Reject {label}", f"Correctly returned 400 Bad Request: {exc.detail}")
            except Exception as e:
                self.log_fail(4, f"Reject {label}", str(e))

    def test_5_oversized_file_rejection(self):
        """Test that files exceeding 10MB limit are rejected with HTTP 413 Payload Too Large."""
        try:
            oversized_size = 10 * 1024 * 1024 + 256 * 1024  # 10.25 MB
            payload = b"\xff\xd8\xff\xe0" + b"\x00" * (oversized_size - 4)
            uf = MockUploadFile(file=io.BytesIO(payload), filename="massive.jpg")

            try:
                run_coro(upload_photo(file=uf, category="memories"))
                self.log_fail(5, "Oversized file rejection", "Did not raise HTTPException")
            except HTTPException as exc:
                assert exc.status_code == 413, f"Expected 413, got {exc.status_code}"
                assert "exceeds maximum allowed limit" in exc.detail
                self.log_pass(5, "Oversized file rejection (> 10MB)", f"Correctly returned 413: {exc.detail}")
        except Exception as e:
            self.log_fail(5, "Oversized file rejection", str(e))

    def test_6_empty_file_rejection(self):
        """Test that 0-byte file is rejected with HTTP 400 Bad Request."""
        try:
            uf = MockUploadFile(file=io.BytesIO(b""), filename="empty.jpg")
            try:
                run_coro(upload_photo(file=uf, category="memories"))
                self.log_fail(6, "Empty file rejection", "Did not raise HTTPException")
            except HTTPException as exc:
                assert exc.status_code == 400, f"Expected 400, got {exc.status_code}"
                assert "File is empty or corrupted" in exc.detail
                self.log_pass(6, "Empty file rejection (0 bytes)", f"Correctly returned 400: {exc.detail}")
        except Exception as e:
            self.log_fail(6, "Empty file rejection", str(e))

    def test_7_place_photo_contribution(self):
        """Test POST /places/{id}/photos and GET /places/{id}/photos with DB persistence."""
        db = SessionLocal()
        try:
            place = db.query(Place).first()
            if not place:
                place = Place(
                    id=uuid.uuid4(),
                    name="Swayambhunath Stupa (Monkey Temple)",
                    category="Cultural Heritage",
                    centroid="POINT(85.2904 27.7149)",
                    bbox_min_lat=27.71,
                    bbox_max_lat=27.72,
                    bbox_min_lon=85.29,
                    bbox_max_lon=85.30,
                    popularity=9.6,
                    rating=4.9
                )
                db.add(place)
                db.commit()
                db.refresh(place)

            place_id = str(place.id)
            uf = MockUploadFile(file=io.BytesIO(PNG_BYTES), filename="monkey_temple.png")

            # Post photo contribution with is_cover=True
            res = run_coro(upload_place_photo(
                id=place_id,
                file=uf,
                caption="Golden spire in evening light",
                is_cover=True,
                db=db
            ))

            assert res["place_id"] == place_id, "place_id mismatch"
            assert res["caption"] == "Golden spire in evening light"
            assert res["is_cover"] is True
            assert res["image_url"].startswith("/uploads/places/")

            # Verify PlacePhoto persisted in database
            photo_record = db.query(PlacePhoto).filter(PlacePhoto.id == uuid.UUID(res["id"])).first()
            assert photo_record is not None, "PlacePhoto not saved in database"
            assert photo_record.caption == "Golden spire in evening light"

            # Verify place.image_url updated
            db.refresh(place)
            assert place.image_url == res["image_url"]

            # Verify GET /places/{id}/photos returns photo
            photos_list = run_coro(get_place_photos(id=place_id, db=db))
            assert "photos" in photos_list
            assert any(p["id"] == res["id"] for p in photos_list["photos"])

            self.log_pass(7, "Place Photo Contribution & DB Persistence", f"Contributed to {place.name}")
        except Exception as e:
            self.log_fail(7, "Place Photo Contribution", str(e))
        finally:
            db.close()

    def test_8_path_traversal_safeguards(self):
        """Test that directory traversal filename attempts are sanitized to UUIDs."""
        try:
            malicious_filename = "../../../../etc/passwd.jpg"
            uf = MockUploadFile(file=io.BytesIO(JPEG_BYTES), filename=malicious_filename)

            res = run_coro(upload_photo(file=uf, category="memories"))

            assert ".." not in res["filename"], "Filename contains traversal '..'"
            assert "/" not in res["filename"] and "\\" not in res["filename"], "Filename contains path separators"
            assert re.match(r"^[0-9a-f]{32}\.(jpg|jpeg)$", res["filename"]), "Filename is not clean UUID"

            # Check delete traversal protection
            assert upload_service.delete_upload_file("../../../secret.txt") is False

            self.log_pass(8, "Path Traversal Safeguards", f"Sanitized malicious filename to {res['filename']}")
        except Exception as e:
            self.log_fail(8, "Path Traversal Safeguards", str(e))

    def test_9_upload_categories_endpoint(self):
        """Test GET /uploads/categories endpoint returns allowed namespaces."""
        try:
            data = run_coro(list_upload_categories())
            assert "categories" in data
            expected = sorted(list(ALLOWED_CATEGORIES))
            assert data["categories"] == expected
            self.log_pass(9, "Upload Categories Endpoint", f"Returned categories: {data['categories']}")
        except Exception as e:
            self.log_fail(9, "Upload Categories Endpoint", str(e))


if __name__ == "__main__":
    verifier = UploadPipelineVerifier()
    exit_code = verifier.run_all()
    sys.exit(exit_code)
