"""
Places API endpoints.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from backend.app.services.place_service import place_service

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
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{place_id}")
async def get_place(place_id: str):
    """Get a specific place by ID."""
    place = place_service.get_place(place_id)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


@router.get("/categories/list")
async def get_categories():
    """Get all categories with counts."""
    return {"categories": place_service.get_categories()}
