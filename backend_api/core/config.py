"""
Configuration management for Guardian backend.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    api_title: str = "equitas Guardian API"
    api_version: str = "0.1.0"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./equitas.db"
    mongodb_url: str = ""  # MongoDB connection URL
    mongodb_database: str = "equitas"  # MongoDB database name
    
    # OpenAI
    openai_api_key: str = ""
    
    # Security
    secret_key: str = ""  # Must be set via SECRET_KEY environment variable
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: str = "*"  # Comma-separated list of allowed origins, or "*" for all
    
    # Clerk Authentication
    clerk_secret_key: str = ""  # Clerk secret key for backend verification
    clerk_publishable_key: str = ""  # Clerk publishable key (frontend)
    
    # Guardian Settings
    default_toxicity_threshold: float = 0.7
    default_bias_threshold: float = 0.3
    enable_async_logging: bool = True
    
    # Model Settings
    toxicity_model: str = "openai-moderation"
    bias_detection_enabled: bool = True
    jailbreak_detection_enabled: bool = True
    
    # Environment
    environment: str = "development"  # development, production
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validate required settings in production
        if self.environment == "production":
            if not self.secret_key or self.secret_key == "your-secret-key-change-in-production":
                raise ValueError(
                    "SECRET_KEY must be set in production environment. "
                    "Generate a secure random key and set it via SECRET_KEY environment variable."
                )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
