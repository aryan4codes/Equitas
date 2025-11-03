"""
Credit management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ...core.database import get_db
from ...core.auth import verify_api_key
from ...services.credit_manager import CreditManager
from ...models.schemas import CreditBalanceResponse, CreditTransactionResponse, CreditAddRequest, CreditAddResponse

router = APIRouter()


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    tenant_id: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current credit balance for tenant.
    
    Returns:
        Current balance, limit, and usage information
    """
    credit_manager = CreditManager(db)
    balance = await credit_manager.get_balance(tenant_id)
    
    return CreditBalanceResponse(**balance)


@router.post("/add", response_model=CreditAddResponse)
async def add_credits(
    request: CreditAddRequest,
    tenant_id: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Add credits to tenant account.
    
    Requires admin privileges or specific API key.
    """
    # TODO: Add admin check here
    credit_manager = CreditManager(db)
    
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
    db: AsyncSession = Depends(get_db),
):
    """
    Get transaction history for tenant.
    
    Returns paginated list of credit transactions.
    """
    credit_manager = CreditManager(db)
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
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate cost for operations before executing.
    
    Useful for checking if tenant has sufficient credits.
    """
    credit_manager = CreditManager(db)
    cost = await credit_manager.calculate_operation_cost(operation_types)
    
    balance = await credit_manager.get_balance(tenant_id)
    
    return {
        "cost": cost,
        "current_balance": balance["credit_balance"],
        "sufficient": balance["credit_balance"] >= cost,
        "operation_types": operation_types,
    }

