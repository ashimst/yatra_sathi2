"""
Configuration settings for YatraSathi backend.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "YatraSathi Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/yatra_sathi")
    
    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")  # groq or nvidia_nim
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    NVIDIA_NIM_API_KEY: Optional[str] = os.getenv("NVIDIA_NIM_API_KEY")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4000"))
    
    # AI Assistant
    AI_ENABLED: bool = os.getenv("AI_ENABLED", "true").lower() == "true"
    SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    MAX_TOOL_CALLS: int = int(os.getenv("MAX_TOOL_CALLS", "10"))
    PLANNING_TIMEOUT_SECONDS: int = int(os.getenv("PLANNING_TIMEOUT_SECONDS", "60"))
    
    # Authentication
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
    
    # OSRM Routing
    OSRM_URL: str = os.getenv("OSRM_URL", "https://router.project-osrm.org")
    OSRM_SERVERS: list = [
        "https://router.project-osrm.org",
        "https://routing.openstreetmap.de/routed-car",
    ]
    OSRM_TIMEOUT: int = int(os.getenv("OSRM_TIMEOUT", "15"))
    
    # Weather API
    OPENWEATHER_API_KEY: Optional[str] = os.getenv("OPENWEATHER_API_KEY")
    
    # Embedding Model
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    class Config:
        # Resolve .env relative to this file's location so it works regardless
        # of which directory the server is launched from.
        import os as _os
        env_file = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "..", ".env")
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def reload_settings() -> Settings:
    """Force reload settings (useful for testing)."""
    get_settings.cache_clear()
    return get_settings()


# Global settings instance
settings = get_settings()
