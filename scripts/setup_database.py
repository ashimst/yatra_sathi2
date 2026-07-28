"""
Database setup script for Yatra Sathi.

This script helps set up the PostgreSQL database with required extensions.
It supports reading connection parameters from environment variables or
prompting interactively.
"""

import os
import subprocess
import sys
import getpass
from pathlib import Path


# PostgreSQL installation paths to check (common on Windows)
POSTGRES_PATHS = [
    r"C:\Program Files\PostgreSQL\18\bin",
    r"C:\Program Files\PostgreSQL\17\bin",
    r"C:\Program Files\PostgreSQL\16\bin",
    r"C:\Program Files\PostgreSQL\15\bin",
    r"C:\Program Files\PostgreSQL\14\bin",
]


def find_postgres_bin():
    """Find PostgreSQL bin directory on Windows."""
    for path in POSTGRES_PATHS:
        if Path(path).exists():
            psql_path = Path(path) / "psql.exe"
            if psql_path.exists():
                return path
    return None


def check_postgresql_installed():
    """Check if PostgreSQL is installed and accessible."""
    postgres_bin = find_postgres_bin()

    if postgres_bin:
        psql_path = Path(postgres_bin) / "psql.exe"
        try:
            result = subprocess.run(
                [str(psql_path), "--version"],
                capture_output=True,
                text=True,
            )
            print(f"[OK] PostgreSQL found: {result.stdout.strip()}")
            print(f"[INFO] Using PostgreSQL from: {postgres_bin}")
            return postgres_bin
        except FileNotFoundError:
            print("[ERROR] PostgreSQL (psql) not found")
            return None
    else:
        print("[ERROR] PostgreSQL not found in common installation paths")
        return None


def get_connection_params():
    """
    Get PostgreSQL connection parameters from environment or prompt.
    Returns (user, password, host, port).
    """
    # Check environment variables first
    user = os.environ.get("PGUSER") or os.environ.get("POSTGRES_USER")
    password = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("PGHOST") or os.environ.get("POSTGRES_HOST") or "localhost"
    port = os.environ.get("PGPORT") or os.environ.get("POSTGRES_PORT") or "5432"

    if not user:
        user = input("PostgreSQL username [postgres]: ").strip()
        if not user:
            user = "postgres"

    if not password:
        password = getpass.getpass(f"Password for user {user} (press Enter if none): ")
        # If password is empty, we'll assume trust authentication

    return user, password, host, port


def create_database(postgres_bin, user, password, host, port):
    """Create the yatra_sathi database."""
    print("\n[INFO] Creating database 'yatra_sathi'...")

    createdb_path = Path(postgres_bin) / "createdb.exe"

    # Set up environment with PGPASSWORD if provided
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    cmd = [
        str(createdb_path),
        "-U", user,
        "-h", host,
        "-p", port,
        "yatra_sathi",
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode == 0:
        print("[OK] Database 'yatra_sathi' created successfully")
        return True

    if "already exists" in result.stderr.lower():
        print("[INFO] Database 'yatra_sathi' already exists")
        return True

    print(f"[ERROR] Failed to create database: {result.stderr}")
    return False


def enable_extensions(postgres_bin, user, password, host, port):
    """Enable PostGIS and pgvector extensions."""
    print("\n[INFO] Enabling extensions...")

    psql_path = Path(postgres_bin) / "psql.exe"

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    sql_commands = [
        "CREATE EXTENSION IF NOT EXISTS postgis;",
        "CREATE EXTENSION IF NOT EXISTS vector;",
    ]

    for cmd in sql_commands:
        result = subprocess.run(
            [
                str(psql_path),
                "-U", user,
                "-h", host,
                "-p", port,
                "-d", "yatra_sathi",
                "-c", cmd,
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"[ERROR] Failed to enable extension: {cmd}")
            print(result.stderr)
            return False

        print(f"[OK] Extension enabled: {cmd.strip()}")

    return True


def verify_setup(postgres_bin, user, password, host, port):
    """Verify that the required extensions are installed."""
    print("\n[INFO] Verifying setup...")

    psql_path = Path(postgres_bin) / "psql.exe"

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    result = subprocess.run(
        [
            str(psql_path),
            "-U", user,
            "-h", host,
            "-p", port,
            "-d", "yatra_sathi",
            "-c",
            "SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'vector');",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("[OK] Extensions verified:")
        print(result.stdout)
        return True

    print(f"[ERROR] Verification failed: {result.stderr}")
    return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("Yatra Sathi Database Setup")
    print("=" * 60)

    # Check PostgreSQL installation
    postgres_bin = check_postgresql_installed()
    if not postgres_bin:
        print("\n" + "=" * 60)
        print("PostgreSQL is not installed or not in PATH")
        print("=" * 60)
        print("\nTo install PostgreSQL on Windows:")
        print("1. Download from: https://www.postgresql.org/download/windows/")
        print("2. Run the installer")
        print("3. Make sure to include psql in your PATH")
        print("4. Restart your terminal/command prompt")
        print("\nAfter installation, run this script again.")
        return

    # Get connection parameters
    user, password, host, port = get_connection_params()

    # Create database
    if not create_database(postgres_bin, user, password, host, port):
        print("\n[ERROR] Database setup failed at database creation")
        return

    # Enable extensions
    if not enable_extensions(postgres_bin, user, password, host, port):
        print("\n[ERROR] Database setup failed at extension setup")
        return

    # Verify setup
    if not verify_setup(postgres_bin, user, password, host, port):
        print("\n[ERROR] Database setup verification failed")
        return

    print("\n" + "=" * 60)
    print("[OK] Database setup completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Copy .env.example to .env")
    print("2. Update DATABASE_URL in .env")
    print("3. Run the ETL pipeline: python scripts/run_pipeline.py")
    print("4. Start the API server: uvicorn app.api.main:app --reload")


if __name__ == "__main__":
    main()