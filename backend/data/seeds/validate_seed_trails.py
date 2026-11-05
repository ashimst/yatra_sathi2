"""
Standalone verification script for trekking_trails.json and waypoints.json seed files.
Usage:
  python backend/data/seeds/validate_seed_trails.py
"""

import json
import os
import sys
from shapely import wkt

NEPAL_BOUNDS = {
    "min_lat": 26.0,
    "max_lat": 30.5,
    "min_lon": 80.0,
    "max_lon": 88.5,
}

REQUIRED_TRAIL_REGIONS = {
    "Annapurna",
    "Everest",
    "Manaslu",
    "Langtang",
    "Mustang",
    "Kanchenjunga",
    "Makalu",
    "Dolpo",
}

ALLOWED_WAYPOINT_CATEGORIES = {
    "Mountain Pass",
    "Emergency Helipad",
    "Medical Post",
    "Checkpost",
    "Guest House",
    "Settlement",
    "Acclimatization Hub",
}

REQUIRED_CLINIC_KEYWORDS = ["Pheriche", "Manang", "Kunde", "Machhermo"]
REQUIRED_HELIPAD_LOCATIONS = [
    "Gorak Shep", "Everest Base Camp", "Pheriche", "Dingboche",
    "Annapurna Base Camp", "Machapuchare Base Camp", "Thorong Phedi",
    "Samagaun", "Kyanjin Gompa", "Lo Manthang", "Ghunsa"
]
REQUIRED_PASSES = ["Thorong La", "Cho La", "Renjo La", "Kongma La", "Larkya La", "Laurebina"]

def check_coord(lat, lon, entity_name):
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False, f"Coordinates not float: lat={lat}, lon={lon} for {entity_name}"
    if not (NEPAL_BOUNDS["min_lat"] <= lat <= NEPAL_BOUNDS["max_lat"]):
        return False, f"Latitude {lat} out of Nepal bounds [26.0, 30.5] for {entity_name}"
    if not (NEPAL_BOUNDS["min_lon"] <= lon <= NEPAL_BOUNDS["max_lon"]):
        return False, f"Longitude {lon} out of Nepal bounds [80.0, 88.5] for {entity_name}"
    return True, ""

def validate():
    seeds_dir = os.path.dirname(os.path.abspath(__file__))
    trails_file = os.path.join(seeds_dir, "trekking_trails.json")
    waypoints_file = os.path.join(seeds_dir, "waypoints.json")

    print(f"Validating trails from: {trails_file}")
    with open(trails_file, "r", encoding="utf-8") as f:
        trails = json.load(f)

    print(f"Validating waypoints from: {waypoints_file}")
    with open(waypoints_file, "r", encoding="utf-8") as f:
        waypoints = json.load(f)

    errors = []
    # 1. Trails
    regions = set()
    for t in trails:
        name = t.get("name")
        regions.add(t.get("region"))
        for pt_name in ["start_point", "end_point"]:
            pt = t.get(pt_name, {})
            ok, err = check_coord(pt.get("latitude"), pt.get("longitude"), f"{name} {pt_name}")
            if not ok:
                errors.append(err)
        line = wkt.loads(t["route_geometry_wkt"])
        for lon, lat in line.coords:
            ok, err = check_coord(lat, lon, f"{name} vertex")
            if not ok:
                errors.append(err)

    missing_regs = REQUIRED_TRAIL_REGIONS - regions
    if missing_regs:
        errors.append(f"Missing required trail regions: {missing_regs}")

    # 2. Waypoints
    keys = set()
    helipads = []
    meds = []
    passes = []
    for w in waypoints:
        name = w["name"]
        cat = w["category"]
        if cat not in ALLOWED_WAYPOINT_CATEGORIES:
            errors.append(f"Invalid category '{cat}' for {name}")
        lat, lon = w["latitude"], w["longitude"]
        ok, err = check_coord(lat, lon, name)
        if not ok:
            errors.append(err)
        key = (name.lower().strip(), round(lat, 4), round(lon, 4))
        if key in keys:
            errors.append(f"Duplicate waypoint: {key}")
        keys.add(key)

        if cat == "Emergency Helipad":
            helipads.append(w)
        elif cat == "Medical Post":
            meds.append(w)
        elif cat == "Mountain Pass":
            passes.append(w)

    if len(helipads) < 19:
        errors.append(f"Expected at least 19 helipads, got {len(helipads)}")

    for kw in REQUIRED_CLINIC_KEYWORDS:
        if not any(kw.lower() in m["name"].lower() for m in meds):
            errors.append(f"Missing clinic keyword: {kw}")

    for p in REQUIRED_PASSES:
        if not any(p.lower() in item["name"].lower() for item in passes):
            errors.append(f"Missing pass: {p}")

    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for e in errors[:10]:
            print(" -", e)
        sys.exit(1)

    print(f"SUCCESS: {len(trails)} trails and {len(waypoints)} waypoints strictly valid!")
    print(f"Emergency Helipads: {len(helipads)}, Medical Posts: {len(meds)}, Mountain Passes: {len(passes)}")

if __name__ == "__main__":
    validate()
