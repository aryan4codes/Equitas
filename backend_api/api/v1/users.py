"""
User management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId

from ...core.mongodb import get_database
from ...core.auth import verify_clerk_token, get_current_user_id
from ...models.mongodb_models import User
from ...models.schemas import CreditBalanceResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    name: Optional[str] = None


@router.post("/register")
async def register_user(
    request: RegisterRequest,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Register a new user (called after Clerk signup).
    Creates a tenant_id based on user ID.
    """
    # Check if user already exists
    existing_user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if existing_user:
        return {
            "success": True,
            "user_id": str(existing_user["_id"]),
            "tenant_id": existing_user["tenant_id"],
            "message": "User already registered",
        }
    
    # Create tenant_id from user_id (or use user_id directly)
    tenant_id = f"tenant_{clerk_user_id[:8]}"
    
    user = User(
        clerk_user_id=clerk_user_id,
        email=request.email,
        name=request.name,
        tenant_id=tenant_id,
        role="user",
    )
    
    result = await db.users.insert_one(user.dict(by_alias=True, exclude={"id"}))
    
    # Create default tenant config
    from ...models.mongodb_models import TenantConfig
    default_config = TenantConfig(
        tenant_id=tenant_id,
        credit_balance=0.0,
        credit_enabled=True,
    )
    await db.tenant_configs.insert_one(default_config.dict(by_alias=True, exclude={"id"}))
    
    return {
        "success": True,
        "user_id": str(result.inserted_id),
        "tenant_id": tenant_id,
    }


@router.get("/me")
async def get_current_user(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get current user information."""
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user["_id"]),
        "clerk_user_id": user["clerk_user_id"],
        "email": user["email"],
        "name": user.get("name"),
        "tenant_id": user["tenant_id"],
        "role": user.get("role", "user"),
    }


@router.get("/balance")
async def get_user_balance(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get credit balance for current user."""
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    from ...services.mongodb_credit_manager import MongoCreditManager
    credit_manager = MongoCreditManager(db)
    balance = await credit_manager.get_balance(user["tenant_id"])
    
    return CreditBalanceResponse(**balance)

