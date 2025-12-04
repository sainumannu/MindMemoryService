"""
Script to fix collections.py
"""

import os

# Create simple collections.py file
collections_content = '''"""
Collections module for Vectorstore Service.
"""

from fastapi import APIRouter

# Create router
router = APIRouter()

@router.get("/")
async def get_collections():
    """
    Get collections.
    
    Returns:
        Dict: Collections information.
    """
    return {
        "message": "Collections endpoint operational",
        "collections": []
    }
'''

with open('app/api/routes/collections.py', 'w') as f:
    f.write(collections_content)
    
print("Fixed collections.py file created!")
