"""
Adversarial LineString Geometry and Spatial Proximity Audit
"""
import sqlite3
import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "yatra_sathi.db"

NEPAL_LAT_MIN = 26.0
NEPAL_LAT_MAX = 30.5
NEPAL_LON_MIN = 80.0
NEPAL_LON_MAX = 88.5

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    return 2.0 * R * math.asin(math.sqrt(a))

def audit_trail_geometries_and_proximity():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- 1. AUDITING ALL TRAIL LINESTRING ROUTE GEOMETRIES ---")
    cursor.execute("SELECT id, name, route_geometry_wkt FROM trails")
    trails = cursor.fetchall()
    total_linestring_pts = 0
    linestring_oob = []

    for tid, name, wkt in trails:
        if not wkt:
            print(f"Warning: Trail {name} has no route_geometry_wkt")
            continue
        assert wkt.startswith("LINESTRING(") and wkt.endswith(")"), f"Invalid WKT in {name}"
        raw_coords = wkt[11:-1].strip().split(",")
        total_linestring_pts += len(raw_coords)
        for pt_str in raw_coords:
            parts = pt_str.strip().split()
            lon, lat = float(parts[0]), float(parts[1])
            if not (NEPAL_LAT_MIN <= lat <= NEPAL_LAT_MAX) or not (NEPAL_LON_MIN <= lon <= NEPAL_LON_MAX):
                linestring_oob.append((name, lat, lon))

    print(f"Total trail LineString vertices checked: {total_linestring_pts}")
    print(f"Vertices outside Nepal bounds: {len(linestring_oob)}")
    assert len(linestring_oob) == 0

    print("\n--- 2. SPATIAL PROXIMITY & CO-LOCATION AUDIT ON 1,487 PLACES ---")
    cursor.execute("SELECT id, name, category, centroid FROM places")
    places = cursor.fetchall()

    parsed = []
    for pid, name, cat, c_wkt in places:
        parts = c_wkt[6:-1].strip().split()
        lon, lat = float(parts[0]), float(parts[1])
        parsed.append({"id": pid, "name": name, "cat": cat, "lat": lat, "lon": lon})

    print(f"Loaded {len(parsed)} places for pairwise spatial proximity audit.")

    # Spatial grid indexing for efficient pairwise proximity search
    grid = {}
    for p in parsed:
        gx = int(p["lon"] * 100)
        gy = int(p["lat"] * 100)
        grid.setdefault((gx, gy), []).append(p)

    exact_coincidences = 0
    co_located_pairs = []
    
    for (gx, gy), cell_places in grid.items():
        # Check within same and neighboring cells
        candidates = []
        for dx in (0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == -1:
                    continue
                neighbor = grid.get((gx + dx, gy + dy), [])
                if dx == 0 and dy == 0:
                    # Within cell
                    for i in range(len(cell_places)):
                        for j in range(i + 1, len(cell_places)):
                            p1, p2 = cell_places[i], cell_places[j]
                            d = haversine_m(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
                            if d < 0.1:  # Exactly co-located (under 10 cm)
                                exact_coincidences += 1
                                co_located_pairs.append((p1["name"], p2["name"], d))
                else:
                    for p1 in cell_places:
                        for p2 in neighbor:
                            d = haversine_m(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
                            if d < 0.1:
                                exact_coincidences += 1
                                co_located_pairs.append((p1["name"], p2["name"], d))

    print(f"Total exact co-located pairs (<10cm): {exact_coincidences}")
    if co_located_pairs:
        print("Sample co-located pairs:")
        for p1, p2, d in co_located_pairs[:10]:
            print(f"  - '{p1}' and '{p2}' (dist={d:.2f}m)")

    conn.close()
    print("\nAudit completed successfully!")

if __name__ == "__main__":
    audit_trail_geometries_and_proximity()
