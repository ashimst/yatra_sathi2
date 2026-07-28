"""
Debug script to test embedding generation for a single place.

Uses the runtime EmbeddingService facade, which internally delegates to the
shared ETL embedding logic — so the text + vector produced here is byte-identical
to those stored during the main ETL pipeline.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
for _p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.app.services.embedding_service import embedding_service  # noqa: E402
from backend.app.db.database import SessionLocal  # noqa: E402
from backend.app.models.place import Place as PlaceDB  # noqa: E402


def main() -> None:
    print("=" * 70)
    print("Testing Single Place Embedding Generation (ETL-consistent)")
    print("=" * 70)

    session = SessionLocal()
    try:
        place = session.query(PlaceDB).first()
        if not place:
            print("[ERROR] No places found in database")
            return

        print(f"\n[INFO] Testing place: {place.name}")
        print(f"[INFO] Category:     {place.category}")
        print(f"[INFO] ID:           {place.id}")

        # 1) Text generation (uses ETL shared helpers via service facade)
        print("\n[INFO] Generating embedding text...")
        try:
            embedding_text = embedding_service.create_embedding_text(place)
            print(f"[OK] Generated text (length: {len(embedding_text)})")
            try:
                safe_text = embedding_text.encode("utf-8", errors="replace").decode("utf-8")
                print("---")
                print(safe_text[:500] + ("..." if len(safe_text) > 500 else ""))
                print("---")
            except Exception:
                print("[INFO] Text contains special characters, skipping display")
        except Exception as e:
            print(f"[ERROR] Failed to generate text: {e}")
            import traceback
            traceback.print_exc()
            return

        # 2) Model loading + embedding
        print("\n[INFO] Generating embedding vector...")
        try:
            embedding_service.load_model()
            vector = embedding_service.generate_embedding(embedding_text)
            print(f"[OK] Generated embedding (dimensions: {len(vector)})")
            print(f"[OK] Sample values: {vector[:5]}")
        except Exception as e:
            print(f"[ERROR] Failed to generate embedding: {e}")
            import traceback
            traceback.print_exc()
            return

        # 3) Storage (via the shared ETL upsert helper)
        print("\n[INFO] Testing storage via service.upsert_for_place...")
        try:
            stored = embedding_service.upsert_for_place(place, session, commit=True)
            if stored is None:
                print("[ERROR] upsert_for_place returned None (place may not exist in DB)")
            else:
                print(f"[OK] Stored embedding successfully")
                print(f"[OK] Embedding ID: {stored.id}")
        except Exception as e:
            print(f"[ERROR] Failed to store embedding: {e}")
            import traceback
            traceback.print_exc()
            return

        print("\n" + "=" * 70)
        print("[OK] All tests passed!")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()
