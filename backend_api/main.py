"""
Equitas Backend API - FastAPI application for AI safety analysis.
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
import uvicorn

from .api.v1 import analysis, logging as logging_api, metrics, incidents, credits, users, api_keys, credit_requests, waitlist
from .core.config import get_settings
from .core.mongodb import get_mongodb_client, close_mongodb_connection
from .core.auth import verify_api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    logger.info(
        f"Starting Equitas API v{app.version} (slim={settings.equitas_slim}) "
        f"in {settings.environment} mode"
    )
    
    # Initialize MongoDB connection
    try:
        get_mongodb_client()
        logger.info("✅ MongoDB connected successfully")
    except ValueError as e:
        logger.warning(f"❌ MongoDB connection failed: {e}")
        logger.warning("   Please add MONGODB_URL to your environment variables")
        logger.warning("   Example: MONGODB_URL=mongodb://localhost:27017")
    except Exception as e:
        logger.warning(f"❌ MongoDB connection failed: {e}")
        logger.warning("   Please check MONGODB_URL in your environment variables")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Equitas API...")
    await close_mongodb_connection()
    logger.info("MongoDB connection closed")


# Create FastAPI app
app = FastAPI(
    title="Equitas API",
    description="Backend API for AI Safety & Observability",
    version="2.0.1",
    lifespan=lifespan,
)

# Get settings for CORS configuration
def get_cors_origins():
    """Get CORS origins from settings."""
    settings = get_settings()
    if settings.cors_origins == "*":
        return ["*"]
    return [origin.strip() for origin in settings.cors_origins.split(",")]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    settings = get_settings()
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.environment == "development" else "An error occurred"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": exc.errors()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    settings = get_settings()
    return {
        "service": "Equitas API",
        "version": "2.0.1",
        "status": "operational",
        "equitas_slim": settings.equitas_slim,
    }


@app.head("/")
async def root_head():
    """HEAD for uptime probes that do not use GET."""
    return Response(status_code=200)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.head("/health")
async def health_check_head():
    """HEAD /health for monitors that send HEAD (e.g. some load balancers)."""
    return Response(status_code=200)


# Include routers
app.include_router(
    analysis.public_analysis_router,
    prefix="/v1/analysis",
    tags=["analysis"],
)

app.include_router(
    analysis.router,
    prefix="/v1/analysis",
    tags=["analysis"],
    dependencies=[Depends(verify_api_key)],
)

app.include_router(
    logging_api.router,
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

# Public waitlist endpoint (no auth required)
app.include_router(
    waitlist.router,
    prefix="/v1/waitlist",
    tags=["waitlist"],
)


if __name__ == "__main__":
    uvicorn.run(
        "backend_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
