"""
Vectorstore Statistics module.
"""

from fastapi import APIRouter, Query, Path, HTTPException, status
from app.utils.sqlite_metadata_manager import SQLiteMetadataManager
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Create router
router = APIRouter()

# Configure logger
logger = logging.getLogger(__name__)

# Initialize MetadataStoreManager
metadata_manager = SQLiteMetadataManager()

@router.get("/")
async def get_vectorstore_stats():
    """
    Get vectorstore statistics.
    
    Returns:
        Dict: Vectorstore statistics.
    """
    documents = metadata_manager.get_documents()
    collections = metadata_manager.get_collections()
    
    # Calcola le statistiche del vectorstore
    return {
        "status": "ok",
        "documents_count": len(documents),
        "collections_count": len(collections),
        "collections": collections
    }

@router.get("/documents")
async def get_vectorstore_documents(collection: Optional[str] = Query(None, description="Filtra per collezione")):
    """
    Get documents from vectorstore, optionally filtered by collection.
    
    Args:
        collection: Optional collection name to filter by.
        
    Returns:
        Dict: List of documents.
    """
    documents = metadata_manager.get_documents()
    
    if collection:
        # Filtra i documenti per collezione
        documents = [doc for doc in documents if doc.get("collection") == collection]
    
    return {
        "documents": documents,
        "total": len(documents)
    }

@router.get("/collections")
async def get_vectorstore_collections():
    """
    Get list of collections in the vectorstore.
    
    Returns:
        Dict: List of collections.
    """
    collections = metadata_manager.get_collections()
    
    # Conta i documenti per collezione
    documents = metadata_manager.get_documents()
    collection_counts = {}
    
    for doc in documents:
        collection = doc.get("collection")
        if collection:
            collection_counts[collection] = collection_counts.get(collection, 0) + 1
    
    # Crea il risultato
    result = []
    for collection in collections:
        result.append({
            "name": collection,
            "document_count": collection_counts.get(collection, 0)
        })
    
    return {
        "collections": result,
        "total": len(result)
    }

# REDIRECT per compatibilità: /collections/ -> /vectorstore/collections  
@router.get("/", include_in_schema=False, deprecated=True)
async def collections_redirect():
    """
    DEPRECATED: Redirect from /collections/ to /vectorstore/collections.
    
    Il vecchio endpoint /collections/ era inutile (restituiva sempre []).
    Usa /vectorstore/collections che funziona davvero!
    """
    # Chiama direttamente il metodo sopra invece di fare un redirect HTTP
    return await get_vectorstore_collections()

@router.get("/document/{document_id}")
async def get_vectorstore_document(document_id: str = Path(..., description="ID del documento da recuperare")):
    """
    Get a specific document from the vectorstore.
    
    Args:
        document_id: ID of the document to retrieve.
        
    Returns:
        Dict: Document information.
    """
    document = metadata_manager.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento con ID {document_id} non trovato"
        )
    
    return document


# REDIRECT ENDPOINT for /collections/ compatibility
@router.get("/", response_model=dict)
async def collections_redirect():
    """
    Redirect endpoint for /collections/ requests.
    This handles the case when the router is mounted at /collections prefix.
    
    Returns:
        Dict: Collection list with document counts.
    """
    return await get_vectorstore_collections()
