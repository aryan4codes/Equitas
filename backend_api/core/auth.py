"""
Authentication and authorization.
"""

from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from jose import jwt, JWTError
import hashlib
from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import get_settings
from .mongodb import get_database

settings = get_settings()

# Simple API key validation (backward compatibility)
VALID_API_KEYS = {
    "fs-dev-key-123": "tenant_demo",
    "fs-prod-key-456": "tenant_prod",
    "fs-test-key-789": "tenant_test_aggressive",
}


async def verify_api_key(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> str:
    """
    Verify API key and return tenant ID.
    Supports both old API keys and new MongoDB-based keys.
    
    Args:
        authorization: Bearer token
        x_tenant_id: Tenant identifier
        db: MongoDB database
        
    Returns:
        Tenant ID
        
    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    
    # Extract token
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    
    api_key = parts[1]
    
    # Check old API keys first (backward compatibility)
    if api_key in VALID_API_KEYS:
        tenant_from_key = VALID_API_KEYS[api_key]
        if x_tenant_id and x_tenant_id != tenant_from_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant ID mismatch",
            )
        return tenant_from_key
    
    # Check MongoDB API keys
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_doc = await db.api_keys.find_one({
        "key_hash": key_hash,
        "is_active": True,
    })
    
    if not api_key_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Check expiration
    if api_key_doc.get("expires_at"):
        from datetime import datetime
        if datetime.utcnow() > api_key_doc["expires_at"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired",
            )
    
    # Update last used
    from datetime import datetime
    await db.api_keys.update_one(
        {"_id": api_key_doc["_id"]},
        {"$set": {"last_used_at": datetime.utcnow()}}
    )
    
    tenant_id = api_key_doc["tenant_id"]
    
    # Verify tenant ID matches if provided
    if x_tenant_id and x_tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID mismatch",
        )
    
    return tenant_id


async def verify_clerk_token(
    authorization: Optional[str] = Header(None),
) -> dict:
    """
    Verify Clerk JWT token and return user info.
    
    Args:
        authorization: Bearer token
        
    Returns:
        Dict with user info
        
    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    
    token = parts[1]
    
    # Verify JWT token with Clerk
    # In production, use Clerk's verification endpoint or SDK
    try:
        # For now, decode without verification (replace with Clerk SDK)
        # from clerk_sdk import Clerk
        # clerk = Clerk(secret_key=settings.clerk_secret_key)
        # payload = clerk.verify_token(token)
        
        # Temporary: decode JWT (in production use Clerk SDK)
        payload = jwt.decode(
            token,
            settings.clerk_secret_key or "temp-secret",
            algorithms=["HS256"],
            options={"verify_signature": False},  # Disable for now, use Clerk SDK in production
        )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> str:
    """
    Get current user ID from Clerk token.
    
    Returns:
        Clerk user ID
    """
    payload = await verify_clerk_token(authorization)
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )
    return user_id


async def require_admin(
    authorization: Optional[str] = Header(None),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> str:
    """
    Require admin role. Returns admin user ID.
    """
    user_id = await get_current_user_id(authorization)
    
    user = await db.users.find_one({"clerk_user_id": user_id})
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return user_id


def get_current_tenant(authorization: str = Header(...)) -> str:
    """Get current tenant ID from request."""
    # In production, decode JWT and extract tenant
    return "tenant_demo"
