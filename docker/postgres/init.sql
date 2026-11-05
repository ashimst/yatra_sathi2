-- YatraSathi Database Initialization Script
-- Automatically run when the PostgreSQL container is first initialized

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- Ensure schema permissions
GRANT ALL PRIVILEGES ON DATABASE yatra_sathi TO postgres;
