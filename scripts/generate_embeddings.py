"""
Generate embeddings for all places already in the database.

Delegates 100% of the work to :class:`etl.embeddings.DBEmbeddingPipeline` so
the output is byte-identical to embeddings produced during the main ETL
pipeline (same text format, same model, same batch-upsert semantics).

Usage:
    python scripts/generate_embeddings.py
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from tqdm import tqdm  # noqa: F401  (re-exported so dependencies still import-clean)

# Ensure both project root and backend/ are on sys.path so ETL + backend imports
# resolve the same way they do during the main pipeline run.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
for _p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Absolute imports from backend.app (per project conventions).
from backend.app.db.database import SessionLocal  # noqa: E402
from backend.app.models.place import Place as PlaceDB  # noqa: E402
from etl.embeddings import DBEmbeddingPipeline  # noqa: E402


def main() -> None:
    """Generate embeddings for every place already in the database."""
    print("=" * 70)
    print("Generating Embeddings for All Places (ETL-consistent pipeline)")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    session = SessionLocal()
    try:
        place_count = session.query(PlaceDB).count()
    finally:
        session.close()

    print(f"\n[INFO] Total places in database: {place_count}")

    if place_count == 0:
        print("[ERROR] No places found in database. Please run ETL pipeline first.")
        sys.exit(1)

    # Configuration
    batch_size = 128
    model_name = "all-MiniLM-L6-v2"
    print(f"[CONFIG] Batch size: {batch_size}")
    print(f"[CONFIG] Model:      {model_name}")

    start_time = time.time()

    # Entirely delegate to the ETL pipeline — one source of truth.
    pipeline = DBEmbeddingPipeline(
        model_name=model_name,
        batch_size=batch_size,
    )
    stats = pipeline.run()

    elapsed_time = time.time() - start_time
    rate = stats["total_places"] / elapsed_time if elapsed_time > 0 else 0

    print("\n" + "=" * 70)
    print("Embedding Generation Complete")
    print("=" * 70)
    print(f"Total places:         {stats['total_places']}")
    print(f"Embeddings generated: {stats['embeddings_generated']}")
    print(f"Embeddings stored:    {stats['embeddings_stored']}")
    print(f"Failed:               {stats['failed']}")
    print(f"Model:                {model_name}")
    print(f"Time elapsed:         {elapsed_time:.2f} seconds")
    print(f"Average rate:         {rate:.2f} places/sec")
    print(f"Finished at:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
