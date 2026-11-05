import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
from backend.app.db.database import SessionLocal
from backend.app.models.place import Place as PlaceDB
from backend.app.models.embedding import Embedding as EmbeddingDB
from sentence_transformers import SentenceTransformer
from etl.embedding_helpers import EmbeddingTextHelpers

print("=" * 60)
print("Generating Embeddings with BAAI/bge-small-en-v1.5")
print("=" * 60)

model_name = "BAAI/bge-small-en-v1.5"
print(f"Loading {model_name}...")
model = SentenceTransformer(model_name)
dims = model.get_sentence_embedding_dimension()
print(f"Model ready. Dimensions: {dims}")

db = SessionLocal()
try:
    # Get all places with image_url (curated places)
    places = db.query(PlaceDB).filter(PlaceDB.image_url.isnot(None)).all()
    print(f"Targeting {len(places)} curated places...")

    start_time = time.time()
    
    # Prepare texts
    texts = []
    place_ids = []
    for p in places:
        rt = p.raw_tags or {}
        # Synthetic descriptive text
        sentence = EmbeddingTextHelpers.build_synthetic_structured_sentence(
            p, rt, lambda attr, default: getattr(p, attr, default)
        )
        # Add rich notes/descriptions if present
        desc = p.raw_tags.get("description") or ""
        if p.must_try:
            desc += f" Signature experience: {p.must_try}."
        if p.price_level:
            desc += f" Price level: {p.price_level}."
        full_text = f"{sentence}. {desc}".strip()
        texts.append(full_text)
        place_ids.append(p.id)

    # Encode in batch
    print("Encoding texts in batch...")
    vectors = model.encode(texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
    
    # Upsert into embeddings table
    print("Upserting into embeddings table...")
    upserted = 0
    for pid, text_val, vec in zip(place_ids, texts, vectors):
        vec_list = vec.tolist()
        existing = db.query(EmbeddingDB).filter(EmbeddingDB.place_id == pid).first()
        if existing:
            existing.model_name = model_name
            existing.model_version = "1.5"
            existing.dimensions = dims
            existing.vector = vec_list
            existing.embedding_text = text_val
        else:
            new_emb = EmbeddingDB(
                place_id=pid,
                model_name=model_name,
                model_version="1.5",
                dimensions=dims,
                vector=vec_list,
                embedding_text=text_val
            )
            db.add(new_emb)
        upserted += 1

    db.commit()
    elapsed = time.time() - start_time
    print(f"[OK] Successfully embedded and saved {upserted} places in {elapsed:.2f}s!")
finally:
    db.close()
