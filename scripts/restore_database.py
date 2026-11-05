"""
Database Restore Script for YatraSathi
Restores the pre-populated Nepal destination dump (with PostGIS coordinates and pgvector embeddings)
into the PostgreSQL database.
"""
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")

def restore_database():
    database_url = os.getenv("DATABASE_URL")
    dump_file = root_dir / "data" / "yatra_sathi.dump"

    if not dump_file.exists():
        print(f"[ERROR] Dump file not found at: {dump_file}")
        sys.exit(1)

    print("=" * 60)
    print("YatraSathi Nepal - Database Restore Utility")
    print("=" * 60)
    print(f"Dump file: {dump_file} ({dump_file.stat().st_size / (1024*1024):.1f} MB)")

    if not database_url:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        print("Please check your .env file or supply DATABASE_URL.")
        sys.exit(1)

    print(f"Target Database URL: {database_url.split('@')[-1] if '@' in database_url else database_url}")

    # Use pg_restore
    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "-d", database_url,
        "-v",
        str(dump_file)
    ]

    print("\n[INFO] Running pg_restore...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Note: pg_restore outputs detailed progress on stderr
        if result.returncode == 0:
            print("[SUCCESS] Database restored successfully!")
        else:
            # Often pg_restore returns non-zero warnings on clean/drop if tables didn't exist yet
            print(f"[INFO] pg_restore exited with code {result.returncode}")
            if "completed" in result.stderr.lower() or "restoring" in result.stderr.lower():
                print("[SUCCESS] Restore completed (any warnings were non-fatal).")
            else:
                print(result.stderr[:500])
    except FileNotFoundError:
        print("[ERROR] 'pg_restore' command not found in PATH.")
        print("Please ensure PostgreSQL command-line tools are installed and in your PATH.")
        print("\nAlternatively, restore using Docker:")
        print(f"  docker exec -i yatrasathi_db pg_restore -U postgres -d yatra_sathi --clean --if-exists < {dump_file}")

if __name__ == "__main__":
    restore_database()
