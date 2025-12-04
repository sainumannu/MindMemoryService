"""
API per la gestione del database.
Questo modulo fornisce endpoint per monitorare e gestire il database SQLite.
"""

import os
import json
import sqlite3
import shutil
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Importiamo il modello base di pydantic per la risposta di stato
# from app.api.models import StatusResponse
from app.utils.sqlite_metadata_manager import SQLiteMetadataManager

# Router per la gestione del database
router = APIRouter(prefix="/admin/database", tags=["admin"])

# Modelli di dati
class DatabaseStats(BaseModel):
    """Statistiche del database"""
    tables: int
    documents: int
    size: float
    usage: Optional[float] = None
    fragmentation: Optional[float] = None
    vectorStoreStatus: str = "ok"

class BackupResponse(BaseModel):
    """Risposta per l'operazione di backup"""
    success: bool
    backupPath: Optional[str] = None
    timestamp: str
    message: Optional[str] = None

class OptimizeResponse(BaseModel):
    """Risposta per l'operazione di ottimizzazione"""
    success: bool
    message: Optional[str] = None
    originalSize: float
    newSize: float
    reductionPercentage: float

# Funzioni di utility
def get_db_path():
    """Restituisce il percorso del file database."""
    return os.path.join(os.getcwd(), "data", "documents.db")

def get_db_size_kb():
    """Restituisce la dimensione del database in KB."""
    try:
        return os.path.getsize(get_db_path()) / 1024
    except Exception:
        return 0

def get_table_count():
    """Restituisce il numero di tabelle nel database."""
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        return cursor.fetchone()[0]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

def get_document_count():
    """Restituisce il numero di documenti nel database."""
    db = SQLiteMetadataManager(data_dir=os.path.join(os.getcwd(), "data"))
    return db.get_document_count()

def calculate_fragmentation():
    """Stima la frammentazione del database."""
    # Implementazione semplificata
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # Verifica la frammentazione con PRAGMA integrity_check
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchall()
        
        if integrity and integrity[0][0] == "ok":
            # Se l'integrità è ok, facciamo una stima basata sulla dimensione
            # e sul numero di record
            doc_count = get_document_count()
            db_size = get_db_size_kb()
            
            if doc_count > 0 and db_size > 0:
                # Valore euristico, più alto è questo rapporto, 
                # maggiore potrebbe essere la frammentazione
                avg_size_per_doc = db_size / doc_count
                
                # Se superiamo una certa soglia, stimiamo frammentazione
                if avg_size_per_doc > 5:  # soglia arbitraria
                    return min(((avg_size_per_doc - 5) / 5) * 10, 100)
                
            return 0
        else:
            # Se ci sono problemi di integrità, consideriamo alta frammentazione
            return 75
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()

# Endpoint API

@router.get("/stats", response_model=DatabaseStats)
async def get_database_stats():
    """Recupera le statistiche del database"""
    try:
        return DatabaseStats(
            tables=get_table_count(),
            documents=get_document_count(),
            size=get_db_size_kb(),
            usage=min(get_db_size_kb() / 1000 * 100, 100) if get_db_size_kb() > 0 else 0,
            fragmentation=calculate_fragmentation(),
            vectorStoreStatus="ok"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante il recupero delle statistiche: {str(e)}")

@router.post("/backup", response_model=BackupResponse)
async def create_database_backup():
    """Crea un backup del database"""
    try:
        # Percorso del database
        db_path = get_db_path()
        
        # Verifica se il file esiste
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail="File database non trovato")
        
        # Crea la directory di backup se non esiste
        backup_dir = os.path.join(os.getcwd(), "data", "backup")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Nome del file di backup con timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_filename = f"documents.{timestamp}.db.bak"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Crea il backup
        shutil.copy2(db_path, backup_path)
        
        return BackupResponse(
            success=True,
            backupPath=backup_path,
            timestamp=datetime.now().isoformat(),
            message="Backup creato con successo"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la creazione del backup: {str(e)}")

@router.get("/backup/latest", response_model=BackupResponse)
async def get_latest_backup():
    """Recupera informazioni sull'ultimo backup disponibile"""
    try:
        # Percorso della directory di backup
        backup_dir = os.path.join(os.getcwd(), "data", "backup")
        
        # Se la directory non esiste, non ci sono backup
        if not os.path.exists(backup_dir):
            return BackupResponse(
                success=False,
                timestamp=datetime.now().isoformat(),
                message="Nessun backup disponibile"
            )
        
        # Trova il file più recente
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith("documents.") and f.endswith(".db.bak")]
        
        if not backup_files:
            return BackupResponse(
                success=False,
                timestamp=datetime.now().isoformat(),
                message="Nessun backup disponibile"
            )
        
        # Ordina per nome (che include il timestamp)
        backup_files.sort(reverse=True)
        latest_backup = backup_files[0]
        
        # Estrai il timestamp dal nome del file
        timestamp_str = latest_backup.split(".")[1]
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S").isoformat()
        except:
            timestamp = datetime.now().isoformat()
        
        return BackupResponse(
            success=True,
            backupPath=os.path.join(backup_dir, latest_backup),
            timestamp=timestamp,
            message="Backup trovato"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante il recupero dell'ultimo backup: {str(e)}")

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_database():
    """Ottimizza il database eseguendo VACUUM"""
    try:
        # Percorso del database
        db_path = get_db_path()
        
        # Verifica se il file esiste
        if not os.path.exists(db_path):
            raise HTTPException(status_code=404, detail="File database non trovato")
        
        # Dimensione originale
        original_size = get_db_size_kb()
        
        # Esegui VACUUM
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.commit()
        finally:
            if conn:
                conn.close()
        
        # Dimensione dopo ottimizzazione
        new_size = get_db_size_kb()
        
        # Calcola la riduzione percentuale
        if original_size > 0:
            reduction_pct = (original_size - new_size) / original_size * 100
        else:
            reduction_pct = 0
        
        return OptimizeResponse(
            success=True,
            message="Database ottimizzato con successo",
            originalSize=original_size,
            newSize=new_size,
            reductionPercentage=reduction_pct
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l'ottimizzazione del database: {str(e)}")
