"""
Health check module for Vectorstore Service.
"""

from fastapi import APIRouter, Depends
from app.services.health import get_service_health

# Create router
router = APIRouter()

@router.get("/")
async def get_health():
    """
    Get basic health status.
    
    Returns:
        Dict: Basic health information.
    """
    return {
        "status": "ok"
    }

@router.get("/dependencies")
async def get_dependencies_health():
    """
    Get detailed health status of all dependencies.
    
    Returns:
        Dict: Detailed health information.
    """
    return await get_service_health()
