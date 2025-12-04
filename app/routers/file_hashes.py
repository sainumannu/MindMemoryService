"""
Router per la gestione degli hash dei file nel VectorstoreService.
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
import hashlib
from pydantic import BaseModel, Field

from app.utils.file_hash_manager import FileHashManager
from app.dependencies.auth import get_api_key

# Istanzia il gestore degli hash
file_hash_manager = FileHashManager()

router = APIRouter(
    prefix="/api/file-hashes",
    tags=["file-hashes"],
    responses={404: {"description": "Non trovato"}},
)

class DuplicateCheckRequest(BaseModel):
    """Modello per la richiesta di controllo duplicati."""
    file_hash: str = Field(..., description="Hash MD5 del file")
    filename: str = Field(..., description="Nome del file")
    client_id: str = Field("system", description="ID del client")
    original_path: str = Field("", description="Percorso originale del file")

class DuplicateCheckResponse(BaseModel):
    """Modello per la risposta al controllo duplicati."""
    is_duplicate: bool = Field(..., description="Indica se il file è un duplicato")
    document_id: Optional[str] = Field(None, description="ID del documento duplicato, se presente")
    is_path_duplicate: bool = Field(False, description="Indica se è un duplicato esatto del percorso")
    
class SaveHashRequest(BaseModel):
    """Modello per la richiesta di salvataggio hash."""
    file_hash: str = Field(..., description="Hash MD5 del file")
    filename: str = Field(..., description="Nome del file")
    document_id: str = Field(..., description="ID del documento")
    client_id: str = Field("system", description="ID del client")
    original_path: str = Field("", description="Percorso originale del file")
    
class HashRecord(BaseModel):
    """Modello per un record di hash."""
    file_hash: str
    file_name: str
    document_id: str
    upload_time: str
    file_path: str = ""
    client_id: str = "system"
    original_path: str = ""
    
class MigrationRequest(BaseModel):
    """Modello per la richiesta di migrazione."""
    backend_db_path: str = Field(..., description="Percorso al database del backend")

class MigrationResponse(BaseModel):
    """Modello per la risposta alla migrazione."""
    success: bool
    total_migrated: int
    errors: int
    message: str


@router.post("/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate(
    request: DuplicateCheckRequest,
    api_key: str = Depends(get_api_key)
) -> DuplicateCheckResponse:
    """
    Controlla se un file è un duplicato basandosi sull'hash.
    """
    is_duplicate, document_id, is_path_duplicate = file_hash_manager.check_duplicate(
        file_hash=request.file_hash,
        client_id=request.client_id,
        original_path=request.original_path
    )
    
    return DuplicateCheckResponse(
        is_duplicate=is_duplicate,
        document_id=document_id,
        is_path_duplicate=is_path_duplicate
    )
    
@router.post("/save", status_code=201)
async def save_hash(
    request: SaveHashRequest,
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """
    Salva l'hash di un file nel database.
    """
    success = file_hash_manager.save_file_hash(
        file_hash=request.file_hash,
        filename=request.filename,
        document_id=request.document_id,
        client_id=request.client_id,
        original_path=request.original_path
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Impossibile salvare l'hash del file")
        
    return {"success": True, "message": "Hash salvato con successo"}
    
@router.get("/list", response_model=List[HashRecord])
async def list_hashes(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    api_key: str = Depends(get_api_key)
) -> List[HashRecord]:
    """
    Ottiene tutti gli hash dal database.
    """
    all_hashes = file_hash_manager.get_all_hashes()
    
    # Applica paginazione
    paginated_hashes = all_hashes[offset:offset + limit]
    
    return paginated_hashes
    
@router.delete("/{file_hash}")
async def delete_hash(
    file_hash: str,
    api_key: str = Depends(get_api_key)
) -> Dict[str, Any]:
    """
    Elimina un hash dal database.
    """
    success = file_hash_manager.delete_hash(file_hash)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Hash {file_hash} non trovato")
        
    return {"success": True, "message": f"Hash {file_hash} eliminato con successo"}
    
@router.post("/migrate", response_model=MigrationResponse)
async def migrate_hashes(
    request: MigrationRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key)
) -> MigrationResponse:
    """
    Migra gli hash dal database del backend.
    Questa operazione può richiedere tempo, quindi viene eseguita in background.
    """
    # Verifica che il database esista
    import os
    if not os.path.exists(request.backend_db_path):
        raise HTTPException(status_code=404, detail=f"Database {request.backend_db_path} non trovato")
    
    # Avvia la migrazione in background
    background_tasks.add_task(
        file_hash_manager.migrate_from_backend_db,
        request.backend_db_path
    )
    
    return MigrationResponse(
        success=True,
        total_migrated=0,  # Non conosciamo ancora il risultato
        errors=0,
        message=f"Migrazione avviata in background dal database {request.backend_db_path}"
    )