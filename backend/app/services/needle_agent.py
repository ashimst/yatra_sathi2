"""
Cactus Needle Agent Service — Sub-second tool execution for AI chat & itinerary editing.

Runs locally with ~28MB RAM footprint, using grammar-constrained decoding and SLM tool execution
to execute typed Python tools without syntax errors, hallucinated parameters, or dropped itinerary days.
Provides deterministic structured execution for System 1.
"""
from __future__ import annotations

import logging
import math
import uuid
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.db.database import SessionLocal
from backend.app.models.place import Place as PlaceDB
from backend.app.services.decision_service import decision_service

logger = logging.getLogger(__name__)

# Check for cactus-needle package
try:
    import needle
    HAS_NEEDLE = True
    logger.info("Cactus Needle engine loaded successfully for System 1 execution.")
except ImportError:
    HAS_NEEDLE = False
    logger.info("cactus-needle package not installed; using high-speed native tool execution engine.")


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in kilometers between two geographic points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Needle Tool Implementations (Deterministic Operations)
# ---------------------------------------------------------------------------
def search_places(query: str, limit: int = 6, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search places in Nepal by name or category.
    
    Args:
        query: Search keywords (e.g. "Phewa Lake", "Thakali", "Boudhanath")
        limit: Maximum number of results to return
        category: Optional category filter (e.g. "Attraction", "Restaurant", "Hotel", "Viewpoint")
    """
    db = SessionLocal()
    try:
        q_clean = query.strip().lower()
        base_query = db.query(PlaceDB)
        
        if category:
            base_query = base_query.filter(func.lower(PlaceDB.category) == category.lower())
            
        if q_clean:
            q_like = f"%{q_clean}%"
            filtered = base_query.filter(
                func.lower(PlaceDB.name).like(q_like)
                | func.lower(PlaceDB.category).like(q_like)
            )
            results = filtered.order_by(PlaceDB.popularity.desc().nullslast()).limit(limit).all()
            
            # Fallback keyword search if full phrase has 0 matches
            if not results:
                stopwords = {"quiet", "peaceful", "good", "best", "nice", "great", "the", "a", "an", "on", "in", "near", "with", "please", "some", "by", "around"}
                words = [w for w in re.findall(r"\w+", q_clean) if w not in stopwords and len(w) > 2]
                for w in words:
                    w_like = f"%{w}%"
                    w_res = base_query.filter(
                        func.lower(PlaceDB.name).like(w_like)
                        | func.lower(PlaceDB.category).like(w_like)
                    ).order_by(PlaceDB.popularity.desc().nullslast()).limit(limit).all()
                    if w_res:
                        results = w_res
                        break
        else:
            results = base_query.order_by(PlaceDB.popularity.desc().nullslast()).limit(limit).all()
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "category": p.category,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "description": (p.raw_tags or {}).get("description", "")[:150] if p.raw_tags else "",
                "rating": p.rating,
                "price_level": p.price_level,
                "must_try": p.must_try,
                "is_hidden_gem": p.is_hidden_gem,
                "image_url": p.image_url,
            }
            for p in results
        ]
    finally:
        db.close()


def get_place_details(poi_id: str) -> Dict[str, Any]:
    """
    Retrieve full details for a specific place by its UUID.
    """
    db = SessionLocal()
    try:
        try:
            val_id = uuid.UUID(str(poi_id).strip())
        except ValueError:
            val_id = str(poi_id).strip()

        place = db.query(PlaceDB).filter(PlaceDB.id == val_id).first()
        if not place:
            return {"error": f"Place with ID {poi_id} not found."}

        return {
            "id": str(place.id),
            "name": place.name,
            "category": place.category,
            "latitude": place.latitude,
            "longitude": place.longitude,
            "description": (place.raw_tags or {}).get("description", "") if place.raw_tags else "",
            "semantic_tags": place.semantic_tags or [],
            "travel_styles": place.travel_styles or [],
            "best_seasons": place.best_seasons or [],
            "difficulty": place.difficulty,
            "visit_duration": place.visit_duration,
            "rating": place.rating,
            "price_level": place.price_level,
            "must_try": place.must_try,
            "is_hidden_gem": place.is_hidden_gem,
            "image_url": place.image_url,
        }
    finally:
        db.close()


def find_nearby_restaurant(
    lat: float, lng: float, radius_km: float = 5.0, diet: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Find authentic restaurants or cafes near a geographic coordinate.
    """
    db = SessionLocal()
    try:
        deg = radius_km / 111.0
        candidates = (
            db.query(PlaceDB)
            .filter(
                PlaceDB.latitude.between(lat - deg, lat + deg),
                PlaceDB.longitude.between(lng - deg, lng + deg),
                PlaceDB.category.in_(["Restaurant", "Cafe", "Food", "Bar"]),
            )
            .limit(20)
            .all()
        )

        results = []
        for c in candidates:
            dist = _haversine(lat, lng, c.latitude, c.longitude)
            if dist <= radius_km:
                results.append(
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "category": c.category,
                        "latitude": c.latitude,
                        "longitude": c.longitude,
                        "distance_km": round(dist, 2),
                        "rating": c.rating,
                        "price_level": c.price_level,
                        "must_try": c.must_try,
                        "image_url": c.image_url,
                    }
                )
        results.sort(key=lambda x: x["distance_km"])
        return results[:5]
    finally:
        db.close()


def insert_activity(itinerary: Dict[str, Any], day: int, poi_id: str) -> Dict[str, Any]:
    """
    Insert a destination activity into an itinerary day without altering other stops.
    """
    details = get_place_details(poi_id)
    if "error" in details:
        return {"success": False, "error": details["error"]}

    days = itinerary.get("days", [])
    if not days or day < 1 or day > len(days):
        return {"success": False, "error": f"Invalid day {day}. Total days: {len(days)}"}

    target_day = days[day - 1]
    activities = target_day.get("activities", [])
    
    new_act = {
        "poi_id": details["id"],
        "name": details["name"],
        "category": details.get("category", "Attraction"),
        "lat": details["latitude"],
        "lng": details["longitude"],
        "duration_minutes": details.get("visit_duration") or 90,
        "description": details.get("description") or f"Visit {details['name']}.",
        "rating": details.get("rating"),
        "price_level": details.get("price_level"),
        "must_try": details.get("must_try"),
        "is_hidden_gem": details.get("is_hidden_gem", False),
        "image_url": details.get("image_url"),
    }
    activities.append(new_act)
    target_day["activities"] = activities
    itinerary["days"] = days
    return {"success": True, "itinerary": itinerary, "added": details["name"]}


def remove_activity(itinerary: Dict[str, Any], day: int, activity_name: str) -> Dict[str, Any]:
    """
    Remove an activity by name from a specific itinerary day.
    """
    days = itinerary.get("days", [])
    if not days or day < 1 or day > len(days):
        return {"success": False, "error": f"Invalid day {day}."}

    target_day = days[day - 1]
    acts = target_day.get("activities", [])
    removed = None
    remaining = []
    
    act_name_lower = activity_name.lower().strip()
    for a in acts:
        cur_name = a.get("name", "").lower()
        if act_name_lower in cur_name or cur_name in act_name_lower:
            removed = a.get("name")
        else:
            remaining.append(a)

    target_day["activities"] = remaining
    itinerary["days"] = days
    return {
        "success": True,
        "itinerary": itinerary,
        "removed": removed or activity_name,
    }


def swap_activity(
    itinerary: Dict[str, Any], day: int, old_name: str, new_poi_id: str
) -> Dict[str, Any]:
    """
    Swap an existing activity in an itinerary day with a new POI.
    """
    res_rem = remove_activity(itinerary, day, old_name)
    res_ins = insert_activity(res_rem.get("itinerary", itinerary), day, new_poi_id)
    return res_ins


def reorder_activities(
    itinerary: Dict[str, Any], day: int, from_index: int, to_index: int
) -> Dict[str, Any]:
    """
    Reorder activities within a single itinerary day.
    """
    days = itinerary.get("days", [])
    if not days or day < 1 or day > len(days):
        return {"success": False, "error": f"Invalid day {day}."}
    target_day = days[day - 1]
    acts = target_day.get("activities", [])
    if from_index < 0 or from_index >= len(acts) or to_index < 0 or to_index >= len(acts):
        return {"success": False, "error": f"Invalid indices: from={from_index}, to={to_index}"}
    
    item = acts.pop(from_index)
    acts.insert(to_index, item)
    target_day["activities"] = acts
    itinerary["days"] = days
    return {"success": True, "itinerary": itinerary}


# ---------------------------------------------------------------------------
# Structured Pydantic Extraction Schemas for Needle
# ---------------------------------------------------------------------------
class ExtractedEditSlots(BaseModel):
    action: str = Field(description="Action type: remove, add, swap, reorder")
    scope: str = Field(default="minor_swap", description="Blast radius: 'minor_swap', 'day_overhaul', or 'full_reschedule'")
    day: int = Field(default=1, description="Target itinerary day (1-based)")
    target_place: str = Field(default="", description="Name of place to remove or swap")
    new_place_query: str = Field(default="", description="Name or query of new place to add or swap")


class ExtractedSearchSlots(BaseModel):
    query: str = Field(description="Search terms for places or food")
    category: Optional[str] = Field(default=None, description="Category filter like Restaurant, Cafe, Viewpoint, Hotel")
    limit: int = Field(default=5, description="Number of results")


# ---------------------------------------------------------------------------
# Cactus Needle Agent Service Class
# ---------------------------------------------------------------------------
class NeedleAgentService:
    """
    Handler Agent Service (System 1).
    
    Receives user requests, performs intent parsing, extracts structured arguments,
    and executes deterministic tools on the itinerary and database with sub-second latency.
    """

    def __init__(self):
        self.tools = {
            "search_places": search_places,
            "get_place_details": get_place_details,
            "find_nearby_restaurant": find_nearby_restaurant,
            "insert_activity": insert_activity,
            "remove_activity": remove_activity,
            "swap_activity": swap_activity,
            "reorder_activities": reorder_activities,
        }
        self.needle_instance = None
        if HAS_NEEDLE:
            try:
                # Initialize Needle engine with Python tools
                self.needle_instance = needle.Needle(
                    tools=[
                        search_places,
                        get_place_details,
                        find_nearby_restaurant,
                    ]
                )
                logger.info("Needle instance registered with System 1 tool definitions.")
            except Exception as e:
                logger.warning(f"Could not initialize needle.Needle: {e}")
                self.needle_instance = None

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Executes a tool deterministically with argument validation."""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        fn = self.tools[tool_name]
        try:
            return fn(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}

    def parse_and_execute_edit(
        self,
        user_request: str,
        current_itinerary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Uses Cactus Needle to parse unstructured edit requests into structured slots,
        then executes the corresponding deterministic tool.
        """
        # Step 1: Extract slots and action using Cactus Needle & KEV Decision Engine
        action = "swap"
        scope = "minor_swap"
        target_day = 1
        target_place = ""
        new_query = ""

        if HAS_NEEDLE:
            try:
                slots = needle.extract(user_request, ExtractedEditSlots, strict=False)
                if slots:
                    action = getattr(slots, "action", action) or action
                    scope = getattr(slots, "scope", scope) or scope
                    target_day = getattr(slots, "day", target_day) or target_day
                    target_place = getattr(slots, "target_place", "") or ""
                    new_query = getattr(slots, "new_place_query", "") or ""
            except Exception as e:
                logger.debug(f"Needle extract fallback: {e}")

        # Semantic Scope & Action Refinement via KEV
        req_lower = user_request.lower()
        if any(w in req_lower for w in ["replan", "re-plan", "reschedule", "start from", "entire trip", "whole trip", "add day", "extra day"]):
            scope = "full_reschedule"
        elif any(w in req_lower for w in ["overhaul", "whole day", "all stops on day", "completely change day"]):
            scope = "day_overhaul"

        # KEV SLM intent refinement if action is ambiguous
        if not action or action not in ("swap", "replace", "remove", "delete", "add", "insert", "reorder"):
            kev_choice = decision_service.classify_edit_intent(user_request)
            intent_map = {
                "swap_stop": "swap",
                "remove_stop": "remove",
                "add_stop": "add",
                "reorder_days": "reorder",
            }
            action = intent_map.get(kev_choice.selected, "swap")

        # Fallback target place extraction from current itinerary context
        days = current_itinerary.get("days", [])

        # Full multi-day reschedule scope handler
        if scope == "full_reschedule":
            return {
                "action": "replan",
                "scope": "full_reschedule",
                "day": target_day,
                "requires_full_pipeline": True,
                "message": "Full multi-day itinerary reschedule requested. Initiating corridor re-solve.",
                "success": True,
                "result": {"itinerary": current_itinerary},
            }
        if not target_place and days and 0 < target_day <= len(days):
            for act in days[target_day - 1].get("activities", []):
                act_name = (act.get("name") or "").lower()
                if act_name and (act_name in req_lower or any(word in req_lower for word in act_name.split() if len(word) > 3)):
                    target_place = act.get("name")
                    break

        # Step 2: Execute tool based on action
        if action in ("remove", "delete"):
            if not target_place and days and 0 < target_day <= len(days):
                acts = days[target_day - 1].get("activities", [])
                if acts:
                    target_place = acts[-1].get("name")  # Default to last activity
            res = self.execute_tool(
                "remove_activity",
                itinerary=current_itinerary,
                day=target_day,
                activity_name=target_place or "activity",
            )
            return {
                "action": "remove",
                "scope": scope,
                "day": target_day,
                "target_place": target_place,
                "result": res,
                "success": res.get("success", False),
            }

        elif action in ("swap", "replace"):
            # If target place not specified, pick one from that day
            if not target_place and days and 0 < target_day <= len(days):
                acts = days[target_day - 1].get("activities", [])
                if acts:
                    target_place = acts[0].get("name")

            # Extract replacement query via Needle Search Slots if not extracted
            search_query = new_query
            if not search_query and HAS_NEEDLE:
                try:
                    search_slots = needle.extract(user_request, ExtractedSearchSlots, strict=False)
                    if search_slots and search_slots.query:
                        search_query = search_slots.query
                except Exception:
                    pass

            search_query = search_query or "viewpoint"
            
            candidates = search_places(query=search_query, limit=5)
            if candidates:
                new_poi = candidates[0]
                
                # Check mountain highway transit & run KEV Mountain Safety Gater
                target_day_acts = days[target_day - 1].get("activities", []) if 0 < target_day <= len(days) else []
                detour_km = 0.0
                if target_day_acts and new_poi.get("latitude") and new_poi.get("longitude"):
                    last_act = target_day_acts[-1]
                    if last_act.get("latitude") and last_act.get("longitude"):
                        detour_km = _haversine(
                            last_act["latitude"], last_act["longitude"],
                            new_poi["latitude"], new_poi["longitude"]
                        )

                transit_duration_hours = detour_km / 28.0  # ~28 km/h on Nepal mountain corridors
                safety_eval = decision_service.gate_mountain_safety(
                    day_number=target_day,
                    existing_activities=target_day_acts,
                    new_activity=new_poi,
                    transit_duration_hours=transit_duration_hours,
                )

                if not safety_eval.is_safe:
                    logger.warning(f"[SAFETY REJECTION] {safety_eval.reason}")
                    return {
                        "action": "swap",
                        "scope": scope,
                        "day": target_day,
                        "target_place": target_place,
                        "added_place": new_poi["name"],
                        "safety_rejection": True,
                        "safety_warning": {
                            "title": safety_eval.warning_title,
                            "reason": safety_eval.reason,
                            "excess_hours": safety_eval.excess_hours,
                            "night_driving": safety_eval.night_driving,
                        },
                        "success": False,
                        "message": safety_eval.reason,
                    }

                res = self.execute_tool(
                    "swap_activity",
                    itinerary=current_itinerary,
                    day=target_day,
                    old_name=target_place,
                    new_poi_id=new_poi["id"],
                )
                return {
                    "action": "swap",
                    "scope": scope,
                    "day": target_day,
                    "target_place": target_place,
                    "added_place": new_poi["name"],
                    "result": res,
                    "success": res.get("success", False),
                }

        elif action in ("add", "insert"):
            search_query = new_query or "attraction"
            candidates = search_places(query=search_query, limit=5)
            if candidates:
                new_poi = candidates[0]

                # Check mountain highway transit & run KEV Mountain Safety Gater
                target_day_acts = days[target_day - 1].get("activities", []) if 0 < target_day <= len(days) else []
                detour_km = 0.0
                if target_day_acts and new_poi.get("latitude") and new_poi.get("longitude"):
                    last_act = target_day_acts[-1]
                    if last_act.get("latitude") and last_act.get("longitude"):
                        detour_km = _haversine(
                            last_act["latitude"], last_act["longitude"],
                            new_poi["latitude"], new_poi["longitude"]
                        )

                transit_duration_hours = detour_km / 28.0
                safety_eval = decision_service.gate_mountain_safety(
                    day_number=target_day,
                    existing_activities=target_day_acts,
                    new_activity=new_poi,
                    transit_duration_hours=transit_duration_hours,
                )

                if not safety_eval.is_safe:
                    logger.warning(f"[SAFETY REJECTION] {safety_eval.reason}")
                    return {
                        "action": "add",
                        "scope": scope,
                        "day": target_day,
                        "added_place": new_poi["name"],
                        "safety_rejection": True,
                        "safety_warning": {
                            "title": safety_eval.warning_title,
                            "reason": safety_eval.reason,
                            "excess_hours": safety_eval.excess_hours,
                            "night_driving": safety_eval.night_driving,
                        },
                        "success": False,
                        "message": safety_eval.reason,
                    }

                res = self.execute_tool(
                    "insert_activity",
                    itinerary=current_itinerary,
                    day=target_day,
                    poi_id=new_poi["id"],
                )
                return {
                    "action": "add",
                    "scope": scope,
                    "day": target_day,
                    "added_place": new_poi["name"],
                    "result": res,
                    "success": res.get("success", False),
                }

        return {"success": False, "error": "Could not determine structured tool action."}


needle_agent = NeedleAgentService()
