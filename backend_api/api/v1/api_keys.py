"""
API Key management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel
import secrets
import hashlib

from ...core.mongodb import get_database
from ...core.auth import verify_clerk_token, get_current_user_id
from ...models.mongodb_models import APIKey
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()


class GenerateAPIKeyRequest(BaseModel):
    """Request model for generating API key."""
    name: str
    expires_days: Optional[int] = None


def generate_api_key() -> Tuple[str, str, str]:
    """Generate a new API key."""
    # Generate random key
    key = f"eq_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    key_prefix = key[:12]  # eq_xxxxx for display
    return key, key_hash, key_prefix


@router.post("/generate")
async def generate_api_key_endpoint(
    request: GenerateAPIKeyRequest,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Generate a new API key for the current user.
    Returns the key once - store it securely!
    """
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate API key
    key, key_hash, key_prefix = generate_api_key()
    
    expires_at = None
    if request.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
    
    api_key = APIKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        tenant_id=user["tenant_id"],
        user_id=clerk_user_id,
        name=request.name,
        expires_at=expires_at,
    )
    
    await db.api_keys.insert_one(api_key.dict(by_alias=True, exclude={"id"}))
    
    return {
        "success": True,
        "api_key": key,  # Return only once!
        "key_prefix": key_prefix,
        "name": request.name,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": datetime.utcnow().isoformat(),
    }


@router.get("/list")
async def list_api_keys(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List all API keys for current user."""
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cursor = db.api_keys.find({"user_id": clerk_user_id}).sort("created_at", -1)
    keys = await cursor.to_list(length=100)
    
    return {
        "keys": [
            {
                "id": str(k["_id"]),
                "key_prefix": k["key_prefix"],
                "name": k["name"],
                "is_active": k["is_active"],
                "last_used_at": k.get("last_used_at").isoformat() if k.get("last_used_at") else None,
                "expires_at": k.get("expires_at").isoformat() if k.get("expires_at") else None,
                "created_at": k["created_at"].isoformat() if isinstance(k["created_at"], datetime) else k["created_at"],
            }
            for k in keys
        ]
    }


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Revoke an API key."""
    try:
        # Verify ownership
        key = await db.api_keys.find_one({"_id": ObjectId(key_id)})
    except (InvalidId, ValueError):
        raise HTTPException(status_code=400, detail="Invalid API key ID")
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    if key["user_id"] != clerk_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.api_keys.update_one(
        {"_id": ObjectId(key_id)},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    return {"success": True, "message": "API key revoked"}

