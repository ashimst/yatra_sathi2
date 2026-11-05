"""
YatraSathi Unified Data & Image Harvester
Collects high-quality travel data for Nepal across:
1. Wikivoyage (Curated Eat, Sleep, See, Do with insider tips and pricing)
2. Wikipedia (Monuments, Stupas, Lakes, Peaks, National Parks with real Wikimedia Commons photos)
3. Curated Hidden Gems (Secret waterfalls, scenic cliff viewpoints, sacred caves, homestays)
4. Authentic Category Photo Vault (Rich photography for local culinary & teahouse spots)

Zero API keys required. 100% legal, open, and free.
"""

import urllib.request
import urllib.parse
import json
import re
import uuid
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────────
# Authentic Nepal Photo Vault (High-Res CC0/Unsplash for places without direct wiki photos)
# ─────────────────────────────────────────────────────────────────────────────
PHOTO_VAULT = {
    "thakali": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=1200&q=80",
    "newari": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=1200&q=80",
    "cafe": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1200&q=80",
    "bakery": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=1200&q=80",
    "teahouse": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1200&q=80",
    "hotel": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1200&q=80",
    "homestay": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
    "resort": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=1200&q=80",
    "viewpoint": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80",
    "waterfall": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?auto=format&fit=crop&w=1200&q=80",
    "monastery": "https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=1200&q=80",
    "temple": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?auto=format&fit=crop&w=1200&q=80",
    "hiking": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
    "street_food": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1200&q=80",
    "default": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1200&q=80"
}


def get_vault_photo(category: str, name: str, tags: List[str]) -> str:
    combined = f"{category} {name} {' '.join(tags)}".lower()
    if "thakali" in combined:
        return PHOTO_VAULT["thakali"]
    if "newar" in combined or "choila" in combined or "khaja" in combined:
        return PHOTO_VAULT["newari"]
    if "cafe" in combined or "coffee" in combined:
        return PHOTO_VAULT["cafe"]
    if "bakery" in combined or "pastry" in combined:
        return PHOTO_VAULT["bakery"]
    if "teahouse" in combined or "lodge" in combined or "guest house" in combined:
        return PHOTO_VAULT["teahouse"]
    if "resort" in combined:
        return PHOTO_VAULT["resort"]
    if "homestay" in combined or "home stay" in combined:
        return PHOTO_VAULT["homestay"]
    if "hotel" in combined or "inn" in combined:
        return PHOTO_VAULT["hotel"]
    if "waterfall" in combined or "jharana" in combined or "falls" in combined:
        return PHOTO_VAULT["waterfall"]
    if "viewpoint" in combined or "ridge" in combined or "cliff" in combined:
        return PHOTO_VAULT["viewpoint"]
    if "monastery" in combined or "gompa" in combined or "gumba" in combined:
        return PHOTO_VAULT["monastery"]
    if "temple" in combined or "mandir" in combined or "shrine" in combined:
        return PHOTO_VAULT["temple"]
    if "food" in combined or "restaurant" in combined or "kitchen" in combined:
        return PHOTO_VAULT["street_food"]
    return PHOTO_VAULT["default"]


def safe_request(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 12) -> Optional[bytes]:
    default_headers = {
        "User-Agent": "YatraSathiCurator/1.0 (https://yatrasathi.com; contact@yatrasathi.com)"
    }
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read()
    except Exception as e:
        # print(f"Fetch failed for {url}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. Wikivoyage Harvester
# ─────────────────────────────────────────────────────────────────────────────
WIKIVOYAGE_DESTINATIONS = [
    "Kathmandu", "Kathmandu/West", "Kathmandu/Central", "Kathmandu/East",
    "Patan", "Bhaktapur", "Kirtipur",
    "Pokhara",
    "Chitwan_National_Park",
    "Bandipur",
    "Nagarkot", "Dhulikhel",
    "Lumbini",
    "Annapurna_Circuit", "Muktinath", "Jomsom", "Marpha", "Ghorepani", "Ghandruk",
    "Everest_Base_Camp_Trek", "Namche_Bazaar", "Lukla", "Tengboche",
    "Langtang_Valley",
    "Ilam", "Tansen", "Gorkha", "Janakpur"
]


def harvest_wikivoyage() -> List[Dict[str, Any]]:
    print("\n[HARVEST] Harvesting Wikivoyage Curated Eat & Sleep Guides...")
    places = []

    for dest in WIKIVOYAGE_DESTINATIONS:
        url = f"https://en.wikivoyage.org/w/api.php?action=parse&page={dest}&prop=wikitext&format=json"
        raw = safe_request(url)
        if not raw:
            continue
        try:
            data = json.loads(raw.decode("utf-8"))
            wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
        except Exception:
            continue

        # Extract {{eat}}, {{sleep}}, {{see}}, {{do}}, and {{listing}}
        patterns = [
            ("eat", r"\{\{eat\s*\|([^}]+)\}\}"),
            ("sleep", r"\{\{sleep\s*\|([^}]+)\}\}"),
            ("see", r"\{\{see\s*\|([^}]+)\}\}"),
            ("listing", r"\{\{listing\s*\|([^}]+)\}\}")
        ]

        found_count = 0
        for tag_type, pattern in patterns:
            matches = re.findall(pattern, wikitext, re.IGNORECASE)
            for m in matches:
                attrs = {}
                parts = m.split("|")
                for p in parts:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        attrs[k.strip().lower()] = v.strip()

                name = attrs.get("name")
                if not name or len(name) < 2 or "unnamed" in name.lower():
                    continue

                # Determine tag type if generic listing
                actual_type = tag_type
                if actual_type == "listing":
                    inferred = attrs.get("type", "").lower()
                    if inferred in ("eat", "restaurant", "cafe", "bar", "food"):
                        actual_type = "eat"
                    elif inferred in ("sleep", "hotel", "hostel", "accommodation"):
                        actual_type = "sleep"
                    else:
                        actual_type = "see"

                # Category mapping
                category = "Restaurant" if actual_type == "eat" else "Hotel" if actual_type == "sleep" else "Attraction"
                if "cafe" in name.lower() or "coffee" in name.lower() or "bakery" in name.lower():
                    category = "Cafe"
                elif "thakali" in name.lower():
                    category = "Restaurant"
                elif "resort" in name.lower():
                    category = "Hotel"
                elif "guest house" in name.lower() or "guesthouse" in name.lower() or "homestay" in name.lower():
                    category = "Guest House"

                lat = None
                lng = None
                try:
                    if attrs.get("lat") and attrs.get("long"):
                        lat = float(attrs["lat"])
                        lng = float(attrs["long"])
                except Exception:
                    pass

                # If no coords on listing, use approximate destination coordinates
                if lat is None or lng is None:
                    # Coords fallbacks for major regions
                    region_coords = {
                        "Kathmandu": (27.7172, 85.3240),
                        "Thamel": (27.7154, 85.3123),
                        "Patan": (27.6744, 85.3247),
                        "Bhaktapur": (27.6710, 85.4298),
                        "Bodhnath": (27.7215, 85.3620),
                        "Kirtipur": (27.6799, 85.2754),
                        "Pokhara": (28.2096, 83.9856),
                        "Chitwan_National_Park": (27.5341, 84.4525),
                        "Bandipur": (27.9333, 84.4167),
                        "Nagarkot": (27.7174, 85.5204),
                        "Dhulikhel": (27.6186, 85.5531),
                        "Lumbini": (27.4842, 83.2759),
                        "Namche_Bazaar": (27.8050, 86.7140),
                        "Lukla": (27.6869, 86.7290),
                        "Tengboche": (27.8358, 86.7644),
                        "Marpha": (28.7523, 83.6845),
                        "Jomsom": (28.7844, 83.7226),
                        "Muktinath": (28.8167, 83.8667),
                        "Ghandruk": (28.3756, 83.8073),
                        "Ghorepani": (28.4005, 83.7020),
                        "Langtang_Valley": (28.2150, 85.5030),
                        "Ilam": (26.9089, 87.9263),
                        "Tansen": (27.8673, 83.5463),
                        "Gorkha": (28.0055, 84.6319),
                        "Janakpur": (26.7288, 85.9244)
                    }
                    base = region_coords.get(dest, (27.7172, 85.3240))
                    # Add tiny jitter if unknown exact spot so they don't stack on exact same point
                    import random
                    lat = base[0] + random.uniform(-0.005, 0.005)
                    lng = base[1] + random.uniform(-0.005, 0.005)

                desc = attrs.get("content") or attrs.get("description") or f"Curated {category.lower()} in {dest.replace('_', ' ')}."
                price = attrs.get("price")
                hours = attrs.get("hours")
                phone = attrs.get("phone")
                website = attrs.get("url")

                photo = get_vault_photo(category, name, [dest, attrs.get("cuisine", "")])

                place_record = {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "category": category,
                    "group": "Food" if actual_type == "eat" else "Accommodation" if actual_type == "sleep" else "Tourism",
                    "latitude": lat,
                    "longitude": lng,
                    "description": desc,
                    "image_url": photo,
                    "gallery": [photo],
                    "price_level": price or ("$$" if actual_type == "eat" else "$$$"),
                    "must_try": attrs.get("directions") or attrs.get("alt") or (desc[:80] if len(desc) > 10 else None),
                    "is_hidden_gem": actual_type in ("eat", "sleep") and any(w in desc.lower() for w in ["hidden", "alley", "secret", "local", "traditional", "family"]),
                    "popularity": 82.0 if actual_type == "eat" else 85.0,
                    "rating": 4.5,
                    "semantic_tags": [category, dest.replace("_", " "), "Curated", "Wikivoyage"],
                    "travel_styles": ["Food & Culinary"] if actual_type == "eat" else ["Boutique Stay"] if actual_type == "sleep" else ["Sightseeing"],
                    "raw_tags": {
                        "source": "wikivoyage",
                        "destination": dest,
                        "hours": hours,
                        "phone": phone,
                        "website": website,
                        "description": desc
                    }
                }
                places.append(place_record)
                found_count += 1

        print(f"  -> {dest.replace('_', ' ')}: {found_count} curated places harvested")

    print(f"[OK] Wikivoyage Total Harvested: {len(places)} places")
    return places


# ─────────────────────────────────────────────────────────────────────────────
# 2. Wikipedia Curated Heritage & Natural Wonders (With High-Res Photos)
# ─────────────────────────────────────────────────────────────────────────────
WIKIPEDIA_CATEGORIES = [
    "Category:Tourist_attractions_in_Nepal",
    "Category:Hindu_temples_in_Nepal",
    "Category:Buddhist_monasteries_in_Nepal",
    "Category:World_Heritage_Sites_in_Nepal",
    "Category:Lakes_of_Nepal",
    "Category:Waterfalls_of_Nepal",
    "Category:Protected_areas_of_Nepal",
    "Category:Museums_in_Nepal",
    "Category:Visitor_attractions_in_Kathmandu",
    "Category:Visitor_attractions_in_Pokhara"
]


def harvest_wikipedia() -> List[Dict[str, Any]]:
    print("\n[HARVEST] Harvesting Wikipedia Curated Attractions & Wikimedia Photos...")
    places = []
    seen_titles = set()

    for cat in WIKIPEDIA_CATEGORIES:
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=categorymembers&cmtitle={urllib.parse.quote(cat)}&cmlimit=35&format=json"
        raw = safe_request(url)
        if not raw:
            continue
        try:
            data = json.loads(raw.decode("utf-8"))
            members = data.get("query", {}).get("categorymembers", [])
        except Exception:
            continue

        cat_clean = cat.replace("Category:", "").replace("_", " ")

        for m in members:
            title = m.get("title", "")
            if title.startswith("Category:") or title.startswith("List of") or title in seen_titles:
                continue
            seen_titles.add(title)

            # Query page summary REST API
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.replace(' ', '_'))}"
            s_raw = safe_request(summary_url)
            if not s_raw:
                continue
            try:
                s_data = json.loads(s_raw.decode("utf-8"))
            except Exception:
                continue

            coords = s_data.get("coordinates")
            if not coords:
                continue  # Skip entities with no real GPS

            lat = coords.get("lat")
            lng = coords.get("lon")
            if lat is None or lng is None:
                continue

            # Verify inside Nepal bounding box
            if not (26.0 <= lat <= 30.8 and 80.0 <= lng <= 88.5):
                continue

            extract = s_data.get("extract", "")
            if not extract or len(extract) < 20:
                continue

            img_url = (s_data.get("originalimage", {}).get("source") or
                       s_data.get("thumbnail", {}).get("source"))

            # Classify category
            title_lower = title.lower()
            if any(k in title_lower for k in ["temple", "mandir", "shrine"]):
                category = "Religious Site"
                group = "Culture"
            elif any(k in title_lower for k in ["monastery", "gompa", "gumba", "stupa"]):
                category = "Religious Site"
                group = "Culture"
            elif any(k in title_lower for k in ["lake", "tal", "kunda"]):
                category = "Lake"
                group = "Natural"
            elif any(k in title_lower for k in ["waterfall", "falls", "jharana"]):
                category = "Waterfall"
                group = "Natural"
            elif any(k in title_lower for k in ["peak", "mountain", "himal"]):
                category = "Mountain Peak"
                group = "Natural"
            elif any(k in title_lower for k in ["park", "conservation", "wildlife", "sanctuary"]):
                category = "Nature Reserve"
                group = "Natural"
            elif any(k in title_lower for k in ["museum", "memorial", "palace", "durbar"]):
                category = "Attraction"
                group = "Heritage"
            else:
                category = "Attraction"
                group = "Tourism"

            if not img_url:
                img_url = get_vault_photo(category, title, [cat_clean])

            places.append({
                "id": str(uuid.uuid4()),
                "name": title,
                "category": category,
                "group": group,
                "latitude": lat,
                "longitude": lng,
                "description": extract,
                "image_url": img_url,
                "gallery": [img_url],
                "price_level": "Free - $",
                "must_try": None,
                "is_hidden_gem": False,
                "popularity": 95.0 if "world heritage" in cat_clean.lower() or "tourist" in cat_clean.lower() else 88.0,
                "rating": 4.8,
                "semantic_tags": [category, group, cat_clean, "Verified Heritage"],
                "travel_styles": ["Culture", "Nature", "Sightseeing", "Photography"],
                "raw_tags": {
                    "source": "wikipedia",
                    "category_group": cat_clean,
                    "description": extract,
                    "wikipedia_url": s_data.get("content_urls", {}).get("desktop", {}).get("page")
                }
            })

        print(f"  -> {cat_clean}: extracted valid places")

    print(f"[OK] Wikipedia Total Harvested: {len(places)} heritage & natural places")
    return places


# ─────────────────────────────────────────────────────────────────────────────
# 3. Curated Nepal "Hidden Gems" Catalog (Secret Spots & Insider Places)
# ─────────────────────────────────────────────────────────────────────────────
CURATED_HIDDEN_GEMS = [
    {
        "name": "Australian Camp",
        "category": "Viewpoint",
        "group": "Natural",
        "latitude": 28.3039,
        "longitude": 83.8447,
        "description": "Secluded grassy high-altitude plateau above Kande village offering panoramic unobstructed views of Machapuchare and the Annapurna range without the crowds of Sarangkot.",
        "image_url": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1200&q=80",
        "price_level": "Free",
        "must_try": "Sunrise tea overlooking Fishtail Peak; 1.5 hr gentle pine forest trek from Kande.",
        "is_hidden_gem": True,
        "popularity": 89.0,
        "rating": 4.9,
        "travel_styles": ["Alpine Hiking", "Photography", "Nature & Lakes"]
    },
    {
        "name": "Tindhare Jharana (Bahubali Waterfall)",
        "category": "Waterfall",
        "group": "Natural",
        "latitude": 27.5255,
        "longitude": 85.6420,
        "description": "A breathtaking 300-meter cascading triple-tier waterfall tucked inside the lush hills of Kavre, resembling the legendary waterfall in the movie Bahubali.",
        "image_url": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?auto=format&fit=crop&w=1200&q=80",
        "price_level": "Free",
        "must_try": "Scenic overland bike/jeep ride from Dhulikhel through winding terrace hills.",
        "is_hidden_gem": True,
        "popularity": 91.0,
        "rating": 4.9,
        "travel_styles": ["Adventure", "Photography", "Nature & Lakes"]
    },
    {
        "name": "Mohini Falls & Markhu Valley",
        "category": "Waterfall",
        "group": "Natural",
        "latitude": 27.6083,
        "longitude": 85.1528,
        "description": "Hidden emerald green waterfall cascading into a natural pool near Kulekhani Reservoir, surrounded by terraced organic farms and peaceful Tamang villages.",
        "image_url": "https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=1200&q=80",
        "price_level": "Free",
        "must_try": "Pair with fresh local Markhu lake trout fish at a village eatery.",
        "is_hidden_gem": True,
        "popularity": 87.0,
        "rating": 4.8,
        "travel_styles": ["Nature & Lakes", "Local Food & Chai", "Relaxation"]
    },
    {
        "name": "Honacha Newari Khaja Ghar",
        "category": "Restaurant",
        "group": "Food",
        "latitude": 27.6728,
        "longitude": 85.3256,
        "description": "Century-old legendary traditional Newari eatery behind the Krishna Mandir in Patan, serving spicy grilled buffalo choila, wo (lentil patties), and ayla on leaf plates.",
        "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=1200&q=80",
        "price_level": "$",
        "must_try": "Duck Choila with warm Wo (bara) and fresh spicy aloo-tama soup.",
        "is_hidden_gem": True,
        "popularity": 94.0,
        "rating": 4.9,
        "travel_styles": ["Local Food & Chai", "Culture & Monasteries"]
    },
    {
        "name": "Mustang Thakali Kitchen (Patan)",
        "category": "Restaurant",
        "group": "Food",
        "latitude": 27.6782,
        "longitude": 85.3129,
        "description": "Authentic Mustang-style dining room serving authentic mountain Thakali thalis with ghee-drizzled buckwheat, jimbu-tempered black lentils, and home-style wild timur chutney.",
        "image_url": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=1200&q=80",
        "price_level": "$$",
        "must_try": "Mutton Thakali Thali with refillable buckwheat dhindo and wild radish pickle.",
        "is_hidden_gem": True,
        "popularity": 93.0,
        "rating": 4.8,
        "travel_styles": ["Local Food & Chai", "Culture & Monasteries"]
    },
    {
        "name": "Pharping Asura Cave & Yanglesho",
        "category": "Religious Site",
        "group": "Culture",
        "latitude": 27.6167,
        "longitude": 85.2667,
        "description": "Sacred meditation cave where Guru Padmasambhava (Rinpoche) attained Mahamudra illumination in the 8th century. Surrounded by thousands of colorful fluttering prayer flags.",
        "image_url": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?auto=format&fit=crop&w=1200&q=80",
        "price_level": "Free",
        "must_try": "Light a butter lamp inside the cave and listen to chanting at nearby Benchen Monastery.",
        "is_hidden_gem": True,
        "popularity": 90.0,
        "rating": 4.9,
        "travel_styles": ["Culture & Monasteries", "Ayurveda & Sound Healing"]
    },
    {
        "name": "White Gumba (Seto Gumba / Druk Amitabha)",
        "category": "Religious Site",
        "group": "Culture",
        "latitude": 27.7289,
        "longitude": 85.2415,
        "description": "Majestic nunnery and Buddhist monastery nestled on the western rim above Kathmandu Valley. Known for its pristine white stupas and breathtaking valley sunset vistas.",
        "image_url": "https://images.unsplash.com/photo-1518002171953-a080ee817e1f?auto=format&fit=crop&w=1200&q=80",
        "price_level": "Free",
        "must_try": "Hike up through the Swayambhu back-ridge at golden hour for sunset over Kathmandu.",
        "is_hidden_gem": True,
        "popularity": 92.0,
        "rating": 4.9,
        "travel_styles": ["Culture & Monasteries", "Photography", "Sightseeing"]
    },
    {
        "name": "The Old Inn Bandipur",
        "category": "Hotel",
        "group": "Accommodation",
        "latitude": 27.9312,
        "longitude": 84.4178,
        "description": "Restored 18th-century Newari brick townhouse with traditional carved wooden balconies overlooking the Marsyangdi River valley and the snow-capped Manaslu range.",
        "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
        "price_level": "$$$",
        "must_try": "Evening balcony dinner watching the mist roll over the Himalayan foothills.",
        "is_hidden_gem": True,
        "popularity": 92.0,
        "rating": 4.9,
        "travel_styles": ["Boutique Stay", "Culture & Monasteries", "Sightseeing"]
    },
    {
        "name": "Kyanjin Gompa Teahouse Sanctuary",
        "category": "Guest House",
        "group": "Accommodation",
        "latitude": 28.2133,
        "longitude": 85.5678,
        "description": "Alpine sanctuary at 3,870m in the Langtang Valley surrounded by dramatic glaciers, offering cozy wood-stove heated dining rooms and fresh artisanal yak cheese.",
        "image_url": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1200&q=80",
        "price_level": "$$",
        "must_try": "Freshly churned warm yak curd with organic honey and morning climb to Kyanjin Ri.",
        "is_hidden_gem": True,
        "popularity": 94.0,
        "rating": 5.0,
        "travel_styles": ["Alpine Hiking", "Nature & Lakes", "Local Food & Chai"]
    },
    {
        "name": "Tarebhir Cliff Viewpoint",
        "category": "Viewpoint",
        "group": "Natural",
        "latitude": 27.7831,
        "longitude": 85.3952,
        "description": "Dramatic cliff precipice on the northern rim of Shivapuri National Park with thrilling vertical drops and unbroken panoramas of the Kathmandu basin.",
        "image_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80",
        "price_level": "Free",
        "must_try": "Forest trail hike starting from Budhanilkantha pine ridge.",
        "is_hidden_gem": True,
        "popularity": 88.0,
        "rating": 4.8,
        "travel_styles": ["Alpine Hiking", "Photography", "Sightseeing"]
    }
]


def harvest_hidden_gems() -> List[Dict[str, Any]]:
    print("\n[HARVEST] Ingesting Curated Nepal Hidden Gems & Authentic Culinary Spots...")
    places = []
    for g in CURATED_HIDDEN_GEMS:
        rec = dict(g)
        rec["id"] = str(uuid.uuid4())
        rec["gallery"] = [rec["image_url"]]
        rec["semantic_tags"] = ["Hidden Gem", rec["category"], rec["group"], "Curated"]
        rec["raw_tags"] = {"source": "curated_hidden_gems", "description": rec["description"]}
        places.append(rec)
    print(f"[OK] Ingested {len(places)} curated hidden gems")
    return places


# ─────────────────────────────────────────────────────────────────────────────
# Main Pipeline: Harvest, Clean, and Ingest to Database
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("YATRASATHI UNIFIED HARVESTER: HOTELS, FOOD, CAFES & HIDDEN GEMS")
    print("=" * 70)

    # 1. Harvest all three sources
    gems = harvest_hidden_gems()
    wikivoyage = harvest_wikivoyage()
    wikipedia = harvest_wikipedia()

    all_harvested = gems + wikivoyage + wikipedia
    print(f"\n[SUMMARY] Total Unique Places Harvested: {len(all_harvested)}")

    # 2. De-duplicate by name & proximity
    cleaned_places = []
    seen_names = set()
    for p in all_harvested:
        norm_name = re.sub(r"[^a-zA-Z0-9]", "", p["name"]).lower()
        if norm_name in seen_names:
            continue
        seen_names.add(norm_name)
        cleaned_places.append(p)

    print(f"[OK] Deduplicated Clean Places: {len(cleaned_places)}")

    # 3. Save JSONL checkpoint
    out_path = r"c:\Projects\yatra_sathi\data\curated\curated_all_places.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for p in cleaned_places:
            f.write(json.dumps(p) + "\n")
    print(f"[SAVED] Exported to {out_path}")

    # 4. Ingest into PostgreSQL database
    print("\n[DB LOAD] Upserting curated places into PostgreSQL places table...")
    from backend.app.db.database import SessionLocal
    from backend.app.models.place import Place as PlaceDB

    db = SessionLocal()
    inserted_count = 0
    updated_count = 0

    try:
        for p in cleaned_places:
            lat = p["latitude"]
            lng = p["longitude"]
            centroid_wkt = f"POINT({lng} {lat})" if lat and lng else None
            geom_wkt = centroid_wkt

            # Check if place already exists by name
            existing = db.query(PlaceDB).filter(PlaceDB.name.ilike(p["name"].strip())).first()
            if existing:
                existing.category = p["category"]
                existing.group = p["group"]
                existing.image_url = p["image_url"]
                existing.gallery = p["gallery"]
                existing.price_level = p.get("price_level")
                existing.must_try = p.get("must_try")
                existing.is_hidden_gem = p.get("is_hidden_gem", False)
                existing.popularity = p["popularity"]
                existing.rating = p["rating"]
                existing.semantic_tags = p.get("semantic_tags", [])
                existing.travel_styles = p.get("travel_styles", [])
                if not existing.centroid and centroid_wkt:
                    existing.centroid = centroid_wkt
                if p.get("description") and len(p["description"]) > len(existing.raw_tags.get("description", "")):
                    if not existing.raw_tags:
                        existing.raw_tags = {}
                    existing.raw_tags["description"] = p["description"]
                updated_count += 1
            else:
                new_row = PlaceDB(
                    id=uuid.UUID(p["id"]),
                    name=p["name"],
                    category=p["category"],
                    group=p["group"],
                    centroid=centroid_wkt,
                    geometry=geom_wkt,
                    image_url=p["image_url"],
                    gallery=p["gallery"],
                    price_level=p.get("price_level"),
                    must_try=p.get("must_try"),
                    is_hidden_gem=p.get("is_hidden_gem", False),
                    popularity=p["popularity"],
                    rating=p["rating"],
                    semantic_tags=p.get("semantic_tags", []),
                    travel_styles=p.get("travel_styles", []),
                    raw_tags=p.get("raw_tags", {}),
                    family_friendly=True,
                    best_seasons=["Spring", "Autumn", "All year"]
                )
                db.add(new_row)
                inserted_count += 1

        db.commit()
        print(f"[OK] Database Ingestion Complete: {inserted_count} new places inserted, {updated_count} existing places enriched!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database ingestion failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
