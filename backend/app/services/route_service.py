"""
OSRM Route Service
Handles routing requests using OSRM (Open Source Routing Machine)
"""
import httpx
from typing import Dict, Any, List, Optional
from backend.app.config.settings import settings


class RouteService:
    """Service for OSRM routing operations."""
    
    def __init__(self):
        self.osrm_url = settings.OSRM_URL
        self._client = None
    
    @property
    def client(self):
        """Lazy initialization of HTTP client to avoid SSL issues at startup."""
        if self._client is None:
            import os
            # Remove SSL_CERT_FILE if it's causing issues
            if 'SSL_CERT_FILE' in os.environ:
                del os.environ['SSL_CERT_FILE']
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def get_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        profile: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get route between two points using OSRM.

        Args:
            origin_lat: Origin latitude
            origin_lng: Origin longitude
            dest_lat: Destination latitude
            dest_lng: Destination longitude
            profile: OSRM profile (driving, walking, cycling)

        Returns:
            Route data with geometry, distance, duration
        """
        if profile is None:
            profile = "driving"

        # Handle both base URL and full URL configurations
        base_url = self.osrm_url.rstrip('/')
        if base_url.endswith(f'/route/v1/{profile}'):
            # URL already includes the full path
            url = f"{base_url}/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        else:
            # URL is base, append the path
            url = f"{base_url}/route/v1/{profile}/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
        
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true"
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != "Ok":
                raise Exception(f"OSRM error: {data.get('message', 'Unknown error')}")
            
            route = data["routes"][0]
            
            return {
                "geometry": route["geometry"],
                "distance_km": route["distance"] / 1000,  # Convert meters to km
                "duration_minutes": route["duration"] / 60,  # Convert seconds to minutes
                "coordinates": route["geometry"]["coordinates"]
            }
        except Exception as e:
            print(f"OSRM routing error: {e}")
            raise
    
    async def get_route_buffer(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        buffer_km: float = 20
    ) -> List[List[float]]:
        """
        Get route geometry and create a buffer around it.
        
        Args:
            origin_lat: Origin latitude
            origin_lng: Origin longitude
            dest_lat: Destination latitude
            dest_lng: Destination longitude
            buffer_km: Buffer radius in kilometers
        
        Returns:
            List of coordinates representing the buffered route
        """
        route_data = await self.get_route(origin_lat, origin_lng, dest_lat, dest_lng)
        coordinates = route_data["coordinates"]
        
        # Convert coordinates to (lng, lat) tuples for shapely
        coords = [(coord[0], coord[1]) for coord in coordinates]
        
        # Create a simple buffer by expanding each point
        # For a proper buffer, we'd use shapely, but for now we'll do a simple expansion
        buffer_coords = []
        buffer_deg = buffer_km / 111.0  # Approximate km to degrees conversion
        
        for lng, lat in coords:
            # Add points around each coordinate to create a buffer
            for angle in range(0, 360, 45):
                import math
                rad = math.radians(angle)
                buffer_lng = lng + buffer_deg * math.cos(rad)
                buffer_lat = lat + buffer_deg * math.sin(rad)
                buffer_coords.append([buffer_lng, buffer_lat])
        
        return buffer_coords
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global instance
route_service = RouteService()
