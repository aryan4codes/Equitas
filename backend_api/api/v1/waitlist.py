"""
Waitlist API endpoints - Public endpoint for pre-launch signups.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.mongodb import get_database

router = APIRouter()


class WaitlistRequest(BaseModel):
    """Request to join waitlist."""
    email: EmailStr
    name: str


class WaitlistResponse(BaseModel):
    """Response from waitlist signup."""
    success: bool
    message: str


@router.post("/join", response_model=WaitlistResponse)
async def join_waitlist(
    request: WaitlistRequest,
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Join the waitlist - Public endpoint (no auth required).
    
    Saves user email and name to MongoDB waitlist collection.
    """
    try:
        # Check if email already exists
        existing = await mongodb.waitlist.find_one({"email": request.email.lower()})
        if existing:
            return WaitlistResponse(
                success=True,
                message="You're already on the waitlist! We'll notify you when we launch."
            )
        
        # Create waitlist entry
        waitlist_entry = {
            "email": request.email.lower(),
            "name": request.name,
            "created_at": datetime.utcnow(),
            "status": "pending",
        }
        
        # Insert into waitlist collection
        await mongodb.waitlist.insert_one(waitlist_entry)
        
        return WaitlistResponse(
            success=True,
            message="Thanks for joining! We'll notify you when we launch."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to join waitlist: {str(e)}"
        )




