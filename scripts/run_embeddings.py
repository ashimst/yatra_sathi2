"""
Run the embeddings pipeline.

Reads every place from the ``places`` DB table, generates sentence-transformer
vectors, and upserts them into the ``embeddings`` table.

Prerequisites
-------------
1. PostgreSQL running with the pgvector extension available.
2. The ``places`` table must be populated — run the load stage first:

       python -m etl.orchestrator --stage load

Usage
-----
    # From the project root:
    python scripts/run_embeddings.py

    # Or via the orchestrator:
    python -m etl.orchestrator --stage embeddings
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path regardless of where this is invoked from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.database import SessionLocal, init_db
from backend.app.models.embedding import Embedding as EmbeddingDB
from backend.app.models.place import Place as PlaceDB
from etl.embeddings import EmbeddingPipeline


def main() -> None:
    # Ensure tables (including the vector extension) exist.
    print("[run_embeddings] Initialising database …")
    init_db()

    # Show current state before running.
    session = SessionLocal()
    try:
        place_count = session.query(PlaceDB).count()
        emb_count   = session.query(EmbeddingDB).count()
    finally:
        session.close()

    print(f"[run_embeddings] Places in DB   : {place_count:,}")
    print(f"[run_embeddings] Embeddings (pre): {emb_count:,}")

    if place_count == 0:
        print(
            "\n[run_embeddings] ERROR: No places found in the database.\n"
            "Run the load stage first:\n"
            "    python -m etl.orchestrator --stage load\n"
        )
        sys.exit(1)

    # Run the pipeline.
    stats = EmbeddingPipeline().run()

    # Show state after run.
    session = SessionLocal()
    try:
        emb_count_after = session.query(EmbeddingDB).count()
    finally:
        session.close()

    print(f"\n[run_embeddings] Embeddings (post): {emb_count_after:,}")
    print(f"[run_embeddings] Net new          : +{emb_count_after - emb_count:,}")

    if stats.get("failed", 0) > 0:
        print(
            f"\n[run_embeddings] WARNING: {stats['failed']:,} places failed — "
            "check logs above for details."
        )
        sys.exit(1)

    print("\n[run_embeddings] Done.")


if __name__ == "__main__":
    main()
