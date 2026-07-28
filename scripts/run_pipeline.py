"""
Pipeline runner for executing the complete ETL pipeline.

This script runs all stages of the data pipeline in sequence:
1. Extract OSM data
2. Validate extracted data
3. Normalize categories
4. Enrich with Wikidata
5. Deduplicate records
6. Generate semantic metadata
7. Load into database
8. Generate embeddings
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(stage_name: str, script_path: Path) -> bool:
    """Run a pipeline stage script."""
    print(f"\n{'='*60}")
    print(f"Running stage: {stage_name}")
    print(f"{'='*60}\n")

    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + os.pathsep + str(backend_dir)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=project_root,
        env=env,
    )

    if result.returncode != 0:
        print(f"\n[ERROR] Stage '{stage_name}' failed with exit code {result.returncode}")
        return False

    print(f"\n[OK] Stage '{stage_name}' completed successfully")
    return True


def main():
    """Run the complete ETL pipeline."""

    parser = argparse.ArgumentParser(
        description="Run the Yatra Sathi ETL pipeline"
    )
    parser.add_argument(
        "--start-at",
        type=str,
        choices=[
            "extract",
            "validate",
            "normalize",
            "enrich",
            "deduplicate",
            "semantic",
            "load",
            "embeddings",
        ],
        default="extract",
        help="Stage to start from (default: extract)",
    )
    parser.add_argument(
        "--stop-at",
        type=str,
        choices=[
            "extract",
            "validate",
            "normalize",
            "enrich",
            "deduplicate",
            "semantic",
            "load",
            "embeddings",
        ],
        default="embeddings",
        help="Stage to stop at (default: embeddings)",
    )
    parser.add_argument(
        "--skip",
        type=str,
        nargs="+",
        choices=[
            "extract",
            "validate",
            "normalize",
            "enrich",
            "deduplicate",
            "semantic",
            "load",
            "embeddings",
        ],
        help="Stages to skip",
    )

    args = parser.parse_args()

    # Define pipeline stages
    stages = [
        ("extract", Path("etl/extract_osm.py")),
        ("validate", Path("etl/validate.py")),
        ("normalize", Path("etl/normalize.py")),
        ("enrich", Path("etl/enrich.py")),
        ("deduplicate", Path("etl/deduplicate.py")),
        ("semantic", Path("etl/semantic.py")),
        ("load", Path("etl/load.py")),
        ("embeddings", Path("etl/embeddings.py")),
    ]

    stage_names = [s[0] for s in stages]

    # Validate arguments
    start_idx = stage_names.index(args.start_at)
    stop_idx = stage_names.index(args.stop_at)

    if start_idx > stop_idx:
        print("Error: --start-at must come before --stop-at")
        sys.exit(1)

    # Filter stages to run
    stages_to_run = []
    skip_set = set(args.skip) if args.skip else set()

    for i, (name, path) in enumerate(stages):
        if i < start_idx or i > stop_idx:
            continue
        if name in skip_set:
            print(f"[SKIP] Skipping stage: {name}")
            continue
        stages_to_run.append((name, path))

    print(f"\n[START] Starting Yatra Sathi ETL Pipeline")
    print(f"Stages to run: {[s[0] for s in stages_to_run]}")
    print(f"Total stages: {len(stages_to_run)}")

    # Run stages
    failed_stage = None
    for stage_name, script_path in stages_to_run:
        if not run_command(stage_name, script_path):
            failed_stage = stage_name
            break

    # Summary
    print(f"\n{'='*60}")
    if failed_stage:
        print(f"[ERROR] Pipeline failed at stage: {failed_stage}")
        print(f"{'='*60}")
        sys.exit(1)
    else:
        print(f"[OK] Pipeline completed successfully!")
        print(f"{'='*60}")
        print(f"\n[OK] All stages completed. The database is ready.")
        print(f"\nYou can now start the API server:")
        print(f"  uvicorn app.api.main:app --reload")


if __name__ == "__main__":
    main()
