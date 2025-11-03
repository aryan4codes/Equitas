"""
MongoDB connection and database management.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from fastapi import HTTPException
from ..core.config import get_settings

settings = get_settings()

# Global MongoDB client
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


def get_mongodb_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance."""
    global _client
    if _client is None:
        mongodb_url = getattr(settings, 'mongodb_url', None)
        if not mongodb_url:
            raise ValueError("MONGODB_URL environment variable not set")
        _client = AsyncIOMotorClient(mongodb_url)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    global _database
    try:
        if _database is None:
            client = get_mongodb_client()
            db_name = getattr(settings, 'mongodb_database', 'equitas')
            _database = client[db_name]
        return _database
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail=f"MongoDB not configured: {str(e)}. Please set MONGODB_URL in your .env file."
        )


async def close_mongodb_connection():
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        _client = None
        _database = None

