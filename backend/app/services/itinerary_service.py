"""
Itinerary Generation Service
Uses LLM to generate coherent travel itineraries from POI candidates
"""
from typing import Dict, Any, List, Optional
from backend.app.config.settings import settings
import httpx
import json


class ItineraryService:
    """Service for generating coherent travel itineraries using LLM."""
    
    def __init__(self):
        self.llm_provider = settings.LLM_PROVIDER
        self.llm_model = settings.LLM_MODEL
        self.groq_api_key = settings.GROQ_API_KEY
        self.nvidia_nim_api_key = settings.NVIDIA_NIM_API_KEY
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
    
    async def generate_itinerary(
        self,
        pois: List[Dict[str, Any]],
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        num_days: int = 3,
        user_preferences: Optional[List[str]] = None,
        travel_style: str = "balanced",
        budget: str = "medium",
        structured_representation: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a coherent itinerary from POI candidates using LLM.
        
        Args:
            pois: List of POI candidates along the route
            origin_lat: Origin latitude
            origin_lng: Origin longitude
            dest_lat: Destination latitude
            dest_lng: Destination longitude
            num_days: Number of days for the trip
            user_preferences: User preference tags
            travel_style: Travel style (relaxed, balanced, packed)
            budget: Budget level (low, medium, high)
            structured_representation: Pre-planned structured candidate itinerary
        
        Returns:
            Generated itinerary with day-by-day breakdown
        """
        # Prepare POI context for LLM
        poi_context = self._prepare_poi_context(pois)
        
        # Create prompt for LLM
        prompt = self._create_itinerary_prompt(
            poi_context,
            origin_lat, origin_lng,
            dest_lat, dest_lng,
            num_days,
            user_preferences,
            travel_style,
            budget,
            structured_representation
        )
        
        # Call LLM
        itinerary_data = await self._call_llm(prompt)
        
        # Parse and structure the response
        structured_itinerary = self._parse_itinerary_response(itinerary_data, pois)
        
        return {
            "itinerary": structured_itinerary,
            "num_days": num_days,
            "total_pois": len(pois),
            "selected_pois": len(structured_itinerary.get("days", [])),
            "user_preferences": user_preferences,
            "travel_style": travel_style,
            "budget": budget
        }
    
    def _prepare_poi_context(self, pois: List[Dict[str, Any]]) -> str:
        """
        Prepare POI information as structured context for LLM.

        Each place is represented as a human-readable sentence (embedding_text)
        plus key structured fields.  This gives the LLM real content to write
        descriptions from rather than just a list of generic tag labels.
        """
        # Sort by relevance score, fall back to embedding similarity
        pois = sorted(
            pois,
            key=lambda x: x.get("relevance_score", x.get("embedding_similarity", 0)),
            reverse=True,
        )

        categorized: dict[str, list] = {
            "accommodation": [],
            "restaurants": [],
            "attractions": [],
        }

        for poi in pois:
            name = (poi.get("name") or "").strip()
            if not name or len(name) <= 2 or any(p in name.lower() for p in ('unnamed', 'unknown', 'no name', 'noname', 'n/a', 'null')):
                continue
            category = (poi.get("category") or "").lower()
            if any(k in category for k in ("hotel", "guest house", "resort", "lodge",
                                            "hostel", "inn", "homestay")):
                categorized["accommodation"].append(poi)
            elif any(k in category for k in ("restaurant", "cafe", "food", "eatery", "dining")):
                categorized["restaurants"].append(poi)
            else:
                categorized["attractions"].append(poi)

        limits = {
            "accommodation": min(len(categorized["accommodation"]), 10),
            "restaurants":   min(len(categorized["restaurants"]),   15),
            "attractions":   min(len(categorized["attractions"]),   20),
        }

        context_data: dict[str, list] = {
            "accommodation": [],
            "restaurants": [],
            "attractions": [],
        }

        for cat_key in ("accommodation", "restaurants", "attractions"):
            for poi in categorized[cat_key][: limits[cat_key]]:
                # embedding_text is the rich human-readable sentence generated
                # during the ETL embedding stage — gives LLM real content.
                description = (
                    poi.get("embedding_text")
                    or poi.get("description")
                    or f"{poi.get('name', 'Unknown')} is a {poi.get('category', 'place')} in Nepal."
                )
                context_data[cat_key].append({
                    "id":           poi.get("id", ""),
                    "name":         poi.get("name", "Unknown"),
                    "category":     poi.get("category", "Unknown"),
                    "lat":          round(poi.get("latitude", 0) or 0, 5),
                    "lng":          round(poi.get("longitude", 0) or 0, 5),
                    "description":  description[:300],   # cap to keep prompt size reasonable
                    "similarity":   round(poi.get("embedding_similarity", 0), 3),
                    "popularity":   poi.get("popularity") or 0,
                    "has_wiki":     bool(poi.get("wikidata_id") or poi.get("wikipedia_url")),
                    "difficulty":   poi.get("difficulty") or "",
                    "duration":     poi.get("visit_duration") or "",
                    "near_dest":    poi.get("_in_dest_buffer", False),
                })

        import json
        total = sum(len(v) for v in context_data.values())
        context = f"Available POIs ({total} total, categorized):\n"
        context += json.dumps(context_data, indent=2)
        return context
    
    def _create_itinerary_prompt(
        self,
        poi_context: str,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        num_days: int,
        user_preferences: Optional[List[str]],
        travel_style: str,
        budget: str,
        structured_representation: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create the prompt for LLM itinerary generation with new role constraints."""
        
        # Use structured representation if available
        if structured_representation:
            context_section = f"""
STRUCTURED CANDIDATE PLAN:
{json.dumps(structured_representation, indent=2)}

This is a pre-planned candidate itinerary with specific places already selected.
Your role is to:
1. Explain the itinerary naturally and engagingly
2. Organize the selected activities into a readable schedule
3. Generate useful descriptions for each place
4. Explain why places fit the user's preferences
5. Handle minor sequencing adjustments when safe
6. Respect the supplied candidate set completely
"""
        else:
            context_section = f"""
{poi_context}
"""

        prompt = f"""You are an expert travel planner for Nepal. Your role is to ORGANIZE AND EXPLAIN a pre-planned itinerary, NOT to discover or invent places.

Route: From ({origin_lat}, {origin_lng}) to ({dest_lat}, {dest_lng})

{context_section}

User Preferences:
- Number of days: {num_days}
- Travel style: {travel_style} (relaxed = 2-3 activities/day, balanced = 3-5 activities/day, packed = 5-7 activities/day)
- Budget: {budget}
- Interests: {', '.join(user_preferences) if user_preferences else 'General sightseeing'}

CRITICAL CONSTRAINTS:
1. You may ONLY recommend places present in the supplied candidate data
2. Do NOT invent businesses, attractions, hotels, restaurants, or geographic facts
3. If a required category has insufficient candidates, state that the category has limited availability rather than fabricating recommendations
4. Do NOT violate route progression without explicitly explaining the reason
5. Do NOT schedule activities that are geographically or temporally impossible
6. Respect the meal plan and category availability information provided
7. Use the structured candidate slots as your foundation - organize them, don't replace them

YOUR RESPONSIBILITIES:
1. Explain the itinerary naturally and engagingly
2. Organize the selected activities into a readable daily schedule
3. Generate useful descriptions for each place based on its category and features
4. Explain why places fit the user's preferences (use similarity scores as guidance)
5. Handle minor timing adjustments when safe for geographic coherence
6. Respect the supplied candidate set completely - never add external places
7. If restaurant availability is limited, suggest alternatives like hotel breakfast or local food options

Return the itinerary in this JSON format:
{{
    "days": [
        {{
            "day": 1,
            "starting_location": "Location name",
            "overnight_accommodation": {{
                "poi_id": "POI ID",
                "poi_name": "Hotel name",
                "latitude": 27.7172,
                "longitude": 85.3240,
                "description": "Brief description of the accommodation"
            }},
            "activities": [
                {{
                    "poi_id": "POI ID",
                    "poi_name": "POI name",
                    "category": "POI category",
                    "latitude": 27.7172,
                    "longitude": 85.3240,
                    "start_time": "09:00",
                    "end_time": "11:00",
                    "duration_hours": 2,
                    "activity_type": "attraction/restaurant",
                    "description": "Engaging description of what to do and why it fits preferences",
                    "notes": "Any special tips or information"
                }}
            ],
            "total_distance_km": 50,
            "estimated_driving_time_hours": 2,
            "day_summary": "Brief overview of the day's theme"
        }}
    ],
    "summary": "Engaging overview of the entire itinerary experience",
    "total_distance_km": 200,
    "estimated_total_driving_time_hours": 8,
    "tips": ["Practical travel tips for this route"],
    "availability_notes": "Any notes about category limitations or alternatives"
}}

Ensure the response is valid JSON only, no additional text."""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API to generate itinerary."""
        if self.llm_provider == "groq":
            return await self._call_groq(prompt)
        elif self.llm_provider == "nvidia_nim":
            return await self._call_nvidia_nim(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
    
    async def _call_groq(self, prompt: str) -> str:
        """Call Groq API for LLM inference."""
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": "You are an expert travel planner specializing in Nepal tourism."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _call_nvidia_nim(self, prompt: str) -> str:
        """Call NVIDIA NIM API for LLM inference."""
        if not self.nvidia_nim_api_key:
            raise ValueError("NVIDIA_NIM_API_KEY not configured")
        
        url = f"https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.nvidia_nim_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": "You are an expert travel planner specializing in Nepal tourism."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _parse_itinerary_response(self, llm_response: str, pois: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse LLM response and match POIs to database entries."""
        try:
            itinerary_data = json.loads(llm_response)
            
            # Match POI names to actual POI data
            for day in itinerary_data.get("days", []):
                for activity in day.get("activities", []):
                    poi_name = activity.get("poi_name", "")
                    # Find matching POI from candidates
                    matching_poi = self._find_matching_poi(poi_name, pois)
                    if matching_poi:
                        activity["poi_id"] = matching_poi.get("id")
                        activity["latitude"] = matching_poi.get("latitude")
                        activity["longitude"] = matching_poi.get("longitude")
                        activity["category"] = matching_poi.get("category")
                    else:
                        # Keep LLM-provided coordinates if no match found
                        activity["poi_id"] = None
            
            return itinerary_data
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return {
                "days": [],
                "summary": "Error generating itinerary",
                "error": str(e)
            }
    
    def _find_matching_poi(self, name: str, pois: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find a POI by name with fuzzy matching."""
        name_lower = name.lower()
        
        # Exact match
        for poi in pois:
            if poi.get("name", "").lower() == name_lower:
                return poi
        
        # Partial match
        for poi in pois:
            if name_lower in poi.get("name", "").lower():
                return poi
        
        return None


# Global instance
itinerary_service = ItineraryService()
