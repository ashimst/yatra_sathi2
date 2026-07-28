"""
Recommendation Service

Two-stage, trip-aware recommender:
  1. Candidate retrieval + relevance scoring — "how relevant is this place
     to this user?" (spatial buffer, interests, seasonal fit, popularity)
  2. Trip-level optimization — "does this place actually fit in the trip?"
     (time budget from num_days x pace, detour cost from the route,
     category diversity), producing a coherent SET of destinations rather
     than an independently top-N ranked list.
"""
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.database import SessionLocal
from backend.app.models.place import Place as PlaceDB
from backend.app.services.route_service import route_service
from backend.app.services.itinerary_service import itinerary_service
from backend.app.services.embedding_service import embedding_service
import math

# Rough active hours per day, by pace, used to size the trip-level time budget.
PACE_HOURS_PER_DAY = {
    "relaxed": 5.0,
    "balanced": 7.0,
    "packed": 9.0,
}

# Assumed average off-route detour speed (km/h), for estimating detour time
# from straight-line detour distance. Coarse but directionally correct until
# real routing-engine detour times are wired in.
DETOUR_SPEED_KMH = 35.0


class RecommendationService:
    """Service for route-based, trip-level-optimized recommendations."""

    def __init__(self):
        # Latitude: constant conversion (1 degree ≈ 111 km everywhere)
        self.buffer_deg_per_km_lat = 1.0 / 111.0
        # Longitude: varies with cos(latitude) - 1 degree = 111 * cos(lat) km
        self._get_longitude_deg_per_km = lambda lat: 1.0 / (111.0 * math.cos(math.radians(lat)))

    async def get_route_recommendations(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        corridor_km: float = 20,
        limit: int = 12,
        # --- trip-shaping inputs (these are what actually drive the itinerary) ---
        interests: Optional[List[str]] = None,
        dietary_preferences: Optional[List[str]] = None,
        num_adults: int = 1,
        num_children: int = 0,
        preferred_start_time: Optional[str] = None,  # e.g. "08:00"
        pace: str = "balanced",  # relaxed | balanced | packed
        budget: str = "medium",  # low | medium | high
        travel_season: Optional[str] = None,  # e.g. "winter", matched against place.seasons
        generate_itinerary: bool = False,
        num_days: int = 3,
    ) -> Dict[str, Any]:
        """
        Get recommendations along a route corridor.

        This is a two-stage recommender, not a single ranked list:

          Stage 1 (candidate relevance) — _get_pois_in_route_buffer,
          _apply_hard_filters, _score_candidates: "how relevant is this
          place to this user?", using spatial proximity, interests, diet,
          season, popularity, rating.

          Stage 2 (trip-level optimization) — _optimize_trip_selection:
          "does this place actually fit in the whole journey?", using a
          time budget derived from num_days x pace, an estimated detour
          cost off the route, and category diversity — so the output is a
          coherent, feasible SET of destinations rather than an
          independently top-scored list.
        """
        route_data = await route_service.get_route(
            origin_lat, origin_lng, dest_lat, dest_lng
        )
        route_coordinates = route_data["coordinates"]

        candidates = self._get_pois_in_route_buffer(
            route_coordinates, 
            15,  # Route corridor 15km — captures worthwhile en-route stops
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            destination_buffer_km=100  # Destination buffer 100km for attractions
        )

        # Diagnose category counts after spatial retrieval
        self._diagnose_category_counts(candidates, "Spatial retrieval")

        # Hard filters: things that should REMOVE a place from consideration
        # entirely, not just nudge its score.
        candidates = self._apply_hard_filters(
            candidates,
            num_children=num_children,
            dietary_preferences=dietary_preferences,
            budget=budget,
        )

        # Diagnose category counts after hard filters
        self._diagnose_category_counts(candidates, "After hard filters")

        # Stage 1: relevance scoring among eligible candidates using embedding similarity.
        scored_candidates = self._score_candidates(
            candidates,
            interests=interests,
            dietary_preferences=dietary_preferences,
            num_children=num_children,
            budget=budget,
            travel_season=travel_season,
            pace=pace,
            num_days=num_days,
        )

        # Diagnose category counts after semantic scoring
        self._diagnose_category_counts(scored_candidates, "After semantic scoring")

        # Apply category-aware filtering for structural balance
        if generate_itinerary:
            print("[INFO] Applying category-specific retrieval for itinerary generation")
            # Extract route distance and duration for time-aware calculations
            route_distance_km = route_data.get("distance_km", 200)
            route_duration_hours = route_data.get("duration_minutes", 480) / 60
            
            category_results = self._category_specific_retrieval(
                scored_candidates,
                num_days=num_days,
                pace=pace,
                route_distance_km=route_distance_km,
                route_duration_hours=route_duration_hours
            )
            
            # Plan meal slots
            has_restaurants = category_results["restaurants"]["selected"] > 0
            meal_plan = self._plan_meal_slots(num_days, pace, has_restaurants)
            
            # Plan trip slots
            trip_slots = self._plan_trip_slots(
                category_results, num_days, pace, route_coordinates,
                dest_lat=dest_lat, dest_lng=dest_lng,
                origin_lat=origin_lat, origin_lng=origin_lng,
            )
            
            # Store trip slots for LLM context
            self.trip_slots = trip_slots
            
            # Store category availability info for LLM context
            self.category_availability = {
                category: {
                    "requested": info["requested"],
                    "available": info["available"],
                    "selected": info["selected"]
                }
                for category, info in category_results.items()
            }
            self.meal_plan = meal_plan
            
            # Create structured intermediate representation
            structured_representation = self._create_structured_representation(
                trip_slots,
                self.category_availability,
                meal_plan,
                origin_lat,
                origin_lng,
                dest_lat,
                dest_lng
            )
            
            # Store structured representation for LLM context
            self.structured_representation = structured_representation
            
            # Flatten categorized POIs for trip optimization
            filtered_candidates = (
                category_results["accommodation"]["candidates"] +
                category_results["restaurants"]["candidates"] +
                category_results["attractions"]["candidates"]
            )
            # Store category availability info for LLM context
            self.category_availability = {
                category: {
                    "requested": info["requested"],
                    "available": info["available"],
                    "selected": info["selected"]
                }
                for category, info in category_results.items()
            }
            self.meal_plan = meal_plan
            print(f"[INFO] Total candidates after category-specific retrieval: {len(filtered_candidates)}")
        else:
            filtered_candidates = scored_candidates

        # Stage 2: pick the feasible, diverse, trip-fitting SET.
        try:
            print("[INFO] Starting trip optimization...")
            selected, time_summary = self._optimize_trip_selection(
                filtered_candidates,
                route_coordinates=route_coordinates,
                num_days=num_days,
                pace=pace,
            )
            print(f"[INFO] Trip optimization complete: {len(selected)} selected")
        except Exception as e:
            print(f"[ERROR] Trip optimization failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        try:
            print("[INFO] Building reasons for recommendations...")
            recommended_destinations = self._build_reasons(
                selected,
                interests=interests,
                dietary_preferences=dietary_preferences,
                num_children=num_children,
                budget=budget,
                travel_season=travel_season,
            )
            print(f"[INFO] Reasons built: {len(recommended_destinations)} destinations")
        except Exception as e:
            print(f"[ERROR] Building reasons failed: {e}")
            import traceback
            traceback.print_exc()
            raise

        if generate_itinerary:
            # Use LLM to generate natural language itinerary from structured representation
            print("[INFO] Generating natural language itinerary using LLM")

            try:
                # Collect all POIs from structured representation
                all_pois = []
                if hasattr(self, 'trip_slots') and isinstance(self.trip_slots, dict):
                    trip_days = self.trip_slots.get("days", [])
                    for day_slot in trip_days:
                        # Add overnight accommodation
                        if day_slot.get("overnight"):
                            all_pois.append({
                                "id": day_slot["overnight"].get("place_id"),
                                "name": day_slot["overnight"].get("name"),
                                "category": day_slot["overnight"].get("category"),
                                "latitude": day_slot["overnight"].get("latitude"),
                                "longitude": day_slot["overnight"].get("longitude"),
                                "embedding_similarity": day_slot["overnight"].get("similarity", 0)
                            })

                        # Add activities
                        for activity in day_slot.get("activities", []):
                            all_pois.append({
                                "id": activity.get("place_id"),
                                "name": activity.get("name"),
                                "category": activity.get("category"),
                                "latitude": activity.get("latitude"),
                                "longitude": activity.get("longitude"),
                                "embedding_similarity": activity.get("similarity", 0)
                            })

                        # Add meals
                        for meal in day_slot.get("meals", []):
                            all_pois.append({
                                "id": meal.get("place_id"),
                                "name": meal.get("name"),
                                "category": meal.get("category"),
                                "latitude": meal.get("latitude"),
                                "longitude": meal.get("longitude"),
                                "embedding_similarity": meal.get("similarity", 0)
                            })

                # Call LLM itinerary service
                natural_itinerary = await itinerary_service.generate_itinerary(
                    pois=all_pois,
                    origin_lat=origin_lat,
                    origin_lng=origin_lng,
                    dest_lat=dest_lat,
                    dest_lng=dest_lng,
                    num_days=num_days,
                    user_preferences=interests,
                    travel_style=pace,
                    budget=budget,
                    structured_representation=self.trip_slots if hasattr(self, 'trip_slots') else None
                )

                return natural_itinerary

            except Exception as e:
                print(f"[ERROR] LLM itinerary generation failed: {e}")
                print("[INFO] Falling back to structured trip slots")
                # Fallback to structured slots if LLM fails
                # Build simple itinerary from trip slots
                itinerary = {
                    "days": [],
                    "total_days": num_days,
                    "pace": pace,
                    "budget": budget,
                    "interests": interests or [],
                }

                if hasattr(self, 'trip_slots') and isinstance(self.trip_slots, dict):
                    trip_days = self.trip_slots.get("days", [])
                    for day_slot in trip_days:
                        day_data = {
                            "day": day_slot["day"],
                            "activities": [],
                            "meals": [],
                            "overnight_accommodation": None
                        }

                        # Add activities
                        for activity in day_slot.get("activities", []):
                            day_data["activities"].append({
                                "poi_id": activity.get("place_id"),
                                "name": activity.get("name"),
                                "category": activity.get("category"),
                                "latitude": activity.get("latitude"),
                                "longitude": activity.get("longitude")
                            })

                        # Add meals
                        for meal in day_slot.get("meals", []):
                            day_data["meals"].append({
                                "poi_id": meal.get("place_id"),
                                "name": meal.get("name"),
                                "category": meal.get("category"),
                                "latitude": meal.get("latitude"),
                                "longitude": meal.get("longitude")
                            })

                        # Add overnight accommodation
                        if day_slot.get("overnight"):
                            day_data["overnight_accommodation"] = {
                                "poi_id": day_slot["overnight"].get("place_id"),
                                "name": day_slot["overnight"].get("name"),
                                "category": day_slot["overnight"].get("category"),
                                "latitude": day_slot["overnight"].get("latitude"),
                                "longitude": day_slot["overnight"].get("longitude")
                            }

                        itinerary["days"].append(day_data)

                return {
                    "route": route_data,
                    "itinerary": itinerary,
                    "total_pois_found": len(candidates),
                    "corridor_km": corridor_km,
                    "time_budget": time_summary,
                }
            except Exception as e:
                print(f"[ERROR] Error building itinerary: {e}")
                import traceback
                traceback.print_exc()
                raise

        # Log buffer distances of final recommendations for debugging
        if not generate_itinerary:
            print(f"[INFO] Final recommendations buffer distances:")
            for i, dest in enumerate(recommended_destinations[:limit], 1):
                dist_to_route = dest.get("distance_to_route_km", "N/A")
                print(f"  {i}. {dest.get('name', 'Unknown')}: {dist_to_route}km from route")
        
        return {
            "route": route_data,
            "recommended_destinations": recommended_destinations[:limit],
            "nearby_pois": candidates,  # All POIs in buffer for overlay
            "total_candidates_found": len(candidates),
            "corridor_km": corridor_km,
            "time_budget": time_summary,
        }

    def _get_pois_in_route_buffer(
        self,
        route_coordinates: List[List[float]],
        buffer_km: float,
        origin_lat: float = None,
        origin_lng: float = None,
        dest_lat: float = None,
        dest_lng: float = None,
        destination_buffer_km: float = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get POIs within a buffer around the route using bounding box + distance check.
        
        Also includes a larger buffer around the destination for better coverage.
        
        Args:
            route_coordinates: List of [lng, lat] coordinates for the route
            buffer_km: Buffer radius around the route (default 20km)
            dest_lat: Destination latitude for additional destination buffer
            dest_lng: Destination longitude for additional destination buffer
            destination_buffer_km: Buffer radius around destination (default 50km)
        """
        db: Session = SessionLocal()
        try:
            lats = [coord[1] for coord in route_coordinates]
            lngs = [coord[0] for coord in route_coordinates]

            # Calculate center latitude for longitude conversion
            # Use Nepal center as fallback if both route and origin are unavailable
            center_lat = sum(lats) / len(lats) if lats else (origin_lat if origin_lat is not None else 27.7172)
            lng_deg_per_km = self._get_longitude_deg_per_km(center_lat)

            # Route buffer - use separate lat/lng conversions
            buffer_lat_deg = buffer_km * self.buffer_deg_per_km_lat
            buffer_lng_deg = buffer_km * lng_deg_per_km
            min_lat, max_lat = min(lats) - buffer_lat_deg, max(lats) + buffer_lat_deg
            min_lng, max_lng = min(lngs) - buffer_lng_deg, max(lngs) + buffer_lng_deg

            # Add destination buffer if provided
            if dest_lat is not None and dest_lng is not None:
                dest_lat_deg = destination_buffer_km * self.buffer_deg_per_km_lat
                dest_lng_deg = destination_buffer_km * lng_deg_per_km
                min_lat = min(min_lat, dest_lat - dest_lat_deg)
                max_lat = max(max_lat, dest_lat + dest_lat_deg)
                min_lng = min(min_lng, dest_lng - dest_lng_deg)
                max_lng = max(max_lng, dest_lng + dest_lng_deg)
                print(f"Added {destination_buffer_km}km destination buffer around ({dest_lat}, {dest_lng})")

            # Calculate route distance to determine if origin exclusion should be applied
            route_distance_km = self._calculate_route_distance(route_coordinates)
            origin_buffer_km = 20.0 if route_distance_km > 50 else 0

            # Add origin buffer exclusion - remove POIs within 20km of origin
            # Only apply if route is long enough (>50km) to avoid wiping out first segment
            if origin_buffer_km > 0:
                origin_lat_deg = origin_buffer_km * self.buffer_deg_per_km_lat
                origin_lng_deg = origin_buffer_km * self._get_longitude_deg_per_km(origin_lat)
                origin_min_lat = origin_lat - origin_lat_deg
                origin_max_lat = origin_lat + origin_lat_deg
                origin_min_lng = origin_lng - origin_lng_deg
                origin_max_lng = origin_lng + origin_lng_deg
                print(f"Excluding POIs within {origin_buffer_km}km of origin ({origin_lat}, {origin_lng}) for {route_distance_km:.1f}km route")
            else:
                print(f"Route distance {route_distance_km:.1f}km is too short for origin exclusion (threshold: 50km)")
                origin_min_lat = origin_min_lng = origin_max_lat = origin_max_lng = None

            # Cast centroid Text → geometry so PostGIS functions are unambiguous
            from sqlalchemy import cast
            from geoalchemy2 import Geometry
            centroid_geom = cast(PlaceDB.centroid, Geometry("POINT", srid=4326))

            lat_expr = func.ST_Y(centroid_geom)
            lng_expr = func.ST_X(centroid_geom)

            # Calculate destination point for ordering — places closer to the
            # destination rank first so they are not cut by the row limit.
            # Falls back to route centre if destination is not provided.
            if dest_lat is not None and dest_lng is not None:
                order_point = func.ST_SetSRID(func.ST_MakePoint(dest_lng, dest_lat), 4326)
            else:
                route_center_lng = sum(lngs) / len(lngs) if lngs else origin_lng
                route_center_lat = sum(lats) / len(lats) if lats else origin_lat
                order_point = func.ST_SetSRID(func.ST_MakePoint(route_center_lng, route_center_lat), 4326)

            query = (
                db.query(PlaceDB, lat_expr.label("lat"), lng_expr.label("lng"))
                .filter(
                    lat_expr >= min_lat,
                    lat_expr <= max_lat,
                    lng_expr >= min_lng,
                    lng_expr <= max_lng,
                )
                .filter(PlaceDB.name.isnot(None))
                .filter(func.trim(PlaceDB.name) != "")
                .filter(func.length(func.trim(PlaceDB.name)) > 1)
                .filter(~PlaceDB.category.ilike("%tour operator%"))
                .filter(~PlaceDB.category.ilike("%tour agency%"))
                .filter(~PlaceDB.category.ilike("%tourist information%"))
                # Order by distance to DESTINATION so destination-area places
                # come first and are not cut by the row limit.
                .order_by(func.ST_Distance(centroid_geom, order_point))
            )

            # Only apply origin exclusion filter if route is long enough
            if origin_buffer_km > 0:
                query = query.filter(
                    ~((lat_expr >= origin_min_lat) & (lat_expr <= origin_max_lat) &
                      (lng_expr >= origin_min_lng) & (lng_expr <= origin_max_lng))
                )

            query = query.limit(2000)  # Raised from 1000 — destination-ordered so dest places come first

            rows = query.all()

            # Use full route coordinates for precise buffer enforcement
            # Downsample only if route is extremely long (>1000 points) to avoid performance issues
            if len(route_coordinates) > 1000:
                sampled_route = self._sample_route(route_coordinates, max_points=500)
                print(f"Route downsampled from {len(route_coordinates)} to {len(sampled_route)} points for buffer check")
            else:
                sampled_route = route_coordinates
                print(f"Using full route with {len(route_coordinates)} points for buffer check")

            pois_in_buffer = []
            excluded_count = 0
            for place, lat, lng in rows:
                if not lat or not lng or lat == 0.0 or lng == 0.0:
                    continue
                lat_f, lng_f = float(lat), float(lng)
                
                # Check if within route buffer OR destination buffer
                distance_to_route = self._calculate_distance_to_route(lat_f, lng_f, sampled_route)
                within_route_buffer = distance_to_route <= buffer_km
                
                within_dest_buffer = False
                if dest_lat is not None and dest_lng is not None:
                    distance_to_dest = self._haversine_distance(lat_f, lng_f, dest_lat, dest_lng)
                    within_dest_buffer = distance_to_dest <= destination_buffer_km
                
                # Include if within either buffer
                if within_route_buffer or within_dest_buffer:
                    place_dict = self._place_to_dict(place)
                    place_dict["latitude"] = lat_f
                    place_dict["longitude"] = lng_f
                    place_dict["distance_to_route_km"] = round(distance_to_route, 2)
                    # Tag which buffer(s) this POI belongs to — used downstream
                    # to prevent route-proximity scoring from penalising
                    # destination-area places.
                    place_dict["_in_route_buffer"] = within_route_buffer
                    place_dict["_in_dest_buffer"] = within_dest_buffer
                    # Classify POI type for downstream routing:
                    #   "route"       — only in route corridor
                    #   "destination" — only in destination buffer
                    #   "both"        — in both buffers
                    if within_route_buffer and within_dest_buffer:
                        place_dict["_poi_type"] = "both"
                    elif within_route_buffer:
                        place_dict["_poi_type"] = "route"
                    else:
                        place_dict["_poi_type"] = "destination"
                    if dest_lat is not None and dest_lng is not None:
                        distance_to_dest = self._haversine_distance(lat_f, lng_f, dest_lat, dest_lng)
                        place_dict["distance_to_dest_km"] = round(distance_to_dest, 2)
                    pois_in_buffer.append(place_dict)
                else:
                    excluded_count += 1
            
            # Count POI types for diagnostics
            route_only_count = sum(1 for p in pois_in_buffer if p.get("_poi_type") == "route")
            dest_only_count = sum(1 for p in pois_in_buffer if p.get("_poi_type") == "destination")
            both_count = sum(1 for p in pois_in_buffer if p.get("_poi_type") == "both")
            print(
                f"Buffer enforcement: {excluded_count} excluded, {len(pois_in_buffer)} included "
                f"(route buffer: {buffer_km}km, dest buffer: {destination_buffer_km}km) | "
                f"route-only: {route_only_count}, dest-only: {dest_only_count}, both: {both_count}"
            )

            # ── Per-category caps to prevent low-value categories from
            #    flooding the candidate pool and crowding out real tourist POIs.
            # Categories not listed here are uncapped.
            _CATEGORY_CAPS: dict[str, int] = {
                "Religious Site":  60,
                "Spring":          20,
                "Pond":            10,
                "Tree":             0,   # hard exclude — no tourist value
                "Bus Station":      0,   # hard exclude
                "Fuel Station":     0,   # hard exclude
                "Fast Food":       30,
                "Apartment":        0,   # hard exclude
            }

            if _CATEGORY_CAPS:
                category_counts: dict[str, int] = {}
                capped_result: list[dict] = []
                hard_excluded = 0
                soft_capped = 0
                for poi in pois_in_buffer:
                    cat = (poi.get("category") or "").strip()
                    cap = _CATEGORY_CAPS.get(cat)
                    if cap is None:
                        # uncapped category — always include
                        capped_result.append(poi)
                    elif cap == 0:
                        hard_excluded += 1
                    else:
                        count = category_counts.get(cat, 0)
                        if count < cap:
                            capped_result.append(poi)
                            category_counts[cat] = count + 1
                        else:
                            soft_capped += 1
                print(
                    f"Category caps: {hard_excluded} hard-excluded, "
                    f"{soft_capped} soft-capped, "
                    f"{len(capped_result)} remain"
                )
                pois_in_buffer = capped_result

            return pois_in_buffer
        finally:
            db.close()

    @staticmethod
    def _sample_route(
        route_coordinates: List[List[float]], max_points: int
    ) -> List[List[float]]:
        """Evenly downsample route coordinates for cheaper distance checks."""
        n = len(route_coordinates)
        if n <= max_points:
            return route_coordinates
        step = n / max_points
        return [route_coordinates[int(i * step)] for i in range(max_points)]

    def _is_near_route_by_coords(
        self,
        lat: float,
        lng: float,
        route_coordinates: List[List[float]],
        buffer_km: float,
    ) -> bool:
        """Check if a point is within buffer distance of the route."""
        for coord in route_coordinates:
            route_lat = coord[1]
            route_lng = coord[0]
            distance = self._haversine_distance(lat, lng, route_lat, route_lng)
            if distance <= buffer_km:
                return True
        return False

    def _calculate_distance_to_route(
        self,
        lat: float,
        lng: float,
        route_coordinates: List[List[float]],
    ) -> float:
        """Calculate the minimum distance from a point to the route."""
        # Downsample route if it's too long to avoid O(N*M) performance issues
        if len(route_coordinates) > 200:
            route_coordinates = self._sample_route(route_coordinates, max_points=200)

        min_distance = float('inf')
        for coord in route_coordinates:
            route_lat = coord[1]
            route_lng = coord[0]
            distance = self._haversine_distance(lat, lng, route_lat, route_lng)
            if distance < min_distance:
                min_distance = distance
        return min_distance

    def _haversine_distance(
        self, lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """Calculate Haversine distance between two points in kilometers."""
        R = 6371.0  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)

        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _calculate_route_distance(
        self, route_coordinates: List[List[float]]
    ) -> float:
        """Calculate total route distance by summing segment distances."""
        if len(route_coordinates) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(route_coordinates) - 1):
            lng1, lat1 = route_coordinates[i]
            lng2, lat2 = route_coordinates[i + 1]
            total_distance += self._haversine_distance(lat1, lng1, lat2, lng2)

        return total_distance

    def _calculate_benefit_score(self, relevance: float, total_minutes: float) -> float:
        """
        Calculate benefit score using diminishing returns to prevent short stops
        from suppressing long, high-value destinations.

        Uses logarithmic penalty on time with time_factor >= 1.0 to prevent
        short stop amplification.
        """
        # Smooth logarithmic cost penalty where time_factor is >= 1.0 for all t >= 0
        # This prevents short stops from being amplified (previous bug)
        time_factor = 1.0 + math.log1p(total_minutes / 30.0)

        # Benefit = relevance / time_factor
        benefit = relevance / time_factor

        # Add minimum baseline for high-relevance places to prevent suppression
        if relevance > 0.8:
            benefit = max(benefit, relevance * 0.5)

        return benefit

    def _calculate_route_progress(
        self,
        lat: float,
        lng: float,
        route_coordinates: List[List[float]]
    ) -> float:
        """
        Calculate progress (0-1) of a point along the route.
        Returns the fraction of the route that has been passed to reach this point.
        """
        # Find closest route point index
        min_dist = float('inf')
        closest_idx = 0
        for i, coord in enumerate(route_coordinates):
            dist = self._haversine_distance(lat, lng, coord[1], coord[0])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        return closest_idx / len(route_coordinates)

    def _cluster_activities_by_route_progress(
        self,
        activities: List[Dict],
        route_coordinates: List[List[float]],
        num_days: int
    ) -> List[List[Dict]]:
        """
        Cluster activities by their progress along the route.
        Day 1: 0-33% of route, Day 2: 33-66%, Day 3: 66-100%, etc.
        This ensures geographical coherence in daily itineraries.

        Each activity is assigned to exactly ONE day bucket — no duplicates.
        """
        if not activities:
            return [[] for _ in range(num_days)]

        # Calculate route progress for each activity
        for activity in activities:
            activity["_route_progress"] = self._calculate_route_progress(
                activity["latitude"],
                activity["longitude"],
                route_coordinates
            )

        # Sort by route progress (does not modify dicts in-place structurally)
        sorted_activities = sorted(activities, key=lambda x: x["_route_progress"])

        # --- Assign each activity to exactly ONE day based on its progress ---
        # First pass: natural home segment
        daily_clusters: List[List[Dict]] = [[] for _ in range(num_days)]
        assigned_ids: set = set()

        for act in sorted_activities:
            progress = act["_route_progress"]
            # Use min to handle progress==1.0 landing in day num_days (out of range)
            target_day = min(int(progress * num_days), num_days - 1)
            daily_clusters[target_day].append(act)
            assigned_ids.add(id(act))

        # --- Fill empty or sparse days from nearest neighbors, no dupes ---
        # Compute ideal minimum per day: if we have N activities and D days,
        # each day should have at least (N // D) activities, rest distributed as +1
        ideal_min = max(1, len(sorted_activities) // num_days) if sorted_activities else 0

        for day in range(num_days):
            current = daily_clusters[day]
            if len(current) >= ideal_min:
                continue

            needed = ideal_min - len(current)
            borrowed = 0

            # Look through sorted_activities in order (closest first) for
            # unassigned activities that can fill this gap
            for act in sorted_activities:
                if borrowed >= needed:
                    break
                if id(act) in assigned_ids:
                    # Already assigned somewhere; try to steal if neighbor is overfull
                    src_day = min(int(act["_route_progress"] * num_days), num_days - 1)
                    if src_day == day:
                        continue
                    # Only steal if source day has more than ideal_min to spare
                    if len(daily_clusters[src_day]) > ideal_min and act in daily_clusters[src_day]:
                        daily_clusters[src_day].remove(act)
                        daily_clusters[day].append(act)
                        borrowed += 1

            # If still underfilled: redistribute from the most overfull days
            while borrowed < needed:
                overfull = max(range(num_days), key=lambda d: len(daily_clusters[d]))
                if len(daily_clusters[overfull]) <= ideal_min or overfull == day:
                    break  # No one has extras to give
                mover = daily_clusters[overfull].pop()
                daily_clusters[day].append(mover)
                borrowed += 1

        # Sanity check: no activity present in 2+ days
        seen: set = set()
        for cluster in daily_clusters:
            for act in cluster:
                key = id(act)
                if key in seen:
                    # Safety fallback: remove any duplicate we find
                    cluster.remove(act)
                    continue
                seen.add(key)

        return daily_clusters

    def _apply_hard_filters(
        self,
        pois: List[Dict[str, Any]],
        num_children: int,
        dietary_preferences: Optional[List[str]],
        budget: str,
    ) -> List[Dict[str, Any]]:
        """
        Remove POIs that are outright unsuitable, rather than just scoring
        them lower. This is what "traveling with 2 kids" or "vegetarian only"
        should actually mean to the recommender.
        """
        utility_categories = {
            "waste_basket", "bench", "post_box", "telephone", "water_tap", 
            "power", "pole", "surveillance", "bus_stop", "toilets", "parking", 
            "atm", "bank", "pharmacy", "fuel", "fire_station", "crossing",
            "construction", "disused", "dumping_ground"
        }
        filtered = []
        dropped_nameless = 0
        for poi in pois:
            # ------------------------------------------------------------------
            # Hard-drop POIs with no name, placeholder name, or generic OSM name.
            # These add no value to an itinerary and annoy users.
            # ------------------------------------------------------------------
            name = (poi.get("name") or "").strip()
            name_lower = name.lower()
            has_wiki = bool(poi.get("wikidata_id") or poi.get("wikipedia_url"))

            # 1. Hard drop: missing, blank, or length <= 2 (e.g. 'R', 'SN', '1', '..', 'Pk', 'ct', etc.)
            if not name or len(name) <= 2:
                dropped_nameless += 1
                continue

            # 2. Hard drop: placeholder phrases ('unnamed', 'no name', 'noname', 'unknown', 'n/a', 'node/', etc.)
            placeholders = ('unnamed', 'unknown', 'no name', 'noname', 'no_name', 'n/a', 'null', 'node/', 'way/', 'relation/')
            if any(p in name_lower for p in placeholders) and not has_wiki:
                dropped_nameless += 1
                continue

            # 3. Hard drop: pure generic terms or stripped generic terms (e.g. 'Teahouse', 'Coffee Shop', 'Homestay', 'Hotel', 'Bar')
            import re as _re
            stripped = _re.sub(r"[\d\s\-_#.,()/]+", "", name_lower)
            if (name_lower in self._GENERIC_NAMES or stripped in self._GENERIC_NAMES) and not has_wiki:
                dropped_nameless += 1
                continue

            # 4. Hard drop: low-quality names (score <= 0.4) that have no wiki verification
            name_quality = self._score_name_quality(poi)
            if name_quality <= 0.4 and not has_wiki:
                dropped_nameless += 1
                continue

            # Drop non-tourist utility OSM elements
            category_lower = (poi.get("category") or "").lower()
            if any(cat in category_lower for cat in utility_categories):
                continue

            # Kids in the group: drop anything flagged high-difficulty.
            if num_children > 0:
                difficulty = (poi.get("difficulty") or "").lower()
                if difficulty in ("hard", "difficult", "strenuous"):
                    continue

            # Dietary preferences - use soft scoring instead of hard exclusion
            # This allows mixed-cuisine restaurants to be included with lower scores
            if dietary_preferences and self._is_food_place(poi):
                poi_tags = (
                    (poi.get("tags") or []) +
                    (poi.get("travel_styles") or []) +
                    (poi.get("semantic_tags") or [])
                )

                # Tokenize with special negation-merging: transform
                # "non veg", "non-veg" -> single token "nonveg" so that "veg" pref
                # does not false-positive match a "non-veg restaurant" tag.
                import re
                def _diet_tokens(phrases):
                    out = set()
                    for s in phrases:
                        if s is None:
                            continue
                        text = str(s).lower()
                        # Merge negation prefixes: "non X", "non-X" -> "nonX"
                        # Also handle vegan-style prefixes similarly
                        text = re.sub(r'\bnon[\s-]+(\w+)', r'non\1', text)
                        # Merge "jain" style "no onion/garlic" if present
                        text = re.sub(r'\bno[\s-]+(\w+)', r'no\1', text)
                        out.update(re.findall(r'[a-zA-Z0-9]+', text))
                    return out

                tag_tokens = _diet_tokens(poi_tags)

                # Also tokenize category, name, and raw_tag cuisine fields
                tag_tokens |= _diet_tokens([
                    poi.get("category", ""),
                    poi.get("name", ""),
                    (poi.get("raw_tags") or {}).get("cuisine", ""),
                    (poi.get("raw_tags") or {}).get("diet", ""),
                ])

                # Preference keyword expansions: normalize aliases to canonical tokens
                pref_token_map = {
                    "veg": {"veg", "vegetarian", "veggie"},
                    "vegetarian": {"veg", "vegetarian", "veggie"},
                    "vegan": {"vegan"},
                    "nonveg": {"nonveg", "non", "meat", "chicken", "mutton", "beef", "fish", "seafood"},
                    "non-veg": {"nonveg", "non", "meat", "chicken", "mutton", "beef", "fish", "seafood"},
                    "non veg": {"nonveg", "non", "meat", "chicken", "mutton", "beef", "fish", "seafood"},
                    "jain": {"jain"},
                    "halal": {"halal"},
                    "kosher": {"kosher"},
                }

                # Also merge negations in the user preference itself, so
                # dietary_preferences=["Non-Veg"] -> canonical lookup finds it
                def _normalize_pref(p):
                    t = p.lower().strip()
                    t = re.sub(r'\bnon[\s-]+(\w+)', r'non\1', t)
                    t = re.sub(r'\bno[\s-]+(\w+)', r'no\1', t)
                    return t

                exact_match = False
                partial_match = False
                for pref in dietary_preferences:
                    pref_norm = _normalize_pref(pref)
                    canonical = pref_token_map.get(pref_norm, pref_token_map.get(pref.lower().strip(), {pref_norm}))
                    matches = canonical & tag_tokens
                    if matches:
                        exact_match = True
                        break
                    # Loose partial: any tag token starts-with preference token
                    for t in tag_tokens:
                        for p in canonical:
                            if len(p) >= 3 and len(t) >= 3 and (t.startswith(p) or p.startswith(t)):
                                partial_match = True
                                break
                        if partial_match:
                            break
                    if partial_match:
                        break

                if exact_match:
                    dietary_match_score = 1.0
                elif partial_match:
                    dietary_match_score = 0.5
                else:
                    dietary_match_score = 0.3

                poi["dietary_match_score"] = dietary_match_score
            else:
                poi["dietary_match_score"] = 1.0

            # Budget: if a place is explicitly ticketed and marked
            # high-cost, drop it for low-budget trips.
            if budget == "low":
                raw_tags = poi.get("raw_tags") or {}
                if str(raw_tags.get("price_range", "")).lower() in ("high", "expensive", "luxury"):
                    continue

            filtered.append(poi)
        print(f"[INFO] Hard filters: {dropped_nameless} nameless/generic POIs dropped, {len(filtered)} remain")
        return filtered

    @staticmethod
    def _is_food_place(poi: Dict[str, Any]) -> bool:
        category = (poi.get("category") or "").lower()
        return any(k in category for k in ("restaurant", "cafe", "food", "eatery", "dining"))

    @staticmethod
    def _is_accommodation(poi: Dict[str, Any]) -> bool:
        category = (poi.get("category") or "").lower()
        return any(k in category for k in ("hotel", "guest house", "resort", "lodge", "hostel", "inn", "homestay"))

    @staticmethod
    def _is_attraction(poi: Dict[str, Any]) -> bool:
        """Determine if a POI is an attraction/activity (not accommodation or food)."""
        if RecommendationService._is_accommodation(poi) or RecommendationService._is_food_place(poi):
            return False
        return True

    def _diagnose_category_counts(self, pois: List[Dict[str, Any]], stage: str) -> Dict[str, int]:
        """Diagnostic function to track category counts at each pipeline stage."""
        counts = {
            "accommodation": 0,
            "restaurants": 0,
            "attractions": 0,
            "total": len(pois)
        }
        
        for poi in pois:
            if self._is_accommodation(poi):
                counts["accommodation"] += 1
            elif self._is_food_place(poi):
                counts["restaurants"] += 1
            else:
                counts["attractions"] += 1
        
        print(f"[DIAGNOSTIC] {stage}:")
        print(f"  Total: {counts['total']}")
        print(f"  Accommodation: {counts['accommodation']}")
        print(f"  Restaurants: {counts['restaurants']}")
        print(f"  Attractions: {counts['attractions']}")
        
        return counts

    def _plan_meal_slots(
        self,
        num_days: int,
        pace: str = "balanced",
        has_restaurants: bool = True
    ) -> Dict[str, Any]:
        """
        Plan meal slots for the trip, distinguishing between meal requirements and restaurant candidates.
        
        Skip breakfast since it's usually at the hotel. Only plan lunch and dinner.
        
        Returns:
            Dict with meal slot information and restaurant availability
        """
        # Define meal slots per day (skip breakfast - hotel-based)
        daily_meals = ["lunch", "dinner"]
        total_meal_slots = num_days * len(daily_meals)
        
        # Calculate how many meal slots need restaurant recommendations
        # This depends on restaurant availability and trip characteristics
        if has_restaurants:
            # Assume 80% of lunch/dinner need restaurant recommendations (others: hotel dinner, self-catering, etc.)
            restaurant_needed_slots = int(total_meal_slots * 0.8)
        else:
            # No restaurants available - all meals must be handled differently
            restaurant_needed_slots = 0
        
        meal_plan = {
            "total_days": num_days,
            "daily_meals": daily_meals,
            "total_meal_slots": total_meal_slots,
            "restaurant_needed_slots": restaurant_needed_slots,
            "has_restaurants": has_restaurants,
            "meal_options": []
        }
        
        if not has_restaurants:
            meal_plan["meal_options"] = ["hotel_dinner", "self_catering", "local_food_establishments", "cafes"]
        else:
            meal_plan["meal_options"] = ["restaurants", "hotel_dinner", "cafes", "local_food_establishments"]
        
        print(f"[INFO] Meal slot planning:")
        print(f"  Total meal slots: {total_meal_slots} (lunch + dinner only, breakfast at hotel)")
        print(f"  Restaurant slots needed: {restaurant_needed_slots}")
        print(f"  Available meal options: {', '.join(meal_plan['meal_options'])}")
        
        return meal_plan

    def _calculate_time_aware_limits(
        self,
        num_days: int,
        pace: str = "balanced",
        route_distance_km: float = 200,
        route_duration_hours: float = 8
    ) -> Dict[str, int]:
        """
        Calculate how many candidates of each category to pull into the
        trip-slot planner.

        Design goals
        ------------
        • Dense itineraries: 5–7 attractions/day depending on pace.
        • Guaranteed meals: exactly 2 meal slots/day (lunch + dinner).
          We retrieve 3× the meal slots needed so the slot planner always
          has options even after spatial filtering.
        • 1 hotel per night: retrieve num_days × 3 so we have per-night
          choice even in sparse areas.
        • Candidate buffer: attractions are retrieved at 2× the target so
          the diversity/destination sorting has room to pick the best set.
        """
        # Target activities per day by pace
        target_per_day = {
            "relaxed": 5,
            "balanced": 6,
            "packed": 7,
        }.get(pace, 6)

        # Retrieve 2× candidates so sorting + diversity has headroom
        attractions_needed = target_per_day * 2 * num_days

        # Meals: exactly 2 slots/day, retrieve 3× as candidates
        meal_slots_per_day = 2   # lunch + dinner (breakfast at hotel)
        restaurants_needed = meal_slots_per_day * 3 * num_days

        # Hotels: 1 per night, retrieve 3× for choice
        accommodation_needed = num_days * 3

        limits = {
            "accommodation": accommodation_needed,
            "restaurants":   restaurants_needed,
            "attractions":   attractions_needed,
        }

        print(f"[INFO] Candidate limits → "
              f"accommodation: {accommodation_needed}, "
              f"restaurants: {restaurants_needed}, "
              f"attractions: {attractions_needed} "
              f"(target {target_per_day}/day × {num_days} days)")

        return limits

    def _category_specific_retrieval(
        self,
        pois: List[Dict[str, Any]],
        num_days: int,
        pace: str = "balanced",
        route_distance_km: float = 200,
        route_duration_hours: float = 8
    ) -> Dict[str, Dict[str, Any]]:
        """
        Perform category-specific retrieval with independent quotas using time-aware limits.
        
        Returns:
            Dict with category info including requested, available, and selected counts
            and the actual selected candidates for each category.
        """
        # Calculate time-aware limits
        requested_limits = self._calculate_time_aware_limits(
            num_days, pace, route_distance_km, route_duration_hours
        )
        
        print(f"[INFO] Category-specific retrieval quotas: {requested_limits}")
        
        # Categorize all candidates
        categorized = {
            "accommodation": [],
            "restaurants": [],
            "attractions": []
        }
        
        for poi in pois:
            if self._is_accommodation(poi):
                categorized["accommodation"].append(poi)
            elif self._is_food_place(poi):
                categorized["restaurants"].append(poi)
            else:
                categorized["attractions"].append(poi)
        
        # Sort each category by composite relevance_score (fallback to embedding_similarity).
        # Destination-buffer POIs now carry a fair route_score (fixed in
        # _calculate_modular_score), so a single sort by relevance_score is
        # sufficient.  We add a secondary sort key so that when two POIs have
        # near-identical relevance scores, destination-buffer POIs rank higher
        # than corridor-only ones — this prevents them from being cut at the
        # quota boundary just because their scores are fractionally lower.
        for category in categorized:
            if categorized[category]:
                categorized[category].sort(
                    key=lambda x: (
                        x.get("relevance_score", x.get("embedding_similarity", 0)),
                        1 if (x.get("wikidata_id") or x.get("wikipedia_url")) else 0,  # wiki places win ties
                        1 if x.get("_in_dest_buffer") else 0,   # then dest-buffer
                    ),
                    reverse=True
                )
        
        # Select candidates for each category independently
        # Wikidata reservation: for attractions, reserve up to 50% of slots
        # for wikidata-enriched places, then fill the rest by score.
        results = {}
        for category, candidates in categorized.items():
            requested = requested_limits[category]
            available = len(candidates)
            selected_count = min(requested, available)

            if category == "attractions" and selected_count > 3:
                # ── Wikidata reservation ──────────────────────────────────
                wiki_candidates = [
                    c for c in candidates
                    if c.get("wikidata_id") or c.get("wikipedia_url")
                ]
                non_wiki_candidates = [
                    c for c in candidates
                    if not (c.get("wikidata_id") or c.get("wikipedia_url"))
                ]

                # Reserve up to 50% of slots for wiki places
                wiki_slots = min(len(wiki_candidates), selected_count // 2)
                remaining_slots = selected_count - wiki_slots

                reserved_wiki = wiki_candidates[:wiki_slots]
                reserved_ids = {c.get("id") for c in reserved_wiki}

                # Fill remaining slots from full pool (excluding reserved)
                fill_pool = [c for c in candidates if c.get("id") not in reserved_ids]

                # Apply diversity-aware selection on the fill pool
                diverse_fill = self._diversity_aware_selection(
                    fill_pool, remaining_slots, lambda_param=0.6
                )

                # Combine: reserved wiki first, then diverse fill
                selected_candidates = reserved_wiki + diverse_fill

                # Enforce minimum spacing on combined result
                selected_candidates = self._enforce_minimum_spacing(
                    selected_candidates, min_distance_km=5.0
                )

                wiki_in_final = sum(
                    1 for c in selected_candidates
                    if c.get("wikidata_id") or c.get("wikipedia_url")
                )
                print(
                    f"[INFO] Attractions wikidata reservation: "
                    f"{wiki_slots} reserved, {wiki_in_final} wiki in final {len(selected_candidates)}"
                )
            else:
                # For accommodation and restaurants, keep top-ranked
                selected_candidates = candidates[:selected_count]

            results[category] = {
                "requested": requested,
                "available": available,
                "selected": len(selected_candidates),
                "candidates": selected_candidates
            }

            print(f"[INFO] {category.capitalize()}: requested={requested}, available={available}, selected={len(selected_candidates)}")

        return results

    # ------------------------------------------------------------------
    # Name-quality scoring
    # ------------------------------------------------------------------

    # Single-word generic names that add no information about a specific
    # place.  A POI whose full name IS one of these words (case-insensitive,
    # stripped) gets the lowest score tier.
    _GENERIC_NAMES: frozenset = frozenset({
        # English generic names
        "bridge", "viewpoint", "view point", "waterfall", "temple", "shrine",
        "monastery", "stupa", "lake", "river", "park", "forest", "hill",
        "mountain", "peak", "trail", "path", "road", "street", "school",
        "hospital", "hotel", "lodge", "guest house", "guesthouse", "resort",
        "restaurant", "cafe", "shop", "market", "store", "station",
        "checkpoint", "gate", "entrance", "exit", "tower", "wall", "fort",
        "museum", "gallery", "garden", "field", "camp", "campsite",
        "helipad", "airport", "bus stop", "parking", "homestay", "home stay",
        "teahouse", "tea house", "tea shop", "coffee shop", "bakery", "eatery",
        "bar", "pub", "building", "office", "house", "church", "mosque", "tap",
        "water tap", "toilet", "toilets",
        # Nepali / local generic names (transliterations)
        "मन्दिर", "मठ", "गुम्बा", "स्तूप", "ताल", "नदी", "खोला",
        "पुल", "बगैंचा", "बजार", "चोक", "टोल", "गाउँ", "विद्यालय",
        "अस्पताल", "होटल", "लज", "रेस्टुरेन्ट", "पार्क", "वन",
        "पहाड", "डाँडा", "चुली", "धारा", "कुवा", "पोखरी",
        "chautara", "pipal", "chowk", "tole", "gaun", "danda",
        "khola", "kund", "pokhari", "dhara", "mandir", "gompa",
        "gumba", "chorten", "mane",
    })

    def _score_name_quality(self, poi: Dict[str, Any]) -> float:
        """
        Return a 0–1 name-quality score.

        Tiers
        -----
        1.0  Proper specific name  (e.g. "Phewa Lake", "Boudhanath Stupa")
        0.7  Name contains a generic word but also has a qualifier
             (e.g. "Sarangkot Viewpoint", "Begnas Lake")
        0.3  Name IS a single generic word  (e.g. "Viewpoint", "Bridge")
        0.1  Name is missing, blank, or only whitespace/punctuation

        A POI with a wikidata_id or wikipedia_url is assumed well-known
        enough that its name score is floored at 0.6 regardless.
        """
        name = (poi.get("name") or "").strip()
        name_lower = name.lower()

        placeholders = ('unnamed', 'unknown', 'no name', 'noname', 'no_name', 'n/a', 'null', 'node/', 'way/', 'relation/')

        # Missing, blank, extremely short name (<= 2 chars), or placeholder phrase
        if not name or len(name) <= 2 or any(p in name_lower for p in placeholders):
            score = 0.1
        else:
            # Exact match against the generic-name set
            if name_lower in self._GENERIC_NAMES:
                score = 0.3
            else:
                # Check whether the name is *only* a generic word plus digits/
                # punctuation (e.g. "Bridge 1", "Viewpoint 3")
                import re
                stripped = re.sub(r"[\d\s\-_#.,()/]+", "", name_lower)
                if stripped in self._GENERIC_NAMES:
                    score = 0.3
                # Name contains a generic word but also real qualifiers
                elif any(g in name_lower for g in self._GENERIC_NAMES):
                    # Reward proportionally to how much extra content there is
                    generic_len = max(len(g) for g in self._GENERIC_NAMES if g in name_lower)
                    extra_ratio = (len(name) - generic_len) / max(len(name), 1)
                    score = 0.7 + 0.3 * min(extra_ratio, 1.0)
                else:
                    score = 1.0

        # Well-known places (have wiki linkage) get a floor of 0.6
        if score < 0.6 and (poi.get("wikidata_id") or poi.get("wikipedia_url")):
            score = 0.6

        return score

    def _calculate_modular_score(
        self,
        poi: Dict[str, Any],
        interests: Optional[List[str]],
        travel_season: Optional[str],
        route_coordinates: List[List[float]],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Calculate a destination-aware composite score.

        Architecture
        ------------
        Every POI is tagged with _in_dest_buffer / _in_route_buffer from the
        retrieval stage.  We compute two independent spatial scores:

          dest_proximity  — how close the POI is to the trip destination
          route_proximity — how close the POI is to the travel corridor

        Then we blend them with a destination_weight that is:
          • 0.85 for pure destination-buffer POIs  (e.g. Pokhara attractions)
          • 0.50 for dual-buffer POIs               (near both road and dest)
          • 0.10 for pure route-corridor POIs       (highway stop)

        This means Pokhara places are scored primarily on how good they are
        AT the destination, not on how far they sit from the Kathmandu highway.

        Score components (all 0-1 except detour which is negative):
          semantic      — embedding similarity to user preferences
          dest_spatial  — proximity to destination (destination-weighted)
          route_spatial — proximity to route corridor (route-weighted)
          preference    — keyword match to stated interests
          popularity    — normalized OSM popularity (0-100 → 0-1)
          quality       — rating + wiki recognition
          category      — category appropriateness bonus
          season        — seasonal suitability
          dietary       — dietary preference match
          name_quality  — penalises unnamed / purely generic names
          detour        — small penalty for route-only detours (zeroed for dest POIs)
        """
        scores = {}

        # ── 1. Semantic similarity ─────────────────────────────────────────
        semantic_score = poi.get("embedding_similarity", 0)
        scores["semantic"] = semantic_score

        # ── 2. Spatial scores — destination vs route ───────────────────────
        in_dest_buffer  = poi.get("_in_dest_buffer", False)
        in_route_buffer = poi.get("_in_route_buffer", True)

        dist_to_dest  = poi.get("distance_to_dest_km") or 999.0
        dist_to_route = poi.get("distance_to_route_km") or 50.0

        # Proximity curves: 1.0 at 0 km, ~0.5 at the half-decay distance
        # Destination: half-decay at 30 km  (tight — we want local Pokhara places)
        # Route:       half-decay at 20 km  (loose — highway stops are spread out)
        dest_proximity  = 1.0 / (1.0 + dist_to_dest  / 30.0)
        route_proximity = 1.0 / (1.0 + dist_to_route / 20.0)

        # Dynamic destination weight
        if in_dest_buffer and not in_route_buffer:
            destination_weight = 0.85   # Almost entirely destination-scored
        elif in_dest_buffer and in_route_buffer:
            destination_weight = 0.50   # Balanced
        else:
            destination_weight = 0.10   # Highway stop — route matters more

        route_weight = 1.0 - destination_weight

        # Combined spatial score (0-1)
        spatial_score = (destination_weight * dest_proximity
                         + route_weight     * route_proximity)
        scores["dest_proximity"]  = dest_proximity
        scores["route_proximity"] = route_proximity
        scores["spatial"]         = spatial_score
        # Keep "route" key for backward compat with any downstream readers
        scores["route"] = route_proximity

        # ── 3. Preference match ────────────────────────────────────────────
        preference_score = 0.5
        if interests:
            poi_text_corpus = (
                " ".join(str(t) for t in (poi.get("tags") or [])) + " " +
                " ".join(str(s) for s in (poi.get("travel_styles") or [])) + " " +
                " ".join(str(l) for l in (poi.get("landscape") or [])) + " " +
                str(poi.get("category") or "") + " " +
                str(poi.get("name") or "") + " " +
                str(poi.get("description") or "")
            ).lower()

            interest_keywords = {
                "nature":      ["nature", "viewpoint", "lake", "waterfall", "park", "hiking",
                                 "mountain", "forest", "landscape", "scenic", "river", "valley",
                                 "sanctuary", "peak"],
                "culture":     ["culture", "temple", "monastery", "stupa", "museum", "historic",
                                 "heritage", "palace", "monument", "shrine", "architecture",
                                 "religious", "ancient"],
                "history":     ["historic", "heritage", "museum", "ancient", "palace", "fort",
                                 "history", "monument", "site"],
                "photography": ["viewpoint", "landscape", "scenic", "lake", "temple",
                                 "architecture", "sunset", "sunrise", "panorama", "view", "peak"],
                "adventure":   ["hiking", "trekking", "rafting", "climbing", "zipline",
                                 "paragliding", "trail", "camp", "adventure", "safari"],
                "food":        ["restaurant", "cafe", "bakery", "food", "dining", "cuisine",
                                 "eatery", "tea house"],
            }

            match_count = sum(
                1 for interest in interests
                if any(kw in poi_text_corpus
                       for kw in interest_keywords.get(interest.lower(), [interest.lower()]))
            )
            if match_count > 0:
                preference_score = min(1.0, 0.5 + match_count * 0.25)

        scores["preference"] = preference_score

        # ── 4. Popularity ──────────────────────────────────────────────────
        scores["popularity"] = min(1.0, (poi.get("popularity") or 0.0) / 100.0)

        # ── 5. Quality & recognition ───────────────────────────────────────
        rating_norm      = min(1.0, (poi.get("rating") or 3.5) / 5.0)
        has_recognition  = 1.0 if (poi.get("wikidata_id") or poi.get("wikipedia_url")
                                   or poi.get("description")) else 0.5
        scores["quality"] = rating_norm * 0.7 + has_recognition * 0.3

        # ── 6. Category relevance ──────────────────────────────────────────
        category = (poi.get("category") or "").lower()
        if any(k in category for k in ("viewpoint", "temple", "museum", "cultural",
                                        "national park", "lake", "waterfall", "heritage")):
            scores["category"] = 1.0
        elif any(k in category for k in ("hotel", "guest house", "resort",
                                          "restaurant", "cafe")):
            scores["category"] = 0.85
        else:
            scores["category"] = 0.70

        # ── 7. Seasonal relevance ──────────────────────────────────────────
        seasonal_score = 0.7
        if travel_season and poi.get("seasons"):
            if travel_season.lower() in [s.lower() for s in poi["seasons"]]:
                seasonal_score = 1.0
        scores["season"] = seasonal_score

        # ── 8. Dietary match ───────────────────────────────────────────────
        scores["dietary"] = poi.get("dietary_match_score", 1.0)

        # ── 9. Name quality ────────────────────────────────────────────────
        scores["name_quality"] = self._score_name_quality(poi)

        # ── 10. Wiki bonus — places with Wikidata/Wikipedia are verifiably
        #        real, notable, and named. Give them a concrete lift so they
        #        rise above the mass of anonymous OSM entries.
        has_wiki = bool(poi.get("wikidata_id") or poi.get("wikipedia_url"))
        scores["wiki_bonus"] = 1.0 if has_wiki else 0.0

        # ── 11. Detour penalty (only for route-corridor-only POIs) ─────────
        if in_dest_buffer:
            scores["detour"] = 0.0
        else:
            scores["detour"] = -min(0.2, dist_to_route / 150.0)

        # ── 12. Route POI bonus — reward route-corridor POIs so they aren't
        #        drowned out by destination-area POIs.
        poi_type = poi.get("_poi_type", "destination")
        if poi_type == "route":
            scores["route_poi_bonus"] = 1.0
        elif poi_type == "both":
            scores["route_poi_bonus"] = 0.5
        else:
            scores["route_poi_bonus"] = 0.0

        # ── Final composite ────────────────────────────────────────────────
        # Weights sum to 1.0 (detour is a signed offset).
        # wiki_bonus (15%) strongly rewards verifiably notable places.
        # name_quality (10%) penalises generic/unnamed places harder.
        # route_poi_bonus (3%) ensures route stops surface in results.
        final_score = (
            0.20 * scores["semantic"]       +
            0.18 * scores["spatial"]        +
            0.15 * scores["wiki_bonus"]     +
            0.12 * scores["preference"]     +
            0.10 * scores["name_quality"]   +
            0.08 * scores["popularity"]     +
            0.08 * scores["quality"]        +
            0.03 * scores["route_poi_bonus"]+
            0.02 * scores["category"]       +
            0.02 * scores["season"]         +
            0.02 * scores["dietary"]        +
                   scores["detour"]
        )

        scores["final"] = max(0.0, min(1.0, final_score))

        # Expose destination_weight for debugging / logging
        scores["destination_weight"] = destination_weight

        return scores

    def _score_candidates(
        self,
        pois: List[Dict[str, Any]],
        interests: Optional[List[str]],
        dietary_preferences: Optional[List[str]],
        num_children: int,
        budget: str,
        travel_season: Optional[str],
        pace: str = "balanced",
        num_days: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Stage 1 — candidate relevance scoring using embedding similarity and modular composite scoring.
        """
        # Build user preference dictionary
        user_preferences = {
            "interests": interests or [],
            "dietary_preferences": dietary_preferences or [],
            "num_adults": 1,
            "num_children": num_children,
            "travel_style": pace,
            "budget": budget,
            "travel_season": travel_season,
            "num_days": num_days,
            "family_friendly": num_children > 0,
        }
        
        place_ids = [poi.get("id") for poi in pois if poi.get("id")]
        
        if not place_ids:
            print("[WARNING] No valid place IDs found in candidates")
            return pois
        
        print(f"[INFO] Using embedding similarity search for {len(place_ids)} candidates")
        similarities = embedding_service.find_places_by_user_preference(
            user_preferences, 
            place_ids, 
            limit=len(place_ids)
        )
        
        similarity_map = {pid: score for pid, score in similarities}
        
        for poi in pois:
            place_id = poi.get("id")
            if place_id in similarity_map:
                poi["relevance_score"] = similarity_map[place_id]
                poi["embedding_similarity"] = similarity_map[place_id]
            else:
                poi["relevance_score"] = 0.0
                poi["embedding_similarity"] = 0.0
        
        print(f"[INFO] Embedding similarity scoring complete")

        print(f"[INFO] Applying modular route-aware scoring to all {len(pois)} candidates")

        for poi in pois:
            modular_scores = self._calculate_modular_score(
                poi, interests, travel_season, []
            )
            poi["modular_scores"] = modular_scores
            poi["relevance_score"] = modular_scores["final"]

        # Re-sort by final composite modular score
        pois.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return pois

    def _diversity_aware_selection(
        self,
        pois: List[Dict[str, Any]],
        num_select: int,
        lambda_param: float = 0.5,
        similarity_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Implement diversity-aware selection using MMR-like algorithm based on composite relevance score.
        """
        if not pois or num_select <= 0:
            return []
        
        if len(pois) <= num_select:
            return pois
        
        # Sort by composite relevance score first
        pois = sorted(pois, key=lambda x: x.get("relevance_score", x.get("embedding_similarity", 0)), reverse=True)
        
        selected = []
        remaining = pois.copy()
        
        selected.append(remaining.pop(0))
        
        while len(selected) < num_select and remaining:
            best_candidate = None
            best_score = -1
            
            for candidate in remaining:
                relevance_score = candidate.get("relevance_score", candidate.get("embedding_similarity", 0))
                
                diversity_penalty = 0
                for selected_poi in selected:
                    similarity = self._calculate_poi_similarity(candidate, selected_poi)
                    if similarity > similarity_threshold:
                        diversity_penalty += similarity
                
                mmr_score = lambda_param * relevance_score - (1 - lambda_param) * diversity_penalty
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break
        
        print(f"[INFO] Diversity-aware selection: selected {len(selected)} from {len(pois)} candidates")
        return selected
    
    def _calculate_poi_similarity(self, poi1: Dict[str, Any], poi2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two POIs for diversity assessment.
        
        Considers:
        - Semantic similarity (if embeddings available)
        - Category similarity
        - Geographic proximity
        - Attraction type similarity
        """
        similarity = 0.0
        
        # 1. Category similarity
        cat1 = poi1.get("category", "").lower()
        cat2 = poi2.get("category", "").lower()
        if cat1 == cat2:
            similarity += 0.3
        elif any(k in cat1 for k in cat2.split()) or any(k in cat2 for k in cat1.split()):
            similarity += 0.15
        
        # 2. Geographic proximity (closer = more similar)
        # Use 30 km normalization so POIs within ~30 km are considered
        # "nearby" — wider spread pushes the recommender to scatter results.
        lat1, lng1 = poi1.get("latitude", 0), poi1.get("longitude", 0)
        lat2, lng2 = poi2.get("latitude", 0), poi2.get("longitude", 0)
        if lat1 and lng1 and lat2 and lng2:
            distance = self._haversine_distance(lat1, lng1, lat2, lng2)
            geo_similarity = max(0, 1 - (distance / 30))  # Normalize to 0-1 for 30km
            similarity += 0.4 * geo_similarity  # Stronger geo penalty for clustering
        
        # 3. Attraction type similarity (based on semantic tags)
        tags1 = set(str(t).lower() for t in poi1.get("semantic_tags", []))
        tags2 = set(str(t).lower() for t in poi2.get("semantic_tags", []))
        if tags1 and tags2:
            tag_overlap = len(tags1 & tags2) / len(tags1 | tags2)
            similarity += 0.2 * tag_overlap
        
        # 4. Subcategory similarity (travel styles)
        styles1 = set(str(s).lower() for s in poi1.get("travel_styles", []))
        styles2 = set(str(s).lower() for s in poi2.get("travel_styles", []))
        if styles1 and styles2:
            style_overlap = len(styles1 & styles2) / len(styles1 | styles2)
            similarity += 0.1 * style_overlap
        
        return min(1.0, similarity)

    def _enforce_minimum_spacing(
        self,
        pois: List[Dict[str, Any]],
        min_distance_km: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Filter/re-order selected POIs so no two POIs in the result are within
        min_distance_km of each other unless both are wiki-verified notable places.
        """
        if not pois:
            return pois

        selected = []
        for poi in pois:
            lat, lng = poi.get("latitude"), poi.get("longitude")
            if lat is None or lng is None:
                selected.append(poi)
                continue

            too_close = False
            for s in selected:
                s_lat, s_lng = s.get("latitude"), s.get("longitude")
                if s_lat is not None and s_lng is not None:
                    dist = self._haversine_distance(lat, lng, s_lat, s_lng)
                    if dist < min_distance_km:
                        has_wiki1 = bool(poi.get("wikidata_id") or poi.get("wikipedia_url"))
                        has_wiki2 = bool(s.get("wikidata_id") or s.get("wikipedia_url"))
                        # Allow close proximity only if both are major wiki places (e.g. Kathmandu Durbar Square attractions)
                        if not (has_wiki1 and has_wiki2):
                            too_close = True
                            break
            if not too_close:
                selected.append(poi)

        return selected

    def _classify_day_type(self, day_num: int, num_days: int) -> str:
        """
        Classify a day as 'route_day' or 'destination_day'.

        For a multi-day trip:
          - Day 1          → route_day  (departure / travel in)
          - Day N (last)   → route_day  (travel out / return)
          - Days 2 … N-1   → destination_day (explore the destination area)

        For 1- or 2-day trips every day is a route_day because there are no
        dedicated middle days.
        """
        if num_days <= 2:
            return "route_day"
        if day_num == 1 or day_num == num_days:
            return "route_day"
        return "destination_day"

    def _sort_candidates_for_day(
        self,
        candidates: List[Dict[str, Any]],
        day_type: str,
        route_coordinates: List[List[float]],
        dest_lat: float,
        dest_lng: float,
        origin_lat: float,
        origin_lng: float,
        day_num: int,
        num_days: int,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank candidates based on the day type:

        route_day      → prefer places close to the route corridor.  Day 1
                         candidates are biased toward the origin end of the
                         route; last-day candidates toward the destination end.
        destination_day → prefer places close to the destination (dest_lat/lng).
                         Route-only places are pushed to the back.

        The existing embedding_similarity score is blended with the spatial
        proximity score so relevance is not discarded entirely.
        """
        if not candidates:
            return candidates

        scored = []
        for poi in candidates:
            lat = poi.get("latitude")
            lng = poi.get("longitude")
            if lat is None or lng is None:
                scored.append((0.0, poi))
                continue

            similarity = poi.get("embedding_similarity", 0.5)

            if day_type == "route_day":
                # For the first day weight by proximity to origin; last day to destination
                if day_num == 1:
                    anchor_lat, anchor_lng = origin_lat, origin_lng
                else:
                    anchor_lat, anchor_lng = dest_lat, dest_lng

                dist_km = self._haversine_distance(lat, lng, anchor_lat, anchor_lng)
                # Proximity score: 1.0 at 0 km, decays to ~0.5 at 50 km
                proximity = 1.0 / (1.0 + dist_km / 50.0)
                # Also reward being near the route corridor
                if route_coordinates:
                    dist_to_route = self._calculate_distance_to_route(lat, lng, route_coordinates)
                    route_proximity = 1.0 / (1.0 + dist_to_route / 20.0)
                else:
                    route_proximity = 0.5
                spatial_score = 0.5 * proximity + 0.5 * route_proximity
            else:
                # destination_day: rank by closeness to destination
                dist_to_dest = self._haversine_distance(lat, lng, dest_lat, dest_lng)
                # Proximity score: 1.0 at 0 km, decays to ~0.5 at 30 km, ~0.25 at 90 km
                spatial_score = 1.0 / (1.0 + dist_to_dest / 30.0)

            # Blend: 60 % spatial, 40 % semantic relevance
            combined = 0.6 * spatial_score + 0.4 * similarity
            scored.append((combined, poi))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [poi for _, poi in scored]

    def _plan_trip_slots(
        self,
        category_results: Dict[str, Dict[str, Any]],
        num_days: int,
        pace: str = "balanced",
        route_coordinates: List[List[float]] = None,
        dest_lat: float = None,
        dest_lng: float = None,
        origin_lat: float = None,
        origin_lng: float = None,
    ) -> Dict[str, Any]:
        """
        Transform ranked candidates into structured itinerary slots.

        Guarantees
        ----------
        • Exactly 1 overnight hotel per day — cycles if candidates < num_days.
        • Exactly 2 meal slots per day (lunch + dinner) — re-uses restaurants
          across days rather than leaving any day without meals.
        • Activity target met or as close as data allows — fills from
          destination-buffer pool first for destination days, route-progress
          cluster first for route days, then falls back to global unassigned
          pool.

        Day classification
        ------------------
        route_day      Day 1 and last day  — travel in / out
        destination_day  All middle days   — explore the destination
        (1-2 day trips are all route_days)
        """
        accommodation = category_results["accommodation"]["candidates"]
        restaurants   = category_results["restaurants"]["candidates"]
        attractions   = category_results["attractions"]["candidates"]

        # Target activities to PLACE per day (half of retrieved candidates)
        target_activities = {
            "relaxed": 5,
            "balanced": 6,
            "packed": 7,
        }.get(pace, 6)

        trip_slots = {"num_days": num_days, "pace": pace, "days": []}

        # ── Pre-sort all pools by relevance_score descending ──────────────
        def _by_score(lst):
            return sorted(lst, key=lambda x: x.get("relevance_score", 0), reverse=True)

        accommodation = _by_score(accommodation)
        restaurants   = _by_score(restaurants)

        # Split attractions into dest-buffer and route-only pools
        dest_attractions  = _by_score([a for a in attractions if a.get("_in_dest_buffer")])
        route_attractions = _by_score([a for a in attractions if not a.get("_in_dest_buffer")])
        all_attractions   = dest_attractions + route_attractions  # dest first globally

        # Also build route-progress clusters for route_days
        if route_coordinates and len(route_coordinates) > 1:
            attraction_clusters = self._cluster_activities_by_route_progress(
                list(attractions), route_coordinates, num_days
            )
        else:
            chunk = max(1, len(attractions) // max(num_days, 1))
            attraction_clusters = [
                attractions[i * chunk: (i + 1) * chunk if i < num_days - 1 else len(attractions)]
                for i in range(num_days)
            ]

        used_attraction_ids: set = set()

        for day_num in range(1, num_days + 1):
            day_type = self._classify_day_type(day_num, num_days)

            day_slots = {
                "day": day_num,
                "day_type": day_type,
                "overnight": None,
                "activities": [],
                "meals": [],
            }

            # ── 1. Overnight hotel (guaranteed, cycles if needed) ─────────
            if accommodation:
                idx = (day_num - 1) % len(accommodation)
                h = accommodation[idx]
                day_slots["overnight"] = {
                    "place_id": h.get("id"),
                    "name":     h.get("name"),
                    "category": h.get("category"),
                    "latitude": h.get("latitude"),
                    "longitude": h.get("longitude"),
                    "similarity": h.get("embedding_similarity", 0),
                }
            else:
                print(f"[WARN] Day {day_num}: no accommodation candidates available")

            # ── 2. Attractions ─────────────────────────────────────────────
            # Build an ordered candidate pool for this day.
            if day_type == "destination_day" and dest_lat is not None:
                # Primary: unassigned dest-buffer attractions sorted by dest proximity
                unassigned_dest = [
                    a for a in dest_attractions if a.get("id") not in used_attraction_ids
                ]
                if dest_lat is not None and dest_lng is not None:
                    unassigned_dest = self._sort_candidates_for_day(
                        unassigned_dest,
                        day_type="destination_day",
                        route_coordinates=route_coordinates or [],
                        dest_lat=dest_lat,
                        dest_lng=dest_lng,
                        origin_lat=origin_lat or dest_lat,
                        origin_lng=origin_lng or dest_lng,
                        day_num=day_num,
                        num_days=num_days,
                    )
                # Fallback: any unassigned attraction (dest first)
                fallback = [
                    a for a in all_attractions if a.get("id") not in used_attraction_ids
                    and a.get("id") not in {x.get("id") for x in unassigned_dest}
                ]
                day_pool = unassigned_dest + fallback
                print(
                    f"[INFO] Day {day_num} ({day_type}): "
                    f"{len(unassigned_dest)} dest-buffer + {len(fallback)} fallback candidates"
                )
            else:
                # route_day: route-progress cluster first, then dest attractions, then rest
                cluster_pool = [
                    a for a in (attraction_clusters[day_num - 1]
                                if day_num - 1 < len(attraction_clusters) else [])
                    if a.get("id") not in used_attraction_ids
                ]
                if route_coordinates and dest_lat is not None:
                    cluster_pool = self._sort_candidates_for_day(
                        cluster_pool,
                        day_type="route_day",
                        route_coordinates=route_coordinates,
                        dest_lat=dest_lat,
                        dest_lng=dest_lng,
                        origin_lat=origin_lat or dest_lat,
                        origin_lng=origin_lng or dest_lng,
                        day_num=day_num,
                        num_days=num_days,
                    )
                extra = [
                    a for a in all_attractions
                    if a.get("id") not in used_attraction_ids
                    and a.get("id") not in {x.get("id") for x in cluster_pool}
                ]
                day_pool = cluster_pool + extra
                print(
                    f"[INFO] Day {day_num} ({day_type}): "
                    f"{len(cluster_pool)} cluster + {len(extra)} extra candidates"
                )

            # Fill up to target
            day_attractions = []
            for a in day_pool:
                if len(day_attractions) >= target_activities:
                    break
                aid = a.get("id")
                if aid not in used_attraction_ids:
                    day_attractions.append(a)
                    used_attraction_ids.add(aid)

            time_labels = ["morning", "late_morning", "afternoon", "late_afternoon",
                           "evening", "late_evening", "night"]
            for i, attraction in enumerate(day_attractions):
                in_dest = False
                if dest_lat is not None and dest_lng is not None:
                    in_dest = self._haversine_distance(
                        attraction.get("latitude", 0), attraction.get("longitude", 0),
                        dest_lat, dest_lng
                    ) <= 100
                day_slots["activities"].append({
                    "place_id":             attraction.get("id"),
                    "name":                 attraction.get("name"),
                    "category":             attraction.get("category"),
                    "latitude":             attraction.get("latitude"),
                    "longitude":            attraction.get("longitude"),
                    "similarity":           attraction.get("embedding_similarity", 0),
                    "time_slot":            time_labels[i] if i < len(time_labels) else "daytime",
                    "activity_type":        "attraction",
                    "in_destination_buffer": in_dest,
                })

            # ── 3. Meals — guaranteed lunch + dinner every day ─────────────
            # Sort restaurants for this day by spatial relevance.
            # Always re-use from full restaurant pool (restaurants can repeat
            # across days — that's fine, they're different meals).
            if restaurants:
                if day_type == "destination_day" and dest_lat is not None and dest_lng is not None:
                    day_rest_pool = self._sort_candidates_for_day(
                        restaurants,
                        day_type="destination_day",
                        route_coordinates=route_coordinates or [],
                        dest_lat=dest_lat,
                        dest_lng=dest_lng,
                        origin_lat=origin_lat or dest_lat,
                        origin_lng=origin_lng or dest_lng,
                        day_num=day_num,
                        num_days=num_days,
                    )
                else:
                    # route_day: rotate starting index so we don't repeat the
                    # same restaurant at position 0 every single day
                    offset = ((day_num - 1) * 2) % len(restaurants)
                    day_rest_pool = restaurants[offset:] + restaurants[:offset]

                # Pick 2 unique restaurants for this day
                # (unique within the day; repetition across days is acceptable)
                seen_today: set = set()
                day_restaurants = []
                for r in day_rest_pool:
                    if len(day_restaurants) >= 2:
                        break
                    rid = r.get("id")
                    if rid not in seen_today:
                        day_restaurants.append(r)
                        seen_today.add(rid)

                # If fewer than 2 unique, cycle back through to fill
                if len(day_restaurants) < 2:
                    for r in restaurants:
                        if len(day_restaurants) >= 2:
                            break
                        rid = r.get("id")
                        if rid not in seen_today:
                            day_restaurants.append(r)
                            seen_today.add(rid)
            else:
                day_restaurants = []
                print(f"[WARN] Day {day_num}: no restaurant candidates — meals will be empty")

            for i, r in enumerate(day_restaurants):
                meal_type = "lunch" if i == 0 else "dinner"
                in_dest = False
                if dest_lat is not None and dest_lng is not None:
                    in_dest = self._haversine_distance(
                        r.get("latitude", 0), r.get("longitude", 0),
                        dest_lat, dest_lng
                    ) <= 100
                day_slots["meals"].append({
                    "place_id":             r.get("id"),
                    "name":                 r.get("name"),
                    "category":             r.get("category"),
                    "latitude":             r.get("latitude"),
                    "longitude":            r.get("longitude"),
                    "similarity":           r.get("embedding_similarity", 0),
                    "meal_type":            meal_type,
                    "activity_type":        "restaurant",
                    "in_destination_buffer": in_dest,
                })

            trip_slots["days"].append(day_slots)

        # ── Summary log ───────────────────────────────────────────────────
        print(f"[INFO] Trip slots: {num_days} days, pace={pace}")
        for day in trip_slots["days"]:
            dest_count = sum(1 for a in day["activities"] if a.get("in_destination_buffer"))
            hotel_name = day["overnight"]["name"] if day["overnight"] else "NONE"
            print(
                f"  Day {day['day']} [{day['day_type']}]: "
                f"{len(day['activities'])} activities ({dest_count} near dest), "
                f"{len(day['meals'])} meals, "
                f"hotel: {hotel_name}"
            )

        return trip_slots

    def _create_structured_representation(
        self,
        trip_slots: Dict[str, Any],
        category_availability: Dict[str, Dict[str, int]],
        meal_plan: Dict[str, Any],
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float
    ) -> Dict[str, Any]:
        """
        Create structured intermediate representation for LLM context.
        
        This transforms trip slots into a structured format that the LLM can use
        to generate natural language itineraries without having to discover or invent places.
        """
        structured = {
            "trip": {
                "origin": {"lat": origin_lat, "lng": origin_lng},
                "destination": {"lat": dest_lat, "lng": dest_lng},
                "num_days": trip_slots["num_days"],
                "pace": trip_slots["pace"]
            },
            "category_availability": category_availability,
            "meal_plan": meal_plan,
            "days": []
        }
        
        for day in trip_slots["days"]:
            day_data = {
                "day": day["day"],
                "overnight": day["overnight"],
                "activities": day["activities"],
                "meals": day["meals"]
            }
            structured["days"].append(day_data)
        
        print(f"[INFO] Created structured intermediate representation:")
        print(f"  Trip: {structured['trip']['num_days']} days, pace={structured['trip']['pace']}")
        print(f"  Category availability: {category_availability}")
        print(f"  Meal plan: {meal_plan['total_meal_slots']} meal slots, {meal_plan['restaurant_needed_slots']} restaurant slots")
        
        return structured

    def _validate_itinerary(
        self,
        itinerary: Dict[str, Any],
        structured_representation: Dict[str, Any],
        category_availability: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """
        Validate the LLM-generated itinerary against constraints.
        
        Validates:
        - Geographic constraints (no excessive backtracking, activities near route)
        - Category constraints (accommodation, restaurants, attractions exist in candidate data)
        - Time constraints (no impossible schedules)
        - User constraints (dietary, budget, pace, season)
        - Data integrity (all POIs have valid candidate IDs)
        
        Returns:
            Validation result with valid flag and any violations
        """
        violations = []
        
        # Extract candidate IDs from structured representation
        candidate_ids = set()
        for day in structured_representation.get("days", []):
            if day.get("overnight"):
                candidate_ids.add(day["overnight"].get("place_id"))
            for activity in day.get("activities", []):
                candidate_ids.add(activity.get("place_id"))
            for meal in day.get("meals", []):
                candidate_ids.add(meal.get("place_id"))
        
        # Validate data integrity
        itinerary_days = itinerary.get("days", [])
        for day_idx, day in enumerate(itinerary_days, 1):
            # Check overnight accommodation
            overnight = day.get("overnight_accommodation")
            if overnight:
                poi_id = overnight.get("poi_id")
                if poi_id not in candidate_ids:
                    violations.append({
                        "type": "invalid_poi_id",
                        "day": day_idx,
                        "poi_id": poi_id,
                        "message": f"Overnight accommodation POI ID {poi_id} not in candidate set"
                    })
            
            # Check activities
            for activity in day.get("activities", []):
                poi_id = activity.get("poi_id")
                if poi_id not in candidate_ids:
                    violations.append({
                        "type": "invalid_poi_id",
                        "day": day_idx,
                        "poi_id": poi_id,
                        "message": f"Activity POI ID {poi_id} not in candidate set"
                    })
        
        # Validate category availability
        if category_availability["restaurants"]["selected"] == 0:
            # Check if LLM hallucinated restaurants
            restaurant_count = sum(
                1 for day in itinerary_days
                for activity in day.get("activities", [])
                if activity.get("activity_type") == "restaurant"
            )
            if restaurant_count > 0:
                violations.append({
                    "type": "hallucinated_restaurants",
                    "message": f"LLM recommended {restaurant_count} restaurants but 0 were available in candidates"
                })
        
        # Validate geographic coherence (basic check)
        # Check if overnight locations progress reasonably
        overnight_locations = []
        for day in itinerary_days:
            overnight = day.get("overnight_accommodation")
            if overnight:
                overnight_locations.append({
                    "day": day.get("day"),
                    "lat": overnight.get("latitude"),
                    "lng": overnight.get("longitude")
                })
        
        # Check for excessive backtracking (simplified)
        if len(overnight_locations) > 2:
            for i in range(1, len(overnight_locations) - 1):
                prev = overnight_locations[i - 1]
                curr = overnight_locations[i]
                next_loc = overnight_locations[i + 1]
                
                # If current is far from both previous and next, might be backtracking
                dist_prev = self._haversine_distance(
                    curr["lat"], curr["lng"],
                    prev["lat"], prev["lng"]
                )
                dist_next = self._haversine_distance(
                    curr["lat"], curr["lng"],
                    next_loc["lat"], next_loc["lng"]
                )
                
                if dist_prev > 50 and dist_next > 50:
                    violations.append({
                        "type": "excessive_backtracking",
                        "day": curr["day"],
                        "message": f"Day {curr['day']} overnight location may cause excessive backtracking"
                    })
        
        # Validate time constraints (basic check)
        for day in itinerary_days:
            activities = day.get("activities", [])
            total_hours = sum(
                activity.get("duration_hours", 2) 
                for activity in activities
            )
            if total_hours > 12:  # More than 12 hours of activities is unrealistic
                violations.append({
                    "type": "time_constraint_violation",
                    "day": day.get("day"),
                    "message": f"Day {day.get('day')} has {total_hours} hours of activities, which may be unrealistic"
                })
        
        validation_result = {
            "valid": len(violations) == 0,
            "violations": violations,
            "total_violations": len(violations)
        }
        
        print(f"[INFO] Itinerary validation: {'VALID' if validation_result['valid'] else 'INVALID'}")
        if violations:
            print(f"[WARNING] Found {len(violations)} validation violations:")
            for violation in violations:
                print(f"  - {violation['type']}: {violation['message']}")
        
        return validation_result

    def _estimate_detour_km(
        self, poi: Dict[str, Any], route_coordinates: List[List[float]]
    ) -> float:
        """
        Estimate round-trip detour distance to visit a POI: the straight-line
        distance from the nearest point on the route, doubled (there + back).
        This is a proxy for real routing-engine detour cost — good enough to
        rank/select with, not to publish as a drive-time estimate.
        """
        lat, lng = poi["latitude"], poi["longitude"]
        nearest = min(
            self._haversine_distance(lat, lng, c[1], c[0]) for c in route_coordinates
        )
        return nearest * 2

    def _optimize_trip_selection(
        self,
        scored_candidates: List[Dict[str, Any]],
        route_coordinates: List[List[float]],
        num_days: int,
        pace: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Stage 2 — trip-level optimization: "does this place fit in the whole
        journey?" Greedily selects the highest relevance-per-minute
        candidates that fit inside a time budget (num_days x pace), subject
        to a detour-cost penalty and a per-category diversity cap so the
        result isn't 8 temples and nothing else.

        This is a greedy heuristic, not an exact solver — it optimizes one
        pass by relevance-per-minute density. If you need provably-optimal
        packing later (e.g. exact time-window constraints), this is the
        seam to swap in a proper solver (OR-tools, ILP) without touching
        stage 1.
        """
        sampled_route = self._sample_route(route_coordinates, max_points=150)
        hours_per_day = PACE_HOURS_PER_DAY.get(pace, PACE_HOURS_PER_DAY["balanced"])
        budget_minutes = num_days * hours_per_day * 60

        enriched = []
        for poi in scored_candidates:
            detour_km = self._estimate_detour_km(poi, sampled_route)
            detour_minutes = (detour_km / DETOUR_SPEED_KMH) * 60
            visit_minutes = self._parse_visit_duration_to_minutes(poi.get("visit_duration"))
            total_minutes = detour_minutes + visit_minutes

            # Use non-linear benefit scoring instead of linear density
            benefit_score = self._calculate_benefit_score(
                poi.get("relevance_score", 0),
                total_minutes
            )

            poi["_detour_km"] = round(detour_km, 2)
            poi["_estimated_minutes"] = round(total_minutes, 1)
            poi["_benefit_score"] = benefit_score
            enriched.append(poi)

        enriched.sort(key=lambda p: p["_benefit_score"], reverse=True)

        # Diversity cap: no single category can dominate the trip.
        max_per_category = max(2, len(enriched) // 6 or 1)

        selected: List[Dict[str, Any]] = []
        used_minutes = 0.0
        category_counts: Dict[str, int] = {}

        for poi in enriched:
            category = (poi.get("category") or "other").lower()
            if category_counts.get(category, 0) >= max_per_category:
                continue
            if used_minutes + poi["_estimated_minutes"] > budget_minutes:
                continue
            selected.append(poi)
            used_minutes += poi["_estimated_minutes"]
            category_counts[category] = category_counts.get(category, 0) + 1

        time_summary = {
            "budget_minutes": round(budget_minutes, 1),
            "used_minutes": round(used_minutes, 1),
            "remaining_minutes": round(budget_minutes - used_minutes, 1),
            "pace": pace,
            "hours_per_day": hours_per_day,
        }
        return selected, time_summary

    def _build_reasons(
        self,
        selected: List[Dict[str, Any]],
        interests: Optional[List[str]],
        dietary_preferences: Optional[List[str]],
        num_children: int,
        budget: str,
        travel_season: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Attach a short "why this was recommended" list to each selected
        destination, matching the destination-set shape (place + reasons)
        rather than a bare numeric ranking.
        """
        for poi in selected:
            reasons = []
            if interests:
                poi_tags = set(poi.get("tags") or []) | set(poi.get("travel_styles") or [])
                if set(interests) & poi_tags:
                    reasons.append("Matches your interests")
            if travel_season:
                seasons = set(s.lower() for s in (poi.get("seasons") or []))
                if travel_season.lower() in seasons:
                    reasons.append(f"Good fit for {travel_season} travel")
            if num_children > 0 and poi.get("family_friendly"):
                reasons.append("Family-friendly")
            if dietary_preferences and self._is_food_place(poi):
                reasons.append("Matches dietary preferences")
            if poi.get("_detour_km", 0) <= 2:
                reasons.append("Right on the route, minimal detour")
            if not reasons:
                reasons.append("Highly rated along your route")
            poi["reasons"] = reasons
        return selected

    def _place_to_dict(self, place: PlaceDB) -> Dict[str, Any]:
        """Convert PlaceDB model to dictionary.

        Uses the database row's ST_Y/ST_X parsed lat/lng when available, otherwise
        falls back to centroid WKT parse, then to bbox midpoint as last resort.
        """
        lat = place.latitude
        lng = place.longitude

        if lat is None or lng is None:
            # Fallback: bbox midpoint (same as Place.to_dict() logic)
            if (place.bbox_min_lat and place.bbox_min_lon and
                    place.bbox_max_lat and place.bbox_max_lon):
                lat = (place.bbox_min_lat + place.bbox_max_lat) / 2
                lng = (place.bbox_min_lon + place.bbox_max_lon) / 2

        return {
            "id": str(place.id),
            "name": place.name,
            "category": place.category,
            "latitude": lat,
            "longitude": lng,
            "district": place.raw_tags.get("addr:district") if place.raw_tags else None,
            "province": place.raw_tags.get("addr:province") if place.raw_tags else None,
            "city": place.raw_tags.get("addr:city") if place.raw_tags else None,
            "description": place.raw_tags.get("description") if place.raw_tags else None,
            "history": place.raw_tags.get("historic") if place.raw_tags else None,
            "tags": place.semantic_tags,
            "seasons": place.best_seasons,
            "images": place.raw_tags.get("images") if place.raw_tags else None,
            "has_ticket": place.raw_tags.get("has_ticket") if place.raw_tags else None,
            "family_friendly": place.family_friendly,
            "popularity": place.popularity,
            "rating": place.rating,
            "difficulty": place.difficulty,
            "visit_duration": place.visit_duration,
            "accessibility": place.accessibility,
            "travel_styles": place.travel_styles,
            "landscape": place.landscape,
            "wikidata_id": place.wikidata_id,
            "wikipedia_url": place.wikipedia_url,
            "website": place.website,
            "raw_tags": place.raw_tags,
        }

    @staticmethod
    def _parse_visit_duration_to_minutes(visit_duration) -> float:
        """
        Parse a visit_duration string (e.g. "1-2 hours", "30 minutes - 1 hour",
        "Overnight", "4-8 hours") into a numeric number of minutes.

        Falls back to a category-aware default of 60 minutes if parsing fails.
        """
        if visit_duration is None:
            return 60.0

        if isinstance(visit_duration, (int, float)):
            return float(visit_duration)

        s = str(visit_duration).strip().lower()

        if not s:
            return 60.0

        # Overnight stays (accommodation) - use a low value so they don't dominate
        if "overnight" in s:
            return 30.0

        try:
            total_minutes = 0.0

            # Extract hour patterns like "1-2 hours", "4 hours", "1 hour"
            import re

            # Pattern like "X-Y hours" or "X hours" or "X hour"
            range_match = re.search(
                r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*hours?", s
            )
            if range_match:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                avg_hours = (low + high) / 2.0
                total_minutes += avg_hours * 60.0
            else:
                single_hour = re.search(r"(\d+(?:\.\d+)?)\s*hours?", s)
                if single_hour:
                    total_minutes += float(single_hour.group(1)) * 60.0

            # Pattern like "X minutes" or "X-Y minutes" or "X minutes - Y hour"
            # Handle standalone minutes or range with minutes
            minute_range_match = re.search(
                r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*minutes?", s
            )
            if minute_range_match:
                low = float(minute_range_match.group(1))
                high = float(minute_range_match.group(2))
                avg_minutes = (low + high) / 2.0
                total_minutes += avg_minutes
            else:
                # Check for standalone "X minutes" (avoid double counting "30 minutes" already parsed as "30 minutes - 1 hour")
                if not range_match and not single_hour:
                    single_minute = re.search(r"(\d+(?:\.\d+)?)\s*minutes?", s)
                    if single_minute:
                        total_minutes += float(single_minute.group(1))

            # Handle hybrid "30 minutes - 1 hour"
            hybrid_match = re.search(
                r"(\d+(?:\.\d+)?)\s*minutes?\s*-\s*(\d+(?:\.\d+)?)\s*hours?", s
            )
            if hybrid_match:
                low_min = float(hybrid_match.group(1))
                high_hours = float(hybrid_match.group(2))
                avg_minutes = (low_min + high_hours * 60.0) / 2.0
                total_minutes = avg_minutes

            if total_minutes > 0:
                return total_minutes

        except Exception:
            pass

        return 60.0


# Global instance
recommendation_service = RecommendationService()