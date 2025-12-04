"""
Endpoint di configurazione dinamica per VectorstoreService.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os

logger = logging.getLogger(__name__)

router = APIRouter()

class VectorStoreConfig(BaseModel):
    """Modello per la configurazione del VectorStore."""
    chroma_host: Optional[str] = None
    chroma_port: Optional[int] = None
    batch_size: Optional[int] = None
    max_worker_threads: Optional[int] = None

class ConfigResponse(BaseModel):
    """Modello per la risposta di configurazione."""
    success: bool
    message: str
    config: Dict[str, Any]

@router.post("/configure", response_model=ConfigResponse)
async def update_vectorstore_configuration(config: VectorStoreConfig):
    """
    Aggiorna la configurazione del VectorStore Service.
    
    Args:
        config: Nuova configurazione del VectorStore
        
    Returns:
        ConfigResponse: Risultato dell'aggiornamento
    """
    try:
        logger.info(f"Aggiornamento configurazione VectorStore: {config.dict(exclude_unset=True)}")
        
        # Percorso del file di configurazione
        config_file = os.path.join(os.getcwd(), "config", "vectorstore_config.json")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        # Carica configurazione esistente o crea nuova
        current_config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    current_config = json.load(f)
            except Exception as e:
                logger.warning(f"Errore lettura configurazione esistente: {e}")
                current_config = {}
        
        # Aggiorna solo i parametri forniti
        config_updates = config.dict(exclude_unset=True)
        current_config.update(config_updates)
        
        # Salva la nuova configurazione
        with open(config_file, 'w') as f:
            json.dump(current_config, f, indent=2)
        
        logger.info(f"Configurazione salvata in: {config_file}")
        
        # TODO: Ricarica la configurazione nel servizio
        # Questo richiederà una ristrutturazione del servizio per supportare
        # il ricaricamento dinamico della configurazione
        
        return ConfigResponse(
            success=True,
            message="Configurazione aggiornata con successo. Riavvio del servizio necessario per applicare le modifiche.",
            config=current_config
        )
        
    except Exception as e:
        logger.error(f"Errore aggiornamento configurazione: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno durante l'aggiornamento della configurazione: {str(e)}"
        )

@router.get("/configure", response_model=Dict[str, Any])
async def get_vectorstore_configuration():
    """
    Ottiene la configurazione corrente del VectorStore Service.
    
    Returns:
        Dict: Configurazione corrente
    """
    try:
        # Configurazione da file
        config_file = os.path.join(os.getcwd(), "config", "vectorstore_config.json")
        file_config = {}
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
            except Exception as e:
                logger.warning(f"Errore lettura configurazione: {e}")
        
        # Configurazione da variabili d'ambiente (fallback)
        env_config = {
            "chroma_host": os.getenv("CHROMA_HOST", "localhost"),
            "chroma_port": int(os.getenv("CHROMA_PORT", "8000")),
            "batch_size": int(os.getenv("VECTORSTORE_BATCH_SIZE", "100")),
            "max_worker_threads": int(os.getenv("MAX_WORKER_THREADS", "4"))
        }
        
        # Unisci configurazioni (file ha precedenza)
        current_config = {**env_config, **file_config}
        
        return {
            "current_config": current_config,
            "config_source": "file" if file_config else "environment",
            "config_file": config_file
        }
        
    except Exception as e:
        logger.error(f"Errore lettura configurazione: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno durante la lettura della configurazione: {str(e)}"
        )

@router.post("/restart")
async def restart_service():
    """
    Riavvia il servizio per applicare le nuove configurazioni.
    
    Returns:
        Dict: Stato del riavvio
    """
    try:
        logger.info("Riavvio del VectorStore Service richiesto")
        
        # TODO: Implementare riavvio graceful del servizio
        # Per ora restituiamo un messaggio informativo
        
        return {
            "success": True,
            "message": "Riavvio del servizio richiesto. Implementare meccanismo di riavvio graceful.",
            "restart_required": True
        }
        
    except Exception as e:
        logger.error(f"Errore riavvio servizio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno durante il riavvio: {str(e)}"
        )