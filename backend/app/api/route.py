"""
Route API Endpoints
Handles routing requests using OSRM
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.services.route_service import route_service


router = APIRouter(prefix="/route", tags=["route"])


class RouteRequest(BaseModel):
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lng: Optional[float] = None
    profile: Optional[str] = None
    waypoints: Optional[List[List[float]]] = None


@router.post("")
async def get_route(request: Dict[str, Any]):
    """
    Get route between two points using OSRM.
    
    Args:
        request: Route request with origin and destination coordinates or waypoints
    
    Returns:
        Route data with geometry, distance, and duration
    """
    try:
        # Handle waypoints if provided
        if 'waypoints' in request and request['waypoints']:
            waypoints = request['waypoints']
            # waypoints format: [[lng, lat], [lng, lat], ...]
            origin_lat = waypoints[0][1]
            origin_lng = waypoints[0][0]
            dest_lat = waypoints[-1][1]
            dest_lng = waypoints[-1][0]
        else:
            origin_lat = request.get('origin_lat')
            origin_lng = request.get('origin_lng')
            dest_lat = request.get('dest_lat')
            dest_lng = request.get('dest_lng')
        
        if origin_lat is None or origin_lng is None or dest_lat is None or dest_lng is None:
            raise HTTPException(status_code=400, detail="Either origin/dest coordinates or waypoints must be provided")
        
        profile = request.get('profile', 'driving')
        
        route_data = await route_service.get_route(
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
            profile
        )
        return route_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_route_get(
    origin_lat: float = Query(..., description="Origin latitude"),
    origin_lng: float = Query(..., description="Origin longitude"),
    dest_lat: float = Query(..., description="Destination latitude"),
    dest_lng: float = Query(..., description="Destination longitude"),
    profile: str = Query("driving", description="Routing profile (driving, walking, cycling)")
):
    """
    GET endpoint for route (for easier browser testing).
    
    Args:
        origin_lat: Origin latitude
        origin_lng: Origin longitude
        dest_lat: Destination latitude
        dest_lng: Destination longitude
        profile: Routing profile (driving, walking, cycling)
    
    Returns:
        Route data with geometry, distance, and duration
    """
    try:
        route_data = await route_service.get_route(
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
            profile
        )
        return route_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
