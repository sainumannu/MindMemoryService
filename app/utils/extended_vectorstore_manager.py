"""
Estende il HybridDocumentManager con metodi per supportare le nuove API di gestione.
"""

from app.utils.hybrid_document_manager import HybridDocumentManager as BaseHybridDocumentManager
import os
import logging
import chromadb
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configurazione logger
logger = logging.getLogger(__name__)

class ExtendedHybridDocumentManager(BaseHybridDocumentManager):
    """
    Versione estesa del HybridDocumentManager che aggiunge metodi necessari
    per supportare le nuove funzionalità dell'API di gestione.
    """
    
    def __init__(self, data_dir: str = None):
        """Inizializza il gestore esteso."""
        super().__init__(data_dir=data_dir)
        self.chroma_path = os.path.join(self.data_dir, "chroma_db")
    
    def check_connection(self) -> bool:
        """
        Verifica se la connessione a ChromaDB è funzionante.
        
        Returns:
            True se la connessione è ok, False altrimenti.
        """
        try:
            # Tenta di creare un client ChromaDB e verificare la connessione
            from chromadb import PersistentClient
            client = PersistentClient(path=self.chroma_path)
            # Tenta di elencare le collezioni per verificare che il client funzioni
            collections = client.list_collections()
            return True
        except Exception as e:
            logger.error(f"Errore nella verifica della connessione a ChromaDB: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Ottiene statistiche dettagliate sul vector store.
        
        Returns:
            Dizionario con le statistiche.
        """
        try:
            # Carica le statistiche di base
            stats = self._load_stats()
            
            # Aggiungi statistiche aggiuntive
            # Conta documenti nel ChromaDB
            try:
                from chromadb import PersistentClient
                client = PersistentClient(path=self.chroma_path)
                collections = client.list_collections()
                
                total_documents = 0
                collection_names = []
                
                for collection in collections:
                    collection_size = collection.count()
                    total_documents += collection_size
                    collection_names.append({
                        "name": collection.name,
                        "count": collection_size
                    })
                
                stats["total_documents"] = total_documents
                stats["collections"] = collection_names
                
                # Calcola dimensione media dei chunk
                if total_documents > 0:
                    # Questo è solo una stima approssimativa
                    avg_chunk_size = 1.5  # Kb, valore medio stimato
                    stats["avg_chunk_size"] = avg_chunk_size
                
                # Modello di embedding utilizzato
                stats["embedding_model"] = "sentence-transformers/all-MiniLM-L6-v2"
                
            except Exception as chroma_error:
                logger.warning(f"Errore nel recupero delle statistiche ChromaDB: {str(chroma_error)}")
                stats["chroma_error"] = str(chroma_error)
            
            return stats
        except Exception as e:
            logger.error(f"Errore nel recupero delle statistiche: {str(e)}")
            return {
                "error": str(e),
                "total_documents": 0,
                "collections": []
            }
    
    def get_persistence_path(self) -> str:
        """
        Ottiene il percorso della directory di persistenza di ChromaDB.
        
        Returns:
            Path della directory di persistenza.
        """
        return self.chroma_path
    
    def get_document_count(self) -> int:
        """
        Ottiene il numero totale di documenti nel vector store.
        
        Returns:
            Numero di documenti.
        """
        try:
            from chromadb import PersistentClient
            client = PersistentClient(path=self.chroma_path)
            collections = client.list_collections()
            
            total = 0
            for collection in collections:
                total += collection.count()
            
            return total
        except Exception as e:
            logger.error(f"Errore nel conteggio dei documenti: {str(e)}")
            return 0
    
    def list_documents(self, limit: int = 20, offset: int = 0, metadata_only: bool = False) -> List[Dict[str, Any]]:
        """
        Ottiene l'elenco dei documenti nel vector store.
        
        Args:
            limit: Numero massimo di documenti da restituire.
            offset: Offset per la paginazione.
            metadata_only: Se True, restituisce solo i metadati senza il contenuto.
            
        Returns:
            Lista di documenti.
        """
        try:
            from chromadb import PersistentClient
            client = PersistentClient(path=self.chroma_path)
            collections = client.list_collections()
            
            all_documents = []
            
            for collection in collections:
                try:
                    # Ottieni tutti i documenti dalla collezione
                    result = collection.get(
                        limit=limit + offset
                    )
                    
                    # Crea una lista di documenti
                    documents = []
                    if result and "metadatas" in result and "documents" in result and "ids" in result:
                        for i in range(len(result["ids"])):
                            doc = {
                                "id": result["ids"][i],
                                "metadata": result["metadatas"][i]
                            }
                            if not metadata_only:
                                doc["content"] = result["documents"][i] if i < len(result["documents"]) else ""
                            documents.append(doc)
                    
                    all_documents.extend(documents)
                except Exception as coll_error:
                    logger.warning(f"Errore nel recupero dei documenti dalla collezione {collection.name}: {str(coll_error)}")
            
            # Applica limit e offset
            return all_documents[offset:offset + limit]
        except Exception as e:
            logger.error(f"Errore nel recupero dei documenti: {str(e)}")
            return []
    
    def reset(self) -> bool:
        """
        Resetta il vector store eliminando tutti i documenti.
        
        Returns:
            True se il reset è avvenuto con successo, False altrimenti.
        """
        try:
            from chromadb import PersistentClient
            
            # Prima elimina tutte le collezioni esistenti
            try:
                client = PersistentClient(path=self.chroma_path)
                collections = client.list_collections()
                
                for collection in collections:
                    client.delete_collection(collection.name)
                
                logger.info(f"Tutte le collezioni ChromaDB eliminate con successo")
            except Exception as del_error:
                logger.error(f"Errore nell'eliminazione delle collezioni ChromaDB: {str(del_error)}")
            
            # Poi, a seconda della gravità del problema, potrebbe essere necessario eliminare fisicamente la directory
            import shutil
            try:
                if os.path.exists(self.chroma_path):
                    # Rimuovi la directory ChromaDB
                    shutil.rmtree(self.chroma_path)
                    logger.info(f"Directory ChromaDB eliminata: {self.chroma_path}")
                    
                    # Ricrea la directory vuota
                    os.makedirs(self.chroma_path, exist_ok=True)
            except Exception as rm_error:
                logger.error(f"Errore nella rimozione della directory ChromaDB: {str(rm_error)}")
                return False
            
            # Resetta le statistiche
            stats = self._load_stats()
            stats["documents_total"] = 0
            stats["documents_today"] = 0
            stats["documents_in_queue"] = 0
            stats["collections"] = 0
            self._save_stats(stats)
            
            return True
        except Exception as e:
            logger.error(f"Errore nel reset del vector store: {str(e)}")
            return False

# Alias per compatibilità con il vecchio nome
ExtendedMetadataStoreManager = ExtendedHybridDocumentManager
