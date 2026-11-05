"""
Database connection and session management.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from backend.app.config.settings import settings

# Register SQLite compiler hooks for PostgreSQL specific types
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


try:
    from pgvector.sqlalchemy import Vector

    @compiles(Vector, "sqlite")
    def compile_vector_sqlite(type_, compiler, **kw):
        return "BLOB"
except ImportError:
    pass


# Enforce foreign keys on SQLite connections
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.close()


# Configure engine. SQLite is only used by the legacy test suite; production
# runs on PostgreSQL (PostGIS + pgvector).
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_engine_kwargs = {"echo": settings.DEBUG}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update(
        pool_pre_ping=True,          # drop dead connections (pooler restarts, idle timeouts)
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=1800,
        connect_args={"connect_timeout": 10},
    )

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency for getting database sessions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    """
    from backend.app.models import (
        user,
        itinerary,
        session as session_model,
        place,
        memory,
        trail_watch,
        place_photo,
    )
    try:
        from backend.app.models import embedding
    except ImportError:
        pass
    Base.metadata.create_all(bind=engine)

    # Safe schema migration for pre-existing tables missing newly added columns
    try:
        from sqlalchemy import inspect as sa_inspect, text as sa_text
        inspector = sa_inspect(engine)
        if "users" in inspector.get_table_names():
            user_cols = {c["name"] for c in inspector.get_columns("users")}
            if "avatar_url" not in user_cols:
                with engine.begin() as conn:
                    conn.execute(sa_text("ALTER TABLE users ADD COLUMN avatar_url TEXT"))
    except Exception:
        pass


def init_database():
    """
    Initialize database tables (alias for init_db for ETL compatibility).
    """
    init_db()


def create_tables():
    """
    Create database tables (alias for init_db for ETL compatibility).
    """
    init_db()
