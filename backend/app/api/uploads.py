"""
Uploads API Router for YatraSathi platform.
Exposes multipart image upload endpoints for places, memories, avatars, and trail watch.
All uploads require an authenticated traveler (guest accounts count).
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from backend.app.config.settings import settings
from backend.app.core.deps import get_current_user
from backend.app.core.rate_limit import rate_limit
from backend.app.models.user import User
from backend.app.services.upload_service import (
    ALLOWED_CATEGORIES,
    normalize_category,
    read_upload_capped,
    upload_service,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])

_UPLOAD_LIMIT = [rate_limit("upload", settings.RATE_LIMIT_UPLOAD)]


@router.post("/photo", status_code=status.HTTP_200_OK, response_model=Dict[str, Any], dependencies=_UPLOAD_LIMIT)
@router.post("", status_code=status.HTTP_200_OK, response_model=Dict[str, Any], include_in_schema=False, dependencies=_UPLOAD_LIMIT)
@router.post("/", status_code=status.HTTP_200_OK, response_model=Dict[str, Any], include_in_schema=False, dependencies=_UPLOAD_LIMIT)
async def upload_photo(
    file: UploadFile = File(..., description="Binary image file (JPEG, PNG, WebP, BMP)"),
    category: Optional[str] = Form(None, description="Upload target category (memories, places, avatars, trail_reports)"),
    category_query: Optional[str] = Query(None, alias="category", description="Upload target category via query parameter"),
    entity_id: Optional[str] = Form(None, max_length=64, description="Optional UUID string of related entity"),
    caption: Optional[str] = Form(None, max_length=1000, description="Optional image caption or title"),
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Upload and persist an image file.
    Validates binary file signature (JPEG, PNG, WebP, BMP), enforces the size
    limit while streaming, and returns the stored file's URL.
    """
    raw_cat = category or category_query or "memories"
    clean_cat = normalize_category(raw_cat)
    if clean_cat not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category '{raw_cat[:50]}'. Valid categories are: {', '.join(sorted(ALLOWED_CATEGORIES))}",
        )

    file_bytes = await read_upload_capped(file)

    filename = file.filename or "uploaded_image.bin"
    mime_type = upload_service.validate_image_file(file_bytes, filename)

    result = upload_service.save_upload_file(
        file_bytes=file_bytes,
        filename=filename,
        category=clean_cat,
        mime_type=mime_type,
    )

    if entity_id:
        result["entity_id"] = entity_id
    if caption:
        result["caption"] = caption

    return result


@router.get("/categories", response_model=Dict[str, List[str]])
async def list_upload_categories() -> Dict[str, List[str]]:
    """List valid upload category namespaces."""
    return {"categories": sorted(list(ALLOWED_CATEGORIES))}
