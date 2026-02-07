# -*- coding: utf-8 -*-
"""
PramaIA-MindMemoryService - Servizio centralizzato per la gestione della memoria di Mind.

Questo servizio fornisce:
1. API REST completa per operazioni CRUD sul vectorstore
2. Riconciliazione pianificata tra filesystem e vectorstore
3. Gestione delle collezioni e dei namespace
4. Operazioni di embedding e recupero documenti
5. Monitoraggio avanzato delle modifiche ai file
"""


import os
import sys
import logging
import signal
import traceback
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
from contextlib import asynccontextmanager

# Configurazione logging
from app.utils.logger_simple import setup_logging

# Importa router API
from app.api import api_router

# Importa il file watcher personalizzato
from app.utils.file_watcher import FileWatcher, start_file_watcher, FileChange

# Carica variabili d'ambiente
load_dotenv()

# Configura logger
# Configura logger
logger = setup_logging()

# --- HANDLER GLOBALE ECCEZIONI E SEGNALI ---
def log_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    msg = "\n[UNCAUGHT EXCEPTION] {}: {}\n{}".format(
        exc_type.__name__, exc_value, ''.join(traceback.format_tb(exc_traceback)))
    logger.critical(msg)
    print(msg, file=sys.stderr)

def handle_signal(sig, frame):
    logger.critical(f"Ricevuto segnale {sig}. Stacktrace:\n{''.join(traceback.format_stack(frame))}")
    print(f"[CRITICAL] Ricevuto segnale {sig}. Stacktrace:\n{''.join(traceback.format_stack(frame))}", file=sys.stderr)
    sys.exit(1)

sys.excepthook = log_uncaught_exception
for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, handle_signal)

# Variabile globale per il file watcher
file_watcher = None

def file_change_handler(change: FileChange):
    """Handler per i cambiamenti rilevati nei file."""
    rel_path = os.path.relpath(change.path, os.getcwd())
    logger.info(f"Cambiamento rilevato: {change.change_type.value.upper()} - File: {rel_path}")
    
    # Log dettagliati sui metadati
    if change.metadata:
        if change.change_type.value == "created":
            logger.info(f"Nuovo file creato: {rel_path}, "
                      f"dimensione: {change.metadata.get('size', 'N/A')} bytes, "
                      f"estensione: {change.metadata.get('extension', 'N/A')}")
        elif change.change_type.value == "modified":
            logger.info(f"File modificato: {rel_path}, "
                      f"dimensione: {change.metadata.get('size', 'N/A')} bytes, "
                      f"orario precedente: {datetime.fromtimestamp(change.metadata.get('previous_mtime', 0)).strftime('%H:%M:%S')}, "
                      f"orario attuale: {datetime.fromtimestamp(change.metadata.get('current_mtime', 0)).strftime('%H:%M:%S')}")
        elif change.change_type.value == "deleted":
            logger.info(f"File eliminato: {rel_path}, "
                      f"estensione: {change.metadata.get('extension', 'N/A')}")

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Gestisce il ciclo di vita dell'applicazione.
    Questo sostituisce i vecchi gestori di eventi on_event("startup") e on_event("shutdown").
    """
    # --- Codice di startup ---
    global file_watcher
    
    try:
        logger.info("Inizializzazione MindMemoryService...")
        
        # Inizializza ChromaDB Manager (in modalita persistente locale)
        from app.core.vectordb_manager import vector_db_manager
        chroma_status = vector_db_manager.get_status()
        logger.info(f"ChromaDB inizializzato in modalita persistente locale. Stato: {chroma_status.get('status')}")
        
        # Avvia il file watcher personalizzato
        monitored_paths = [
            os.getcwd(),  # Directory corrente
            # Aggiungi altri percorsi da monitorare
        ]
        
        # Configura ed avvia il file watcher
        file_watcher = start_file_watcher(
            paths=monitored_paths,
            on_change_callback=file_change_handler,
            interval=1.0,  # Controlla ogni secondo
            exclude_patterns=[
                "*.pyc", "*.pyo", "*.pyd", "__pycache__/*", "*.git/*", "*.log",
                "logs/*", "event_buffer.db", "*.db", "temp/*",
                # Escludi directory ChromaDB (file binari interni)
                "data/chroma_db/*", "data\\chroma_db\\*", 
                "*/chroma_db/*", "*\\chroma_db\\*",
                "*.bin",  # File binari ChromaDB
                # Escludi altre directory di sistema
                ".venv/*", "venv/*", "node_modules/*", 
                "backups/*", ".pytest_cache/*"
            ]
        )
        logger.info(f"File watcher avviato su {len(monitored_paths)} percorsi")
        
        logger.info(f"MindMemoryService avviato con successo. Versione: 1.0.0")
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione: {str(e)}")
        # In un ambiente di produzione, potremmo voler terminare il processo
        # sys.exit(1)
    
    # Yield control to FastAPI to handle requests
    yield
    
    # --- Codice di shutdown ---
    try:
        logger.info("Arresto MindMemoryService...")
        
        # Arresta file watcher
        if file_watcher:
            file_watcher.stop()
            logger.info("File watcher arrestato.")
        
        logger.info("MindMemoryService arrestato con successo.")
    except Exception as e:
        logger.error(f"Errore durante l'arresto: {str(e)}")

# Crea applicazione FastAPI con il nuovo gestore del ciclo di vita
app = FastAPI(
    title="PramaIA MindMemoryService",
    description="Servizio centralizzato per la gestione del vectorstore e la riconciliazione con il filesystem",
    version="1.0.0",
    lifespan=app_lifespan  # Usiamo il nuovo gestore del ciclo di vita invece di on_event
)

# Configurazioni aggiuntive
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione, specificare domini specifici
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aggiungi i router all'app
app.include_router(api_router)

# Aggiungi un endpoint radice per /reset per la compatibilità con il frontend
from fastapi import BackgroundTasks
import os
import logging
from datetime import datetime
from app.utils.sqlite_metadata_manager import SQLiteMetadataManager

doc_db = SQLiteMetadataManager()
logger = logging.getLogger(__name__)

@app.post("/reset")
async def reset_database_root():
    """
    Endpoint semplificato per resettare il database documenti (compatibilità frontend).
    """
    try:
        logger.info("Richiesta reset database ricevuta su endpoint root /reset")
        
        # Reset diretto del database SQLite
        import os
        
        # Ottieni il percorso del database
        db_path = doc_db.db_file
        logger.info(f"Resettando database: {db_path}")
        
        # Chiudi eventuali connessioni
        if hasattr(doc_db, '_connection') and doc_db._connection:
            doc_db._connection.close()
            
        # Rimuovi il file del database
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Database file rimosso: {db_path}")
            
        # Ricrea il database vuoto
        doc_db._init_database()
        logger.info("Database ricreato vuoto")
        
        return {
            "success": True,
            "message": "Database SQL resettato con successo",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Errore nel reset del database: {str(e)}")
        return {
            "success": False,
            "message": f"Errore nel reset: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    port = int(os.getenv("VECTORSTORE_PORT", os.getenv("PORT", "8090")))
    host = os.getenv("HOST", "0.0.0.0")
    workers = int(os.getenv("WORKERS", "1"))  # Default 1 worker, configurabile via env
    
    logger.info(f"Avvio MindMemoryService su http://{host}:{port}")
    logger.info(f"Configurazione: {workers} worker(s), SQLite WAL mode, async FastAPI")
    
    # Configurazione uvicorn per NON sovrascrivere il logging
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "WARNING"},
            "uvicorn.error": {"handlers": ["default"], "level": "WARNING"},
            "uvicorn.access": {"handlers": ["default"], "level": "WARNING"},
        },
    }
    
    # Avvia server Uvicorn
    if workers > 1:
        # Multi-worker: usa uvicorn programmatically con gunicorn-style
        logger.warning("Multi-worker richiede attenzione: singleton (model cache) sarà duplicato per worker")
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            workers=workers,
            reload=False,
            log_config=log_config
        )
    else:
        # Single-worker: configurazione standard
        uvicorn.run(
            "main:app", 
            host=host, 
            port=port, 
            reload=False,
            log_config=log_config
        )
