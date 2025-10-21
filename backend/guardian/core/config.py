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
    
    # OpenAI
    openai_api_key: str = ""
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Guardian Settings
    default_toxicity_threshold: float = 0.7
    default_bias_threshold: float = 0.3
    enable_async_logging: bool = True
    
    # Model Settings
    toxicity_model: str = "openai-moderation"
    bias_detection_enabled: bool = True
    jailbreak_detection_enabled: bool = True
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
