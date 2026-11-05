"""
YatraSathi Adversarial Stress & Penetration Verification Script (Milestone 5 - Challenger 1)
=============================================================================================
Standalone deterministic verification script exercising adversarial attack vectors
against the image upload and storage engine:
1. Signature Spoofing (Fake extensions containing HTML, ELF, PE, PDF, ZIP, TXT, JSON, random bytes)
2. Header Corruption (Truncated/malformed magic bytes for JPEG, PNG, WebP, BMP)
3. Strict Boundary Size Stress (0 bytes, 10MB exact [10,485,760 B], 10MB + 1 byte [10,485,761 B])
4. Path Traversal & Injection (Directory traversal filenames, Windows paths, URL encoding, null bytes)
5. Category Spoofing & Directory Isolation (Invalid categories, traversal categories, aliases)
6. Concurrency Stress (10 rapid concurrent image uploads asserting zero collision)
7. Place Photo Contribution Adversarial Vector (POST /places/{id}/photos)

Usage:
    python scripts/verify_adversarial_upload_stress.py
"""

import io
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure SQLite local database and non-blocking LLM settings
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = f"sqlite:///{PROJECT_ROOT / 'yatra_sathi.db'}"
os.environ["AI_ENABLED"] = "false"
os.environ["DEBUG"] = "false"

from fastapi import UploadFile, HTTPException
from backend.app.config.settings import settings
settings.DATABASE_URL = os.environ["DATABASE_URL"]

from backend.app.db.database import SessionLocal, init_db, engine
from backend.app.models.place import Place
from backend.app.models.place_photo import PlacePhoto
from backend.app.api.uploads import upload_photo
from backend.app.api.places import upload_place_photo
from backend.app.services.upload_service import (
    upload_service,
    validate_image_file,
    save_upload_file,
    normalize_category,
    ALLOWED_CATEGORIES
)


def _run_coro(coro):
    """Execute async coroutine synchronously."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    except Exception as ex:
        raise ex


class MockUploadFile(UploadFile):
    """Synchronous UploadFile mock avoiding thread pool socket deadlocks."""
    def __init__(self, file: io.BytesIO, filename: str = "image.bin", content_type: str = "application/octet-stream"):
        super().__init__(file=file, filename=filename, headers={"content-type": content_type})

    async def read(self, size: int = -1) -> bytes:
        if hasattr(self.file, "seek"):
            self.file.seek(0)
        return self.file.read()


VALID_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
    + b"\x00" * 128
    + b"\xff\xd9"
)

VALID_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def run_verification() -> int:
    start_time = time.time()
    passed = 0
    failed = 0

    print("=" * 80)
    print("YATRASATHI EMPIRICAL ADVERSARIAL STRESS TEST HARNESS (CHALLENGER 1 - M5)")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Test 1: Signature Spoofing
    # -------------------------------------------------------------------------
    spoofed_cases = [
        ("fake.jpg", b"This is plain text pretending to be JPEG.", "plain_text"),
        ("exploit.png", b"<script>alert('xss')</script>", "html_xss"),
        ("malware.webp", b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x3e\x00", "elf_binary"),
        ("trojan.bmp", b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff", "pe_mz_binary"),
        ("doc.jpg", b"%PDF-1.7\n1 0 obj\n<<>>\nendobj", "pdf_document"),
        ("archive.png", b"PK\x03\x04\x14\x00\x00\x00\x08\x00", "zip_archive"),
        ("data.webp", b'{"role": "root", "auth": true}', "json_string"),
        ("noise.bmp", os.urandom(512), "random_entropy"),
    ]

    all_spoofed_rejected = True
    for fname, payload, desc in spoofed_cases:
        try:
            mock = MockUploadFile(io.BytesIO(payload), filename=fname)
            _run_coro(upload_photo(file=mock, category="memories"))
            all_spoofed_rejected = False
            print(f"  [FAIL] Test 1: Spoofed payload '{fname}' ({desc}) was unexpectedly accepted!")
        except HTTPException as exc:
            if exc.status_code != 400 or "Unsupported file format" not in exc.detail:
                all_spoofed_rejected = False
                print(f"  [FAIL] Test 1: Spoofed payload '{fname}' raised wrong error: {exc}")

    if all_spoofed_rejected:
        print(f"  [PASS] Test 1: Signature Spoofing -- All {len(spoofed_cases)} spoofed payloads strictly rejected with HTTP 400")
        passed += 1
    else:
        failed += 1

    # -------------------------------------------------------------------------
    # Test 2: Header Corruption
    # -------------------------------------------------------------------------
    corrupted_cases = [
        ("jpeg_2b.jpg", b"\xff\xd8"),
        ("jpeg_bad3.jpg", b"\xff\xd8\x00"),
        ("png_7b.png", b"\x89PNG\r\n\x1a"),
        ("png_bad_lead.png", b"PNG\r\n\x1a\n"),
        ("webp_riff_only.webp", b"RIFF"),
        ("webp_8b.webp", b"RIFF\x20\x00\x00\x00"),
        ("webp_wave.webp", b"RIFF\x20\x00\x00\x00WAVEfmt "),
        ("bmp_1b.bmp", b"B"),
        ("bmp_ba.bmp", b"BA"),
        ("bmp_rev.bmp", b"MB"),
    ]

    all_corrupt_rejected = True
    for fname, payload in corrupted_cases:
        try:
            mock = MockUploadFile(io.BytesIO(payload), filename=fname)
            _run_coro(upload_photo(file=mock, category="memories"))
            all_corrupt_rejected = False
            print(f"  [FAIL] Test 2: Corrupted header '{fname}' was unexpectedly accepted!")
        except HTTPException as exc:
            if exc.status_code != 400:
                all_corrupt_rejected = False

    if all_corrupt_rejected:
        print(f"  [PASS] Test 2: Header Corruption -- All {len(corrupted_cases)} truncated/malformed headers rejected with HTTP 400")
        passed += 1
    else:
        failed += 1

    # -------------------------------------------------------------------------
    # Test 3: Strict Boundary Size Stress
    # -------------------------------------------------------------------------
    max_size = settings.MAX_UPLOAD_SIZE_BYTES  # 10,485,760 bytes

    # 0 bytes -> HTTP 400
    zero_rejected = False
    try:
        mock_zero = MockUploadFile(io.BytesIO(b""), filename="zero.jpg")
        _run_coro(upload_photo(file=mock_zero, category="memories"))
    except HTTPException as exc:
        if exc.status_code == 400 and "empty or corrupted" in exc.detail.lower():
            zero_rejected = True

    # 10MB exact -> HTTP 200
    ten_mb_header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    ten_mb_trailer = b"\xff\xd9"
    ten_mb_pad = b"\x00" * (max_size - len(ten_mb_header) - len(ten_mb_trailer))
    ten_mb_payload = ten_mb_header + ten_mb_pad + ten_mb_trailer
    assert len(ten_mb_payload) == max_size

    mock_exact = MockUploadFile(io.BytesIO(ten_mb_payload), filename="exact_10mb.jpg")
    exact_res = _run_coro(upload_photo(file=mock_exact, category="memories"))
    exact_succeeded = (exact_res["status"] == "success" and exact_res["size_bytes"] == max_size)
    exact_disk = Path(settings.UPLOAD_DIR) / "memories" / exact_res["filename"]
    exact_file_ok = exact_disk.exists() and exact_disk.stat().st_size == max_size
    exact_disk.unlink(missing_ok=True)

    # 10MB + 1 byte -> HTTP 413
    oversized_payload = ten_mb_payload + b"\x00"
    assert len(oversized_payload) == max_size + 1
    oversized_rejected = False
    try:
        mock_over = MockUploadFile(io.BytesIO(oversized_payload), filename="over_10mb.jpg")
        _run_coro(upload_photo(file=mock_over, category="memories"))
    except HTTPException as exc:
        if exc.status_code == 413 and "exceeds maximum allowed limit" in exc.detail:
            oversized_rejected = True

    if zero_rejected and exact_succeeded and exact_file_ok and oversized_rejected:
        print(f"  [PASS] Test 3: Strict Boundary Size -- 0B -> 400, Exact 10MB ({max_size:,} B) -> 200, 10MB+1B ({max_size+1:,} B) -> 413")
        passed += 1
    else:
        print(f"  [FAIL] Test 3: Boundary size stress failed: zero={zero_rejected}, exact={exact_succeeded}, exact_file={exact_file_ok}, over={oversized_rejected}")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 4: Path Traversal & Injection
    # -------------------------------------------------------------------------
    traversal_names = [
        "../../../../etc/passwd.jpg",
        "..\\..\\Windows\\System32\\cmd.exe.png",
        "%2e%2e%2f%2e%2e%2fetc%2fshadow.webp",
        "....//....//boot.ini.bmp",
        "C:\\Windows\\win.ini.jpg",
        "image.jpg\x00.exe",
    ]

    all_traversals_contained = True
    for t_name in traversal_names:
        mock = MockUploadFile(io.BytesIO(VALID_JPEG), filename=t_name)
        res = _run_coro(upload_photo(file=mock, category="memories"))
        gen_filename = res["filename"]
        if not re.match(r"^[a-f0-9]{32}\.(jpg|jpeg|png|webp|bmp)$", gen_filename):
            all_traversals_contained = False
            print(f"  [FAIL] Test 4: Unsanitized filename: {gen_filename}")
        saved_file = Path(settings.UPLOAD_DIR) / "memories" / gen_filename
        if not saved_file.exists():
            all_traversals_contained = False
        saved_file.unlink(missing_ok=True)

    # delete_upload_file path traversal defense
    del_traversal_ok = (
        upload_service.delete_upload_file("/uploads/../../../../etc/passwd") is False and
        upload_service.delete_upload_file("/uploads/places/..\\..\\main.py") is False and
        upload_service.delete_upload_file("/etc/passwd") is False
    )

    if all_traversals_contained and del_traversal_ok:
        print(f"  [PASS] Test 4: Path Traversal & Injection -- Malicious filenames sanitized to UUIDs; escaping blocked")
        passed += 1
    else:
        print(f"  [FAIL] Test 4: Path traversal protection failed!")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 5: Category Spoofing & Directory Escapes
    # -------------------------------------------------------------------------
    bad_cats = ["system", "../secrets", "..\\..\\Windows", "/etc", "admin", "root", "uploads", ".."]
    all_bad_cats_rejected = True
    for bad_cat in bad_cats:
        try:
            mock = MockUploadFile(io.BytesIO(VALID_JPEG), filename="test.jpg")
            _run_coro(upload_photo(file=mock, category=bad_cat))
            all_bad_cats_rejected = False
        except HTTPException as exc:
            if exc.status_code != 400 or f"Invalid category '{bad_cat}'" not in exc.detail:
                all_bad_cats_rejected = False

    normalization_ok = (
        normalize_category("places") == "places" and
        normalize_category("place") == "places" and
        normalize_category(" MEMORIES ") == "memories" and
        normalize_category("trail_watch") == "trail_reports"
    )

    if all_bad_cats_rejected and normalization_ok:
        print(f"  [PASS] Test 5: Category Spoofing -- Unapproved categories rejected with 400; aliases normalized cleanly")
        passed += 1
    else:
        print(f"  [FAIL] Test 5: Category spoofing validation failed!")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 6: Concurrency Stress (10 rapid concurrent uploads)
    # -------------------------------------------------------------------------
    concurrency_count = 10
    created_paths = []

    def _concurrent_upload_worker(worker_id: int):
        marker = f"CONCURRENCY_TEST_{worker_id}_{uuid.uuid4().hex}".encode("ascii")
        payload = VALID_JPEG[:-2] + marker + b"\xff\xd9"
        mock = MockUploadFile(io.BytesIO(payload), filename=f"concurrent_{worker_id}.jpg")
        res = _run_coro(upload_photo(file=mock, category="memories"))
        res["worker_id"] = worker_id
        res["payload"] = payload
        return res

    with ThreadPoolExecutor(max_workers=concurrency_count) as pool:
        futures = [pool.submit(_concurrent_upload_worker, i) for i in range(concurrency_count)]
        concurrent_results = [f.result() for f in as_completed(futures)]

    filenames = [r["filename"] for r in concurrent_results]
    zero_collisions = (len(filenames) == concurrency_count and len(set(filenames)) == concurrency_count)

    disk_integrity_ok = True
    for r in concurrent_results:
        fpath = Path(settings.UPLOAD_DIR) / "memories" / r["filename"]
        created_paths.append(fpath)
        if not fpath.exists() or fpath.read_bytes() != r["payload"]:
            disk_integrity_ok = False

    for p in created_paths:
        p.unlink(missing_ok=True)

    if zero_collisions and disk_integrity_ok:
        print(f"  [PASS] Test 6: Concurrency Stress -- 10 rapid concurrent uploads completed: 0 collisions, 100% byte fidelity")
        passed += 1
    else:
        print(f"  [FAIL] Test 6: Concurrency stress failed: collisions={not zero_collisions}, disk_ok={disk_integrity_ok}")
        failed += 1

    # -------------------------------------------------------------------------
    # Test 7: Place Photo Contribution Adversarial Vector
    # -------------------------------------------------------------------------
    db = SessionLocal()
    try:
        place = db.query(Place).first()
        if not place:
            place = Place(
                id=uuid.uuid4(),
                name="Test Heritage Place",
                category="Religious Site",
                group="Religious",
                centroid="POINT(85.3 27.7)",
                popularity=80.0,
                rating=4.5
            )
            db.add(place)
            db.commit()

        place_adversarial_ok = True

        # Test fake text rejection
        try:
            mock_text = MockUploadFile(io.BytesIO(b"Not an image"), filename="fake.jpg")
            _run_coro(upload_place_photo(id=str(place.id), file=mock_text, caption=None, is_cover=False, db=db))
            place_adversarial_ok = False
        except HTTPException as e:
            if e.status_code != 400:
                place_adversarial_ok = False

        # Test 0-byte rejection
        try:
            mock_empty = MockUploadFile(io.BytesIO(b""), filename="empty.jpg")
            _run_coro(upload_place_photo(id=str(place.id), file=mock_empty, caption=None, is_cover=False, db=db))
            place_adversarial_ok = False
        except HTTPException as e:
            if e.status_code != 400:
                place_adversarial_ok = False

        # Test oversized rejection
        try:
            mock_huge = MockUploadFile(io.BytesIO(VALID_JPEG + b"\x00" * (11 * 1024 * 1024)), filename="huge.jpg")
            _run_coro(upload_place_photo(id=str(place.id), file=mock_huge, caption=None, is_cover=False, db=db))
            place_adversarial_ok = False
        except HTTPException as e:
            if e.status_code != 413:
                place_adversarial_ok = False

        # Test invalid place ID
        try:
            mock_valid = MockUploadFile(io.BytesIO(VALID_JPEG), filename="valid.jpg")
            _run_coro(upload_place_photo(id="invalid-uuid-id", file=mock_valid, caption=None, is_cover=False, db=db))
            place_adversarial_ok = False
        except HTTPException as e:
            if e.status_code != 400:
                place_adversarial_ok = False

        # Test valid place photo with path traversal filename
        mock_trav = MockUploadFile(io.BytesIO(VALID_PNG), filename="../../../../trav.png")
        place_res = _run_coro(upload_place_photo(id=str(place.id), file=mock_trav, caption="Traversal Test", is_cover=False, db=db))
        if not place_res["image_url"].startswith("/uploads/places/"):
            place_adversarial_ok = False
        p_filename = Path(place_res["image_url"]).name
        if not re.match(r"^[a-f0-9]{32}\.png$", p_filename):
            place_adversarial_ok = False
        (Path(settings.UPLOAD_DIR) / "places" / p_filename).unlink(missing_ok=True)

        if place_adversarial_ok:
            print(f"  [PASS] Test 7: Place Photo Contribution Adversarial Vector -- Corrupt, empty, oversized payloads & malformed IDs rejected")
            passed += 1
        else:
            print(f"  [FAIL] Test 7: Place photo contribution adversarial tests failed!")
            failed += 1
    finally:
        db.close()

    elapsed = time.time() - start_time
    print("=" * 80)
    print(f"ADVERSARIAL STRESS TEST SUMMARY: {passed} PASSED, {failed} FAILED in {elapsed:.2f}s")
    print("=" * 80)

    if failed == 0:
        print("Status: [OK] ALL ADVERSARIAL STRESS TESTS PASSED (100% SUCCESS)")
        return 0
    else:
        print("Status: [FAIL] ADVERSARIAL VULNERABILITIES DETECTED")
        return 1


if __name__ == "__main__":
    sys.exit(run_verification())
