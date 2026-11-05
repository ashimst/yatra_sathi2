"""
Route API Endpoints
Handles routing requests using OSRM.
"""
import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from backend.app.services.route_service import route_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/route", tags=["route"])

Profile = Literal["driving", "walking", "cycling"]


class RouteRequest(BaseModel):
    origin_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    origin_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    dest_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    dest_lng: Optional[float] = Field(default=None, ge=-180, le=180)
    profile: Profile = "driving"
    # [[lng, lat], [lng, lat], ...]; only the first and last points are routed.
    waypoints: Optional[List[List[float]]] = Field(default=None, min_length=2, max_length=50)

    @model_validator(mode="after")
    def _resolve_endpoints(self) -> "RouteRequest":
        if self.waypoints:
            for pt in (self.waypoints[0], self.waypoints[-1]):
                if len(pt) != 2 or not (-180 <= pt[0] <= 180 and -90 <= pt[1] <= 90):
                    raise ValueError("Each waypoint must be [lng, lat] with valid ranges.")
            self.origin_lng, self.origin_lat = self.waypoints[0]
            self.dest_lng, self.dest_lat = self.waypoints[-1]
        if None in (self.origin_lat, self.origin_lng, self.dest_lat, self.dest_lng):
            raise ValueError("Either origin/dest coordinates or waypoints must be provided.")
        return self


async def _route(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, profile: str):
    try:
        return await route_service.get_route(origin_lat, origin_lng, dest_lat, dest_lng, profile)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Routing failed")
        raise HTTPException(status_code=502, detail="Routing service is unavailable. Please try again.")


@router.post("")
async def get_route(request: RouteRequest):
    """Get route between two points using OSRM."""
    return await _route(request.origin_lat, request.origin_lng, request.dest_lat, request.dest_lng, request.profile)


@router.get("")
async def get_route_get(
    origin_lat: float = Query(..., ge=-90, le=90, description="Origin latitude"),
    origin_lng: float = Query(..., ge=-180, le=180, description="Origin longitude"),
    dest_lat: float = Query(..., ge=-90, le=90, description="Destination latitude"),
    dest_lng: float = Query(..., ge=-180, le=180, description="Destination longitude"),
    profile: Profile = Query("driving", description="Routing profile (driving, walking, cycling)"),
):
    """GET endpoint for route (for easier browser testing)."""
    return await _route(origin_lat, origin_lng, dest_lat, dest_lng, profile)
