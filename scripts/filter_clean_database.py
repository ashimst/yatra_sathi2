"""
Filter and Purge Useless / BS Data from YatraSathi Database
Removes:
- Junk categories (Springs, Ponds, Trees, Fuel Stations, Bus Stations, Apartments, Playgrounds, Parking)
- Generic non-names ("Stupa", "Church", "Temple", "Chautari", "Masjid", "Hotel", "Lodge", "Khaja Ghar", etc.)
- Short/corrupted names (<= 2 chars or pure numbers/symbols)
- Bare unverified OSM nodes with zero metadata, contact, description, or tourism value.
- Synchronizes pgvector embeddings index via CASCADE.
"""
import os
import sys

# Ensure backend importable
sys.path.insert(0, os.path.abspath("."))

from backend.app.db.database import SessionLocal
from sqlalchemy import text

def clean_database():
    db = SessionLocal()
    try:
        initial_places = db.execute(text("SELECT count(*) FROM places")).scalar()
        initial_embeddings = db.execute(text("SELECT count(*) FROM embeddings")).scalar()
        print(f"[START] Initial places: {initial_places} | Initial embeddings: {initial_embeddings}")

        # 1. Delete junk categories
        print("\n[STEP 1] Purging junk infrastructure & non-destination categories...")
        junk_cats = [
            'Spring', 'Pond', 'Tree', 'Fuel Station', 'Bus Station', 
            'Apartment', 'Playground', 'Parking', 'Reservoir', 'Beach', 'Volcano'
        ]
        res1 = db.execute(text("""
            DELETE FROM places
            WHERE category IN :cats
        """), {"cats": tuple(junk_cats)})
        print(f"  Deleted {res1.rowcount} places in junk categories.")

        # 2. Delete generic non-names & corrupted names
        print("\n[STEP 2] Purging generic non-names and corrupted titles...")
        generic_names = [
            'stupa', 'church', 'temple', 'chautari', 'masjid', 'gompa', 'monastery',
            'hotel', 'restaurant', 'cafe', 'lodge', 'khaja ghar', 'tea stall', 'cold store',
            'toilet', 'drinking water', 'tap', 'water tap', 'atm', 'bank', 'hospital', 'pharmacy',
            'school', 'college', 'police', 'post office', 'waste basket', 'bench', 'shop', 'store',
            'rooftop restaurant', 'small hindu shrine', 'hindu shrine', 'shrine',
            'unnamed', 'no name', 'unknown', 'hotel and restaurant', 'guest house'
        ]
        res2 = db.execute(text("""
            DELETE FROM places
            WHERE lower(trim(name)) IN :gnames
               OR name ILIKE '%unnamed%'
               OR name ILIKE '%no name%'
               OR length(trim(name)) <= 2
        """), {"gnames": tuple(generic_names)})
        print(f"  Deleted {res2.rowcount} places with generic/empty titles.")

        # 3. Delete bare unverified OSM nodes with ZERO metadata
        print("\n[STEP 3] Purging bare unverified OSM nodes with zero metadata...")
        res3 = db.execute(text("""
            DELETE FROM places
            WHERE (image_url IS NULL OR trim(image_url) = '')
              AND rating IS NULL
              AND (popularity IS NULL OR popularity = 0)
              AND is_hidden_gem IS NOT TRUE
              AND website IS NULL
              AND wikipedia_url IS NULL
              AND wikidata_id IS NULL
              AND (raw_tags->>'website') IS NULL
              AND (raw_tags->>'phone') IS NULL
              AND (raw_tags->>'contact:phone') IS NULL
              AND (raw_tags->>'description') IS NULL
              AND (raw_tags->>'wikipedia') IS NULL
              AND (raw_tags->>'wikidata') IS NULL
              AND (raw_tags->>'cuisine') IS NULL
              AND (raw_tags->>'stars') IS NULL
              AND (raw_tags->>'rooms') IS NULL
              AND (raw_tags->>'opening_hours') IS NULL
              AND category NOT IN (
                  'Mountain Peak', 'Viewpoint', 'Waterfall', 'Cave', 
                  'National Park', 'Nature Reserve', 'Museum', 'Castle', 
                  'Monument', 'Historical Site', 'Pass'
              )
        """))
        print(f"  Deleted {res3.rowcount} bare unverified OSM nodes.")

        # 4. Cleanup any orphan embeddings (if any)
        print("\n[STEP 4] Ensuring embeddings index is perfectly synchronized...")
        res4 = db.execute(text("""
            DELETE FROM embeddings 
            WHERE place_id NOT IN (SELECT id FROM places)
        """))
        print(f"  Removed {res4.rowcount} orphan embeddings.")

        # Commit transaction
        db.commit()
        print("\n[SUCCESS] Deletions committed successfully to PostgreSQL!")

        # Final counts
        final_places = db.execute(text("SELECT count(*) FROM places")).scalar()
        final_embeddings = db.execute(text("SELECT count(*) FROM embeddings")).scalar()
        with_images = db.execute(text("SELECT count(*) FROM places WHERE image_url IS NOT NULL")).scalar()
        hidden_gems = db.execute(text("SELECT count(*) FROM places WHERE is_hidden_gem = TRUE")).scalar()

        print("\n" + "="*60)
        print("DATABASE PURGE & OPTIMIZATION COMPLETE!")
        print("="*60)
        print(f"Total Places Remaining:     {final_places} (deleted {initial_places - final_places} junk rows)")
        print(f"Total Embeddings Remaining: {final_embeddings}")
        print(f"Verified Places with Photos: {with_images}")
        print(f"Verified Hidden Gems:        {hidden_gems}")
        print("="*60)

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database cleanup failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    clean_database()
