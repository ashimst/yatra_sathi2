"""
YatraSathi Backend - Main FastAPI Application
Unified backend serving places, routes, AI assistant, authentication, and itineraries.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config.settings import settings
from backend.app.db.database import init_db
from backend.app.api import (
    places_router,
    route_router,
    recommend_router,
    ai_router,
    workspace_router,
)
from backend.app.services.place_service import place_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Debug mode: {settings.DEBUG}")
    print(f"AI Enabled: {settings.AI_ENABLED}")
    
    # Initialize database
    init_db()
    
    # Load destinations from database
    destinations_count = place_service.reload_destinations()
    print(f"Loaded {destinations_count} destinations from database")
    
    yield
    
    # Shutdown
    print("Shutting down YatraSathi Backend")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Unified backend for YatraSathi - Nepal travel planning app",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(places_router)
app.include_router(route_router)
app.include_router(recommend_router)
app.include_router(ai_router)
app.include_router(workspace_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "endpoints": {
            "health": "GET /health",
            "places": "GET /places",
            "search": "GET /places/search",
            "nearby": "GET /places/nearby",
            "categories": "GET /places/categories/list",
            "route": "POST /route",
            "recommend": "POST /recommend or GET /recommend",
            "ai_chat": "POST /ai/chat",
            "ai_session": "GET /ai/sessions/{id}, DELETE /ai/sessions/{id}",
            "ai_edit_itinerary": "POST /ai/edit-itinerary",
            "workspace": "POST /workspace, GET /workspace/{id}, POST /workspace/{id}/propose, ...",
            "docs": "GET /docs"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "destinations_count": place_service.reload_destinations(),
        "ai_enabled": settings.AI_ENABLED
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
