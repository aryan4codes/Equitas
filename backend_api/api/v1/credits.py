"""
Credit management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from ...core.mongodb import get_database
from ...core.auth import verify_api_key
from ...services.mongodb_credit_manager import MongoCreditManager
from motor.motor_asyncio import AsyncIOMotorDatabase
from ...models.schemas import CreditBalanceResponse, CreditTransactionResponse, CreditAddRequest, CreditAddResponse

router = APIRouter()


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get current credit balance for tenant.
    
    Returns:
        Current balance, limit, and usage information
    """
    credit_manager = MongoCreditManager(mongodb)
    balance = await credit_manager.get_balance(tenant_id)
    
    return CreditBalanceResponse(**balance)


@router.post("/add", response_model=CreditAddResponse)
async def add_credits(
    request: CreditAddRequest,
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Add credits to tenant account.
    
    Requires admin privileges or specific API key.
    """
    # TODO: Add admin check here
    credit_manager = MongoCreditManager(mongodb)
    
    result = await credit_manager.add_credits(
        tenant_id=tenant_id,
        amount=request.amount,
        reference_type=request.reference_type or "manual",
        reference_id=request.reference_id,
        description=request.description,
        created_by=request.created_by,
        metadata=request.metadata,
    )
    
    return CreditAddResponse(**result)


@router.get("/transactions", response_model=CreditTransactionResponse)
async def get_transaction_history(
    tenant_id: str = Depends(verify_api_key),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    transaction_type: Optional[str] = Query(None),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get transaction history for tenant.
    
    Returns paginated list of credit transactions.
    """
    credit_manager = MongoCreditManager(mongodb)
    history = await credit_manager.get_transaction_history(
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
        transaction_type=transaction_type,
    )
    
    return CreditTransactionResponse(**history)


@router.post("/calculate-cost")
async def calculate_cost(
    operation_types: list[str],
    tenant_id: str = Depends(verify_api_key),
    mongodb: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Calculate cost for operations before executing.
    
    Useful for checking if tenant has sufficient credits.
    """
    credit_manager = MongoCreditManager(mongodb)
    cost = await credit_manager.calculate_operation_cost(operation_types)
    
    balance = await credit_manager.get_balance(tenant_id)
    
    return {
        "cost": cost,
        "current_balance": balance["credit_balance"],
        "sufficient": balance["credit_balance"] >= cost,
        "operation_types": operation_types,
    }

