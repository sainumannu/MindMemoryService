from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import time
import json
import os
from pathlib import Path

from app.core.config import get_settings
from app.core.logger import get_logger
from app.services.health import get_service_health
from app.services.reconciliation import get_next_scheduled_run

logger = get_logger(__name__)
app_settings = get_settings()

router = APIRouter(prefix="/settings", tags=["settings"])

# Schema per le impostazioni
class VectorstoreSettings(BaseModel):
    schedule_enabled: bool = True
    schedule_time: str = "03:00"
    chroma_persist_dir: str = "data/chroma_db"
    chroma_collection_name: str = "prama_documents"
    max_worker_threads: int = 4
    batch_size: int = 100

# Percorso del file di configurazione
CONFIG_PATH = Path(os.environ.get("VECTORSTORE_CONFIG_PATH", 
                                 os.path.join(app_settings.app_dir, "config", "settings.json")))

# Assicurati che la directory config esista
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_settings():
    """Carica le impostazioni dal file di configurazione"""
    if not CONFIG_PATH.exists():
        # Crea il file con le impostazioni predefinite
        default_settings = VectorstoreSettings()
        save_settings(default_settings)
        return default_settings
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
        return VectorstoreSettings(**data)
    except Exception as e:
        logger.error(f"Errore nel caricamento delle impostazioni: {e}")
        return VectorstoreSettings()

def save_settings(settings_data: VectorstoreSettings):
    """Salva le impostazioni nel file di configurazione"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(settings_data.dict(), f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Errore nel salvare le impostazioni: {e}")
        return False

@router.get("/")
async def get_vectorstore_settings():
    """Recupera le impostazioni correnti del servizio"""
    try:
        settings = load_settings()
        return settings
    except Exception as e:
        logger.error(f"Errore nel recuperare le impostazioni: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nel recuperare le impostazioni: {str(e)}")

@router.post("/")
async def update_settings(settings_data: VectorstoreSettings):
    """Aggiorna le impostazioni del servizio"""
    try:
        # Salva le nuove impostazioni
        success = save_settings(settings_data)
        if not success:
            raise HTTPException(status_code=500, detail="Errore nel salvare le impostazioni")
        
        # Aggiorna le variabili d'ambiente per le nuove connessioni
        os.environ["CHROMA_PERSIST_DIR"] = settings_data.chroma_persist_dir
        os.environ["CHROMA_COLLECTION_NAME"] = settings_data.chroma_collection_name
        os.environ["MAX_WORKER_THREADS"] = str(settings_data.max_worker_threads)
        os.environ["BATCH_SIZE"] = str(settings_data.batch_size)
        os.environ["SCHEDULE_ENABLED"] = str(settings_data.schedule_enabled).lower()
        os.environ["SCHEDULE_TIME"] = settings_data.schedule_time
        
        return {"status": "success", "message": "Impostazioni aggiornate con successo"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nell'aggiornare le impostazioni: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nell'aggiornare le impostazioni: {str(e)}")

@router.get("/status")
async def get_status():
    """Recupera lo stato corrente del servizio"""
    try:
        # Ottieni lo stato del servizio
        health_status = await get_service_health()
        
        # Aggiungi informazioni sulla pianificazione
        settings = load_settings()
        next_run = None
        
        if settings.schedule_enabled:
            next_run = get_next_scheduled_run(settings.schedule_time)
        
        return {
            "status": "healthy" if health_status["status"] == "ok" else "degraded",
            "version": app_settings.app_version,
            "dependencies": health_status.get("dependencies", {}),
            "scheduler_enabled": settings.schedule_enabled,
            "next_reconciliation": next_run.isoformat() if next_run else None,
            "chroma_connected": health_status.get("dependencies", {}).get("chroma", {}).get("connected", False)
        }
    except Exception as e:
        logger.error(f"Errore nel recuperare lo stato del servizio: {e}")
        raise HTTPException(status_code=500, detail=f"Errore nel recuperare lo stato del servizio: {str(e)}")
