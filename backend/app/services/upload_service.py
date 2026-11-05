"""
Upload and storage engine service for YatraSathi platform.
Handles binary image signature validation, safe UUID-based disk persistence,
and static metadata generation.
"""
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import HTTPException, UploadFile
from backend.app.config.settings import settings

# Supported binary magic signatures
# JPEG: starts with \xFF\xD8\xFF
# PNG: starts with \x89PNG\r\n\x1a\n (\x89\x50\x4E\x47\x0D\x0A\x1A\x0A)
# WebP: starts with RIFF (bytes 0-4) and WEBP (bytes 8-12)
# BMP: starts with BM (\x42\x4D)
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
RIFF_MAGIC = b"RIFF"
WEBP_MAGIC = b"WEBP"
BMP_MAGIC = b"BM"

MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/bmp": "bmp",
}

ALLOWED_CATEGORIES = {"memories", "places", "avatars", "trail_reports"}

CATEGORY_ALIASES = {
    "memories": "memories",
    "memory": "memories",
    "places": "places",
    "place": "places",
    "avatars": "avatars",
    "avatar": "avatars",
    "trail_reports": "trail_reports",
    "trail-reports": "trail_reports",
    "trail_watch": "trail_reports",
    "trail-watch": "trail_reports",
}


async def read_upload_capped(upload: Optional[UploadFile], max_bytes: Optional[int] = None) -> bytes:
    """
    Read an UploadFile while never holding more than ``max_bytes + 1`` bytes
    in memory, raising 413 if the payload exceeds the limit and 400 if empty.

    Starlette has already spooled the body to a temp file; this bounds what we
    load into RAM. The request-level Content-Length check in ``main.py``
    rejects most oversized bodies before they reach this point.
    """
    if upload is None:
        raise HTTPException(status_code=400, detail="No file provided")

    limit = max_bytes or settings.MAX_UPLOAD_SIZE_BYTES
    too_large = HTTPException(
        status_code=413,
        detail=f"File size exceeds maximum allowed limit of {limit // (1024 * 1024)}MB",
    )

    known_size = getattr(upload, "size", None)
    if isinstance(known_size, int) and known_size > limit:
        raise too_large

    data = await upload.read(limit + 1)
    if not data:
        raise HTTPException(status_code=400, detail="File is empty or corrupted")
    if len(data) > limit:
        raise too_large
    return data


def normalize_category(category: str) -> str:
    """Normalize and validate category names against allowed categories."""
    if not category:
        return "memories"
    normalized = category.strip().lower()
    return CATEGORY_ALIASES.get(normalized, normalized)


def validate_image_file(file_bytes: bytes, filename: str) -> str:
    """
    Validate binary image content against supported magic byte signatures and size limits.

    Supported formats:
    - JPEG (starts with \\xFF\\xD8\\xFF)
    - PNG (starts with \\x89PNG\\r\\n\\x1a\\n)
    - WebP (RIFF....WEBP header)
    - BMP (starts with BM)

    Raises:
    - HTTPException 400: If file is empty or binary signature is unsupported.
    - HTTPException 413: If file size exceeds MAX_UPLOAD_SIZE_BYTES.

    Returns:
    - Detected MIME type string (e.g. 'image/jpeg', 'image/png', 'image/webp', 'image/bmp')
    """
    if not file_bytes or len(file_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty or corrupted"
        )

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File size exceeds maximum allowed limit of 10MB"
        )

    # Validate Magic Bytes / File Signatures
    if file_bytes.startswith(JPEG_MAGIC):
        return "image/jpeg"

    if file_bytes.startswith(PNG_MAGIC):
        return "image/png"

    if len(file_bytes) >= 12 and file_bytes[:4] == RIFF_MAGIC and file_bytes[8:12] == WEBP_MAGIC:
        return "image/webp"

    if file_bytes.startswith(BMP_MAGIC):
        return "image/bmp"

    raise HTTPException(
        status_code=400,
        detail="Unsupported file format. Supported formats: JPEG, PNG, WebP, BMP"
    )


def save_upload_file(
    file_bytes: bytes,
    filename: str,
    category: str = "memories",
    mime_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Persist validated image file to disk under settings.UPLOAD_DIR/{category}.

    Generates a secure UUID4 filename, auto-creates target directories,
    writes the binary payload to disk, and returns metadata with relative HTTP URL.
    """
    detected_mime = mime_type or validate_image_file(file_bytes, filename)
    clean_category = normalize_category(category)

    if clean_category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Valid categories are: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    # Determine safe file extension
    ext = MIME_TO_EXT.get(detected_mime, "bin")
    raw_ext = Path(filename).suffix.lower().lstrip(".")
    if detected_mime == "image/jpeg" and raw_ext in ("jpg", "jpeg"):
        ext = raw_ext

    # Generate secure UUID filename to prevent path traversal
    safe_filename = f"{uuid.uuid4().hex}.{ext}"

    # Ensure target directory exists
    target_dir = Path(settings.UPLOAD_DIR) / clean_category
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / safe_filename
    with open(target_path, "wb") as f:
        f.write(file_bytes)

    relative_url = f"/uploads/{clean_category}/{safe_filename}"
    base = settings.PUBLIC_BASE_URL.rstrip("/")

    return {
        "status": "success",
        "filename": safe_filename,
        "url": f"{base}{relative_url}" if base else relative_url,
        "path": relative_url,
        "content_type": detected_mime,
        "size_bytes": len(file_bytes),
        "category": clean_category,
    }


class UploadService:
    """Class wrapper providing upload service operations."""

    @staticmethod
    def validate_image_file(file_bytes: bytes, filename: str) -> str:
        return validate_image_file(file_bytes, filename)

    @staticmethod
    def save_upload_file(
        file_bytes: bytes,
        filename: str,
        category: str = "memories",
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        return save_upload_file(file_bytes, filename, category, mime_type)

    @staticmethod
    def delete_upload_file(relative_url: str) -> bool:
        """Safely delete an uploaded file by relative URL, guarding against path traversal."""
        try:
            if not relative_url or not relative_url.startswith("/uploads/"):
                return False
            subpath = relative_url.replace("/uploads/", "", 1).lstrip("/")
            full_path = (Path(settings.UPLOAD_DIR) / subpath).resolve()
            upload_dir_resolved = Path(settings.UPLOAD_DIR).resolve()
            # Ensure path does not escape upload directory
            if not str(full_path).startswith(str(upload_dir_resolved)):
                return False
            if full_path.is_file():
                full_path.unlink()
                return True
        except Exception:
            return False
        return False


upload_service = UploadService()
