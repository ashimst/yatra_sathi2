import sqlite3
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "yatra_sathi.db"
SEED_DIR = PROJECT_ROOT / "backend" / "data" / "seeds"

def inspect_database():
    print(f"Connecting to DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables found:", [t[0] for t in tables])

    for (t_name,) in tables:
        cursor.execute(f"SELECT count(*) FROM {t_name}")
        cnt = cursor.fetchone()[0]
        cursor.execute(f"PRAGMA table_info({t_name})")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"Table '{t_name}': {cnt} rows, cols: {cols}")

    # Inspect places
    cursor.execute("SELECT count(*), min(bbox_min_lat), max(bbox_max_lat), min(bbox_min_lon), max(bbox_max_lon) FROM places")
    p_cnt, min_lat, max_lat, min_lon, max_lon = cursor.fetchone()
    print(f"\nPLACES: count={p_cnt}")
    print(f"  Bounding box latitude range:  {min_lat:.6f} to {max_lat:.6f}")
    print(f"  Bounding box longitude range: {min_lon:.6f} to {max_lon:.6f}")

    # Also inspect all centroid WKTs in places
    cursor.execute("SELECT id, name, centroid FROM places")
    place_centroids = cursor.fetchall()
    parsed_lats = []
    parsed_lons = []
    malformed_centroids = []
    for pid, name, c_wkt in place_centroids:
        if not c_wkt or not c_wkt.startswith("POINT(") or not c_wkt.endswith(")"):
            malformed_centroids.append((pid, name, c_wkt))
            continue
        try:
            parts = c_wkt[6:-1].strip().split()
            lon, lat = float(parts[0]), float(parts[1])
            parsed_lons.append(lon)
            parsed_lats.append(lat)
        except Exception as e:
            malformed_centroids.append((pid, name, c_wkt, str(e)))

    print(f"  Centroid parsed count: {len(parsed_lats)}, malformed: {len(malformed_centroids)}")
    if parsed_lats:
        print(f"  Centroid Latitude range:  {min(parsed_lats):.6f} to {max(parsed_lats):.6f}")
        print(f"  Centroid Longitude range: {min(parsed_lons):.6f} to {max(parsed_lons):.6f}")

    # Inspect waypoints table if exists
    if ("waypoints",) in tables:
        cursor.execute("SELECT count(*), min(latitude), max(latitude), min(longitude), max(longitude), min(elevation_m), max(elevation_m) FROM waypoints")
        w_cnt, w_min_lat, w_max_lat, w_min_lon, w_max_lon, min_elev, max_elev = cursor.fetchone()
        print(f"\nWAYPOINTS TABLE: count={w_cnt}")
        print(f"  Latitude range:  {w_min_lat:.6f} to {w_max_lat:.6f}")
        print(f"  Longitude range: {w_min_lon:.6f} to {w_max_lon:.6f}")
        print(f"  Elevation range: {min_elev} to {max_elev}")

    # Inspect trails table if exists
    if ("trails",) in tables:
        cursor.execute("SELECT count(*), min(max_elevation_m), max(max_elevation_m) FROM trails")
        t_cnt, min_t_elev, max_t_elev = cursor.fetchone()
        print(f"\nTRAILS TABLE: count={t_cnt}")
        print(f"  Max elevation range: {min_t_elev} to {max_t_elev}")

    # Inspect festivals table if exists
    if ("festivals",) in tables:
        cursor.execute("SELECT count(*) FROM festivals")
        f_cnt = cursor.fetchone()[0]
        print(f"\nFESTIVALS TABLE: count={f_cnt}")

    # Inspect seeds
    print("\n--- SEED FILES ---")
    for s_name in ["trekking_trails.json", "waypoints.json", "cultural_heritage.json", "festivals.json"]:
        p = SEED_DIR / s_name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"Seed '{s_name}': {len(data)} items")

    conn.close()

if __name__ == "__main__":
    inspect_database()
