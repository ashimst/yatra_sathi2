"""
Configuration settings for YatraSathi backend.

All values are read from environment variables (and ``.env`` in the project
root, if present) by pydantic-settings. In production (``ENVIRONMENT=production``)
the app refuses to start with missing or insecure values; see
``Settings.validate_for_production``.
"""
from functools import lru_cache
from pathlib import Path
from typing import Annotated, List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Project base directory
_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_UPLOAD_DIR = _BASE_DIR / "uploads"
_ENV_FILE = _BASE_DIR / ".env"

INSECURE_JWT_SECRETS = {
    "",
    "your-secret-key-change-in-production",
    "change-this-jwt-secret-in-production-yatrasathi-2026",
}
_DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-do-not-use-in-production"
MIN_JWT_SECRET_LENGTH = 32


def _split_csv(value):
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "YatraSathi Backend"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | test | staging | production
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS: comma-separated list of exact origins, e.g.
    # "https://yatrasathi.pages.dev,https://app.yatrasathi.com"
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Database (no default credentials; local dev uses docker-compose values via .env)
    DATABASE_URL: str = "postgresql://postgres@localhost:5432/yatra_sathi"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5

    # Public base URL of this API (e.g. "https://api.yatrasathi.com"). When set,
    # uploaded file URLs are returned as absolute URLs so a frontend on another
    # origin can load them. Leave empty for same-origin/proxied setups.
    PUBLIC_BASE_URL: str = ""

    # Uploads & Storage Engine
    UPLOAD_DIR: Path = _DEFAULT_UPLOAD_DIR
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "webp", "bmp"]
    ALLOWED_IMAGE_MIMES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/bmp",
        "image/x-ms-bmp",
    ]

    # LLM Configuration
    LLM_PROVIDER: str = "groq"  # groq or nvidia_nim
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_KEY: Optional[str] = None
    NVIDIA_NIM_API_KEY: Optional[str] = None
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 4000

    # AI Assistant
    AI_ENABLED: bool = True
    AI_SESSION_MAX_MESSAGES: int = 40

    # Authentication
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24 * 7
    ADMIN_EMAILS: Annotated[List[str], NoDecode] = []

    # Rate limiting (slowapi syntax, per client IP)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    RATE_LIMIT_DEFAULT: str = "120/minute"
    RATE_LIMIT_AI: str = "20/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "20/minute"

    # OSRM Routing
    OSRM_URL: str = "https://router.project-osrm.org"
    OSRM_TIMEOUT: int = 15

    # Weather API
    OPENWEATHER_API_KEY: Optional[str] = None

    # Embedding Model (must match the model used to generate stored vectors)
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    @field_validator("CORS_ORIGINS", "ADMIN_EMAILS", mode="before")
    @classmethod
    def _parse_csv(cls, value):
        return _split_csv(value)

    @field_validator("ADMIN_EMAILS")
    @classmethod
    def _lower_emails(cls, value: List[str]) -> List[str]:
        return [v.lower() for v in value]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "staging"}

    @model_validator(mode="after")
    def validate_for_production(self) -> "Settings":
        problems: List[str] = []

        if self.JWT_SECRET_KEY in INSECURE_JWT_SECRETS or len(self.JWT_SECRET_KEY) < MIN_JWT_SECRET_LENGTH:
            if self.is_production:
                problems.append(
                    f"JWT_SECRET_KEY must be set to a random value of at least {MIN_JWT_SECRET_LENGTH} characters."
                )
            else:
                # Stable across workers/restarts in dev so tokens keep working.
                object.__setattr__(self, "JWT_SECRET_KEY", _DEV_JWT_SECRET)

        if self.is_production:
            if "*" in self.CORS_ORIGINS or not self.CORS_ORIGINS:
                problems.append("CORS_ORIGINS must list explicit origins (no '*').")
            if self.DATABASE_URL.startswith("postgresql://postgres@localhost"):
                problems.append("DATABASE_URL must be set.")
            if self.AI_ENABLED and not self.GROQ_API_KEY and not self.NVIDIA_NIM_API_KEY:
                problems.append("GROQ_API_KEY (or NVIDIA_NIM_API_KEY) must be set when AI_ENABLED=true.")
            if self.DEBUG:
                problems.append("DEBUG must be false in production.")

        if problems:
            raise ValueError("Invalid production configuration:\n  - " + "\n  - ".join(problems))
        return self


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
