"""
OSM tag → normalised Category mapping.

Single source of truth for what constitutes a "travel place" and
what canonical category/group it belongs to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Category:
    name:  str
    group: str


# ─────────────────────────────────────────────────────────────────────────────
# Mapping table  (osm_key, osm_value) → Category
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_MAPPING: Dict[Tuple[str, str], Category] = {
    # TOURISM
    ("tourism", "attraction"):   Category("Attraction",    "Tourism"),
    ("tourism", "viewpoint"):    Category("Viewpoint",     "Tourism"),
    ("tourism", "museum"):       Category("Museum",        "Tourism"),
    ("tourism", "gallery"):      Category("Gallery",       "Tourism"),
    ("tourism", "camp_site"):    Category("Campground",    "Tourism"),
    ("tourism", "caravan_site"): Category("Campground",    "Tourism"),
    ("tourism", "picnic_site"):  Category("Picnic Site",   "Tourism"),
    ("tourism", "theme_park"):   Category("Theme Park",    "Tourism"),
    ("tourism", "zoo"):          Category("Zoo",           "Tourism"),
    ("tourism", "aquarium"):     Category("Aquarium",      "Tourism"),
    ("tourism", "hotel"):        Category("Hotel",         "Accommodation"),
    ("tourism", "hostel"):       Category("Hostel",        "Accommodation"),
    ("tourism", "guest_house"):  Category("Guest House",   "Accommodation"),
    ("tourism", "motel"):        Category("Motel",         "Accommodation"),
    ("tourism", "apartment"):    Category("Apartment",     "Accommodation"),
    ("tourism", "chalet"):       Category("Chalet",        "Accommodation"),

    # NATURAL
    ("natural", "peak"):          Category("Mountain Peak", "Natural"),
    ("natural", "waterfall"):     Category("Waterfall",     "Natural"),
    ("natural", "cave_entrance"): Category("Cave",          "Natural"),
    ("natural", "beach"):         Category("Beach",         "Natural"),
    ("natural", "wood"):          Category("Forest",        "Natural"),
    ("natural", "spring"):        Category("Spring",        "Natural"),
    ("natural", "hot_spring"):    Category("Hot Spring",    "Natural"),
    ("natural", "glacier"):       Category("Glacier",       "Natural"),
    ("natural", "volcano"):       Category("Volcano",       "Natural"),
    ("natural", "tree"):          Category("Tree",          "Natural"),

    # WATER
    ("water", "lake"):       Category("Lake",       "Natural"),
    ("water", "river"):      Category("River",      "Natural"),
    ("water", "reservoir"):  Category("Reservoir",  "Natural"),
    ("water", "pond"):       Category("Pond",       "Natural"),

    # LEISURE
    ("leisure", "park"):           Category("Park",           "Leisure"),
    ("leisure", "garden"):         Category("Garden",         "Leisure"),
    ("leisure", "nature_reserve"): Category("Nature Reserve", "Leisure"),
    ("leisure", "playground"):     Category("Playground",     "Leisure"),

    # HISTORIC
    ("historic", "castle"):              Category("Castle",               "Historic"),
    ("historic", "fort"):               Category("Fort",                 "Historic"),
    ("historic", "ruins"):              Category("Ruins",                "Historic"),
    ("historic", "monument"):           Category("Monument",             "Historic"),
    ("historic", "memorial"):           Category("Memorial",             "Historic"),
    ("historic", "archaeological_site"):Category("Archaeological Site",  "Historic"),

    # FOOD
    ("amenity", "restaurant"):  Category("Restaurant", "Food"),
    ("amenity", "cafe"):        Category("Cafe",       "Food"),
    ("amenity", "fast_food"):   Category("Fast Food",  "Food"),
    ("amenity", "bar"):         Category("Bar",        "Food"),
    ("amenity", "pub"):         Category("Pub",        "Food"),
    ("amenity", "ice_cream"):   Category("Ice Cream",  "Food"),
    ("amenity", "food_court"):  Category("Food Court", "Food"),

    # ACCOMMODATION
    ("amenity", "hotel"): Category("Hotel", "Accommodation"),

    # RELIGIOUS
    ("amenity", "place_of_worship"): Category("Religious Site", "Religious"),

    # TRANSPORT
    ("amenity", "fuel"):        Category("Fuel Station", "Transport"),
    ("amenity", "parking"):     Category("Parking",      "Transport"),
    ("amenity", "bus_station"): Category("Bus Station",  "Transport"),
    ("aeroway", "aerodrome"):   Category("Airport",      "Transport"),

}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_category(tags: Dict[str, str]) -> Optional[Category]:
    """Return the normalised Category for these OSM tags, or None."""
    for (key, val), category in CATEGORY_MAPPING.items():
        if tags.get(key) == val:
            return category
    return None


def is_place(tags: Dict[str, str]) -> bool:
    """True if these tags map to any known travel category."""
    return get_category(tags) is not None


def get_name(tags: Dict[str, str]) -> Optional[str]:
    """Return the best available display name from OSM tags, or None if invalid/placeholder."""
    raw_name = (
        tags.get("name:en")
        or tags.get("name")
        or tags.get("official_name")
    )
    if not raw_name:
        return None
    
    s = str(raw_name).strip()
    if len(s) <= 2:
        return None
        
    s_lower = s.lower()
    placeholders = ('unnamed', 'unknown', 'no name', 'noname', 'no_name', 'n/a', 'null', 'node/', 'way/', 'relation/')
    if any(p in s_lower for p in placeholders):
        return None
        
    return s
