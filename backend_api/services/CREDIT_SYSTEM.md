# Credit System Documentation

## Overview

Equitas implements a credit-based system to control usage and billing. Each tenant has a credit balance that is deducted when using safety analysis features.

## Credit Costs

| Operation | Cost (Credits) |
|-----------|----------------|
| Toxicity Detection | 1.0 |
| Bias Detection | 2.0 |
| Jailbreak Detection | 1.5 |
| Hallucination Detection | 3.0 |
| Remediation | 2.0 |
| Explanation | 1.0 |
| Custom Classifier | 1.5 |
| Full Analysis (all checks) | 7.5 |

## API Endpoints

### Get Credit Balance

```http
GET /v1/credits/balance
Authorization: Bearer <api_key>
X-Tenant-ID: <tenant_id>
```

**Response:**
```json
{
  "tenant_id": "tenant_demo",
  "credit_balance": 1000.0,
  "credit_enabled": true,
  "safety_units_limit": 10000.0,
  "safety_units_used": 500.0,
  "available_credits": 1000.0
}
```

### Add Credits

```http
POST /v1/credits/add
Authorization: Bearer <api_key>
X-Tenant-ID: <tenant_id>
Content-Type: application/json

{
  "amount": 1000.0,
  "reference_type": "manual",
  "description": "Credits added via admin panel",
  "created_by": "admin_user"
}
```

**Response:**
```json
{
  "success": true,
  "credit_balance": 2000.0,
  "amount_added": 1000.0,
  "transaction_id": 123,
  "balance_before": 1000.0,
  "balance_after": 2000.0
}
```

### Get Transaction History

```http
GET /v1/credits/transactions?limit=100&offset=0&transaction_type=deduct
Authorization: Bearer <api_key>
X-Tenant-ID: <tenant_id>
```

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "transaction_type": "deduct",
      "amount": -1.0,
      "balance_before": 1000.0,
      "balance_after": 999.0,
      "reference_type": "api_call",
      "reference_id": "log_123",
      "description": "Toxicity analysis",
      "created_at": "2024-01-01T12:00:00",
      "created_by": null
    }
  ],
  "total": 50,
  "limit": 100,
  "offset": 0
}
```

### Calculate Cost

```http
POST /v1/credits/calculate-cost
Authorization: Bearer <api_key>
X-Tenant-ID: <tenant_id>
Content-Type: application/json

{
  "operation_types": ["toxicity", "bias", "jailbreak"]
}
```

**Response:**
```json
{
  "cost": 4.5,
  "current_balance": 1000.0,
  "sufficient": true,
  "operation_types": ["toxicity", "bias", "jailbreak"]
}
```

## Error Handling

When a tenant has insufficient credits, the API returns HTTP 402 (Payment Required):

```json
{
  "detail": {
    "error": "Insufficient credits",
    "required": 1.0,
    "available": 0.5,
    "balance": {
      "tenant_id": "tenant_demo",
      "credit_balance": 0.5,
      "credit_enabled": true
    }
  }
}
```

## SDK Usage

The SDK automatically handles credit errors:

```python
from equitas_sdk import Equitas
from equitas_sdk.exceptions import InsufficientCreditsException

try:
    response = await equitas.chat.completions.create_async(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello!"}],
    )
except InsufficientCreditsException as e:
    print(f"Insufficient credits: {e.available} available, {e.required} required")
    # Handle error - prompt user to add credits
```

## Credit Management

### Disabling Credit System

Credits can be disabled per tenant:

```python
credit_manager.set_credit_enabled(tenant_id, enabled=False)
```

When disabled, all operations proceed without credit checking or deduction.

### Automatic Deduction

Credits are automatically deducted after successful operations. If an operation fails before completion, credits are not deducted.

### Transaction Types

- **add**: Credits added to account
- **deduct**: Credits deducted for operations
- **refund**: Credits refunded (e.g., for failed operations)
- **expire**: Credits expired (future feature)

## Database Schema

### TenantConfig

```python
credit_balance: float  # Current balance
credit_enabled: bool    # Whether credit checking is enabled
safety_units_limit: float
safety_units_used: float
```

### CreditTransaction

```python
tenant_id: str
transaction_type: str  # add, deduct, refund, expire
amount: float
balance_before: float
balance_after: float
reference_type: str    # api_call, manual, subscription
reference_id: str      # ID of related entity
description: str
created_at: datetime
created_by: str        # Admin user
```

## Best Practices

1. **Check balance before operations**: Use `/v1/credits/calculate-cost` to check if sufficient credits are available
2. **Monitor transactions**: Regularly review transaction history for anomalies
3. **Set up alerts**: Implement alerts when balance falls below threshold
4. **Handle errors gracefully**: Catch `InsufficientCreditsException` and provide user-friendly messages
5. **Transaction references**: Always include reference IDs for audit trails

## Integration Example

```python
from guardian.services.credit_manager import CreditManager
from guardian.exceptions import InsufficientCreditsException

async def process_with_credits(tenant_id: str, operation_type: str, db: AsyncSession):
    credit_manager = CreditManager(db)
    
    # Check credits
    try:
        await credit_manager.check_credits(tenant_id, operation_type=operation_type)
    except InsufficientCreditsException as e:
        return {
            "error": "Insufficient credits",
            "required": e.required,
            "available": e.available,
        }
    
    # Perform operation
    result = await perform_operation()
    
    # Deduct credits
    await credit_manager.deduct_credits(
        tenant_id=tenant_id,
        amount=credit_manager.CREDIT_COSTS[operation_type],
        operation_type=operation_type,
        reference_type="api_call",
        description=f"{operation_type} analysis",
    )
    
    return result
```

