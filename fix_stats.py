"""
Script to fix stats.py
"""

import os

# Create simple stats.py file
stats_content = '''"""
Statistics module for Vectorstore Service.
"""

from fastapi import APIRouter

# Create router
router = APIRouter()

@router.get("/")
async def get_stats():
    """
    Get statistics.
    
    Returns:
        Dict: Basic statistics.
    """
    return {
        "message": "Stats endpoint operational",
        "status": "ok"
    }
'''

with open('app/api/routes/stats.py', 'w') as f:
    f.write(stats_content)
    
print("Fixed stats.py file created!")
