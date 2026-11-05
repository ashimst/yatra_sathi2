"""
Places API endpoints.
"""
from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Form, Depends, status
from typing import Optional, List
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.services.place_service import place_service
from backend.app.services.upload_service import upload_service, read_upload_capped
from backend.app.config.settings import settings
from backend.app.core.deps import get_current_user, is_admin
from backend.app.core.rate_limit import rate_limit
from backend.app.db.database import get_db
from backend.app.models.place import Place
from backend.app.models.place_photo import PlacePhoto
from backend.app.models.user import User

router = APIRouter(prefix="/places", tags=["places"])


@router.get("")
async def get_places(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get all places with optional category filter."""
    return place_service.get_all_places(category, limit, offset)


@router.get("/search")
async def search_places(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Search places by query string."""
    return place_service.search_places(q, limit, offset)


@router.get("/geocode")
async def geocode_place(
    q: Optional[str] = Query(None, description="Location name in Nepal to geocode"),
    query: Optional[str] = Query(None, description="Alternative alias for location query")
):
    """Universal geocoding endpoint for any Nepal city, district, or landmark."""
    target = q or query or "Kathmandu"
    return place_service.geocode_location(target)


@router.get("/nearby")
async def nearby_places(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: float = Query(10.0, description="Radius in km"),
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Find places near a location."""
    try:
        return place_service.get_nearby_places(lat, lng, radius, category, limit, offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))  # ValueError messages are user-facing validation text


@router.get("/categories/list")
async def get_categories():
    """Get all categories with counts."""
    return {"categories": place_service.get_categories()}


@router.get("/{place_id}")
async def get_place(place_id: str):
    """Get a specific place by ID."""
    place = place_service.get_place(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


@router.post(
    "/{id}/photos",
    status_code=status.HTTP_201_CREATED,
    dependencies=[rate_limit("upload", settings.RATE_LIMIT_UPLOAD)],
)
async def upload_place_photo(
    id: str,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    is_cover: Optional[bool] = Form(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a photographic contribution for a destination place.
    Requires authentication. Only administrators may set the place's cover image.
    Validates binary image magic bytes and file size, saves to uploads/places/,
    persists PlacePhoto record in the database, and returns 201 Created.
    """
    try:
        place_uuid = uuid.UUID(id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid place ID format")

    is_cover_bool = bool(is_cover)
    if is_cover_bool and not is_admin(user):
        raise HTTPException(status_code=403, detail="Only administrators can set a place's cover photo.")

    place = db.query(Place).filter(Place.id == place_uuid).first()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    # Streams with a size cap (413); upload_service then validates magic bytes (400).
    content = await read_upload_capped(file)

    upload_res = upload_service.save_upload_file(
        file_bytes=content,
        filename=file.filename or "photo.jpg",
        category="places"
    )

    photo = PlacePhoto(
        id=uuid.uuid4(),
        place_id=place_uuid,
        user_id=user.id,
        image_url=upload_res["url"],
        caption=caption,
        is_cover=is_cover_bool,
        created_at=datetime.now(timezone.utc)
    )
    db.add(photo)

    # If marked as cover photo, update place.image_url and gallery
    if is_cover_bool:
        place.image_url = upload_res["url"]
        if place.gallery is None:
            place.gallery = [upload_res["url"]]
        elif isinstance(place.gallery, list) and upload_res["url"] not in place.gallery:
            place.gallery = [upload_res["url"]] + place.gallery

    db.commit()
    db.refresh(photo)

    return photo.to_dict()


@router.get("/{id}/photos")
async def get_place_photos(
    id: str,
    db: Session = Depends(get_db)
):
    """Get all photos contributed for a destination place."""
    try:
        place_uuid = uuid.UUID(id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid place ID format")

    photos = (
        db.query(PlacePhoto)
        .filter(PlacePhoto.place_id == place_uuid)
        .order_by(PlacePhoto.created_at.desc())
        .all()
    )
    return {"photos": [p.to_dict() for p in photos]}
