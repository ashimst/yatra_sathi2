"""
ETL Pipeline Orchestrator for Yatra Sathi.

DAG-style execution with checkpoint tracking, step timing, failure recovery,
and a clean CLI for running individual stages or the full end-to-end pipeline.

All stage modules live in etl/ and are imported directly — no phantom
`pipeline` package reference.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from etl.config import CHECKPOINT_FILE


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class PipelineOrchestrator:
    """DAG Pipeline Orchestrator with timing, logging, and resumption."""

    STAGES = [
        "extract",      # OSM PBF → extracted/places.jsonl  (nodes only)
        "normalize",    # extracted → normalized/places.jsonl  (validate + normalise merged)
        "enrich",       # normalized → enriched/places.jsonl   (Wikidata / Wikipedia)
        "deduplicate",  # enriched  → curated/places.jsonl     (spatial dedup)
        "semantic",     # curated   → curated/semantic_places.jsonl
        "embeddings",   # semantic_places.jsonl → DB embeddings table
        "load",         # curated/semantic_places.jsonl → DB places table
    ]

    def __init__(self) -> None:
        self.checkpoints: dict[str, Any] = self._load_checkpoints()

    def _load_checkpoints(self) -> dict[str, Any]:
        if CHECKPOINT_FILE.exists():
            try:
                with open(CHECKPOINT_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_checkpoint(self, stage: str, status: str, duration: float) -> None:
        self.checkpoints[stage] = {
            "status":           status,
            "duration_seconds": round(duration, 2),
            "completed_at":     datetime.now(UTC).isoformat(),
        }
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(self.checkpoints, f, indent=2)

    # ── Stage dispatch ────────────────────────────────────────────────────────

    def run_stage(self, stage_name: str) -> float:
        """Run a single named pipeline stage and return its wall-clock duration."""
        print(f"\n{'=' * 70}")
        print(f"[START] {stage_name.upper()}")
        print(f"{'=' * 70}")
        start = time.time()

        try:
            if stage_name == "extract":
                from etl import extract_osm
                extract_osm.main()
            elif stage_name == "normalize":
                from etl import normalize
                normalize.main()
            elif stage_name == "enrich":
                from etl import enrich
                enrich.main()
            elif stage_name == "deduplicate":
                from etl import deduplicate
                deduplicate.main()
            elif stage_name == "semantic":
                from etl import semantic
                semantic.main()
            elif stage_name == "embeddings":
                from etl import embeddings
                embeddings.main()
            elif stage_name == "load":
                from etl import load
                load.main()
            else:
                raise ValueError(f"Unknown stage: {stage_name!r}  (valid: {self.STAGES})")

            duration = time.time() - start
            self._save_checkpoint(stage_name, "SUCCESS", duration)
            print(f"[OK] {stage_name.upper()} completed in {duration:.2f}s")
            return duration

        except Exception as e:
            duration = time.time() - start
            self._save_checkpoint(stage_name, f"FAILED: {e}", duration)
            print(f"[ERROR] {stage_name.upper()} failed in {duration:.2f}s: {e}")
            raise

    # ── Full pipeline ─────────────────────────────────────────────────────────

    def run_pipeline(
        self,
        start_stage: str | None = None,
        skip_stages: set[str] | None = None,
    ) -> None:
        skip = skip_stages or set()
        start_idx = 0
        if start_stage:
            if start_stage not in self.STAGES:
                raise ValueError(
                    f"Invalid start stage: {start_stage!r}  (valid: {self.STAGES})"
                )
            start_idx = self.STAGES.index(start_stage)

        total_start = time.time()
        executed: list[tuple[str, float]] = []

        print("\n" + "=" * 70)
        print("  YATRA SATHI ETL PIPELINE")
        print("=" * 70)

        for stage in self.STAGES[start_idx:]:
            if stage in skip:
                print(f"[SKIP] {stage}")
                continue
            duration = self.run_stage(stage)
            executed.append((stage, duration))

        total = time.time() - total_start
        print("\n" + "=" * 70)
        print(f"  PIPELINE COMPLETE  ({total:.2f}s)")
        print("=" * 70)
        for stage, dur in executed:
            print(f"  {stage:<15} {dur:>8.2f}s")
        print("=" * 70 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Yatra Sathi ETL Pipeline Orchestrator"
    )
    parser.add_argument(
        "--stage",
        choices=PipelineOrchestrator.STAGES,
        help="Run exactly one stage",
    )
    parser.add_argument(
        "--from-stage",
        choices=PipelineOrchestrator.STAGES,
        help="Run from this stage through to the end",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        choices=PipelineOrchestrator.STAGES,
        help="Stages to skip",
    )

    args = parser.parse_args()
    orch = PipelineOrchestrator()

    if args.stage:
        orch.run_stage(args.stage)
    else:
        skip_set = set(args.skip) if args.skip else set()
        orch.run_pipeline(start_stage=args.from_stage, skip_stages=skip_set)


if __name__ == "__main__":
    main()
