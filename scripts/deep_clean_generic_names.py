import os
import sys

sys.path.insert(0, os.path.abspath("."))
from backend.app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    generic_words = [
        'tree', 'pond', 'spring', 'toilet', 'drinking water', 'water tap',
        'atm', 'bus station', 'petrol pump', 'fuel station', 'bench', 'shop',
        'house', 'building', 'wall', 'gate', 'entrance', 'bridge', 'stream',
        'river', 'field', 'playground', 'rubbish', 'waste', 'bin', 'chautara',
        'chautari', 'school', 'college', 'ward office', 'health post', 'hospital',
        'pharmacy', 'clinic', 'shed', 'shelter', 'view point', 'viewpoint',
        'stupa', 'temple', 'church', 'mosque', 'masjid', 'gompa', 'monastery',
        'hotel', 'restaurant', 'cafe', 'lodge', 'khaja ghar', 'tea stall'
    ]

    res = db.execute(text("""
        DELETE FROM places
        WHERE lower(trim(name)) IN :words
    """), {"words": tuple(generic_words)})

    print(f"Purged {res.rowcount} generic single-word places (like 'Tree', 'Pond', etc.)")

    # Also clean up any place that has no description, no image, no rating, no contact info,
    # and has a name like 'Hotel', 'Lodge', 'Restaurant' embedded without brand
    res2 = db.execute(text("""
        DELETE FROM places
        WHERE image_url IS NULL
          AND rating IS NULL
          AND (popularity IS NULL OR popularity = 0)
          AND is_hidden_gem IS NOT TRUE
          AND (raw_tags->>'website') IS NULL
          AND (raw_tags->>'phone') IS NULL
          AND (raw_tags->>'contact:phone') IS NULL
          AND (raw_tags->>'description') IS NULL
          AND (raw_tags->>'wikipedia') IS NULL
          AND (raw_tags->>'wikidata') IS NULL
          AND lower(trim(name)) ~ '^(hotel|lodge|restaurant|cafe|guest house|resort|bhojanalaya|khaja ghar|tea shop|cold store|fast food)$'
    """))
    print(f"Purged {res2.rowcount} generic unbranded food/lodging entries.")

    db.commit()
    
    count = db.execute(text("SELECT count(*) FROM places")).scalar()
    print(f"Final places in database: {count}")
finally:
    db.close()
