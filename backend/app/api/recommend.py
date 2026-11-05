"""
Recommendation API Endpoints
Handles route-based recommendations with buffer and embedding ranking.
"""
import logging
from typing import Annotated, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, BeforeValidator, Field

from backend.app.services.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommend", tags=["recommend"])

# Clients use friendly labels ("Fast-paced", "High Adventure", "Economy",
# "Luxury"); map them onto the values the recommender understands. Unknown
# values are rejected (422) instead of being silently ignored.
_PACE_ALIASES = {
    "relaxed": "relaxed",
    "balanced": "balanced",
    "packed": "packed",
    "fast-paced": "packed",
    "fast paced": "packed",
    "fast": "packed",
    "high adventure": "packed",
    "adventure": "packed",
}
_BUDGET_ALIASES = {
    "low": "low",
    "economy": "low",
    "budget": "low",
    "medium": "medium",
    "mid-range": "medium",
    "moderate": "medium",
    "high": "high",
    "luxury": "high",
    "premium": "high",
}


def _alias(mapping: dict):
    def _normalize(value):
        if isinstance(value, str):
            return mapping.get(value.strip().lower(), value)
        return value
    return BeforeValidator(_normalize)


Pace = Annotated[Literal["relaxed", "balanced", "packed"], _alias(_PACE_ALIASES)]
Budget = Annotated[Literal["low", "medium", "high"], _alias(_BUDGET_ALIASES)]

MAX_DAYS = 14
MAX_LIMIT = 100
DEFAULT_CORRIDOR_KM = 15.0  # Captures worthwhile en-route stops


def _default_limit(num_days: int) -> int:
    # Enough candidates for multi-day itineraries (10 per day).
    return min(num_days * 10, MAX_LIMIT)


def _split_csv(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    return [p.strip() for p in value.split(",") if p.strip()][:20]


class RecommendRequest(BaseModel):
    origin_lat: float = Field(ge=-90, le=90)
    origin_lng: float = Field(ge=-180, le=180)
    dest_lat: float = Field(ge=-90, le=90)
    dest_lng: float = Field(ge=-180, le=180)
    corridor_km: float = Field(default=DEFAULT_CORRIDOR_KM, gt=0, le=50)
    limit: Optional[int] = Field(default=None, ge=1, le=MAX_LIMIT)
    user_preferences: Optional[List[str]] = Field(default=None, max_length=20)
    dietary_preferences: Optional[List[str]] = Field(default=None, max_length=10)
    num_adults: int = Field(default=1, ge=1, le=50)
    num_children: int = Field(default=0, ge=0, le=50)
    travel_season: Optional[str] = Field(default=None, max_length=20)
    generate_itinerary: bool = False
    num_days: int = Field(default=3, ge=1, le=MAX_DAYS)
    travel_style: Pace = "balanced"
    budget: Budget = "medium"


async def _run(
    *,
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    corridor_km: float,
    limit: Optional[int],
    interests: Optional[List[str]],
    dietary: Optional[List[str]],
    num_adults: int,
    num_children: int,
    travel_season: Optional[str],
    generate_itinerary: bool,
    num_days: int,
    pace: str,
    budget: str,
):
    try:
        return await recommendation_service.get_route_recommendations(
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
            corridor_km,
            limit or _default_limit(num_days),
            interests,
            dietary,
            num_adults,
            num_children,
            None,  # preferred_start_time
            pace,
            budget,
            travel_season,
            generate_itinerary,
            num_days,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Recommendation generation failed")
        raise HTTPException(status_code=500, detail="Could not generate recommendations. Please try again.")


@router.post("")
async def get_recommendations(request: RecommendRequest):
    """
    Get recommendations along a route corridor.

    1. Gets the route from OSRM between origin and destination
    2. Creates a buffer of ``corridor_km`` around the route
    3. Queries POIs from the database that fall within the buffer
    4. If generate_itinerary is True, builds a coherent day-by-day itinerary
    5. Otherwise, ranks POIs based on user preferences, popularity, rating, etc.
    """
    return await _run(
        origin_lat=request.origin_lat,
        origin_lng=request.origin_lng,
        dest_lat=request.dest_lat,
        dest_lng=request.dest_lng,
        corridor_km=request.corridor_km,
        limit=request.limit,
        interests=request.user_preferences,
        dietary=request.dietary_preferences,
        num_adults=request.num_adults,
        num_children=request.num_children,
        travel_season=request.travel_season,
        generate_itinerary=request.generate_itinerary,
        num_days=request.num_days,
        pace=request.travel_style,
        budget=request.budget,
    )


@router.get("")
async def get_recommendations_get(
    origin_lat: float = Query(..., ge=-90, le=90, description="Origin latitude"),
    origin_lng: float = Query(..., ge=-180, le=180, description="Origin longitude"),
    dest_lat: float = Query(..., ge=-90, le=90, description="Destination latitude"),
    dest_lng: float = Query(..., ge=-180, le=180, description="Destination longitude"),
    corridor_km: float = Query(DEFAULT_CORRIDOR_KM, gt=0, le=50, description="Buffer radius in kilometers"),
    limit: Optional[int] = Query(None, ge=1, le=MAX_LIMIT, description="Maximum number of recommendations"),
    user_preferences: Optional[str] = Query(None, max_length=500, description="Comma-separated user preferences"),
    dietary_preferences: Optional[str] = Query(None, max_length=200, description="Comma-separated dietary preferences"),
    num_adults: int = Query(1, ge=1, le=50, description="Number of adult travelers"),
    num_children: int = Query(0, ge=0, le=50, description="Number of children traveling"),
    travel_season: Optional[str] = Query(None, max_length=20, description="Travel season: spring, summer, autumn, winter"),
    generate_itinerary: bool = Query(False, description="Generate coherent itinerary"),
    num_days: int = Query(3, ge=1, le=MAX_DAYS, description="Number of days for itinerary"),
    travel_style: Pace = Query("balanced", description="Travel style: relaxed, balanced, packed"),
    budget: Budget = Query("medium", description="Budget level: low, medium, high"),
):
    """GET variant of the recommendation endpoint (for easier browser testing)."""
    return await _run(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        dest_lat=dest_lat,
        dest_lng=dest_lng,
        corridor_km=corridor_km,
        limit=limit,
        interests=_split_csv(user_preferences),
        dietary=_split_csv(dietary_preferences),
        num_adults=num_adults,
        num_children=num_children,
        travel_season=travel_season,
        generate_itinerary=generate_itinerary,
        num_days=num_days,
        pace=travel_style,
        budget=budget,
    )
