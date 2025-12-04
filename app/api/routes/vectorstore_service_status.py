"""
Aggiunge l'endpoint per ottenere lo stato del servizio VectorStore in modo dettagliato.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
import os
import logging
import json
import sqlite3
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.utils.sqlite_metadata_manager import SQLiteMetadataManager
from app.utils.document_manager import DocumentManager
from app.core.config import Settings, get_settings

# Configurazione logger
logger = logging.getLogger(__name__)

# Creazione del router
router = APIRouter(prefix="/api/database-management/vectorstore", tags=["vectorstore-settings"])

# Directory per i backup
BACKUP_DIR = os.path.join(os.getcwd(), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

@router.get("/service-status")
async def get_service_status(settings: Settings = Depends(get_settings)):
    """
    Restituisce lo stato dettagliato del servizio VectorStore, incluso il check di tutti i componenti.
    """
    return await get_service_status_internal(settings)

@router.get("/status")
async def get_service_status_alias(settings: Settings = Depends(get_settings)):
    """
    Alias per la compatibilità con il frontend esistente.
    """
    return await get_service_status_internal(settings)

async def get_service_status_internal(settings: Settings = Depends(get_settings)):
    """
    Implementazione interna per la funzionalità di stato del servizio VectorStore.
    """
    try:
        # Inizializza metadata store manager
        # metadata_manager = ExtendedMetadataStoreManager()
        metadata_manager = DocumentManager()  # Uso DocumentManager base
        
        # Verifica la connessione al ChromaDB
        # Controllo connessione usando get_statistics
        try:
            stats = metadata_manager.get_statistics()
            chroma_connected = True
        except Exception:
            chroma_connected = False
        
        # Ottieni le statistiche
        stats = metadata_manager.get_statistics()
        
        # Determina lo stato generale del servizio in base a diverse condizioni
        has_documents = stats.get("total_documents", 0) > 0
        collections = stats.get("collections", [])
        has_collections = len(collections) > 0 if isinstance(collections, list) else False
        
        # Log di debug per vedere i valori esatti
        logger.info(f"DEBUG - Status check - ChromaDB connected: {chroma_connected}")
        logger.info(f"DEBUG - Status check - Has documents: {has_documents} (total: {stats.get('total_documents', 0)})")
        logger.info(f"DEBUG - Status check - Has collections: {has_collections} (collections: {stats.get('collections', [])})")
        
        # Il servizio è considerato completamente operativo se:
        # 1. ChromaDB è connesso
        # 2. Ci sono documenti indicizzati
        # 3. Ci sono collezioni create
        service_healthy = chroma_connected and has_documents and has_collections
        service_partial = chroma_connected and (not has_documents or not has_collections)
        
        logger.info(f"DEBUG - Status result - Healthy: {service_healthy}, Partial: {service_partial}")
        
        # Determina il motivo dello stato parziale
        status_message = None
        if service_partial:
            if not has_documents and not has_collections:
                status_message = "nessun dato"
            elif not has_documents:
                status_message = "nessun documento"
            elif not has_collections:
                status_message = "nessuna collezione"
            
            logger.info(f"DEBUG - Status message: {status_message}")
        
        # Determina lo stato finale del servizio
        if service_healthy:
            status = "healthy"  # Tutto funziona correttamente
        elif service_partial:
            status = "partial"  # ChromaDB funziona ma mancano dati
        else:
            status = "error"    # ChromaDB non è connesso
        
        # Determina se lo scheduler è attivo
        scheduler_enabled = getattr(settings, "schedule_enabled", False)
        
        # Calcola la prossima esecuzione della riconciliazione
        next_reconciliation = None
        if scheduler_enabled:
            try:
                schedule_time = getattr(settings, "schedule_time", "03:00")
                # Logica per calcolare la prossima esecuzione
                hour, minute = map(int, schedule_time.split(":"))
                now = datetime.now()
                next_run = datetime(now.year, now.month, now.day, hour, minute)
                if next_run <= now:
                    # Se l'orario è già passato oggi, la prossima esecuzione è domani
                    import datetime as dt
                    next_run = next_run + dt.timedelta(days=1)
                next_reconciliation = next_run.strftime("%Y-%m-%d %H:%M")
            except Exception as e:
                logger.error(f"Errore nel calcolo della prossima riconciliazione: {str(e)}")
        
        # Ottieni la versione dalle impostazioni senza fallback
        app_version = settings.app_version
        
        # Crea la risposta completa
        response = {
            "status": status,  # Utilizziamo lo stato calcolato in base alle reali condizioni
            "status_message": status_message,  # Aggiungiamo il messaggio del motivo dello stato
            "version": app_version,  # Versione dell'applicazione
            "chroma_connected": chroma_connected,
            "documents_in_index": stats.get("total_documents", 0),
            "collections": stats.get("collections", []),
            "scheduler_enabled": scheduler_enabled,
            "next_reconciliation": next_reconciliation,
            "debug_info": {
                "chroma_connected": chroma_connected,
                "has_documents": has_documents,
                "documents_count": stats.get("total_documents", 0),
                "has_collections": has_collections,
                "collections": stats.get("collections", []),
                "service_healthy": service_healthy,
                "service_partial": service_partial
            },
            "dependencies": {
                "chroma": {
                    "status": "healthy" if chroma_connected else "error",
                    "mode": "persistent_local",  # Modalità persistente locale
                    "details": {
                        "host": getattr(settings, "CHROMA_HOST", "localhost"),
                        "port": getattr(settings, "CHROMA_PORT", 8000)
                    }
                }
            }
        }
        
        # Log della risposta completa
        logger.info(f"DEBUG - Full response: {response}")
        
        return response
    except Exception as e:
        logger.error(f"Errore nel recupero dello stato del servizio: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "chroma_connected": False,
            "scheduler_enabled": False
        }
