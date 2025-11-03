"""
Credit request endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel

from ...core.mongodb import get_database
from ...core.auth import verify_clerk_token, get_current_user_id, require_admin
from ...models.mongodb_models import CreditRequest
from ...services.mongodb_credit_manager import MongoCreditManager
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()


class RequestCreditsRequest(BaseModel):
    """Request model for requesting credits."""
    amount: float
    reason: Optional[str] = None


class ApproveRequest(BaseModel):
    """Request model for approving/rejecting."""
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    """Request model for rejecting."""
    notes: Optional[str] = None


@router.post("/request")
async def request_credits(
    request: RequestCreditsRequest,
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Request credits for current user's tenant.
    """
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    credit_request = CreditRequest(
        tenant_id=user["tenant_id"],
        user_id=clerk_user_id,
        amount=request.amount,
        reason=request.reason,
        status="pending",
    )
    
    result = await db.credit_requests.insert_one(
        credit_request.dict(by_alias=True, exclude={"id"})
    )
    
    return {
        "success": True,
        "request_id": str(result.inserted_id),
        "amount": request.amount,
        "status": "pending",
    }


@router.get("/my-requests")
async def get_my_requests(
    clerk_user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get all credit requests for current user."""
    user = await db.users.find_one({"clerk_user_id": clerk_user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cursor = db.credit_requests.find({"tenant_id": user["tenant_id"]}).sort("created_at", -1)
    requests = await cursor.to_list(length=100)
    
    return {
        "requests": [
            {
                "id": str(r["_id"]),
                "amount": r["amount"],
                "reason": r.get("reason"),
                "status": r["status"],
                "reviewed_by": r.get("reviewed_by"),
                "reviewed_at": r.get("reviewed_at").isoformat() if r.get("reviewed_at") else None,
                "notes": r.get("notes"),
                "created_at": r["created_at"].isoformat() if isinstance(r["created_at"], datetime) else r["created_at"],
            }
            for r in requests
        ]
    }


@router.get("/pending")
async def get_pending_requests(
    admin_user_id: str = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get all pending credit requests (admin only)."""
    cursor = db.credit_requests.find({"status": "pending"}).sort("created_at", -1)
    requests = await cursor.to_list(length=100)
    
    # Get user info for each request
    result = []
    for req in requests:
        user = await db.users.find_one({"clerk_user_id": req["user_id"]})
        result.append({
            "id": str(req["_id"]),
            "tenant_id": req["tenant_id"],
            "user_email": user["email"] if user else None,
            "user_name": user.get("name") if user else None,
            "amount": req["amount"],
            "reason": req.get("reason"),
            "status": req["status"],
            "created_at": req["created_at"].isoformat() if isinstance(req["created_at"], datetime) else req["created_at"],
        })
    
    return {"requests": result}


class ApproveRequest(BaseModel):
    """Request model for approving/rejecting."""
    notes: Optional[str] = None


@router.post("/{request_id}/approve")
async def approve_request(
    request_id: str,
    request: ApproveRequest,
    admin_user_id: str = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Approve a credit request (admin only)."""
    try:
        request_obj = await db.credit_requests.find_one({"_id": ObjectId(request_id)})
    except (InvalidId, ValueError):
        raise HTTPException(status_code=400, detail="Invalid request ID")
    if not request_obj:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request_obj["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    # Add credits
    credit_manager = MongoCreditManager(db)
    await credit_manager.add_credits(
        tenant_id=request_obj["tenant_id"],
        amount=request_obj["amount"],
        reference_type="approval",
        reference_id=str(request_id),
        description=f"Credit request approved: {request_obj['amount']} credits",
        created_by=admin_user_id,
        metadata={"request_id": str(request_id)},
    )
    
    # Update request status
    await db.credit_requests.update_one(
        {"_id": ObjectId(request_id)},
        {
            "$set": {
                "status": "approved",
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.utcnow(),
                "notes": request.notes,
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    return {"success": True, "message": "Request approved and credits added"}


class RejectRequest(BaseModel):
    """Request model for rejecting."""
    notes: Optional[str] = None


@router.post("/{request_id}/reject")
async def reject_request(
    request_id: str,
    request: RejectRequest,
    admin_user_id: str = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Reject a credit request (admin only)."""
    try:
        request_obj = await db.credit_requests.find_one({"_id": ObjectId(request_id)})
    except (InvalidId, ValueError):
        raise HTTPException(status_code=400, detail="Invalid request ID")
    if not request_obj:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request_obj["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    await db.credit_requests.update_one(
        {"_id": ObjectId(request_id)},
        {
            "$set": {
                "status": "rejected",
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.utcnow(),
                "notes": request.notes,
                "updated_at": datetime.utcnow(),
            }
        }
    )
    
    return {"success": True, "message": "Request rejected"}

