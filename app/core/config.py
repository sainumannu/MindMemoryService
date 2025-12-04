"""
Configurazione del servizio VectorstoreService.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel, Field
import json

# Logger
logger = logging.getLogger(__name__)

class Settings(BaseModel):
    """
    Impostazioni di configurazione per il servizio.
    """
    # Informazioni sull'applicazione
    app_name: str = "PramaIA-VectorstoreService"
    app_version: str = "1.0.0"
    app_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Informazioni sul server
    host: str = "0.0.0.0"
    port: int = 8090
    
    # Impostazioni di ChromaDB
    chroma_persist_dir: str = "data/chroma_db"
    chroma_collection_name: str = "prama_documents"
    
    # Impostazioni di pianificazione
    schedule_enabled: bool = True
    schedule_time: str = "03:00"
    
    # Impostazioni di elaborazione
    max_worker_threads: int = 4
    batch_size: int = 100
    
    # Impostazioni database
    SQLITE_DB_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "documents.db")

def get_settings() -> Settings:
    """
    Restituisce le impostazioni del servizio.
    """
    return Settings()

# Carica impostazioni da settings.json
def load_settings_from_json() -> Dict[str, Any]:
    """
    Carica le impostazioni dal file settings.json.
    """
    config_path = os.path.join(get_settings().app_dir, "config", "settings.json")
    
    if not os.path.exists(config_path):
        logger.warning(f"File di configurazione {config_path} non trovato. Utilizzo impostazioni predefinite.")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Errore nel caricamento delle impostazioni dal file {config_path}: {str(e)}")
        return {}
