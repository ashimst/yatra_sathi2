"""
Embedding service for generating and managing place embeddings.

All core logic (text generation, encoding, upsert) lives in the ETL module
``etl.embeddings`` so the runtime service, batch ETL pipeline, and standalone
scripts produce byte-identical vectors and texts.

This service is a thin facade exposing:
  * single-place operations (used by the API when saving/updating one place)
  * delegated batch operations (forwarded to :class:`DBEmbeddingPipeline`)
  * similarity search helpers (database + Python-side)
  * user-preference embedding helpers
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional
import os
import sys
from datetime import datetime

import numpy as np
from sqlalchemy.orm import Session

# Ensure both project root and backend/ are on the path so imports match ETL.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_BACKEND_DIR = os.path.join(_PROJECT_ROOT, "backend")
for _p in (_PROJECT_ROOT, _BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.app.db.database import SessionLocal
from backend.app.models.place import Place as PlaceDB
from backend.app.models.embedding import Embedding as EmbeddingDB
from etl.embeddings import EmbeddingGenerator, DBEmbeddingPipeline, upsert_place_embedding
from etl.embedding_helpers import EmbeddingTextHelpers


class EmbeddingService:
    """Facade for generating and managing place embeddings.

    Delegates 100% of text-generation + encoding + DB upsert logic to the ETL
    module (``etl.embeddings``) so the runtime service can never produce a
    different vector than the batch pipeline for the same input.
    """

    def __init__(self):
        # Lazily-loaded shared generator — populated on first `load_model()` call.
        self._generator: EmbeddingGenerator | None = None
        self.model_name = "all-MiniLM-L6-v2"
        # Fallback default for all-MiniLM-L6-v2; overwritten lazily from model.
        self.dimensions = 384

    # ------------------------------------------------------------------
    # Model / generator lifecycle
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Lazy-load the shared :class:`EmbeddingGenerator`.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._generator is None:
            self._generator = EmbeddingGenerator(self.model_name)
            self.dimensions = self._generator.dimensions

    @property
    def generator(self) -> EmbeddingGenerator:
        """Return the generator, loading it first if needed."""
        self.load_model()
        assert self._generator is not None
        return self._generator

    # ------------------------------------------------------------------
    # Text + vector generation (ETL-consistent)
    # ------------------------------------------------------------------

    def create_embedding_text(self, place: PlaceDB) -> str:
        """Return the embedding text for a place using the ETL shared logic."""
        return self.generator.create_embedding_text(place)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a free-form text string."""
        self.load_model()
        embedding = self.generator.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding.tolist()

    def generate_place_embedding(self, place: PlaceDB) -> Dict[str, Any]:
        """Generate text + vector for one place and return a persistable dict."""
        text, vec_list = self.generator.generate_single_embedding(place)
        return {
            "place_id": place.id,
            "model_name": self.model_name,
            "model_version": "1.0",
            "dimensions": self.dimensions,
            "vector": vec_list,
            "embedding_text": text,
        }

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def store_embedding(
        self,
        embedding_data: Dict[str, Any],
        session: Session,
        commit: bool = True,
    ) -> EmbeddingDB:
        """Store or update an embedding dict produced by :meth:`generate_place_embedding`.

        Exposed for API-call symmetry.  Prefer :meth:`upsert_for_place` when you
        already have the place row (it reuses ETL logic directly).
        """
        place_id = embedding_data["place_id"]
        model_name = embedding_data["model_name"]

        existing = session.query(EmbeddingDB).filter(
            EmbeddingDB.place_id == place_id,
            EmbeddingDB.model_name == model_name,
        ).first()

        if existing:
            existing.vector = embedding_data["vector"]
            existing.embedding_text = embedding_data["embedding_text"]
            existing.dimensions = embedding_data["dimensions"]
            existing.model_version = embedding_data["model_version"]
            existing.updated_at = datetime.utcnow()
            row = existing
        else:
            row = EmbeddingDB(
                place_id=place_id,
                model_name=model_name,
                model_version=embedding_data["model_version"],
                dimensions=embedding_data["dimensions"],
                vector=embedding_data["vector"],
                embedding_text=embedding_data["embedding_text"],
            )
            session.add(row)

        if commit:
            session.commit()
        return row

    def upsert_for_place(
        self,
        place: PlaceDB,
        session: Session,
        commit: bool = True,
    ) -> EmbeddingDB | None:
        """Upsert embedding for a single place row using the ETL shared helper."""
        return upsert_place_embedding(self.generator, place, session, commit=commit)

    # ------------------------------------------------------------------
    # Batch operation — delegates entirely to ETL.DBEmbeddingPipeline
    # ------------------------------------------------------------------

    def generate_embeddings_for_all_places(
        self,
        batch_size: int = 128,
    ) -> Dict[str, int]:
        """Generate embeddings for every place already in the database.

        Delegates to :class:`etl.embeddings.DBEmbeddingPipeline` so the result
        is byte-identical to running the batch ETL pipeline.
        """
        pipeline = DBEmbeddingPipeline(
            model_name=self.model_name,
            batch_size=batch_size,
        )
        stats = pipeline.run()
        return stats

    # ------------------------------------------------------------------
    # Similarity search
    # ------------------------------------------------------------------

    def find_similar_places(
        self,
        place_id: str,
        limit: int = 10,
        session: Session | None = None,
    ) -> List[PlaceDB]:
        """Find similar places using cosine similarity (Python-side compute)."""
        self.load_model()

        close_session = session is None
        if session is None:
            session = SessionLocal()
            close_session = True

        try:
            target_embedding = session.query(EmbeddingDB).filter(
                EmbeddingDB.place_id == place_id,
                EmbeddingDB.model_name == self.model_name,
            ).first()

            if not target_embedding or not target_embedding.vector:
                return []

            target_vector = np.array(target_embedding.vector)

            other_embeddings = session.query(EmbeddingDB).filter(
                EmbeddingDB.place_id != place_id,
                EmbeddingDB.model_name == self.model_name,
            ).all()

            similarities: List[Tuple[Any, float]] = []
            for emb in other_embeddings:
                if emb.vector:
                    other_vector = np.array(emb.vector)
                    norm_product = np.linalg.norm(target_vector) * np.linalg.norm(other_vector)
                    if norm_product == 0:
                        continue
                    similarity = float(np.dot(target_vector, other_vector) / norm_product)
                    similarities.append((emb.place_id, similarity))

            similarities.sort(key=lambda x: x[1], reverse=True)
            top_place_ids = [pid for pid, _ in similarities[:limit]]

            places = session.query(PlaceDB).filter(PlaceDB.id.in_(top_place_ids)).all()
            return places

        finally:
            if close_session:
                session.close()

    # ------------------------------------------------------------------
    # User preference embeddings
    # ------------------------------------------------------------------

    def create_user_preference_text(self, preferences: Dict[str, Any]) -> str:
        """Convert a user-preferences dict into natural-language text.

        The sentence structure mirrors place embedding texts so the cosine
        scores between user vectors and place vectors are meaningful.
        """
        parts: List[str] = []

        interests = preferences.get("interests", [])
        if interests:
            interest_text = ", ".join(interests)
            parts.append(f"attractions related to {interest_text}")

        budget = preferences.get("budget", "medium")
        if budget != "medium":
            parts.append(f"{budget} budget places")

        travel_style = preferences.get("travel_style", "balanced")
        if travel_style != "balanced":
            parts.append(f"suitable for {travel_style} travel pace")

        dietary = preferences.get("dietary_preferences", [])
        if dietary:
            dietary_text = " and ".join(dietary)
            parts.append(f"{dietary_text} food options")

        if preferences.get("family_friendly"):
            parts.append("family-friendly destinations")

        accessibility = preferences.get("accessibility")
        if accessibility:
            parts.append(f"accessible for {accessibility}")

        difficulty = preferences.get("difficulty")
        if difficulty:
            parts.append(f"{difficulty} difficulty activities")

        if parts:
            return ". ".join(parts) + "."
        return "tourist attractions and places of interest"

    def generate_user_embedding(self, preferences: Dict[str, Any]) -> List[float]:
        """Generate embedding vector for a user preferences dict."""
        self.load_model()
        preference_text = self.create_user_preference_text(preferences)
        embedding = self.generator.model.encode(
            preference_text, convert_to_numpy=True, show_progress_bar=False
        )
        return embedding.tolist()

    def find_places_by_user_preference(
        self,
        preferences: Dict[str, Any],
        place_ids: List[str],
        limit: int = 50,
        session: Session | None = None,
    ) -> List[Tuple[str, float]]:
        """Return ``(place_id, score)`` tuples most similar to user preferences.

        Tries database-side pgvector cosine search first (fast, indexed), then
        falls back to Python-side computation if DB search is unavailable.
        """
        self.load_model()
        user_embedding = self.generate_user_embedding(preferences)
        user_vector = np.array(user_embedding)

        close_session = session is None
        if session is None:
            session = SessionLocal()
            close_session = True

        try:
            try:
                similarities = self.find_similar_places_db(
                    user_vector,
                    place_ids=place_ids,
                    limit=limit,
                    session=session,
                    close_session=False,
                )
                if similarities:
                    print(
                        f"[DEBUG] Database-side search returned {len(similarities)} matches "
                        f"from {len(place_ids)} candidates"
                    )
                    return similarities
            except Exception as e:
                print(f"[WARNING] Database-side search failed, falling back to Python-side: {e}")

            from uuid import UUID

            try:
                uuid_place_ids = [UUID(pid) for pid in place_ids if pid]
            except ValueError as e:
                print(f"[WARNING] Invalid UUID format in place_ids: {e}")
                uuid_place_ids = []

            place_embeddings = session.query(EmbeddingDB).filter(
                EmbeddingDB.place_id.in_(uuid_place_ids),
                EmbeddingDB.model_name == self.model_name,
            ).all()

            print(f"[DEBUG] Found {len(place_embeddings)} embeddings for {len(uuid_place_ids)} place IDs")

            similarities: List[Tuple[str, float]] = []
            for emb in place_embeddings:
                if emb.vector:
                    place_vector = np.array(emb.vector)
                    norm_product = np.linalg.norm(user_vector) * np.linalg.norm(place_vector)
                    if norm_product == 0:
                        continue
                    similarity = float(np.dot(user_vector, place_vector) / norm_product)
                    similarities.append((str(emb.place_id), similarity))

            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]

        finally:
            if close_session:
                session.close()

    def find_similar_places_db(
        self,
        user_vector: np.ndarray,
        place_ids: Optional[List[str]] = None,
        limit: int = 50,
        session: Optional[Session] = None,
        close_session: bool = True,
    ) -> List[Tuple[str, float]]:
        """Database-side vector similarity search using pgvector operators."""
        from uuid import UUID

        if session is None:
            session = SessionLocal()
            close_session = True

        try:
            user_vector_list = user_vector.tolist()

            query = session.query(
                EmbeddingDB.place_id,
                (1 - EmbeddingDB.vector.cosine_distance(user_vector_list)).label("similarity"),
            ).filter(EmbeddingDB.model_name == self.model_name)

            if place_ids:
                try:
                    uuid_place_ids = [UUID(pid) for pid in place_ids if pid]
                    if uuid_place_ids:
                        query = query.filter(EmbeddingDB.place_id.in_(uuid_place_ids))
                except ValueError as e:
                    print(f"[WARNING] Invalid UUID format in place_ids for DB search: {e}")

            results = (
                query.order_by(EmbeddingDB.vector.cosine_distance(user_vector_list))
                .limit(limit)
                .all()
            )

            print(f"[DEBUG] Database-side vector search returned {len(results)} results")
            return [(str(pid), float(sim)) for pid, sim in results]

        finally:
            if close_session:
                session.close()


# Global singleton
embedding_service = EmbeddingService()
