import sqlite3
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "yatra_sathi.db"

def check_border_points():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=== EXTREME POINTS IN PLACES ===")
    cursor.execute("""
        SELECT name, category, centroid, bbox_min_lat, bbox_min_lon 
        FROM places 
        ORDER BY bbox_min_lat ASC LIMIT 10
    """)
    print("\n-- 10 Southernmost Places (Min Latitude) --")
    for r in cursor.fetchall():
        print(f"Name: {r[0]}, Cat: {r[1]}, Centroid: {r[2]}, BboxMin: ({r[3]}, {r[4]})")

    cursor.execute("""
        SELECT name, category, centroid, bbox_max_lat, bbox_max_lon 
        FROM places 
        ORDER BY bbox_max_lat DESC LIMIT 10
    """)
    print("\n-- 10 Northernmost Places (Max Latitude) --")
    for r in cursor.fetchall():
        print(f"Name: {r[0]}, Cat: {r[1]}, Centroid: {r[2]}, BboxMax: ({r[3]}, {r[4]})")

    cursor.execute("""
        SELECT name, category, centroid, bbox_min_lon, bbox_min_lat 
        FROM places 
        ORDER BY bbox_min_lon ASC LIMIT 10
    """)
    print("\n-- 10 Westernmost Places (Min Longitude) --")
    for r in cursor.fetchall():
        print(f"Name: {r[0]}, Cat: {r[1]}, Centroid: {r[2]}, BboxMin: ({r[4]}, {r[3]})")

    cursor.execute("""
        SELECT name, category, centroid, bbox_max_lon, bbox_max_lat 
        FROM places 
        ORDER BY bbox_max_lon DESC LIMIT 10
    """)
    print("\n-- 10 Easternmost Places (Max Longitude) --")
    for r in cursor.fetchall():
        print(f"Name: {r[0]}, Cat: {r[1]}, Centroid: {r[2]}, BboxMax: ({r[4]}, {r[3]})")

    conn.close()

if __name__ == "__main__":
    check_border_points()
