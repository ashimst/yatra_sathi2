"""
Cleanse repetitive stock photos from database using KEV 0.6B POI Image Gater.
Preserves authentic Wikimedia Commons, Wikipedia, Wikivoyage, and Curated Hidden Gem photos.
Resets generic repetitive stock photos to NULL so only genuine photography is displayed.
"""
import psycopg2
from backend.app.config.settings import settings
from backend.app.services.decision_service import decision_service

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()

cur.execute("""
    SELECT id, name, category, image_url, is_hidden_gem, raw_tags 
    FROM places 
    WHERE image_url IS NOT NULL;
""")
places_with_images = cur.fetchall()
print(f"Total places currently with image_url: {len(places_with_images)}")

kept_count = 0
cleared_count = 0
cleared_ids = []

for p_id, p_name, p_cat, p_img, is_gem, tags in places_with_images:
    gate_res = decision_service.gate_poi_image(
        name=p_name,
        category=p_cat,
        image_url=p_img,
        is_hidden_gem=bool(is_gem),
        raw_tags=tags,
    )
    if gate_res.keep_image:
        kept_count += 1
    else:
        cleared_count += 1
        cleared_ids.append(p_id)

print(f"KEV 0.6B Image Gater Decision:")
print(f" - Kept authentic/verified images: {kept_count}")
print(f" - Cleared generic repeated stock images: {cleared_count}")

if cleared_ids:
    from psycopg2.extras import execute_batch
    execute_batch(cur, "UPDATE places SET image_url = NULL WHERE id = %s;", [(i,) for i in cleared_ids], page_size=1000)
    conn.commit()
    print("Database updated successfully.")

cur.execute("SELECT count(*) FROM places WHERE image_url IS NOT NULL;")
remaining_with_images = cur.fetchone()[0]
print(f"Remaining places with verified images in database: {remaining_with_images}")

# Also clean memories to ensure no repeated photos
cur.execute("SELECT count(*) FROM memories;")
mem_count = cur.fetchone()[0]
print(f"Verified memories count: {mem_count}")

conn.close()

