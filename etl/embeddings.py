"""
Embeddings stage — generates sentence-transformer vectors and upserts them
into the ``embeddings`` table in pgvector.

Two pipelines are provided:

* ``EmbeddingPipeline``   — reads places already in the DB (safe default).
* ``DBEmbeddingPipeline`` — same, accepts an optional subset of place IDs.

Both delegate to the shared ``_store_batch`` helper so they produce
byte-identical vectors.

Additional exports used by the runtime service:
* ``EmbeddingGenerator``     — text composition + encoding
* ``upsert_place_embedding`` — single-place upsert helper
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from tqdm import tqdm

from etl.config import EMBEDDING_MODEL
from etl.embedding_helpers import EmbeddingTextHelpers
from backend.app.db.database import SessionLocal, engine
from backend.app.models.embedding import Embedding as EmbeddingDB
from backend.app.models.place import Place as PlaceDB


# ─────────────────────────────────────────────────────────────────────────────
# Ensure pgvector extension + type adapter are ready before any DB writes
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_vector_ready() -> None:
    """Create the pgvector extension and register the type adapter."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception as e:
        print(f"[embeddings] pgvector extension warning: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Embedding generator  (shared — ETL + runtime service)
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingGenerator:
    """Wraps a SentenceTransformer model with place-aware text composition."""

    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        print(f"[embeddings] Loading model: {model_name}")
        self.model      = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimensions = self.model.get_sentence_embedding_dimension()
        print(f"[embeddings] Model ready — {self.dimensions}d vectors")

    # ------------------------------------------------------------------
    # Text composition
    # ------------------------------------------------------------------

    def create_embedding_text(self, place: Any) -> str:
        """Build the embedding sentence for a place (DB row or ETL dataclass)."""
        rt = getattr(place, "raw_tags", None) or {}

        def getter(attr: str, default: Any) -> Any:
            v = getattr(place, attr, default)
            return default if v is None else v

        synthetic = EmbeddingTextHelpers.build_synthetic_structured_sentence(
            place=place,
            raw_tags=rt,
            place_fields_getter=getter,
        )
        return EmbeddingTextHelpers.compose_embedding_text(
            wikidata_description=rt.get("wikidata_description"),
            wikipedia_extract=rt.get("wikipedia_extract"),
            synthetic_sentence=synthetic,
        )

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def generate_embeddings_batch(
        self,
        places: list[Any],
    ) -> tuple[list[str], list[np.ndarray]]:
        texts = [self.create_embedding_text(p) for p in places]
        vecs  = self.model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False,
        )
        return texts, list(vecs)

    def generate_single_embedding(self, place: Any) -> tuple[str, list[float]]:
        text = self.create_embedding_text(place)
        vec  = self.model.encode(
            text, convert_to_numpy=True, show_progress_bar=False,
        )
        return text, vec.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Shared batch upsert
# ─────────────────────────────────────────────────────────────────────────────

def _store_batch(
    generator: EmbeddingGenerator,
    places:    list[Any],
    texts:     list[str],
    vecs:      list[np.ndarray],
    session:   Any,
    stats:     dict[str, int],
) -> int:
    """Upsert one batch of embeddings. Returns the number of rows stored."""
    stored = 0
    try:
        # Collect valid UUIDs
        place_ids: list[UUID] = []
        for p in places:
            try:
                place_ids.append(UUID(str(p.id)))
            except (ValueError, AttributeError):
                stats["failed"] = stats.get("failed", 0) + 1

        if not place_ids:
            return 0

        # Places that actually exist in the DB (guard against stale JSONL ids)
        existing_place_ids: set[UUID] = {
            r[0]
            for r in session.query(PlaceDB.id).filter(PlaceDB.id.in_(place_ids)).all()
        }

        # Existing embeddings for this batch (for upsert logic)
        existing_embs: dict[UUID, EmbeddingDB] = {
            r.place_id: r
            for r in session.query(EmbeddingDB).filter(
                EmbeddingDB.place_id.in_(place_ids),
                EmbeddingDB.model_name == generator.model_name,
            ).all()
        }

        for place, emb_text, vec, pid in zip(places, texts, vecs, place_ids):
            if pid not in existing_place_ids:
                stats["failed"] = stats.get("failed", 0) + 1
                continue

            # pgvector accepts a plain Python list of floats
            vec_list: list[float] = vec.tolist()

            if pid in existing_embs:
                row = existing_embs[pid]
                row.embedding_text = emb_text
                row.dimensions     = generator.dimensions
                row.vector         = vec_list
            else:
                row = EmbeddingDB(
                    place_id       = pid,
                    model_name     = generator.model_name,
                    model_version  = "1.0",
                    embedding_text = emb_text,
                    dimensions     = generator.dimensions,
                    vector         = vec_list,
                )
                session.add(row)
            stored += 1

        session.commit()
        return stored

    except Exception as e:
        session.rollback()
        print(f"[embeddings] batch store error: {e}")
        stats["failed"] = stats.get("failed", 0) + len(places)
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Base pipeline
# ─────────────────────────────────────────────────────────────────────────────

class _BaseEmbeddingPipeline:

    def __init__(self, model_name: str, batch_size: int) -> None:
        self.batch_size = batch_size
        self.generator  = EmbeddingGenerator(model_name)
        self.stats: dict[str, int] = {
            "total": 0, "generated": 0, "stored": 0, "failed": 0,
        }

    def _process_all(
        self,
        places:  list[Any],
        session: Any,
        desc:    str,
    ) -> None:
        for i in tqdm(range(0, len(places), self.batch_size), desc=desc):
            batch = places[i : i + self.batch_size]
            texts, vecs = self.generator.generate_embeddings_batch(batch)
            self.stats["generated"] += len(vecs)
            stored = _store_batch(
                self.generator, batch, texts, vecs, session, self.stats,
            )
            self.stats["stored"] += stored

    def print_summary(self) -> None:
        print("\nEmbeddings complete:")
        print(f"  Total:     {self.stats['total']:,}")
        print(f"  Generated: {self.stats['generated']:,}")
        print(f"  Stored:    {self.stats['stored']:,}")
        print(f"  Failed:    {self.stats['failed']:,}")
        print(f"  Model:     {self.generator.model_name}  ({self.generator.dimensions}d)")


# ─────────────────────────────────────────────────────────────────────────────
# Main ETL pipeline  (DB places → DB embeddings)
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingPipeline(_BaseEmbeddingPipeline):
    """
    Reads every place already loaded into the ``places`` table and upserts
    a matching row into the ``embeddings`` table.

    Running the ``load`` stage first is a hard prerequisite — places must
    exist in the DB before embeddings can reference them via the foreign key.
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        batch_size: int = 64,
    ) -> None:
        super().__init__(model_name, batch_size)

    def run(self) -> dict[str, int]:
        _ensure_vector_ready()

        session = SessionLocal()
        try:
            total = session.query(PlaceDB).count()
            if total == 0:
                print(
                    "[embeddings] No places found in DB. "
                    "Run the 'load' stage first: python -m etl.orchestrator --stage load"
                )
                return dict(self.stats)

            pre_count = session.query(EmbeddingDB).count()
            print(f"[embeddings] DB places: {total:,}  |  existing embeddings: {pre_count:,}")

            places = session.query(PlaceDB).all()
            self.stats["total"] = len(places)

            self._process_all(places, session, "Embeddings")

            post_count = session.query(EmbeddingDB).count()
            print(f"[embeddings] Embeddings after run: {post_count:,}  (+{post_count - pre_count:,} new)")

        finally:
            session.close()

        self.print_summary()
        return dict(self.stats)


# ─────────────────────────────────────────────────────────────────────────────
# DB → DB backfill / regeneration pipeline
# ─────────────────────────────────────────────────────────────────────────────

class DBEmbeddingPipeline(_BaseEmbeddingPipeline):
    """
    Regenerate embeddings for all (or a subset of) DB places.
    Useful for re-embedding after a model upgrade without re-running the full ETL.
    """

    def __init__(
        self,
        model_name: str                     = EMBEDDING_MODEL,
        batch_size: int                     = 64,
        place_ids:  list[UUID | str] | None = None,
    ) -> None:
        super().__init__(model_name, batch_size)
        self._place_ids = place_ids

    def run(self, session: Any = None) -> dict[str, int]:
        _ensure_vector_ready()

        close = session is None
        if session is None:
            session = SessionLocal()

        try:
            q = session.query(PlaceDB)
            if self._place_ids:
                uuids = [UUID(str(p)) for p in self._place_ids]
                q = q.filter(PlaceDB.id.in_(uuids))

            places = q.all()
            self.stats["total"] = len(places)

            if not places:
                print("[embeddings] No places found in DB.")
                return dict(self.stats)

            print(f"[embeddings] Regenerating embeddings for {len(places):,} places...")
            self._process_all(places, session, "DB Embeddings")

        finally:
            if close:
                session.close()

        self.print_summary()
        return dict(self.stats)


# ─────────────────────────────────────────────────────────────────────────────
# Single-place upsert  (used by the runtime API service)
# ─────────────────────────────────────────────────────────────────────────────

def upsert_place_embedding(
    generator: EmbeddingGenerator,
    place:     Any,
    session:   Any,
    commit:    bool = True,
) -> EmbeddingDB | None:
    """Generate and upsert the embedding for a single DB place row."""
    try:
        pid = UUID(str(place.id))
    except (ValueError, AttributeError):
        return None

    # Guard: place must be in DB
    if not session.query(PlaceDB.id).filter(PlaceDB.id == pid).first():
        return None

    text, vec = generator.generate_single_embedding(place)

    existing = session.query(EmbeddingDB).filter(
        EmbeddingDB.place_id   == pid,
        EmbeddingDB.model_name == generator.model_name,
    ).first()

    if existing:
        existing.embedding_text = text
        existing.dimensions     = generator.dimensions
        existing.vector         = vec  # plain list[float] — pgvector handles it
        row = existing
    else:
        row = EmbeddingDB(
            place_id       = pid,
            model_name     = generator.model_name,
            model_version  = "1.0",
            embedding_text = text,
            dimensions     = generator.dimensions,
            vector         = vec,
        )
        session.add(row)

    if commit:
        session.commit()
    return row


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    EmbeddingPipeline().run()


if __name__ == "__main__":
    main()
