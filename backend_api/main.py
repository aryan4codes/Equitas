"""
Equitas Backend API - FastAPI application for AI safety analysis.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .api.v1 import analysis, logging, metrics, incidents, credits, users, api_keys, credit_requests
from .core.config import get_settings
from .core.mongodb import get_mongodb_client, close_mongodb_connection
from .core.auth import verify_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Initialize MongoDB connection
    try:
        get_mongodb_client()
        print("✅ MongoDB connected successfully")
    except ValueError as e:
        print(f"❌ Warning: MongoDB connection failed: {e}")
        print("   Please add MONGODB_URL to your .env file")
        print("   Example: MONGODB_URL=mongodb://localhost:27017")
        print("   See MONGODB_SETUP.md for detailed instructions")
    except Exception as e:
        print(f"❌ Warning: MongoDB connection failed: {e}")
        print("   Please check MONGODB_URL in your .env file")
        print("   See MONGODB_SETUP.md for detailed instructions")
    
    yield
    # Cleanup
    await close_mongodb_connection()


# Create FastAPI app
app = FastAPI(
    title="Equitas API",
    description="Backend API for AI Safety & Observability",
    version="2.0.1",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Equitas API",
        "version": "2.0.1",
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(
    analysis.router,
    prefix="/v1/analysis",
    tags=["analysis"],
    dependencies=[Depends(verify_api_key)],
)

app.include_router(
    logging.router,
    prefix="/v1",
    tags=["logging"],
    dependencies=[Depends(verify_api_key)],
)

app.include_router(
    metrics.router,
    prefix="/v1",
    tags=["metrics"],
    dependencies=[Depends(verify_api_key)],
)

app.include_router(
    incidents.router,
    prefix="/v1",
    tags=["incidents"],
    dependencies=[Depends(verify_api_key)],
)

app.include_router(
    credits.router,
    prefix="/v1/credits",
    tags=["credits"],
    dependencies=[Depends(verify_api_key)],
)

# User management endpoints (Clerk auth)
app.include_router(
    users.router,
    prefix="/v1/users",
    tags=["users"],
)

app.include_router(
    api_keys.router,
    prefix="/v1/api-keys",
    tags=["api-keys"],
)

app.include_router(
    credit_requests.router,
    prefix="/v1/credit-requests",
    tags=["credit-requests"],
)


if __name__ == "__main__":
    uvicorn.run(
        "backend_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
