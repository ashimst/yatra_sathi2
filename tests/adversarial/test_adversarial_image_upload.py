"""
Adversarial Stress Test Suite for Image Upload & Validation Engine (Milestone 5 - Challenger 1)
=================================================================================================
Empirical verification across 6 hostile threat vectors:
1. Signature Spoofing: Fake extensions (.jpg, .png, .webp, .bmp) with HTML, ELF, PE, PDF, ZIP, TXT, JSON, random bytes.
2. Header Corruption: Truncated or malformed magic bytes across JPEG, PNG, WebP, and BMP.
3. Strict Boundary Size Stress: Exact boundary testing at 0 bytes, 10MB exact (10,485,760 bytes), and 10MB + 1 byte (10,485,761 bytes).
4. Path Traversal & Injection: Directory escaping, Windows backslashes, URL encoded traversals, null bytes, and safe deletion.
5. Category Spoofing: Injection of unapproved category strings, path escaping categories, and normalization.
6. Concurrency Stress: 10 rapid concurrent image uploads asserting zero collision, unique UUID generation, and disk integrity.
7. Destination Place Photo Contribution: Adversarial vector testing against POST /places/{id}/photos.
"""

import io
import os
import re
import sys
import uuid
import shutil
import pytest
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import UploadFile, HTTPException, status

# Import repository test fixtures and backend configuration
import tests.e2e.conftest
from tests.e2e.conftest import PROJECT_ROOT, TestSessionLocal
from tests.auth_helpers import make_test_user
from backend.app.config.settings import settings
from backend.app.models.place import Place
from backend.app.models.place_photo import PlacePhoto
from backend.app.api.uploads import upload_photo, list_upload_categories
from backend.app.api.places import upload_place_photo, get_place_photos
from backend.app.services.upload_service import (
    upload_service,
    validate_image_file,
    save_upload_file,
    normalize_category,
    ALLOWED_CATEGORIES
)


# -----------------------------------------------------------------------------
# Test Helpers & Coroutine Runner
# -----------------------------------------------------------------------------
def _run_coro(coro):
    """Execute coroutine synchronously without event loop socket binding."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    except Exception as ex:
        raise ex


class MockUploadFile(UploadFile):
    """Synchronous UploadFile mock avoiding asyncio thread-pool socket deadlocks."""

    def __init__(self, file: io.BytesIO, filename: str = "image.bin", content_type: str = "application/octet-stream"):
        super().__init__(file=file, filename=filename, headers={"content-type": content_type})

    async def read(self, size: int = -1) -> bytes:
        if hasattr(self.file, "seek"):
            self.file.seek(0)
        return self.file.read()


# -----------------------------------------------------------------------------
# Authoritative Binary Signatures & Payloads
# -----------------------------------------------------------------------------
# Minimal valid JPEG
VALID_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    + b"\x00" * 128
    + b"\xff\xd9"
)

# Minimal valid PNG
VALID_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal valid WebP
VALID_WEBP = (
    b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\xb0\x01\x00\x9d\x01*\x01\x00\x01\x00\x00/ \x00\x00"
)

# Minimal valid BMP
VALID_BMP = (
    b"BM\x3a\x00\x00\x00\x00\x00\x00\x00\x36\x00\x00\x00\x28\x00\x00\x00"
    b"\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00"
    b"\x04\x00\x00\x00\x13\x0b\x00\x00\x13\x0b\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\xff\x00"
)


# =============================================================================
# 1. Signature Spoofing (Adversarial Extension vs Binary Mismatches)
# =============================================================================
class TestSignatureSpoofing:
    """
    Adversarial verification that files with legitimate image extensions (.jpg, .png, .webp, .bmp)
    containing non-image payloads (HTML, ELF, PE, PDF, ZIP, TXT, JSON, random bytes)
    are strictly rejected with HTTP 400 Bad Request.
    """

    SPOOFED_PAYLOADS = [
        ("fake.jpg", b"This is a plaintext ASCII file claiming to be a JPEG.", "plain_text"),
        ("exploit.png", b"<!DOCTYPE html><html><body><script>alert('xss')</script></body></html>", "html_xss"),
        ("malware.webp", b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x3e\x00", "elf_binary"),
        ("trojan.bmp", b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00", "pe_mz_binary"),
        ("doc.jpg", b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj", "pdf_document"),
        ("payload.png", b"PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00\x00\x00", "zip_archive"),
        ("config.webp", b'{"admin": true, "role": "root", "token": "secret_12345"}', "json_string"),
        ("entropy.bmp", os.urandom(1024), "random_entropy_bytes"),
        ("archive.jpg", b"ustar\x0000", "tar_archive"),
        ("compressed.png", b"\x1f\x8b\x08\x00\x00\x00\x00\x00", "gzip_archive"),
    ]

    @pytest.mark.parametrize("filename,payload,description", SPOOFED_PAYLOADS)
    def test_upload_service_rejects_spoofed_signatures(self, filename, payload, description):
        """Directly verify upload_service.validate_image_file rejects spoofed payloads."""
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(payload, filename)
        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in exc_info.value.detail

    @pytest.mark.parametrize("filename,payload,description", SPOOFED_PAYLOADS)
    def test_endpoint_rejects_spoofed_signatures(self, filename, payload, description):
        """Verify POST /uploads/photo endpoint strictly rejects spoofed file extensions."""
        mock_file = MockUploadFile(io.BytesIO(payload), filename=filename)
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_photo(file=mock_file, category="memories"))
        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in exc_info.value.detail


# =============================================================================
# 2. Header Corruption (Partial / Truncated Magic Bytes)
# =============================================================================
class TestHeaderCorruption:
    """
    Adversarial verification testing truncated or corrupted magic headers.
    Ensures that partial matches do not bypass format detection.
    """

    CORRUPTED_HEADERS = [
        # JPEG: requires b"\xff\xd8\xff"
        ("jpeg_2bytes.jpg", b"\xff\xd8", "Truncated 2-byte JPEG magic"),
        ("jpeg_bad3rd.jpg", b"\xff\xd8\x00", "Corrupted 3rd byte of JPEG magic"),
        ("jpeg_1byte.jpg", b"\xff", "Single byte prefix"),
        ("jpeg_inverted.jpg", b"\xd8\xff\xd8", "Inverted JPEG magic"),

        # PNG: requires b"\x89PNG\r\n\x1a\n" (8 bytes)
        ("png_7bytes.png", b"\x89PNG\r\n\x1a", "Truncated 7-byte PNG header (missing newline)"),
        ("png_6bytes.png", b"\x89PNG\r\n", "Truncated 6-byte PNG header"),
        ("png_4bytes.png", b"\x89PNG", "Truncated 4-byte PNG header"),
        ("png_bad_lead.png", b"PNG\r\n\x1a\n", "Missing leading \\x89 byte"),
        ("png_corrupt_char.png", b"\x89PNE\r\n\x1a\n", "Corrupted character in PNG header"),

        # WebP: requires len >= 12 and [:4] == b"RIFF" and [8:12] == b"WEBP"
        ("webp_riff_only.webp", b"RIFF", "RIFF only (4 bytes)"),
        ("webp_8bytes.webp", b"RIFF\x20\x00\x00\x00", "RIFF + size (8 bytes, missing WEBP)"),
        ("webp_wave_audio.webp", b"RIFF\x20\x00\x00\x00WAVEfmt ", "RIFF WAVE audio header"),
        ("webp_avi_video.webp", b"RIFF\x20\x00\x00\x00AVI LIST", "RIFF AVI video header"),
        ("webp_bad_subtype.webp", b"RIFF\x20\x00\x00\x00WEBF", "RIFF with corrupted WEBF subtype"),
        ("webp_reversed.webp", b"WEBP\x00\x00\x00\x00RIFF", "Reversed WEBP and RIFF tags"),

        # BMP: requires b"BM"
        ("bmp_1byte.bmp", b"B", "Single 'B' byte (missing 'M')"),
        ("bmp_os2_array.bmp", b"BA", "OS/2 Bitmap Array 'BA'"),
        ("bmp_icon.bmp", b"CI", "Color Icon 'CI'"),
        ("bmp_reversed.bmp", b"MB", "Reversed 'MB'"),
        ("bmp_null_2nd.bmp", b"B\x00", "Null second byte"),
    ]

    @pytest.mark.parametrize("filename,payload,description", CORRUPTED_HEADERS)
    def test_upload_service_rejects_corrupted_headers(self, filename, payload, description):
        """Verify validate_image_file strictly rejects incomplete magic bytes."""
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(payload, filename)
        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in exc_info.value.detail

    @pytest.mark.parametrize("filename,payload,description", CORRUPTED_HEADERS)
    def test_endpoint_rejects_corrupted_headers(self, filename, payload, description):
        """Verify POST /uploads/photo rejects incomplete magic headers."""
        mock_file = MockUploadFile(io.BytesIO(payload), filename=filename)
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_photo(file=mock_file, category="places"))
        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in exc_info.value.detail


# =============================================================================
# 3. Strict Boundary Size Stress (Exact Limits: 0, 10MB, 10MB + 1)
# =============================================================================
class TestStrictBoundarySizeStress:
    """
    Adversarial boundary testing around max file size (10MB = 10,485,760 bytes)
    and empty payloads (0 bytes).
    """

    MAX_SIZE = settings.MAX_UPLOAD_SIZE_BYTES  # 10,485,760 bytes

    def test_zero_byte_empty_file_rejected_with_http_400(self):
        """Verify 0-byte payload is rejected with HTTP 400 Bad Request."""
        empty_bytes = b""
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(empty_bytes, "empty.jpg")
        assert exc_info.value.status_code == 400
        assert "empty or corrupted" in exc_info.value.detail.lower()

        # Test endpoint
        mock_file = MockUploadFile(io.BytesIO(empty_bytes), filename="empty.jpg")
        with pytest.raises(HTTPException) as exc_info_ep:
            _run_coro(upload_photo(file=mock_file, category="memories"))
        assert exc_info_ep.value.status_code == 400
        assert "empty or corrupted" in exc_info_ep.value.detail.lower()

    def test_exact_10mb_boundary_upload_succeeds(self):
        """
        Verify exact 10MB payload (10,485,760 bytes) is ACCEPTED and succeeds with HTTP 200.
        Constructs a valid JPEG with padding totaling exactly MAX_SIZE bytes.
        """
        header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"  # 18 bytes
        trailer = b"\xff\xd9"  # 2 bytes
        padding_len = self.MAX_SIZE - len(header) - len(trailer)
        ten_mb_jpeg = header + (b"\x00" * padding_len) + trailer

        assert len(ten_mb_jpeg) == self.MAX_SIZE, f"Expected {self.MAX_SIZE}, got {len(ten_mb_jpeg)}"

        # Validate directly
        detected_mime = validate_image_file(ten_mb_jpeg, "boundary_10mb.jpg")
        assert detected_mime == "image/jpeg"

        # Validate through endpoint
        mock_file = MockUploadFile(io.BytesIO(ten_mb_jpeg), filename="boundary_10mb.jpg")
        res = _run_coro(upload_photo(file=mock_file, category="memories"))

        assert res["status"] == "success"
        assert res["size_bytes"] == self.MAX_SIZE
        assert res["content_type"] == "image/jpeg"
        assert res["url"].startswith("/uploads/memories/")

        # Verify disk persistence & exact byte count
        saved_path = Path(settings.UPLOAD_DIR) / "memories" / res["filename"]
        assert saved_path.exists()
        assert saved_path.stat().st_size == self.MAX_SIZE

        # Clean up
        saved_path.unlink(missing_ok=True)

    def test_exact_10mb_plus_one_byte_rejected_with_http_413(self):
        """
        Verify exact 10MB + 1 byte (10,485,761 bytes) is REJECTED with HTTP 413 Payload Too Large.
        """
        header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
        trailer = b"\xff\xd9"
        padding_len = (self.MAX_SIZE + 1) - len(header) - len(trailer)
        oversized_jpeg = header + (b"\x00" * padding_len) + trailer

        assert len(oversized_jpeg) == self.MAX_SIZE + 1

        # Direct service validation check
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(oversized_jpeg, "ten_mb_plus_one.jpg")
        assert exc_info.value.status_code == 413
        assert "exceeds maximum allowed limit" in exc_info.value.detail

        # Endpoint check
        mock_file = MockUploadFile(io.BytesIO(oversized_jpeg), filename="ten_mb_plus_one.jpg")
        with pytest.raises(HTTPException) as exc_info_ep:
            _run_coro(upload_photo(file=mock_file, category="places"))
        assert exc_info_ep.value.status_code == 413
        assert "exceeds maximum allowed limit" in exc_info_ep.value.detail

    def test_extreme_oversized_payload_15mb_rejected(self):
        """Verify massive 15MB payload is rejected with HTTP 413."""
        huge_bytes = VALID_PNG + (b"\x00" * (15 * 1024 * 1024))
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(huge_bytes, "huge.png")
        assert exc_info.value.status_code == 413


# =============================================================================
# 4. Path Traversal & Injection Safeguards
# =============================================================================
class TestPathTraversalAndInjection:
    """
    Adversarial verification testing directory traversal strings, URL encoded sequences,
    Windows backslashes, absolute paths, and null-byte injection.
    Asserts that files strictly remain inside settings.UPLOAD_DIR/{category}/ with safe UUIDs.
    """

    TRAVERSAL_FILENAMES = [
        "../../../../etc/passwd.jpg",
        "..\\..\\Windows\\System32\\cmd.exe.png",
        "%2e%2e%2f%2e%2e%2fetc%2fshadow.webp",
        "....//....//boot.ini.bmp",
        "C:\\Windows\\win.ini.jpg",
        "/var/log/messages.png",
        "..\\..\\..\\..\\..\\..\\..\\..\\secret.webp",
        "nested/sub/dir/image.jpg",
        "image.jpg\x00.exe",
        "photo;rm -rf /;.png",
        "<script>alert(1)</script>.bmp",
    ]

    @pytest.mark.parametrize("traversal_name", TRAVERSAL_FILENAMES)
    def test_path_traversal_filenames_sanitized_to_safe_uuid(self, traversal_name):
        """Verify upload with malicious filename generates pure UUID inside target directory."""
        mock_file = MockUploadFile(io.BytesIO(VALID_JPEG), filename=traversal_name)
        res = _run_coro(upload_photo(file=mock_file, category="memories"))

        assert res["status"] == "success"
        generated_filename = res["filename"]

        # Assert filename matches pure 32-char hex UUID + extension
        uuid_pattern = re.compile(r"^[a-f0-9]{32}\.(jpg|jpeg|png|webp|bmp)$")
        assert uuid_pattern.match(generated_filename), f"Non-UUID filename generated: {generated_filename}"

        # Assert no traversal characters in URL or filename
        assert ".." not in generated_filename
        assert "/" not in generated_filename
        assert "\\" not in generated_filename
        assert "\x00" not in generated_filename

        # Assert file is strictly inside settings.UPLOAD_DIR/memories
        target_dir = (Path(settings.UPLOAD_DIR) / "memories").resolve()
        file_path = (target_dir / generated_filename).resolve()

        assert file_path.exists()
        assert str(file_path).startswith(str(target_dir))

        # Clean up
        file_path.unlink(missing_ok=True)

    def test_delete_upload_file_path_traversal_rejection(self):
        """Verify delete_upload_file guards against path traversal and outside deletions."""
        # Non-upload prefix
        assert upload_service.delete_upload_file("/etc/passwd") is False
        assert upload_service.delete_upload_file("C:\\Windows\\win.ini") is False
        assert upload_service.delete_upload_file("") is False
        assert upload_service.delete_upload_file(None) is False

        # Directory traversal escaping /uploads
        assert upload_service.delete_upload_file("/uploads/../../../../etc/passwd") is False
        assert upload_service.delete_upload_file("/uploads/memories/../../yatra_sathi.db") is False
        assert upload_service.delete_upload_file("/uploads/places/..\\..\\backend\\app\\main.py") is False
        assert upload_service.delete_upload_file("/uploads/%2e%2e%2fsecret.txt") is False

        # Legitimate delete should succeed
        res = upload_service.save_upload_file(VALID_PNG, "legit.png", category="avatars")
        url = res["url"]
        assert upload_service.delete_upload_file(url) is True
        # Second delete should return False (already unlinked)
        assert upload_service.delete_upload_file(url) is False


# =============================================================================
# 5. Category Spoofing & Isolation
# =============================================================================
class TestCategorySpoofing:
    """
    Adversarial verification testing invalid categories, traversal categories,
    and alias normalization.
    """

    INVALID_CATEGORIES = [
        "system",
        "../secrets",
        "..\\..\\Windows",
        "/etc",
        "admin",
        "root",
        "uploads",
        ".",
        "..",
        "\\",
        "exec",
        "config",
        "passwords",
    ]

    @pytest.mark.parametrize("bad_cat", INVALID_CATEGORIES)
    def test_invalid_categories_rejected_with_http_400(self, bad_cat):
        """Verify unapproved categories raise HTTP 400 Bad Request."""
        mock_file = MockUploadFile(io.BytesIO(VALID_JPEG), filename="test.jpg")
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_photo(file=mock_file, category=bad_cat))
        assert exc_info.value.status_code == 400
        assert f"Invalid category '{bad_cat}'" in exc_info.value.detail

    @pytest.mark.parametrize("alias,expected", [
        ("memories", "memories"),
        ("memory", "memories"),
        ("places", "places"),
        ("place", "places"),
        ("avatars", "avatars"),
        ("avatar", "avatars"),
        ("trail_reports", "trail_reports"),
        ("trail-reports", "trail_reports"),
        ("trail_watch", "trail_reports"),
        ("trail-watch", "trail_reports"),
        (" MEMORIES ", "memories"),
        ("Places", "places"),
        ("", "memories"),
        (None, "memories"),
    ])
    def test_category_normalization(self, alias, expected):
        """Verify alias normalization correctly resolves canonical categories."""
        assert normalize_category(alias) == expected


# =============================================================================
# 6. Concurrency Stress (Zero Collision & Race Conditions)
# =============================================================================
class TestConcurrencyStress:
    """
    Adversarial stress testing running 10 rapid concurrent image uploads
    to verify thread safety, collision resistance, and data integrity.
    """

    def test_ten_rapid_concurrent_uploads(self):
        """
        Execute 10 concurrent image uploads in parallel threads.
        Assert:
        - All 10 uploads succeed (HTTP 200)
        - All 10 generated filenames are strictly unique (0 collisions)
        - All 10 files exist on disk with exact matching byte contents
        """
        num_workers = 10
        created_files = []

        def _worker_task(worker_id: int) -> Dict[str, Any]:
            # Generate unique payload per worker (JPEG header + unique marker bytes)
            worker_marker = f"WORKER_{worker_id}_{uuid.uuid4().hex}".encode("ascii")
            worker_payload = VALID_JPEG[:-2] + worker_marker + b"\xff\xd9"

            mock_file = MockUploadFile(
                io.BytesIO(worker_payload),
                filename=f"worker_{worker_id}.jpg"
            )
            result = _run_coro(
                upload_photo(
                    file=mock_file,
                    category="memories",
                    caption=f"Concurrent upload from worker {worker_id}"
                )
            )
            result["expected_bytes"] = worker_payload
            result["worker_id"] = worker_id
            return result

        results = []
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_worker_task, i) for i in range(num_workers)]
            for future in as_completed(futures):
                results.append(future.result())

        assert len(results) == num_workers

        # Check uniqueness of filenames
        filenames = [r["filename"] for r in results]
        assert len(set(filenames)) == num_workers, f"UUID collision detected in concurrent uploads! {filenames}"

        # Check uniqueness of URLs
        urls = [r["url"] for r in results]
        assert len(set(urls)) == num_workers, "URL collision detected in concurrent uploads!"

        # Verify disk integrity for each uploaded file
        for res in results:
            saved_path = Path(settings.UPLOAD_DIR) / "memories" / res["filename"]
            created_files.append(saved_path)

            assert saved_path.exists(), f"Uploaded file missing from disk: {saved_path}"
            disk_bytes = saved_path.read_bytes()
            assert disk_bytes == res["expected_bytes"], f"Byte mismatch on disk for worker {res['worker_id']}"
            assert res["status"] == "success"

        # Cleanup
        for path in created_files:
            path.unlink(missing_ok=True)


# =============================================================================
# 7. Destination Place Photo Contribution Adversarial Vector (POST /places/{id}/photos)
# =============================================================================
@pytest.fixture(scope="function")
def db_session():
    """Provide clean database session with guaranteed test place."""
    session = TestSessionLocal()
    if session.query(Place).count() == 0:
        p = Place(
            id=uuid.uuid4(),
            name="Pashupatinath Temple Complex",
            category="Religious Site",
            group="Religious",
            centroid="POINT(85.3487 27.7105)",
            bbox_min_lat=27.7105,
            bbox_max_lat=27.7105,
            bbox_min_lon=85.3487,
            bbox_max_lon=85.3487,
            popularity=95.0,
            rating=4.9,
            is_hidden_gem=False
        )
        session.add(p)
        session.commit()
    yield session
    session.close()


class TestPlacePhotoContributionAdversarial:
    """
    Adversarial verification testing place photo contribution endpoint against
    corrupted payloads, oversized payloads, invalid place IDs, and cover photo state.
    """

    def test_place_photo_rejects_spoofed_text(self, db_session):
        """Verify POST /places/{id}/photos rejects fake text JPEG with HTTP 400."""
        place = db_session.query(Place).first()
        assert place is not None

        mock_file = MockUploadFile(io.BytesIO(b"Hello world fake image"), filename="spoofed.jpg")
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_place_photo(id=str(place.id), file=mock_file, db=db_session, user=make_test_user(db_session, admin=True)))
        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in exc_info.value.detail

    def test_place_photo_rejects_truncated_magic(self, db_session):
        """Verify POST /places/{id}/photos rejects truncated PNG magic with HTTP 400."""
        place = db_session.query(Place).first()
        mock_file = MockUploadFile(io.BytesIO(b"\x89PNG\r\n\x1a"), filename="truncated.png")
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_place_photo(id=str(place.id), file=mock_file, db=db_session, user=make_test_user(db_session, admin=True)))
        assert exc_info.value.status_code == 400
        assert "Unsupported file format" in exc_info.value.detail

    def test_place_photo_rejects_empty_payload(self, db_session):
        """Verify POST /places/{id}/photos rejects 0-byte payload with HTTP 400."""
        place = db_session.query(Place).first()
        mock_file = MockUploadFile(io.BytesIO(b""), filename="zero.jpg")
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_place_photo(id=str(place.id), file=mock_file, db=db_session, user=make_test_user(db_session, admin=True)))
        assert exc_info.value.status_code == 400
        assert "empty or corrupted" in exc_info.value.detail.lower()

    def test_place_photo_rejects_oversized_payload(self, db_session):
        """Verify POST /places/{id}/photos rejects payload > 10MB with HTTP 413."""
        place = db_session.query(Place).first()
        huge_bytes = VALID_JPEG + (b"\x00" * (11 * 1024 * 1024))
        mock_file = MockUploadFile(io.BytesIO(huge_bytes), filename="oversized.jpg")
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_place_photo(id=str(place.id), file=mock_file, db=db_session, user=make_test_user(db_session, admin=True)))
        assert exc_info.value.status_code == 413
        assert "exceeds maximum allowed limit" in exc_info.value.detail

    def test_place_photo_rejects_invalid_uuid_string(self, db_session):
        """Verify POST /places/{id}/photos rejects malformed UUID with HTTP 400."""
        mock_file = MockUploadFile(io.BytesIO(VALID_JPEG), filename="photo.jpg")
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_place_photo(id="not-a-valid-uuid", file=mock_file, db=db_session, user=make_test_user(db_session, admin=True)))
        assert exc_info.value.status_code == 400
        assert "Invalid place ID format" in exc_info.value.detail

    def test_place_photo_rejects_nonexistent_place(self, db_session):
        """Verify POST /places/{id}/photos returns 404 for non-existent place UUID."""
        random_uuid = str(uuid.uuid4())
        mock_file = MockUploadFile(io.BytesIO(VALID_JPEG), filename="photo.jpg")
        with pytest.raises(HTTPException) as exc_info:
            _run_coro(upload_place_photo(id=random_uuid, file=mock_file, db=db_session, user=make_test_user(db_session, admin=True)))
        assert exc_info.value.status_code == 404
        assert "Place not found" in exc_info.value.detail

    def test_place_photo_path_traversal_filename_sanitized(self, db_session):
        """Verify place photo upload with traversal filename persists cleanly as UUID in places/."""
        place = db_session.query(Place).first()
        mock_file = MockUploadFile(io.BytesIO(VALID_PNG), filename="../../../../var/www/exploit.png")
        res = _run_coro(upload_place_photo(
            id=str(place.id),
            file=mock_file,
            caption="Exploit test",
            is_cover=False,
            db=db_session, user=make_test_user(db_session, admin=True)))

        assert res["place_id"] == str(place.id)
        assert res["image_url"].startswith("/uploads/places/")
        assert ".." not in res["image_url"]

        filename = Path(res["image_url"]).name
        uuid_pattern = re.compile(r"^[a-f0-9]{32}\.png$")
        assert uuid_pattern.match(filename)

        # Cleanup
        saved_file = Path(settings.UPLOAD_DIR) / "places" / filename
        saved_file.unlink(missing_ok=True)
