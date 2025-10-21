"""
Guardian Backend - FastAPI application for equitas safety analysis.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .api.v1 import analysis, logging, metrics, incidents
from .core.config import get_settings
from .core.database import engine, Base
from .core.auth import verify_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="equitas Guardian API",
    description="Backend API for AI Safety & Observability",
    version="0.1.0",
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
        "service": "equitas Guardian API",
        "version": "0.1.0",
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


if __name__ == "__main__":
    uvicorn.run(
        "guardian.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
