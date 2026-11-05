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
                if category.lower() in ("hidden_gems", "hidden_gem", "gem"):
                    query = query.filter(Place.is_hidden_gem.is_(True))
                else:
                    query = query.filter(Place.category == category)
            
            # Prioritize places with high popularity and ratings
            query = query.order_by(Place.popularity.desc().nullslast(), Place.rating.desc().nullslast())
            
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
        """Search places by query string, prioritizing popular and verified places."""
        with SessionLocal() as db:
            search_pattern = f"%{query}%"
            base = db.query(Place).filter(
                Place.name.ilike(search_pattern) | Place.category.ilike(search_pattern)
            )
            base = base.order_by(Place.popularity.desc().nullslast(), Place.rating.desc().nullslast())
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
        """Find places near a location using PostGIS (on PostgreSQL) or bounding box + Haversine (on SQLite)."""
        if not self._valid_coords(lat, lng):
            raise ValueError("Invalid coordinates")
        
        with SessionLocal() as db:
            dialect_name = db.bind.dialect.name if db.bind else "sqlite"

            if dialect_name == "sqlite":
                # SQLite fallback: bounding box filter + Python Haversine calculation
                lat_delta = radius / 111.0
                cos_lat = math.cos(math.radians(lat))
                lon_delta = radius / (111.0 * cos_lat) if abs(cos_lat) > 1e-6 else radius / 111.0
                min_lat = lat - lat_delta
                max_lat = lat + lat_delta
                min_lon = lng - lon_delta
                max_lon = lng + lon_delta

                query = db.query(Place).filter(
                    (
                        (Place.bbox_max_lat >= min_lat) &
                        (Place.bbox_min_lat <= max_lat) &
                        (Place.bbox_max_lon >= min_lon) &
                        (Place.bbox_min_lon <= max_lon)
                    ) | (
                        Place.bbox_min_lat.is_(None)
                    )
                )
                if category:
                    if category.lower() in ("hidden_gems", "hidden_gem", "gem"):
                        query = query.filter(Place.is_hidden_gem.is_(True))
                    else:
                        query = query.filter(Place.category == category)

                places_with_distance = []
                for place in query.all():
                    place_dict = place.to_dict()
                    lat_p = place_dict.get("latitude")
                    lng_p = place_dict.get("longitude")
                    if lat_p is not None and lng_p is not None:
                        dist = self._haversine(lat, lng, lat_p, lng_p)
                        if dist <= radius:
                            place_dict["distance_km"] = round(dist, 2)
                            places_with_distance.append(place_dict)

                places_with_distance.sort(key=lambda x: x["distance_km"])
                total = len(places_with_distance)
                return {
                    "places": places_with_distance[offset:offset + limit],
                    "count": min(limit, max(0, total - offset)),
                    "total_count": total,
                    "offset": offset,
                    "limit": limit
                }
            else:
                # PostgreSQL with PostGIS
                query = db.query(Place).filter(
                    text(
                        "ST_DWithin("
                        "  ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,"
                        "  centroid::geography,"
                        "  :radius_meters"
                        ")"
                    ).params(lng=lng, lat=lat, radius_meters=radius * 1000)
                )
                if category:
                    if category.lower() in ("hidden_gems", "hidden_gem", "gem"):
                        query = query.filter(Place.is_hidden_gem.is_(True))
                    else:
                        query = query.filter(Place.category == category)
                
                places_with_distance = []
                for place in query.all():
                    place_dict = place.to_dict()
                    lat_p = place_dict.get("latitude")
                    lng_p = place_dict.get("longitude")
                    if lat_p is not None and lng_p is not None:
                        dist = self._haversine(lat, lng, lat_p, lng_p)
                        place_dict["distance_km"] = round(dist, 2)
                        places_with_distance.append(place_dict)
                
                places_with_distance.sort(key=lambda x: x["distance_km"])
                total = len(places_with_distance)
                return {
                    "places": places_with_distance[offset:offset + limit],
                    "count": min(limit, max(0, total - offset)),
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
        """Get recommendations along a route corridor using PostGIS (on PostgreSQL) or corridor bounding box (on SQLite)."""
        if not (self._valid_coords(origin_lat, origin_lng) and self._valid_coords(dest_lat, dest_lng)):
            raise ValueError("Invalid coordinates")
        
        with SessionLocal() as db:
            dialect_name = db.bind.dialect.name if db.bind else "sqlite"
            if dialect_name == "sqlite":
                lat_delta = corridor_km / 111.0
                min_lat = min(origin_lat, dest_lat) - lat_delta
                max_lat = max(origin_lat, dest_lat) + lat_delta
                cos_lat = math.cos(math.radians((origin_lat + dest_lat) / 2))
                lon_delta = corridor_km / (111.0 * cos_lat) if abs(cos_lat) > 1e-6 else corridor_km / 111.0
                min_lon = min(origin_lng, dest_lng) - lon_delta
                max_lon = max(origin_lng, dest_lng) + lon_delta

                query = db.query(Place).filter(
                    (
                        (Place.bbox_max_lat >= min_lat) &
                        (Place.bbox_min_lat <= max_lat) &
                        (Place.bbox_max_lon >= min_lon) &
                        (Place.bbox_min_lon <= max_lon)
                    ) | (
                        Place.bbox_min_lat.is_(None)
                    )
                )
            else:
                line_wkt = f"LINESTRING({origin_lng} {origin_lat}, {dest_lng} {dest_lat})"
                query = db.query(Place).filter(
                    text(
                        "ST_DWithin("
                        "  ST_GeomFromText(:line_wkt, 4326)::geography,"
                        "  centroid::geography,"
                        "  :corridor_meters"
                        ")"
                    ).params(line_wkt=line_wkt, corridor_meters=corridor_km * 1000)
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
            candidates = query.limit(limit * 4 if dialect_name == "sqlite" else limit).all()
            for place in candidates:
                place_dict = place.to_dict()
                lat_p = place_dict.get("latitude")
                lng_p = place_dict.get("longitude")
                if lat_p and lng_p:
                    dist = self._point_to_line_distance(
                        lat_p, lng_p,
                        origin_lat, origin_lng, dest_lat, dest_lng
                    )
                    if dialect_name == "sqlite" and dist > corridor_km:
                        continue
                    place_dict["distance_to_route_km"] = round(dist, 2)
                    results.append(place_dict)
            
            results.sort(key=lambda x: x["distance_to_route_km"])
            paged = results[:limit]
            return {"places": paged, "count": len(paged), "total_count": len(paged)}
    
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

    def geocode_location(self, query: str) -> Dict[str, Any]:
        """
        Geocode any Nepal location name into coordinates.
        1. Checks curated high-confidence Nepal destination dictionary.
        2. Queries database places table.
        3. Queries OpenStreetMap Nominatim with np country code fallback.
        """
        q = (query or "").strip()
        if not q:
            return {"name": "Kathmandu", "latitude": 27.7172, "longitude": 85.3240, "source": "default"}

        q_lower = q.lower()
        
        # Curated Nepal Registry for instant, zero-latency precision
        CURATED_REGISTRY = {
            "kathmandu": (27.7172, 85.3240, "Kathmandu Valley"),
            "pokhara": (28.2096, 83.9856, "Pokhara & Annapurna Gateway"),
            "chitwan": (27.5341, 84.4525, "Chitwan National Park"),
            "sauraha": (27.5816, 84.4947, "Sauraha, Chitwan"),
            "bandipur": (27.9333, 84.4167, "Bandipur Heritage Village"),
            "nagarkot": (27.7174, 85.5204, "Nagarkot Sunrise Ridge"),
            "dhulikhel": (27.6186, 85.5531, "Dhulikhel Himalayan Vista"),
            "lumbini": (27.4842, 83.2759, "Lumbini (Birthplace of Buddha)"),
            "janakpur": (26.7288, 85.9244, "Janakpur (Janaki Mandir)"),
            "mustang": (28.7844, 83.7226, "Mustang & Kali Gandaki Corridor"),
            "jomsom": (28.7844, 83.7226, "Jomsom, Lower Mustang"),
            "muktinath": (28.8167, 83.8667, "Muktinath Sacred Valley"),
            "lo manthang": (29.1825, 83.9567, "Lo Manthang, Upper Mustang"),
            "marpha": (28.7523, 83.6845, "Marpha Apple Valley"),
            "ghandruk": (28.3756, 83.8073, "Ghandruk Gurung Village"),
            "ghorepani": (28.4005, 83.7020, "Ghorepani & Poon Hill"),
            "poon hill": (28.3975, 83.6933, "Poon Hill Viewpoint"),
            "sarangkot": (28.2437, 83.9575, "Sarangkot Sunrise Point"),
            "namche": (27.8050, 86.7140, "Namche Bazaar (Sherpa Capital)"),
            "namche bazaar": (27.8050, 86.7140, "Namche Bazaar"),
            "lukla": (27.6869, 86.7290, "Lukla (Tenzing-Hillary)"),
            "tengboche": (27.8358, 86.7644, "Tengboche Monastery"),
            "everest base camp": (28.0026, 86.8528, "Everest Base Camp (Khumbu)"),
            "ebc": (28.0026, 86.8528, "Everest Base Camp"),
            "langtang": (28.2150, 85.5030, "Langtang Valley"),
            "kyanjin gompa": (28.2133, 85.5678, "Kyanjin Gompa, Langtang"),
            "rara": (29.5375, 82.0833, "Rara Lake (Mugu)"),
            "rara lake": (29.5375, 82.0833, "Rara Lake"),
            "shey phoksundo": (29.2100, 82.9500, "Shey Phoksundo Lake (Dolpa)"),
            "ilam": (26.9089, 87.9263, "Ilam Tea Gardens"),
            "tansen": (27.8673, 83.5463, "Tansen (Palpa)"),
            "palpa": (27.8673, 83.5463, "Tansen (Palpa)"),
            "gorkha": (28.0055, 84.6319, "Gorkha Historical Durbar"),
            "dharan": (26.8124, 87.2835, "Dharan Foothills"),
            "biratnagar": (26.4525, 87.2718, "Biratnagar"),
            "butwal": (27.7006, 83.4484, "Butwal"),
            "bardia": (28.5833, 81.3333, "Bardia National Park"),
            "dhangadhi": (28.6833, 80.6000, "Dhangadhi"),
            "manang": (28.6667, 84.0167, "Manang High Valley"),
            "australian camp": (28.3039, 83.8447, "Australian Camp Viewpoint"),
            "swayambhunath": (27.7149, 85.2904, "Swayambhunath Monkey Temple"),
            "boudhanath": (27.7215, 85.3620, "Boudhanath Great Stupa"),
            "pashupatinath": (27.7105, 85.3488, "Pashupatinath Temple"),
            "patan durbar": (27.6744, 85.3247, "Patan Durbar Square"),
            "bhaktapur durbar": (27.6710, 85.4298, "Bhaktapur Durbar Square"),
            "annapurna base camp": (28.5300, 83.8780, "Annapurna Base Camp (ABC Sanctuary)"),
            "abc": (28.5300, 83.8780, "Annapurna Base Camp Sanctuary"),
            "gosainkunda": (28.0833, 85.4167, "Gosainkunda Sacred High Lakes"),
            "helambu": (28.0333, 85.5500, "Helambu Sherpa Trail"),
            "kalinchowk": (27.7478, 86.0267, "Kalinchowk Bhagwati Shrine (Kuri)"),
            "balthali": (27.5500, 85.5333, "Balthali Eco Foothills"),
            "chandragiri": (27.6711, 85.2289, "Chandragiri Cable Car Peak"),
            "namo buddha": (27.5670, 85.5830, "Namo Buddha Thrangu Tashi Monastery"),
            "khaptad": (29.3667, 81.1667, "Khaptad National Park Alpine Moors"),
            "dhorpatan": (28.5167, 83.0500, "Dhorpatan Hunting Reserve"),
            "sinja valley": (29.3167, 81.9833, "Sinja Valley Khas Kingdom"),
            "suklaphanta": (28.8500, 80.2500, "Suklaphanta Grasslands Sanctuary"),
            "kanyam": (26.8500, 88.0500, "Kanyam Tea Rolling Hills"),
            "panch pokhari": (28.0400, 85.7100, "Panch Pokhari Five Sacred Tarns"),
            "kanchenjunga": (27.7025, 88.1475, "Kangchenjunga Wilderness Base"),
            "makalu": (27.8897, 87.0886, "Makalu Barun Valley & High Passes")
        }

        for key, (lat, lng, label) in CURATED_REGISTRY.items():
            if key in q_lower or q_lower in key:
                return {"name": label, "latitude": lat, "longitude": lng, "source": "curated_registry"}

        # Check DB
        with SessionLocal() as db:
            match = db.query(Place).filter(Place.name.ilike(f"%{q}%")).first()
            if match and match.latitude and match.longitude:
                return {
                    "name": match.name,
                    "latitude": match.latitude,
                    "longitude": match.longitude,
                    "category": match.category,
                    "source": "database"
                }

        # Fallback to OSM Nominatim
        import urllib.request
        import urllib.parse
        import json
        try:
            nom_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&countrycodes=np&format=json&limit=1"
            req = urllib.request.Request(nom_url, headers={"User-Agent": "YatraSathiApp/1.0"})
            with urllib.request.urlopen(req, timeout=5) as res:
                items = json.loads(res.read().decode())
                if items:
                    top = items[0]
                    return {
                        "name": top.get("display_name", q),
                        "latitude": float(top["lat"]),
                        "longitude": float(top["lon"]),
                        "source": "nominatim"
                    }
        except Exception:
            pass

        return {"name": q, "latitude": 27.7172, "longitude": 85.3240, "source": "default_fallback"}


# Global place service instance
place_service = PlaceService()
