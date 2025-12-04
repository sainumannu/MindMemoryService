"""
API Gateway module for Vectorstore Service.

This module provides compatibility endpoints for the frontend.
"""

from fastapi import APIRouter, Request, Body, status, HTTPException
from app.api.routes import documents, stats, vectorstore
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import logging

# Create router
router = APIRouter()

# Configure logger
logger = logging.getLogger(__name__)

@router.get("/vectorstore/documents")
async def get_vectorstore_documents(request: Request):
    """
    Gateway endpoint for frontend compatibility.
    Maps to /documents/list
    """
    logger.info(f"Richiesta ricevuta all'endpoint /vectorstore/documents")
    logger.debug(f"Headers: {request.headers}")
    
    # Restituisci i documenti
    response = await documents.list_documents()
    logger.debug(f"Risposta: {response}")
    return response

@router.get("/documents/status")
async def get_documents_status():
    """
    Endpoint compatibilità per il frontend legacy.
    Mappa a /documents/list
    """
    logger.info("Richiesta ricevuta all'endpoint /documents/status")
    
    # Ottieni i documenti
    docs_response = await documents.list_documents()
    
    # Ottieni le statistiche
    stats_response = await stats.get_processing_stats()
    
    return {
        "documents": docs_response.get("documents", []),
        "stats": stats_response
    }

@router.get("/vectorstore/status")
async def get_vectorstore_status():
    """
    Endpoint per lo stato del vectorstore.
    """
    logger.info("Richiesta ricevuta all'endpoint /vectorstore/status")
    
    # Ottieni le statistiche del vectorstore
    vectorstore_stats = await vectorstore.get_vectorstore_stats()
    
    return vectorstore_stats

@router.post("/vectorstore/documents", status_code=status.HTTP_201_CREATED)
async def create_vectorstore_document(document: Dict[str, Any] = Body(...)):
    """
    Gateway endpoint for creating documents.
    Maps to /documents POST
    """
    logger.info("Richiesta di creazione documento ricevuta")
    return await documents.create_document(document)

@router.get("/vectorstore/statistics")
async def get_vectorstore_statistics():
    """
    Gateway endpoint for frontend compatibility.
    Maps to /stats/processing
    """
    logger.info("Richiesta ricevuta all'endpoint /vectorstore/statistics")
    stats_data = await stats.get_processing_stats()
    
    # Modifica per compatibilità con il frontend
    result = {
        "success": True,
        "documents_in_queue": stats_data.get("documents_in_queue", 0),
        "documents_in_coda": stats_data.get("documents_in_coda", 0),
        "documents_processed_today": stats_data.get("documents_processed_today", 0),
        "total_documents": stats_data.get("total_documents", 0)
    }
    return result

@router.get("/vectorstore/health")
async def health_check():
    """
    Health check endpoint for the API gateway.
    """
    return {"status": "ok", "message": "VectorstoreService API Gateway is operational"}

@router.get("/vectorstore/dependencies")
async def get_dependencies_status():
    """
    Endpoint per recuperare lo stato delle dipendenze (ChromaDB).
    """
    from app.services.health import get_service_health
    
    health_data = await get_service_health()
    
    # Formatta la risposta per la UI
    return {
        "status": health_data.get("status", "error"),
        "dependencies": health_data.get("dependencies", {})
    }

@router.get("/vectorstore/settings/status")
async def get_service_status():
    """
    Endpoint per recuperare lo stato completo del servizio.
    Compatibile con la UI.
    """
    from app.api.routes.settings import get_status
    
    # Recupera lo stato dalle impostazioni
    status_data = await get_status()
    
    return status_data
