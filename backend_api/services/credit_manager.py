"""
Credit management service for Equitas.

Handles credit checking, deduction, addition, and transaction history.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError

from ..models.database import TenantConfig, CreditTransaction
from ..exceptions import InsufficientCreditsException, CreditOperationException


class CreditManager:
    """Manages credit operations for tenants."""
    
    # Credit costs per operation type
    CREDIT_COSTS = {
        "toxicity": 1.0,
        "bias": 2.0,
        "jailbreak": 1.5,
        "hallucination": 3.0,
        "remediation": 2.0,
        "explain": 1.0,
        "custom_classifier": 1.5,
        "full_analysis": 7.5,  # Sum of all checks
    }
    
    def __init__(self, db: AsyncSession):
        """
        Initialize credit manager.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_balance(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get current credit balance for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with balance, limit, and usage info
        """
        result = await self.db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        tenant_config = result.scalar_one_or_none()
        
        if not tenant_config:
            # Create default config if doesn't exist
            tenant_config = TenantConfig(
                tenant_id=tenant_id,
                credit_balance=0.0,
                credit_enabled=True,
            )
            self.db.add(tenant_config)
            await self.db.commit()
            await self.db.refresh(tenant_config)
        
        return {
            "tenant_id": tenant_id,
            "credit_balance": tenant_config.credit_balance,
            "credit_enabled": tenant_config.credit_enabled,
            "safety_units_limit": tenant_config.safety_units_limit,
            "safety_units_used": tenant_config.safety_units_used,
            "available_credits": tenant_config.credit_balance,
        }
    
    async def check_credits(
        self,
        tenant_id: str,
        required_credits: float,
        operation_type: str = "full_analysis"
    ) -> bool:
        """
        Check if tenant has sufficient credits.
        
        Args:
            tenant_id: Tenant identifier
            required_credits: Required credit amount (if None, uses operation_type cost)
            operation_type: Type of operation (used to calculate cost if required_credits not provided)
            
        Returns:
            True if sufficient credits available
            
        Raises:
            InsufficientCreditsException: If insufficient credits
        """
        balance_info = await self.get_balance(tenant_id)
        
        # Check if credit system is disabled for this tenant
        if not balance_info["credit_enabled"]:
            return True
        
        # Calculate required credits if not provided
        if required_credits is None:
            required_credits = self.CREDIT_COSTS.get(operation_type, 1.0)
        
        available = balance_info["credit_balance"]
        
        if available < required_credits:
            raise InsufficientCreditsException(
                f"Insufficient credits. Required: {required_credits}, Available: {available}",
                required=required_credits,
                available=available,
                balance=balance_info,
            )
        
        return True
    
    async def deduct_credits(
        self,
        tenant_id: str,
        amount: float,
        operation_type: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Deduct credits from tenant account.
        
        Args:
            tenant_id: Tenant identifier
            amount: Amount to deduct
            operation_type: Type of operation
            reference_type: Type of reference (e.g., "api_call")
            reference_id: ID of related entity
            description: Optional description
            metadata: Optional metadata
            
        Returns:
            Dict with new balance and transaction info
            
        Raises:
            InsufficientCreditsException: If insufficient credits
        """
        # Get current balance
        result = await self.db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        tenant_config = result.scalar_one_or_none()
        
        if not tenant_config:
            raise CreditOperationException(f"Tenant {tenant_id} not found")
        
        # Check if credit system is disabled
        if not tenant_config.credit_enabled:
            return {
                "success": True,
                "credit_balance": tenant_config.credit_balance,
                "amount_deducted": 0.0,
                "transaction_id": None,
                "credit_enabled": False,
            }
        
        balance_before = tenant_config.credit_balance
        
        if balance_before < amount:
            raise InsufficientCreditsException(
                f"Insufficient credits. Required: {amount}, Available: {balance_before}",
                required=amount,
                available=balance_before,
            )
        
        # Deduct credits
        balance_after = balance_before - amount
        tenant_config.credit_balance = balance_after
        
        # Create transaction record
        transaction = CreditTransaction(
            tenant_id=tenant_id,
            transaction_type="deduct",
            amount=-amount,  # Negative for deduction
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type or "api_call",
            reference_id=reference_id,
            description=description or f"Credits deducted for {operation_type}",
            metadata=metadata or {},
        )
        
        self.db.add(transaction)
        
        try:
            await self.db.commit()
            await self.db.refresh(transaction)
            await self.db.refresh(tenant_config)
            
            return {
                "success": True,
                "credit_balance": balance_after,
                "amount_deducted": amount,
                "transaction_id": transaction.id,
                "balance_before": balance_before,
                "balance_after": balance_after,
            }
        except IntegrityError as e:
            await self.db.rollback()
            raise CreditOperationException(f"Failed to deduct credits: {e}")
    
    async def add_credits(
        self,
        tenant_id: str,
        amount: float,
        reference_type: str = "manual",
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add credits to tenant account.
        
        Args:
            tenant_id: Tenant identifier
            amount: Amount to add
            reference_type: Type of reference (e.g., "manual", "subscription", "promotion")
            reference_id: ID of related entity
            description: Optional description
            created_by: User/admin who added credits
            metadata: Optional metadata
            
        Returns:
            Dict with new balance and transaction info
        """
        # Get current balance
        result = await self.db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        tenant_config = result.scalar_one_or_none()
        
        if not tenant_config:
            # Create tenant config if doesn't exist
            tenant_config = TenantConfig(
                tenant_id=tenant_id,
                credit_balance=0.0,
                credit_enabled=True,
            )
            self.db.add(tenant_config)
            await self.db.flush()
        
        balance_before = tenant_config.credit_balance
        balance_after = balance_before + amount
        tenant_config.credit_balance = balance_after
        
        # Create transaction record
        transaction = CreditTransaction(
            tenant_id=tenant_id,
            transaction_type="add",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description or f"Credits added: {amount}",
            created_by=created_by,
            metadata=metadata or {},
        )
        
        self.db.add(transaction)
        
        try:
            await self.db.commit()
            await self.db.refresh(transaction)
            await self.db.refresh(tenant_config)
            
            return {
                "success": True,
                "credit_balance": balance_after,
                "amount_added": amount,
                "transaction_id": transaction.id,
                "balance_before": balance_before,
                "balance_after": balance_after,
            }
        except IntegrityError as e:
            await self.db.rollback()
            raise CreditOperationException(f"Failed to add credits: {e}")
    
    async def refund_credits(
        self,
        tenant_id: str,
        amount: float,
        original_transaction_id: Optional[int] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Refund credits to tenant account.
        
        Args:
            tenant_id: Tenant identifier
            amount: Amount to refund
            original_transaction_id: ID of original transaction being refunded
            description: Optional description
            metadata: Optional metadata
            
        Returns:
            Dict with new balance and transaction info
        """
        return await self.add_credits(
            tenant_id=tenant_id,
            amount=amount,
            reference_type="refund",
            reference_id=str(original_transaction_id) if original_transaction_id else None,
            description=description or f"Credit refund: {amount}",
            metadata=metadata or {},
        )
    
    async def get_transaction_history(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        transaction_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get transaction history for tenant.
        
        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of transactions to return
            offset: Offset for pagination
            transaction_type: Filter by transaction type
            
        Returns:
            Dict with transactions and pagination info
        """
        query = select(CreditTransaction).where(
            CreditTransaction.tenant_id == tenant_id
        )
        
        if transaction_type:
            query = query.where(CreditTransaction.transaction_type == transaction_type)
        
        query = query.order_by(CreditTransaction.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        transactions = result.scalars().all()
        
        # Get total count
        count_query = select(CreditTransaction).where(
            CreditTransaction.tenant_id == tenant_id
        )
        if transaction_type:
            count_query = count_query.where(CreditTransaction.transaction_type == transaction_type)
        
        total_result = await self.db.execute(
            select(func.count()).select_from(count_query.subquery())
        )
        total = total_result.scalar() or 0
        
        return {
            "transactions": [
                {
                    "id": t.id,
                    "transaction_type": t.transaction_type,
                    "amount": t.amount,
                    "balance_before": t.balance_before,
                    "balance_after": t.balance_after,
                    "reference_type": t.reference_type,
                    "reference_id": t.reference_id,
                    "description": t.description,
                    "created_at": t.created_at.isoformat(),
                    "created_by": t.created_by,
                }
                for t in transactions
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    async def calculate_operation_cost(
        self,
        operation_types: List[str],
    ) -> float:
        """
        Calculate total cost for multiple operations.
        
        Args:
            operation_types: List of operation types
            
        Returns:
            Total cost
        """
        total = 0.0
        for op_type in operation_types:
            total += self.CREDIT_COSTS.get(op_type, 1.0)
        return total
    
    async def set_credit_enabled(
        self,
        tenant_id: str,
        enabled: bool,
    ) -> Dict[str, Any]:
        """
        Enable or disable credit checking for tenant.
        
        Args:
            tenant_id: Tenant identifier
            enabled: Whether to enable credit checking
            
        Returns:
            Updated config
        """
        result = await self.db.execute(
            select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        )
        tenant_config = result.scalar_one_or_none()
        
        if not tenant_config:
            raise CreditOperationException(f"Tenant {tenant_id} not found")
        
        tenant_config.credit_enabled = enabled
        await self.db.commit()
        await self.db.refresh(tenant_config)
        
        return {
            "tenant_id": tenant_id,
            "credit_enabled": enabled,
        }

