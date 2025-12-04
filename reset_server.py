#!/usr/bin/env python3
"""
Server API dedicato per il reset del database SQL
"""
import sys
import os

# Aggiungi il percorso del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from datetime import datetime

# Import del nostro SQLite manager
from app.utils.sqlite_metadata_manager import SQLiteMetadataManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea app FastAPI dedicata
app = FastAPI(title="Database Reset API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inizializza il manager SQLite
doc_db = SQLiteMetadataManager()

@app.get("/")
async def root():
    return {"message": "Database Reset API attivo - Endpoint: POST /reset"}

@app.post("/reset")
async def reset_database():
    """Endpoint dedicato per il reset del database SQL"""
    try:
        logger.info("🔄 Richiesta reset database SQL ricevuta")
        
        # Ottieni il percorso del database
        db_path = doc_db.db_file
        logger.info(f"📁 Percorso database: {db_path}")
        
        # Verifica se il database esiste
        if os.path.exists(db_path):
            # Rimuovi il file del database
            os.remove(db_path)
            logger.info(f"🗑️ Database file rimosso: {db_path}")
        else:
            logger.info("ℹ️ Database non esisteva, creazione nuovo database")
            
        # Ricrea il database vuoto
        doc_db._init_database()
        logger.info("✅ Database SQL ricreato vuoto")
        
        return {
            "success": True,
            "message": "Database SQL resettato con successo",
            "database_path": db_path,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Errore nel reset del database SQL: {str(e)}")
        return {
            "success": False,
            "message": f"Errore nel reset: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/status")
async def database_status():
    """Endpoint per verificare lo stato del database"""
    try:
        # Conta i documenti
        count = doc_db.get_document_count()
        db_path = doc_db.db_file
        db_exists = os.path.exists(db_path)
        
        return {
            "database_exists": db_exists,
            "database_path": db_path,
            "document_count": count,
            "status": "healthy" if db_exists else "missing",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    print("🚀 Avvio Database Reset API Server...")
    print("📍 Server in ascolto su: http://localhost:8093")
    print("🔧 Endpoint principale: POST http://localhost:8093/reset")
    print("📊 Stato database: GET http://localhost:8093/status")
    uvicorn.run(app, host="0.0.0.0", port=8093)