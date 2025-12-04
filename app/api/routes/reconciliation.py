"""
Reconciliation module for Vectorstore Service.
"""

from fastapi import APIRouter

# Create router
router = APIRouter()

@router.get("/")
async def get_reconciliation():
    """
    Get reconciliation status.
    
    Returns:
        Dict: Reconciliation information.
    """
    return {
        "message": "Reconciliation endpoint operational",
        "status": "idle"
    }
