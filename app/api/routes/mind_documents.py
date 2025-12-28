"""
Mind-specific documents endpoints for PramaIA-Mind integration.

This module provides strict endpoints designed for the PramaIA-Mind project where:
- Content and metadata MUST ALWAYS be provided together
- Cannot create document with content-only (no metadata)
- Cannot create document with metadata-only (no content)
- Both fields are mandatory and coupled

Endpoints:
- POST   /mind/documents/              - Create document (content+metadata required)
- GET    /mind/documents/{id}          - Get specific document
- POST   /mind/documents/{id}          - Update document (content+metadata required)
- DELETE /mind/documents/{id}          - Delete document
- POST   /mind/documents/{collection}/query - Semantic search with full metadata in response
"""

from fastapi import APIRouter, HTTPException, Body, status
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from app.utils.document_manager import DocumentManager

# Create router for Mind-specific endpoints
router = APIRouter(prefix="/mind/documents", tags=["mind-documents"])

# DocumentManager globale
metadata_manager = None

def get_metadata_manager():
    """Inizializza il DocumentManager in modo lazy."""
    global metadata_manager
    if metadata_manager is None:
        try:
            metadata_manager = DocumentManager()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Errore inizializzazione DocumentManager: {str(e)}"
            )
    return metadata_manager


def validate_document_input(data: Dict[str, Any], require_collection: bool = True) -> Dict[str, Any]:
    """
    Valida che il documento abbia sia content che metadata obbligatori.
    
    Args:
        data: Document data from request
        require_collection: Se True, richiede il campo 'collection' (default: True)
    
    Returns:
        Dict: Validated and normalized document data
    
    Raises:
        HTTPException: Se validazione fallisce
    """
    # Verifica che content sia presente e non vuoto
    if 'content' not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo 'content' obbligatorio per Mind documents. Impossibile creare documento senza contenuto."
        )
    
    content = data.get('content', '').strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo 'content' non può essere vuoto. Il contenuto semantico è obbligatorio per Mind."
        )
    
    # Verifica che metadata sia presente e non vuoto
    if 'metadata' not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo 'metadata' obbligatorio per Mind documents. Impossibile creare documento senza metadati."
        )
    
    metadata = data.get('metadata')
    if not isinstance(metadata, dict) or len(metadata) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo 'metadata' deve essere un oggetto non vuoto. I metadati sono obbligatori per Mind."
        )
    
    # Verifica collection se richiesto
    if require_collection and 'collection' not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo 'collection' obbligatorio per Mind documents."
        )
    
    # Normalizza i dati
    return {
        'id': data.get('id') or f"doc{uuid.uuid4().hex[:8]}",
        'collection': data.get('collection', 'mind_default'),
        'content': content,
        'metadata': metadata
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_mind_document(document: Dict[str, Any] = Body(...)):
    """
    Create a new document for PramaIA-Mind with strict validation.
    
    REQUIRED fields:
    - content (string, non-empty): Semantic content/text to be embedded
    - metadata (object, non-empty): Document metadata (tags, source, etc.)
    - collection (string): Collection name (default: 'mind_default')
    - id (string, optional): Document ID (auto-generated if not provided)
    
    REJECTED:
    - Document with content but no metadata
    - Document with metadata but no content
    - Empty content or metadata
    
    Args:
        document: Document data with required fields
    
    Returns:
        Dict: Created document with id, collection, content, metadata
    
    Raises:
        HTTPException 400: If validation fails (missing or empty required fields)
        HTTPException 500: If save fails
    """
    try:
        # Valida input
        validated_doc = validate_document_input(document, require_collection=True)
        
        # Aggiungi timestamp
        if 'created_at' not in validated_doc['metadata']:
            validated_doc['metadata']['created_at'] = datetime.now().isoformat()
        
        # Salva il documento in ENTRAMBI i database (SQLite + ChromaDB)
        manager = get_metadata_manager()
        success = manager.add_document(
            doc_id=validated_doc['id'],
            content=validated_doc['content'],
            metadata=validated_doc['metadata']
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante il salvataggio del documento in Mind"
            )
        
        # Verifica il salvataggio
        saved_doc = manager.get_document(validated_doc['id'])
        if not saved_doc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Documento salvato ma non verificabile"
            )
        
        return {
            "id": validated_doc['id'],
            "collection": validated_doc['collection'],
            "content": validated_doc['content'],
            "metadata": validated_doc['metadata'],
            "message": "Mind document created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore creazione Mind document: {str(e)}"
        )


@router.get("/{document_id}")
async def get_mind_document(document_id: str):
    """
    Get a specific document for PramaIA-Mind.
    
    Returns complete document with all metadata.
    
    Args:
        document_id: ID of the document to retrieve
    
    Returns:
        Dict: Document with id, collection, content, metadata
    
    Raises:
        HTTPException 404: If document not found
    """
    try:
        manager = get_metadata_manager()
        document = manager.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mind document {document_id} non trovato"
            )
        
        return {
            "id": document.get('id'),
            "collection": document.get('collection'),
            "content": document.get('content'),
            "metadata": document.get('metadata', {}),
            "message": "Mind document retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore recupero Mind document: {str(e)}"
        )


@router.post("/{document_id}", status_code=status.HTTP_200_OK)
async def update_mind_document(document_id: str, document: Dict[str, Any] = Body(...)):
    """
    Update a Mind document with strict validation.
    
    REQUIRED fields (same as create):
    - content (string, non-empty): Updated semantic content
    - metadata (object, non-empty): Updated metadata
    
    Collection cannot be changed. Use delete + create if needed.
    
    Args:
        document_id: ID of document to update
        document: Updated document data
    
    Returns:
        Dict: Updated document
    
    Raises:
        HTTPException 400: If validation fails
        HTTPException 404: If document not found
        HTTPException 500: If update fails
    """
    try:
        manager = get_metadata_manager()
        
        # Verifica che documento esista
        existing = manager.get_document(document_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mind document {document_id} non trovato"
            )
        
        # Valida l'update (richiede content+metadata)
        content = document.get('content', existing.get('content', '')).strip()
        metadata = document.get('metadata', existing.get('metadata', {}))
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campo 'content' non può essere vuoto. Il contenuto semantico è obbligatorio per Mind."
            )
        
        if not isinstance(metadata, dict) or len(metadata) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campo 'metadata' deve essere un oggetto non vuoto. I metadati sono obbligatori per Mind."
            )
        
        # Crea il documento aggiornato
        updated_doc = {
            'id': document_id,
            'collection': existing.get('collection'),
            'content': content,
            'metadata': metadata
        }
        
        # Aggiungi timestamp di update
        updated_doc['metadata']['updated_at'] = datetime.now().isoformat()
        # Mantieni il created_at originale
        if 'created_at' in existing.get('metadata', {}):
            updated_doc['metadata']['created_at'] = existing['metadata']['created_at']
        
        # Aggiorna in ENTRAMBI i database (SQLite + ChromaDB)
        success = manager.add_document(
            doc_id=updated_doc['id'],
            content=updated_doc['content'],
            metadata=updated_doc['metadata']
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante l'update del Mind document"
            )
        
        return {
            "id": updated_doc['id'],
            "collection": updated_doc['collection'],
            "content": updated_doc['content'],
            "metadata": updated_doc['metadata'],
            "message": "Mind document updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore update Mind document: {str(e)}"
        )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_mind_document(document_id: str):
    """
    Delete a Mind document.
    
    Args:
        document_id: ID of document to delete
    
    Returns:
        Dict: Confirmation message
    
    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If delete fails
    """
    try:
        manager = get_metadata_manager()
        
        # Verifica che documento esista
        existing = manager.get_document(document_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mind document {document_id} non trovato"
            )
        
        # Elimina da ENTRAMBI i database (SQLite + ChromaDB)
        success = manager.delete_document(document_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante l'eliminazione del Mind document"
            )
        
        return {
            "id": document_id,
            "message": "Mind document deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore delete Mind document: {str(e)}"
        )


@router.post("/{collection_name}/query", status_code=status.HTTP_200_OK)
async def query_mind_documents(
    collection_name: str,
    query_data: Dict[str, Any] = Body(...),
    limit: int = 10
):
    """
    Semantic search for Mind documents with full metadata in results.
    
    This endpoint returns COMPLETE metadata from SQLite (including tags, timestamps, etc.)
    not just sparse ChromaDB metadata.
    
    Args:
        collection_name: Collection to search in
        query_data: Dict with 'query_text' field (semantic query text)
        limit: Max results (default: 10)
    
    Returns:
        Dict: List of matching documents with {id, content, metadata, similarity_score}
    """
    try:
        query_text = query_data.get('query_text', '').strip() if isinstance(query_data, dict) else ''
        
        if not query_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campo 'query_text' obbligatorio e non può essere vuoto"
            )
        
        if limit <= 0 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parametro 'limit' deve essere tra 1 e 100"
            )
        
        manager = get_metadata_manager()
        
        # Ricerca semantica con enrichment metadata da SQLite
        results = manager.search_documents(
            query=query_text,
            limit=limit,
            where=None
        )
        
        if not results:
            results = []
        
        return {
            "collection": collection_name,
            "query": query_text,
            "matches": results,
            "count": len(results),
            "message": "Mind documents query executed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore query Mind documents: {str(e)}"
        )


@router.get("/", status_code=status.HTTP_200_OK)
async def list_mind_documents(collection_name: Optional[str] = None, limit: int = 50):
    """
    List Mind documents from a collection.
    
    Args:
        collection_name: Optional collection filter
        limit: Max results (default: 50)
    
    Returns:
        Dict: List of documents with full metadata
    """
    try:
        manager = get_metadata_manager()
        all_docs = manager.list_all_documents()
        
        # Filter by collection if provided
        if collection_name:
            all_docs = [
                doc for doc in all_docs 
                if manager.get_document(doc) and 
                manager.get_document(doc).get('collection') == collection_name
            ]
        
        # Apply limit
        docs = []
        for doc_id in all_docs[:limit]:
            doc = manager.get_document(doc_id)
            if doc:
                docs.append({
                    "id": doc.get('id'),
                    "collection": doc.get('collection'),
                    "content": doc.get('content', '')[:200] + "..." if len(doc.get('content', '')) > 200 else doc.get('content'),
                    "metadata": doc.get('metadata', {}),
                })
        
        return {
            "collection": collection_name,
            "documents": docs,
            "count": len(docs),
            "total": len(all_docs),
            "message": "Mind documents listed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore list Mind documents: {str(e)}"
        )
