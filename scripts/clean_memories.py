import psycopg2
from backend.app.config.settings import settings

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()

# Remove junk test memories
cur.execute("DELETE FROM memories WHERE caption = 'nn' OR image_url LIKE 'data:image%' OR caption IS NULL;")
deleted = cur.rowcount
print(f"Deleted {deleted} test/garbage memories.")

# Check current memories
cur.execute("SELECT id, place_name, caption, image_url FROM memories;")
rows = cur.fetchall()
print(f"Current remaining memories: {len(rows)}")
for r in rows:
    print(r)

# If few memories, seed curated gorgeous memories
if len(rows) < 3:
    seed_memories = [
        (
            "Phewa Lake & Annapurna Reflection",
            "Morning serenity on traditional wooden doonga boats with Annapurna reflecting in the emerald water.",
            "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1200&q=80",
            28.2096, 83.9590
        ),
        (
            "Boudhanath Stupa Sunset",
            "Monks circumambulating the sacred mandala under fluttering prayer flags as butter lamps flicker at dusk.",
            "https://images.unsplash.com/photo-1582650625119-3a31f8418365?auto=format&fit=crop&w=1200&q=80",
            27.7215, 85.3620
        ),
        (
            "Bandipur Newari Townscape",
            "Walking along the stone-paved bazaar of Bandipur overlooking the mist-filled Marshyangdi river valley.",
            "https://images.unsplash.com/photo-1605640840605-14ac1855827b?auto=format&fit=crop&w=1200&q=80",
            27.9333, 84.4167
        )
    ]
    import uuid
    for place_name, caption, image_url, lat, lng in seed_memories:
        mem_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO memories (id, place_name, caption, image_url, latitude, longitude, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW());
        """, (mem_id, place_name, caption, image_url, lat, lng))
    conn.commit()
    print(f"Seeded {len(seed_memories)} authentic Nepal traveler memories.")

conn.close()
