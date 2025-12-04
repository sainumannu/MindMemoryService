"""
VectorDB Manager - Gestione del database vettoriale ChromaDB.

Questo modulo fornisce funzionalità per accedere a ChromaDB in modalità persistente locale
senza utilizzare una connessione HTTP.
"""

import os
import logging
from pathlib import Path
import chromadb
from typing import Optional, Dict, List, Any

# Configurazione logger
logger = logging.getLogger(__name__)

# Directory di persistenza di ChromaDB
CHROMA_PERSIST_DIR = os.path.join(os.getcwd(), "data", "chroma_db")
CHROMA_COLLECTION_NAME = "prama_documents"

class VectorDBManager:
    """
    Gestore per il database vettoriale ChromaDB in modalità persistente locale.
    Singleton per garantire una sola istanza in tutta l'applicazione.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorDBManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._client = None
        self._collection = None
        self._initialized = True
        
        # Assicurati che la directory di persistenza esista
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        
        # Inizializza il client
        self._init_client()
    
    def _init_client(self):
        """
        Inizializza il client ChromaDB in modalità persistente locale.
        """
        try:
            logger.info(f"Inizializzazione ChromaDB in modalità persistente locale. Path: {CHROMA_PERSIST_DIR}")
            
            # Imposta variabili di ambiente per ChromaDB per evitare problemi con i binding Rust
            import os
            os.environ["CHROMA_SERVER_GRPC_PORT"] = "8001"
            os.environ["CHROMA_CLIENT_TIMEOUT"] = "30"
            
            # Prova inizializzazione con impostazioni conservative
            settings = chromadb.config.Settings(
                persist_directory=CHROMA_PERSIST_DIR,
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
            
            self._client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=settings
            )
            
            # Assicurati che la collezione esista
            self._collection = self._client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
            
            logger.info(f"ChromaDB inizializzato con successo. Collezione: {CHROMA_COLLECTION_NAME}")
            return True
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di ChromaDB: {str(e)}")
            
            # Fallback: prova con client in-memory temporaneo
            try:
                logger.warning("Tentativo fallback con client in-memory...")
                self._client = chromadb.Client()
                self._collection = self._client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
                logger.warning("Fallback riuscito - usando ChromaDB in modalità in-memory")
                return True
            except Exception as fallback_error:
                logger.error(f"Anche il fallback è fallito: {str(fallback_error)}")
                self._client = None
                self._collection = None
                return False
    
    def get_client(self):
        """
        Restituisce il client ChromaDB.
        """
        if not self._client:
            self._init_client()
        return self._client
    
    def get_collection(self, collection_name=None):
        """
        Restituisce una collezione ChromaDB.
        
        Args:
            collection_name: Nome della collezione. Se None, usa la collezione predefinita.
        """
        if not self._client:
            self._init_client()
            
        if not self._client:
            logger.error("Client ChromaDB non disponibile")
            return None
            
        try:
            name_to_use = CHROMA_COLLECTION_NAME
            if collection_name is not None:
                name_to_use = collection_name
            return self._client.get_or_create_collection(name=name_to_use)
        except Exception as e:
            logger.error(f"Errore nel recupero della collezione '{collection_name}': {str(e)}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Verifica lo stato della connessione a ChromaDB.
        
        Returns:
            Dict con informazioni sullo stato.
        """
        if not self._client:
            success = self._init_client()
            if not success:
                return {"status": "error", "message": "Impossibile inizializzare ChromaDB"}
        
        try:
            collection = self.get_collection()
            if not collection:
                return {"status": "error", "message": "Collezione non disponibile"}
                
            count = collection.count()
            return {
                "status": "healthy",
                "message": f"ChromaDB disponibile. {count} documenti nella collezione {CHROMA_COLLECTION_NAME}",
                "document_count": count,
                "collection": CHROMA_COLLECTION_NAME,
                "mode": "persistent_local",
                "persist_directory": CHROMA_PERSIST_DIR
            }
        except Exception as e:
            logger.error(f"Errore nella verifica dello stato di ChromaDB: {str(e)}")
            return {"status": "error", "message": f"Errore: {str(e)}"}
    
    def list_collections(self) -> List[str]:
        """
        Lista tutte le collezioni disponibili in ChromaDB.
        
        Returns:
            Lista di nomi delle collezioni.
        """
        if not self._client:
            self._init_client()
            
        if not self._client:
            logger.error("Client ChromaDB non disponibile")
            return []
            
        try:
            collections = self._client.list_collections()
            return [collection.name for collection in collections]
        except Exception as e:
            logger.error(f"Errore nel listare le collezioni: {str(e)}")
            return []

# Esporta un'istanza singleton
vector_db_manager = VectorDBManager()
