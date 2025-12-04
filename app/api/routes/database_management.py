"""
API routes per la gestione del database documenti e vector store.
Aggiunge gli endpoint necessari per supportare i nuovi componenti frontend.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
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
# from app.utils.database_admin_manager import DatabaseAdminManager  # Temporaneamente disabilitato

# Configurazione logger
logger = logging.getLogger(__name__)

# Creazione del router
router = APIRouter(prefix="/api/database-management", tags=["database"])

# Inizializzazione delle dipendenze
doc_db = SQLiteMetadataManager()
vector_manager = DocumentManager()
# admin_manager = DatabaseAdminManager()  # Temporaneamente disabilitato

# Directory per i backup
BACKUP_DIR = os.path.join(os.getcwd(), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

# Utility function per ottenere la dimensione del file
def get_file_size(file_path: str) -> int:
    """Ottiene la dimensione di un file in bytes."""
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Errore nel calcolo della dimensione del file {file_path}: {str(e)}")
        return 0

# Utility function per creare un timestamp formattato
def get_timestamp() -> str:
    """Restituisce un timestamp formattato per i nomi dei backup."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# Endpoint per ottenere lo stato del database documenti
@router.get("/documents/status")
async def get_document_db_status():
    """
    Restituisce lo stato e le statistiche del database documenti.
    """
    try:
        # Ottieni il conteggio totale dei documenti
        total_documents = doc_db.get_document_count()
        
        # Calcola dimensione del database
        db_path = doc_db.db_file
        db_size = get_file_size(db_path)
        
        # Ottieni statistiche
        stats = doc_db.get_collection_stats()
        
        # Calcola il numero di documenti aggiunti oggi
        # Utilizziamo una query SQL diretta per questioni di performance
        conn = doc_db._get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "SELECT COUNT(*) FROM documents WHERE created_at LIKE ?",
            (f"{today}%",)
        )
        documents_today = cursor.fetchone()[0]
        
        # Calcola dimensione media documento
        if total_documents > 0:
            avg_document_size = round(db_size / total_documents / 1024, 2)  # in KB
        else:
            avg_document_size = 0
        
        conn.close()
        
        return {
            "status": "ok",
            "total_documents": total_documents,
            "documents_today": documents_today,
            "size_bytes": db_size,
            "avg_document_size": avg_document_size,
            "collections": stats.get("collections", {}),
            "latest_document": stats.get("latest_document"),
            "database_path": db_path
        }
    except Exception as e:
        logger.error(f"Errore nel recupero dello stato del database documenti: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# Endpoint per elencare i documenti
@router.get("/documents/list")
async def list_documents(limit: int = 100, offset: int = 0):
    """
    Restituisce la lista dei documenti nel database.
    """
    try:
        # Ottieni documenti
        documents = doc_db.get_documents(limit=limit, offset=offset)
        total = doc_db.get_document_count()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "documents": documents,
            "message": f"Mostrati {len(documents)} di {total} documenti"
        }
    except Exception as e:
        logger.error(f"Errore nel recupero della lista documenti: {str(e)}")
        return {
            "error": str(e),
            "documents": []
        }

# Endpoint per il backup del database documenti
@router.post("/documents/backup")
async def backup_document_db(background_tasks: BackgroundTasks):
    """
    Crea un backup del database documenti.
    """
    try:
        # Crea directory di backup specifica
        backup_path = os.path.join(BACKUP_DIR, f"documents_backup_{get_timestamp()}")
        os.makedirs(backup_path, exist_ok=True)
        
        # Backup del database SQLite
        db_source = doc_db.db_file
        db_dest = os.path.join(backup_path, "documents.db")
        
        # Utilizziamo la funzione esporta in JSON per un backup secondario
        json_dest = os.path.join(backup_path, "documents.json")
        
        # Esegui il backup in background
        def do_backup():
            try:
                # Copia il file del database
                shutil.copy2(db_source, db_dest)
                
                # Esporta anche in JSON
                doc_db.export_to_json(json_dest)
                
                logger.info(f"Backup del database documenti completato: {backup_path}")
            except Exception as e:
                logger.error(f"Errore durante l'esecuzione del backup in background: {str(e)}")
        
        background_tasks.add_task(do_backup)
        
        return {
            "success": True,
            "message": "Backup del database documenti avviato",
            "details": {
                "backup_path": backup_path
            }
        }
    except Exception as e:
        logger.error(f"Errore nell'avvio del backup del database documenti: {str(e)}")
        return {
            "success": False,
            "message": f"Errore nel backup: {str(e)}"
        }

# Endpoint semplice per il reset (alias)
@router.post("/reset")
async def reset_database():
    """
    Endpoint semplificato per resettare il database documenti.
    """
    try:
        logger.info("Richiesta reset database ricevuta")
        
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

# Endpoint specifico per il tipo di reset (sql/chroma) 
@router.post("/reset/{type}")
async def reset_database_by_type(type: str):
    """
    Resetta un database specifico in base al tipo (sql o chroma).
    """
    try:
        logger.info(f"Richiesta reset database tipo '{type}' ricevuta")
        
        if type.lower() == "sql":
            # Reset diretto del database SQLite
            import os
            
            # Ottieni il percorso del database
            db_path = doc_db.db_file
            logger.info(f"Resettando database SQL: {db_path}")
            
            # Chiudi eventuali connessioni
            if hasattr(doc_db, '_connection') and doc_db._connection:
                doc_db._connection.close()
                
            # Rimuovi il file del database
            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"Database file rimosso: {db_path}")
                
            # Ricrea il database vuoto
            doc_db._init_database()
            logger.info("Database SQL ricreato vuoto")
            
            return {
                "success": True,
                "message": "Database SQL resettato con successo",
                "timestamp": datetime.now().isoformat()
            }
        elif type.lower() == "chroma":
            # Resetta il vector store (ChromaDB)
            logger.info("Resettando ChromaDB vector store")
            
            success = vector_manager.reset()
            
            if success:
                return {
                    "success": True,
                    "message": "Vector store (ChromaDB) resettato con successo",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": "Errore nel reset del vector store",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            logger.warning(f"Tipo di reset non valido: {type}")
            return {
                "success": False,
                "message": f"Tipo di reset non valido: {type}. Valori supportati: 'sql' o 'chroma'",
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Errore nel reset del database tipo '{type}': {str(e)}")
        return {
            "success": False,
            "message": f"Errore nel reset: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# Endpoint per il reset del database documenti
@router.post("/documents/reset")
async def reset_document_db():
    """
    Resetta il database documenti (elimina tutti i documenti).
    """
    try:
        logger.info("Richiesta reset database documenti ricevuta")
        
        # Reset diretto del database SQLite
        import os
        
        # Ottieni il percorso del database
        db_path = doc_db.db_file
        logger.info(f"Resettando database documenti: {db_path}")
        
        # Rimuovi il file del database
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Database file rimosso: {db_path}")
            
        # Ricrea il database vuoto
        doc_db._init_database()
        logger.info("Database documenti ricreato vuoto")
        
        return {
            "success": True,
            "message": "Database documenti resettato con successo",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Errore nel reset del database documenti: {str(e)}")
        return {
            "success": False,
            "message": f"Errore nel reset: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# Endpoint per ottenere lo stato del vector store
@router.get("/vectorstore/status")
async def get_vectorstore_status():
    """
    Restituisce lo stato e le statistiche del vector store.
    """
    try:
        # Ottieni informazioni dal vector store
        stats = vector_manager.get_statistics()
        
        # Aggiungi informazioni aggiuntive specifiche
        today = datetime.now().strftime("%Y-%m-%d")
        documents_today = 0
        
        # Ottieni i documenti del vector store per contare quelli di oggi
        try:
            all_docs = vector_manager.list_documents(metadata_only=True)
            for doc in all_docs:
                if doc.get("metadata", {}).get("ingest_time", "").startswith(today):
                    documents_today += 1
        except Exception as vs_error:
            logger.warning(f"Errore nel conteggio dei documenti odierni: {str(vs_error)}")
        
        return {
            "status": "ok",
            "documents_in_index": stats.get("total_documents", 0),
            "collections": stats.get("collections", []),
            "documents_today": documents_today,
            "avg_chunk_size": stats.get("avg_chunk_size", 0),
            "embedding_model": stats.get("embedding_model", "")
        }
    except Exception as e:
        logger.error(f"Errore nel recupero dello stato del vector store: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# Endpoint per elencare i documenti nel vector store
@router.get("/vectorstore/documents")
async def list_vectorstore_documents(limit: int = 20, offset: int = 0):
    """
    Restituisce la lista dei documenti nel vector store.
    """
    try:
        # Ottieni i documenti
        documents = vector_manager.list_documents(limit=limit, offset=offset)
        total_count = vector_manager.get_document_count()
        
        # Trasforma in formato più adatto alla visualizzazione
        formatted_docs = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            formatted_doc = {
                "id": doc.get("id", ""),
                "source_filename": metadata.get("source", "Sconosciuto"),
                "page": metadata.get("page", "N/A"),
                "ingest_time": metadata.get("ingest_time", "N/A"),
                "content_preview": doc.get("content", "")[:200] + "..." if len(doc.get("content", "")) > 200 else doc.get("content", ""),
                "metadata": metadata
            }
            formatted_docs.append(formatted_doc)
        
        return {
            "total": total_count,
            "documents": formatted_docs,
            "message": f"Mostrati {len(formatted_docs)} di {total_count} documenti"
        }
    except Exception as e:
        logger.error(f"Errore nel recupero dei documenti dal vector store: {str(e)}")
        return {
            "error": str(e),
            "documents": []
        }

# Endpoint per il backup del vector store
@router.post("/vectorstore/backup")
async def backup_vectorstore(background_tasks: BackgroundTasks):
    """
    Crea un backup del vector store.
    """
    return {
        "success": False,
        "message": "Backup vector store non implementato in questa build"
    }

# Endpoint per il reset del vector store
@router.post("/vectorstore/reset")
async def reset_vectorstore():
    """
    Resetta il vector store (elimina tutti i documenti).
    """
    try:
        # Resetta il vector store (ChromaDB)
        success = vector_manager.reset_all_data() if hasattr(vector_manager, 'reset_all_data') else False
    except Exception as e:
        logger.error(f"Errore nel reset del vector store: {str(e)}")
        return {
            "success": False,
            "message": f"Errore nel reset: {str(e)}"
        }
    if success:
        return {
            "success": True,
            "message": "Vector store resettato con successo"
        }
    else:
        return {
            "success": False,
            "message": "Errore nel reset del vector store"
        }
