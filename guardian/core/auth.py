"""
Authentication and authorization.
"""

from typing import Optional
from fastapi import Header, HTTPException, status


# Simple API key validation (in production, use proper auth)
VALID_API_KEYS = {
    "fs-dev-key-123": "tenant_demo",
    "fs-prod-key-456": "tenant_prod",
    "fs-test-key-789": "tenant_test_aggressive",
}


async def verify_api_key(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None),
) -> str:
    """
    Verify API key and return tenant ID.
    
    Args:
        authorization: Bearer token
        x_tenant_id: Tenant identifier
        
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
    
    # Validate API key
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Get tenant from key
    tenant_from_key = VALID_API_KEYS[api_key]
    
    # Verify tenant ID matches
    if x_tenant_id and x_tenant_id != tenant_from_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID mismatch",
        )
    
    return tenant_from_key


def get_current_tenant(authorization: str = Header(...)) -> str:
    """Get current tenant ID from request."""
    # In production, decode JWT and extract tenant
    return "tenant_demo"
