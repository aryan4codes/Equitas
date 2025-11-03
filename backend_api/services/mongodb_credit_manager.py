"""
MongoDB credit manager - handles credit operations using MongoDB.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..exceptions import InsufficientCreditsException, CreditOperationException
from ..models.mongodb_models import TenantConfig, CreditTransaction


class MongoCreditManager:
    """Manages credit operations for tenants using MongoDB."""
    
    # Credit costs per operation type
    CREDIT_COSTS = {
        "toxicity": 1.0,
        "bias": 2.0,
        "jailbreak": 1.5,
        "hallucination": 3.0,
        "remediation": 2.0,
        "explain": 1.0,
        "custom_classifier": 1.5,
        "full_analysis": 7.5,
    }
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize credit manager.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.tenant_configs = db.tenant_configs
        self.credit_transactions = db.credit_transactions
    
    async def get_balance(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get current credit balance for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with balance, limit, and usage info
        """
        tenant_config = await self.tenant_configs.find_one({"tenant_id": tenant_id})
        
        if not tenant_config:
            # Create default config if doesn't exist
            default_config = TenantConfig(
                tenant_id=tenant_id,
                credit_balance=0.0,
                credit_enabled=True,
            )
            result = await self.tenant_configs.insert_one(default_config.dict(by_alias=True, exclude={"id"}))
            tenant_config = await self.tenant_configs.find_one({"_id": result.inserted_id})
        
        return {
            "tenant_id": tenant_id,
            "credit_balance": tenant_config["credit_balance"],
            "credit_enabled": tenant_config["credit_enabled"],
            "safety_units_limit": tenant_config.get("safety_units_limit", 10000.0),
            "safety_units_used": tenant_config.get("safety_units_used", 0.0),
            "available_credits": tenant_config["credit_balance"],
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
        tenant_config = await self.tenant_configs.find_one({"tenant_id": tenant_id})
        
        if not tenant_config:
            raise CreditOperationException(f"Tenant {tenant_id} not found")
        
        # Check if credit system is disabled
        if not tenant_config["credit_enabled"]:
            return {
                "success": True,
                "credit_balance": tenant_config["credit_balance"],
                "amount_deducted": 0.0,
                "transaction_id": None,
                "credit_enabled": False,
            }
        
        balance_before = tenant_config["credit_balance"]
        
        if balance_before < amount:
            raise InsufficientCreditsException(
                f"Insufficient credits. Required: {amount}, Available: {balance_before}",
                required=amount,
                available=balance_before,
            )
        
        # Deduct credits
        balance_after = balance_before - amount
        
        # Update tenant config
        await self.tenant_configs.update_one(
            {"tenant_id": tenant_id},
            {
                "$set": {
                    "credit_balance": balance_after,
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        
        # Create transaction record
        transaction = CreditTransaction(
            tenant_id=tenant_id,
            transaction_type="deduct",
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type or "api_call",
            reference_id=reference_id,
            description=description or f"Credits deducted for {operation_type}",
            metadata=metadata or {},
        )
        
        result = await self.credit_transactions.insert_one(
            transaction.dict(by_alias=True, exclude={"id"})
        )
        
        return {
            "success": True,
            "credit_balance": balance_after,
            "amount_deducted": amount,
            "transaction_id": str(result.inserted_id),
            "balance_before": balance_before,
            "balance_after": balance_after,
        }
    
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
        tenant_config = await self.tenant_configs.find_one({"tenant_id": tenant_id})
        
        if not tenant_config:
            # Create tenant config if doesn't exist
            default_config = TenantConfig(
                tenant_id=tenant_id,
                credit_balance=0.0,
                credit_enabled=True,
            )
            await self.tenant_configs.insert_one(
                default_config.dict(by_alias=True, exclude={"id"})
            )
            tenant_config = await self.tenant_configs.find_one({"tenant_id": tenant_id})
        
        balance_before = tenant_config["credit_balance"]
        balance_after = balance_before + amount
        
        # Update tenant config
        await self.tenant_configs.update_one(
            {"tenant_id": tenant_id},
            {
                "$set": {
                    "credit_balance": balance_after,
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        
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
        
        result = await self.credit_transactions.insert_one(
            transaction.dict(by_alias=True, exclude={"id"})
        )
        
        return {
            "success": True,
            "credit_balance": balance_after,
            "amount_added": amount,
            "transaction_id": str(result.inserted_id),
            "balance_before": balance_before,
            "balance_after": balance_after,
        }
    
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
        query = {"tenant_id": tenant_id}
        
        if transaction_type:
            query["transaction_type"] = transaction_type
        
        # Get total count
        total = await self.credit_transactions.count_documents(query)
        
        # Get transactions
        cursor = self.credit_transactions.find(query).sort("created_at", -1).skip(offset).limit(limit)
        transactions = await cursor.to_list(length=limit)
        
        return {
            "transactions": [
                {
                    "id": str(t["_id"]),
                    "transaction_type": t["transaction_type"],
                    "amount": t["amount"],
                    "balance_before": t["balance_before"],
                    "balance_after": t["balance_after"],
                    "reference_type": t.get("reference_type"),
                    "reference_id": t.get("reference_id"),
                    "description": t.get("description"),
                    "created_at": t["created_at"].isoformat() if isinstance(t["created_at"], datetime) else t["created_at"],
                    "created_by": t.get("created_by"),
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

