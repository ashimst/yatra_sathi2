"""
Recommendation API Endpoints
Handles route-based recommendations with buffer and embedding ranking
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from backend.app.services.recommendation_service import recommendation_service


router = APIRouter(prefix="/recommend", tags=["recommend"])


class RecommendRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    corridor_km: Optional[float] = 20
    limit: Optional[int] = None  # Will be calculated dynamically if not provided
    user_preferences: Optional[List[str]] = None
    dietary_preferences: Optional[List[str]] = None
    num_adults: Optional[int] = 1
    num_children: Optional[int] = 0
    travel_season: Optional[str] = None
    generate_itinerary: Optional[bool] = False
    num_days: Optional[int] = 3
    travel_style: Optional[str] = "balanced"
    budget: Optional[str] = "medium"


@router.post("")
async def get_recommendations(request: RecommendRequest):
    """
    Get recommendations along a route corridor.
    
    This endpoint:
    1. Gets the route from OSRM between origin and destination
    2. Creates a buffer around the route (default 20km)
    3. Queries POIs from the database that fall within the buffer
    4. If generate_itinerary is True, uses LLM to create a coherent day-by-day itinerary
    5. Otherwise, ranks POIs based on user preferences, popularity, rating, etc.
    6. Returns the route with recommendations or itinerary
    
    Args:
        request: Recommendation request with coordinates and parameters
    
    Returns:
        Route data with ranked recommendations or coherent itinerary
    """
    try:
        # Calculate dynamic limit if not provided
        limit = request.limit
        if limit is None:
            # Provide enough candidates for multi-day itineraries (10 per day)
            limit = request.num_days * 10
            print(f"[INFO] Dynamic limit calculated: {limit} (based on {request.num_days} days)")
        
        result = await recommendation_service.get_route_recommendations(
            request.origin_lat,
            request.origin_lng,
            request.dest_lat,
            request.dest_lng,
            request.corridor_km,
            limit,
            request.user_preferences,  # interests
            request.dietary_preferences,
            request.num_adults,
            request.num_children,
            None,  # preferred_start_time
            request.travel_style,  # pace
            request.budget,
            request.travel_season,
            request.generate_itinerary,
            request.num_days
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_recommendations_get(
    origin_lat: float = Query(..., description="Origin latitude"),
    origin_lng: float = Query(..., description="Origin longitude"),
    dest_lat: float = Query(..., description="Destination latitude"),
    dest_lng: float = Query(..., description="Destination longitude"),
    corridor_km: float = Query(20, description="Buffer radius in kilometers"),
    limit: Optional[int] = Query(None, description="Maximum number of recommendations (calculated dynamically if not provided)"),
    user_preferences: Optional[str] = Query(None, description="Comma-separated user preferences"),
    dietary_preferences: Optional[str] = Query(None, description="Comma-separated dietary preferences (Veg, Non-veg, Vegan, etc.)"),
    num_adults: int = Query(1, description="Number of adult travelers"),
    num_children: int = Query(0, description="Number of children traveling"),
    travel_season: Optional[str] = Query(None, description="Travel season: spring, summer, autumn, winter"),
    generate_itinerary: bool = Query(False, description="Generate coherent itinerary using LLM"),
    num_days: int = Query(3, description="Number of days for itinerary"),
    travel_style: str = Query("balanced", description="Travel style: relaxed, balanced, packed"),
    budget: str = Query("medium", description="Budget level: low, medium, high")
):
    """
    GET endpoint for recommendations (for easier browser testing).
    
    Args:
        origin_lat: Origin latitude
        origin_lng: Origin longitude
        dest_lat: Destination latitude
        dest_lng: Destination longitude
        corridor_km: Buffer radius in kilometers
        limit: Maximum number of recommendations (calculated as num_days * 10 if not provided)
        user_preferences: Comma-separated preference tags
        dietary_preferences: Comma-separated dietary restrictions
        num_adults: Number of adult travelers
        num_children: Number of children (affects family-friendly filtering)
        travel_season: Season of travel for seasonal matching
        generate_itinerary: Generate coherent itinerary using LLM
        num_days: Number of days for itinerary
        travel_style: Travel style (relaxed, balanced, packed)
        budget: Budget level (low, medium, high)
    
    Returns:
        Route data with ranked recommendations or coherent itinerary
    """
    try:
        # Parse user preferences if provided
        prefs = None
        if user_preferences:
            prefs = [p.strip() for p in user_preferences.split(",")]

        # Parse dietary preferences if provided
        dietary_prefs = None
        if dietary_preferences:
            dietary_prefs = [p.strip() for p in dietary_preferences.split(",")]
        
        # Calculate dynamic limit if not provided
        if limit is None:
            # Provide enough candidates for multi-day itineraries (10 per day)
            limit = num_days * 10
            print(f"[INFO] Dynamic limit calculated: {limit} (based on {num_days} days)")
        
        result = await recommendation_service.get_route_recommendations(
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
            corridor_km,
            limit,
            prefs,  # interests
            dietary_prefs,
            num_adults,
            num_children,
            None,  # preferred_start_time
            travel_style,  # pace
            budget,
            travel_season,
            generate_itinerary,
            num_days
        )
        return result
    except Exception as e:
        print(f"[ERROR] API endpoint error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
