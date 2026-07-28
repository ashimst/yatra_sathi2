"""
ETL Pipeline Configuration — single source of truth.

All file paths, directory layouts, and environment-bridged settings live here.
Every other etl/* module imports from this file only — no app.* references.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Project layout ────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent          # c:/Projects/yatra_sathi
ETL_DIR      = Path(__file__).parent                 # c:/Projects/yatra_sathi/etl
DATA_DIR     = PROJECT_ROOT / "data"

# ── Raw input ─────────────────────────────────────────────────────────────────

RAW_DIR  = DATA_DIR / "raw"
OSM_FILE = RAW_DIR / "nepal-260717.osm.pbf"

# ── Stage output files (linear: each stage reads the previous stage's output) ─

# Stage 1 — extract
EXTRACTED_DIR  = DATA_DIR / "extracted"
EXTRACTED_FILE = EXTRACTED_DIR / "places.jsonl"

# Stage 2 — normalize + validate (merged single pass)
NORMALIZED_DIR  = DATA_DIR / "normalized"
NORMALIZED_FILE = NORMALIZED_DIR / "places.jsonl"
VALIDATED_DIR   = DATA_DIR / "validated"             # validation report side-effect

# Stage 3 — enrich
ENRICHED_DIR  = DATA_DIR / "enriched"
ENRICHED_FILE = ENRICHED_DIR / "places.jsonl"

# Stage 4 — deduplicate
CURATED_DIR  = DATA_DIR / "curated"
CURATED_FILE = CURATED_DIR / "places.jsonl"          # dedup output

# Stage 5 — semantic
SEMANTIC_FILE = CURATED_DIR / "semantic_places.jsonl"

# Stage 6 — embeddings  (reads SEMANTIC_FILE, writes to DB)

# Stage 7 — load        (reads CURATED_FILE / SEMANTIC_FILE, writes to DB)

# ── Misc ──────────────────────────────────────────────────────────────────────

ENRICHMENT_CACHE = DATA_DIR / "enrichment_cache.sqlite"
CHECKPOINT_FILE  = DATA_DIR / "pipeline_checkpoint.json"

# ── Ensure all output directories exist at import time ───────────────────────

for _d in (EXTRACTED_DIR, NORMALIZED_DIR, VALIDATED_DIR,
           ENRICHED_DIR, CURATED_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Database URL (bridged from backend settings) ──────────────────────────────

try:
    from backend.app.config.settings import settings as _settings
    DATABASE_URL    = _settings.DATABASE_URL
    EMBEDDING_MODEL = _settings.EMBEDDING_MODEL
except Exception:
    DATABASE_URL    = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:1234@localhost:5432/yatra_sathi",
    )
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
