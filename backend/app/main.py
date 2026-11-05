"""
YatraSathi Backend - Main FastAPI Application
Unified backend serving places, routes, AI assistant, authentication, and itineraries.
"""
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.app.api import (
    ai_router,
    auth_router,
    itineraries_router,
    memories_router,
    places_router,
    recommend_router,
    route_router,
    trail_watch_router,
    uploads,
)
from backend.app.config.settings import settings
from backend.app.core.rate_limit import rate_limit
from backend.app.db.database import engine, init_db
from backend.app.services.place_service import place_service

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("yatrasathi")

UPLOAD_CATEGORIES = ["memories", "places", "avatars", "trail_reports"]

# Request body caps (bytes). Multipart uploads get the upload limit plus
# headroom for form fields; everything else is JSON and kept small.
MAX_JSON_BODY_BYTES = 1 * 1024 * 1024
MAX_MULTIPART_BODY_BYTES = settings.MAX_UPLOAD_SIZE_BYTES + 256 * 1024


def _ensure_upload_dirs() -> Path:
    upload_path = Path(settings.UPLOAD_DIR)
    for category in UPLOAD_CATEGORIES:
        (upload_path / category).mkdir(parents=True, exist_ok=True)
    return upload_path


# Cached place count for the public /telemetry endpoint so it doesn't run a
# COUNT(*) on every page load.
_PLACE_COUNT_TTL_SECONDS = 600
_place_count_cache = {"value": None, "at": 0.0}


def _cached_place_count() -> int | None:
    now = time.monotonic()
    if _place_count_cache["value"] is None or now - _place_count_cache["at"] > _PLACE_COUNT_TTL_SECONDS:
        try:
            _place_count_cache["value"] = place_service.reload_destinations()
            _place_count_cache["at"] = now
        except Exception:
            logger.warning("Could not count places", exc_info=True)
    return _place_count_cache["value"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(
        "Starting %s v%s (env=%s, debug=%s, ai=%s)",
        settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT, settings.DEBUG, settings.AI_ENABLED,
    )
    upload_path = _ensure_upload_dirs()
    logger.info("Upload directory: %s", upload_path.resolve())

    init_db()
    logger.info("Loaded %s destinations from database", _cached_place_count())

    yield

    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Unified backend for YatraSathi - Nepal travel planning app",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# CORS: explicit origins only. Auth uses the Authorization header (not
# cookies), so credentials are not needed and '*' is safe only in dev.
_cors_origins = settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    """Reject oversized bodies early based on Content-Length."""
    length = request.headers.get("content-length")
    if length and length.isdigit():
        is_multipart = request.headers.get("content-type", "").startswith("multipart/")
        cap = MAX_MULTIPART_BODY_BYTES if is_multipart else MAX_JSON_BODY_BYTES
        if int(length) > cap:
            return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected errors server-side; never leak internals to clients."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# Include API routers BEFORE mounting static files so API endpoints (e.g. POST /uploads/photo)
# are matched and never shadowed by Starlette's StaticFiles mount.
_default_limit = [rate_limit("default", settings.RATE_LIMIT_DEFAULT)]
app.include_router(places_router, dependencies=_default_limit)
app.include_router(route_router, dependencies=_default_limit)
app.include_router(recommend_router, dependencies=[rate_limit("recommend", settings.RATE_LIMIT_AI)])
app.include_router(ai_router, dependencies=[rate_limit("ai", settings.RATE_LIMIT_AI)])
app.include_router(auth_router)
app.include_router(itineraries_router, dependencies=_default_limit)
app.include_router(memories_router, dependencies=_default_limit)
app.include_router(trail_watch_router, dependencies=_default_limit)
app.include_router(uploads.router)

# Serve uploaded images (GET /uploads/...). In production this should move to
# object storage (see the production-readiness plan, Phase 1.5).
app.mount("/uploads", StaticFiles(directory=str(_ensure_upload_dirs())), name="uploads")


@app.get("/telemetry")
async def get_telemetry():
    """Public platform stats used by the home page."""
    return {
        "status": "operational",
        "total_verified_places": _cached_place_count(),
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health/live")
async def health_live():
    """Liveness: the process is up and serving requests."""
    return {"status": "ok"}


@app.get("/health/ready")
@app.get("/health")
async def health():
    """Readiness: the database is reachable. Returns 503 otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Readiness check failed: database unreachable", exc_info=True)
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "up",
        "ai_enabled": settings.AI_ENABLED,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
