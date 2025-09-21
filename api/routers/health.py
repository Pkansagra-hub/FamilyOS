"""
Health Check Router
==================
Simple health endpoints for monitoring.
"""

from fastapi import APIRouter

from api.schemas.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "memoryos-api"}


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check."""
    return {"status": "ready", "service": "memoryos-api"}


@router.get("/health/live", response_model=HealthResponse)
async def liveness_check():
    """Liveness check."""
    return {"status": "alive", "service": "memoryos-api"}
