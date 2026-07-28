"""
Place service for managing destination data.
"""
import math
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, text, cast
from geoalchemy2 import Geometry
from backend.app.db.database import SessionLocal
from backend.app.models.place import Place


# Reusable cast expression — avoids repeating cast() everywhere
def _centroid_geom(col):
    """Cast a Text centroid column to PostGIS geometry for use in spatial functions."""
    return cast(col, Geometry("POINT", srid=4326))


class PlaceService:
    """Service for place data operations using PostgreSQL."""
    
    def __init__(self):
        self.destinations: List[Dict[str, Any]] = []
    
    def reload_destinations(self) -> int:
        """Reload destinations from database."""
        with SessionLocal() as db:
            count = db.query(Place).count()
            return count
    
    def get_all_places(
        self,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get all places with optional category filter."""
        with SessionLocal() as db:
            query = db.query(Place).filter(Place.name.isnot(None)).filter(func.trim(Place.name) != "")
            if category:
                query = query.filter(Place.category == category)
            
            total = query.count()
            places = query.offset(offset).limit(limit).all()
            return {
                "places": [p.to_dict() for p in places],
                "count": len(places),
                "total_count": total,
                "offset": offset,
                "limit": limit
            }
    
    def search_places(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Search places by query string."""
        with SessionLocal() as db:
            search_pattern = f"%{query}%"
            base = db.query(Place).filter(
                Place.name.ilike(search_pattern) | Place.category.ilike(search_pattern)
            )
            total = base.count()
            places = base.offset(offset).limit(limit).all()
            return {
                "places": [p.to_dict() for p in places],
                "count": len(places),
                "total_count": total,
                "offset": offset,
                "limit": limit
            }
    
    def get_nearby_places(
        self,
        lat: float,
        lng: float,
        radius: float = 10.0,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Find places near a location using PostGIS."""
        if not self._valid_coords(lat, lng):
            raise ValueError("Invalid coordinates")
        
        with SessionLocal() as db:
            # Cast centroid text → geometry; use ::geography for distance in metres
            cgeom = _centroid_geom(Place.centroid)
            point_geom = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)

            query = db.query(Place).filter(
                func.ST_DWithin(
                    func.ST_Transform(cgeom, 4326).cast(Geometry),
                    func.ST_Transform(point_geom, 4326).cast(Geometry),
                    radius * 1000,          # metres — works when cast to geography below
                )
            )
            # Simpler alternative that's well-tested in PostgreSQL/PostGIS:
            # Use raw SQL fragment for DWithin geography (avoids ORM cast ambiguity)
            query = db.query(Place).filter(
                text(
                    f"ST_DWithin("
                    f"  ST_GeomFromText('POINT({lng} {lat})', 4326)::geography,"
                    f"  centroid::geography,"
                    f"  {radius * 1000}"
                    f")"
                )
            )
            if category:
                query = query.filter(Place.category == category)
            
            places_with_distance = []
            for place in query.all():
                place_dict = place.to_dict()
                lat_p = place_dict.get("latitude")
                lng_p = place_dict.get("longitude")
                if lat_p and lng_p:
                    dist = self._haversine(lat, lng, lat_p, lng_p)
                    place_dict["distance_km"] = round(dist, 2)
                    places_with_distance.append(place_dict)
            
            places_with_distance.sort(key=lambda x: x["distance_km"])
            total = len(places_with_distance)
            return {
                "places": places_with_distance[offset:offset + limit],
                "count": min(limit, total - offset),
                "total_count": total,
                "offset": offset,
                "limit": limit
            }
    
    def get_place(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific place by ID."""
        with SessionLocal() as db:
            try:
                from uuid import UUID
                place = db.query(Place).filter(Place.id == UUID(place_id)).first()
                return place.to_dict() if place else None
            except ValueError:
                return None
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories with counts."""
        with SessionLocal() as db:
            categories = db.query(
                Place.category,
                func.count(Place.id).label('count')
            ).group_by(Place.category).all()
            return [{"name": cat, "count": count} for cat, count in categories if cat]
    
    def get_recommendations(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        corridor_km: float = 30.0,
        category: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get recommendations along a route corridor using PostGIS."""
        if not (self._valid_coords(origin_lat, origin_lng) and self._valid_coords(dest_lat, dest_lng)):
            raise ValueError("Invalid coordinates")
        
        with SessionLocal() as db:
            line_wkt = f"LINESTRING({origin_lng} {origin_lat}, {dest_lng} {dest_lat})"
            query = db.query(Place).filter(
                text(
                    f"ST_DWithin("
                    f"  ST_GeomFromText('{line_wkt}', 4326)::geography,"
                    f"  centroid::geography,"
                    f"  {corridor_km * 1000}"
                    f")"
                )
            )
            if category:
                query = query.filter(Place.category == category)
            query = (
                query
                .filter(Place.name.isnot(None))
                .filter(func.trim(Place.name) != "")
                .filter(~Place.category.ilike("%tour operator%"))
                .filter(~Place.category.ilike("%tour agency%"))
                .filter(~Place.category.ilike("%tourist information%"))
            )
            
            results = []
            for place in query.limit(limit).all():
                place_dict = place.to_dict()
                lat_p = place_dict.get("latitude")
                lng_p = place_dict.get("longitude")
                if lat_p and lng_p:
                    dist = self._point_to_line_distance(
                        lat_p, lng_p,
                        origin_lat, origin_lng, dest_lat, dest_lng
                    )
                    place_dict["distance_to_route_km"] = round(dist, 2)
                    results.append(place_dict)
            
            results.sort(key=lambda x: x["distance_to_route_km"])
            return {"places": results, "count": len(results), "total_count": len(results)}
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        return R * 2 * math.asin(math.sqrt(a))
    
    @staticmethod
    def _point_to_line_distance(px, py, ax, ay, bx, by) -> float:
        ab_dist = PlaceService._haversine(ax, ay, bx, by)
        if ab_dist < 0.01:
            return PlaceService._haversine(px, py, ax, ay)
        lat_scale = math.cos(math.radians((ay + by) / 2))
        dx = (bx - ax) * lat_scale
        dy = by - ay
        t = max(0, min(1, ((px - ax) * lat_scale * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-10)))
        proj_x = ax + t * (bx - ax)
        proj_y = ay + t * (by - ay)
        return PlaceService._haversine(px, py, proj_x, proj_y)
    
    @staticmethod
    def _valid_coords(lat: float, lng: float) -> bool:
        return -90 <= lat <= 90 and -180 <= lng <= 180
    
    def get_destinations_summary(self) -> str:
        with SessionLocal() as db:
            total = db.query(Place).count()
            if total == 0:
                return "No destinations loaded."
            cats = db.query(Place.category, func.count(Place.id)).group_by(Place.category).all()
            lines = [f"Total destinations: {total}"]
            for cat, cnt in sorted(cats, key=lambda x: x[1], reverse=True)[:10]:
                lines.append(f"{cat}: {cnt} places")
            return "\n".join(lines)
    
    def find_place_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as db:
            place = db.query(Place).filter(Place.name == name).first()
            if not place:
                place = db.query(Place).filter(Place.name.ilike(f"%{name}%")).first()
            return place.to_dict() if place else None


# Global place service instance
place_service = PlaceService()
