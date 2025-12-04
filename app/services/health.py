"""
Health Check Service - Verifica dello stato del servizio e delle sue dipendenze.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from app.core.vectordb_manager import vector_db_manager

# Logger
logger = logging.getLogger(__name__)

async def get_service_health() -> Dict[str, Any]:
    """
    Verifica lo stato del servizio e delle sue dipendenze.
    
    Returns:
        Dict con informazioni sullo stato.
    """
    # Verifica lo stato di ChromaDB
    try:
        chroma_status = vector_db_manager.get_status()
        
        # Adatta lo stato di ChromaDB per la UI
        # In modalità persistente locale, consideriamo "healthy" come "connected"
        chroma_response = {
            "status": "healthy" if chroma_status.get("status") == "healthy" else "error",
            "message": chroma_status.get("message", "ChromaDB in modalità persistente locale"),
            "document_count": chroma_status.get("document_count", 0),
            "collection": chroma_status.get("collection", "N/A"),
            "mode": chroma_status.get("mode", "persistent_local"),
            "persist_directory": chroma_status.get("persist_directory", "N/A"),
            "connected": chroma_status.get("status") == "healthy"  # Aggiungiamo questo campo per la UI
        }
    except Exception as e:
        logger.error(f"Errore durante la verifica dello stato di ChromaDB: {str(e)}")
        chroma_response = {
            "status": "error",
            "message": f"Errore: {str(e)}",
            "error_details": str(e)
        }
    
    # Costruisci risposta
    response = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "dependencies": {
            "chroma": chroma_response
        }
    }
    
    # Se una dipendenza ha problemi, lo stato complessivo è degraded
    if chroma_response["status"] != "healthy":
        response["status"] = "degraded"
        
    return response
