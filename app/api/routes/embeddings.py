"""
Embeddings module for Vectorstore Service.
"""

from fastapi import APIRouter

# Create router
router = APIRouter()

@router.get("/")
async def get_embeddings():
    """
    Get embeddings information.
    
    Returns:
        Dict: Embeddings information.
    """
    return {
        "message": "Embeddings endpoint operational",
        "models": []
    }
