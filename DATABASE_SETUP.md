# Database Setup Guide for Windows

This guide will help you set up PostgreSQL for Yatra Sathi on Windows.

## Step 1: Install PostgreSQL

### Option A: Download from PostgreSQL Website

1. Go to https://www.postgresql.org/download/windows/
2. Download the latest PostgreSQL installer (recommended version 14 or higher)
3. Run the installer
4. During installation:
   - **Important**: Make sure to check "Include psql in PATH" or add it manually later
   - Set a password for the postgres user (remember this password!)
   - Keep default port 5432
5. Complete the installation

### Option B: Using Chocolatey (if you have it)

```powershell
choco install postgresql
```

### Option C: Using Scoop (if you have it)

```powershell
scoop install postgresql
```

## Step 2: Verify Installation

Open a new Command Prompt or PowerShell and run:

```bash
psql --version
```

You should see something like: `psql (PostgreSQL) 14.x`

## Step 3: Run Database Setup Script

Once PostgreSQL is installed, run the automated setup script:

```bash
python scripts/setup_database.py
```

This script will:
- Create the `yatra_sathi` database
- Enable PostGIS extension
- Enable pgvector extension
- Verify the setup

## Step 4: Manual Setup (if script fails)

If the automated script doesn't work, you can set up the database manually:

### 4a. Create Database

```bash
createdb yatra_sathi
```

### 4b. Enable Extensions

```bash
psql -d yatra_sathi -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -d yatra_sathi -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 4c. Verify Extensions

```bash
psql -d yatra_sathi -c "SELECT extname FROM pg_extension WHERE extname IN ('postgis', 'vector');"
```

## Step 5: Configure Environment

1. Copy the environment template:
```bash
copy .env.example .env
```

2. Edit `.env` file and update the DATABASE_URL:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/yatra_sathi
```

Replace `YOUR_PASSWORD` with the password you set during PostgreSQL installation.

## Step 6: Test Database Connection

You can test the connection using Python:

```bash
python -c "from app.database.connection import init_database; init_database()"
```

## Troubleshooting

### "psql is not recognized"
- PostgreSQL is not in your PATH
- Solution: Add PostgreSQL bin directory to PATH or reinstall with PATH option
- Typical location: `C:\Program Files\PostgreSQL\14\bin`

### "FATAL: password authentication failed"
- Wrong password in DATABASE_URL
- Solution: Update the password in your `.env` file

### "database does not exist"
- Database wasn't created
- Solution: Run `createdb yatra_sathi`

### "could not open extension control file"
- PostGIS or pgvector not installed
- Solution: Install these extensions via Stack Builder (included with PostgreSQL)

### Installing PostGIS on Windows

1. Open Stack Builder (installed with PostgreSQL)
2. Select your PostgreSQL installation
3. Go to Spatial Extensions
4. Install PostGIS for your PostgreSQL version

### Installing pgvector on Windows

pgvector may need to be compiled from source on Windows. Alternative: use Docker or a cloud database service.

## Alternative: Use Docker (Recommended for Development)

If you have Docker installed, this is the easiest option:

```bash
docker run -d \
  --name yatra-sathi-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=yatra_sathi \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

Then update your `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yatra_sathi
```

## Alternative: Use Cloud Database

You can use a cloud PostgreSQL service like:
- Supabase (free tier available)
- Neon (free tier available)
- Railway
- AWS RDS

These services usually have PostGIS and pgvector pre-configured.

## Next Steps

Once the database is set up:

1. Run the ETL pipeline:
```bash
python scripts/run_pipeline.py
```

2. Start the API server:
```bash
uvicorn app.api.main:app --reload
```
