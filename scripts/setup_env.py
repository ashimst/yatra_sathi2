"""
Environment setup script for Yatra Sathi.

Copies .env.example to .env and prompts for any missing secrets.
Run once after cloning:

    python scripts/setup_env.py
"""

import shutil
from pathlib import Path


def setup_env_file() -> None:
    """Create .env from .env.example if it does not already exist."""
    root     = Path(__file__).resolve().parent.parent
    example  = root / ".env.example"
    env_path = root / ".env"

    print("=" * 60)
    print("Yatra Sathi — Environment Setup")
    print("=" * 60)

    if not example.exists():
        print(f"[ERROR] .env.example not found at {example}")
        return

    if env_path.exists():
        print(f"[SKIP] .env already exists at {env_path}")
        print("       Delete it and re-run this script to reset.")
    else:
        shutil.copy(example, env_path)
        print(f"[OK] Created {env_path} from .env.example")

    print("\nEdit .env and set at minimum:")
    print("  DATABASE_URL     — your PostgreSQL connection string")
    print("  GROQ_API_KEY     — from https://console.groq.com")
    print("\nThen run:")
    print("  python -m etl.orchestrator --stage load")
    print("  python scripts/run_embeddings.py")
    print("  uvicorn backend.app.main:app --reload")


if __name__ == "__main__":
    setup_env_file()
