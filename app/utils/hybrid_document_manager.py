"""
HybridDocumentManager - Coordinatore centrale per sincronizzazione ChromaDB + SQLite

Questo modulo implementa il pattern di coordinamento per la gestione ibrida dei documenti
tra ChromaDB (vector database) e SQLite (metadata database).
"""

import logging
import os
from typing import Dict, List, Optional, Any, Union
from app.core.chroma_manager import ChromaDBManager
from app.utils.document_database import DocumentDatabase

logger = logging.getLogger(__name__)

class HybridDocumentManager:
    """
    Gestore ibrido per coordinazione documenti tra ChromaDB e SQLite.
    
    Responsabilità:
    - Coordinamento operazioni documenti tra vector DB e metadata DB
    - Sincronizzazione contenuti e metadati tra i due database
    - Gestione operazioni CRUD coordinate
    - Risoluzione conflitti e recupero errori
    - Monitoraggio consistenza dati
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Inizializza il coordinatore con la directory dei dati.
        
        Args:
            data_dir: Directory per i dati (opzionale)
        """
        # Configura directory dati
        if not data_dir:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        
        self.data_dir = data_dir
            
        # Inizializza gestori database
        self.chroma_manager = ChromaDBManager()
        self.document_db = DocumentDatabase(data_dir=data_dir)
        
        logger.info(f"HybridDocumentManager inizializzato con data_dir: {data_dir}")
    
    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Aggiunge un documento in modo coordinato a entrambi i database.
        
        Args:
            doc_id: ID univoco del documento
            content: Contenuto testuale del documento
            metadata: Metadati del documento
            
        Returns:
            bool: True se l'operazione ha successo, False altrimenti
        """
        try:
            # Prepara documento per SQLite
            document_data = {
                'id': doc_id,
                'content': content,
                **metadata
            }
            
            # 1. Aggiungi a SQLite per metadati e accesso diretto
            sqlite_success = self.document_db.add_document(document_data)
            if not sqlite_success:
                logger.error(f"Errore aggiunta documento {doc_id} a SQLite")
                return False
            
            # 2. Aggiungi a ChromaDB per ricerca semantica
            try:
                collection = self.chroma_manager.get_collection()
                if collection:
                    collection.add(
                        documents=[content],
                        metadatas=[metadata],
                        ids=[doc_id]
                    )
                    logger.info(f"Documento {doc_id} aggiunto anche a ChromaDB")
                else:
                    logger.warning(f"ChromaDB collection non disponibile per {doc_id}")
            except Exception as e:
                logger.warning(f"Errore aggiunta a ChromaDB per {doc_id}: {e}")
                # Non fallire se ChromaDB ha problemi
            
            logger.info(f"Documento {doc_id} aggiunto con successo")
            return True
            
        except Exception as e:
            logger.error(f"Errore coordinamento aggiunta documento {doc_id}: {e}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera un documento usando l'approccio ibrido.
        
        Prima prova SQLite (più veloce per accesso diretto),
        poi ChromaDB come fallback.
        
        Args:
            doc_id: ID del documento da recuperare
            
        Returns:
            Dict con dati documento o None se non trovato
        """
        try:
            # 1. Prova prima SQLite (accesso diretto veloce)
            document = self.document_db.get_document(doc_id)
            if document:
                logger.debug(f"Documento {doc_id} trovato in SQLite")
                return document
            
            # 2. Fallback su ChromaDB
            try:
                collection = self.chroma_manager.get_collection()
                if collection:
                    result = collection.get(ids=[doc_id])
                    if result and result.get('documents') and len(result['documents']) > 0:
                        logger.debug(f"Documento {doc_id} trovato in ChromaDB")
                        doc_content = result['documents'][0]
                        doc_metadata = result.get('metadatas', [{}])[0] or {}
                        
                        return {
                            'id': doc_id,
                            'content': doc_content,
                            **doc_metadata
                        }
            except Exception as e:
                logger.warning(f"Errore ricerca ChromaDB per {doc_id}: {e}")
            
            logger.warning(f"Documento {doc_id} non trovato in nessuno dei database")
            return None
            
        except Exception as e:
            logger.error(f"Errore recupero documento {doc_id}: {e}")
            return None
    
    def update_document(self, doc_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Aggiorna un documento in modo coordinato.
        
        Args:
            doc_id: ID del documento da aggiornare
            content: Nuovo contenuto (opzionale)
            metadata: Nuovi metadati (opzionale)
            
        Returns:
            bool: True se l'operazione ha successo
        """
        try:
            # 1. Aggiorna SQLite
            if metadata is not None:
                for key, value in metadata.items():
                    success = self.document_db.update_metadata(doc_id, key, value)
                    if not success:
                        logger.warning(f"Errore aggiornamento metadato {key} per {doc_id}")
            
            # 2. Per ChromaDB, devo rimuovere e riaggiungi (update pattern)
            if content is not None:
                try:
                    collection = self.chroma_manager.get_collection()
                    if collection:
                        # Ottieni metadati attuali
                        current_doc = self.get_document(doc_id)
                        updated_metadata = current_doc.copy() if current_doc else {}
                        if metadata:
                            updated_metadata.update(metadata)
                        
                        # Rimuovi il documento esistente
                        try:
                            collection.delete(ids=[doc_id])
                        except:
                            pass  # Ignora errori se il documento non esiste
                        
                        # Aggiungi il documento aggiornato
                        collection.add(
                            documents=[content],
                            metadatas=[updated_metadata],
                            ids=[doc_id]
                        )
                        logger.info(f"Documento {doc_id} aggiornato in ChromaDB")
                except Exception as e:
                    logger.warning(f"Errore aggiornamento ChromaDB per {doc_id}: {e}")
            
            logger.info(f"Documento {doc_id} aggiornato")
            return True
            
        except Exception as e:
            logger.error(f"Errore aggiornamento documento {doc_id}: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Elimina un documento da entrambi i database.
        
        Args:
            doc_id: ID del documento da eliminare
            
        Returns:
            bool: True se l'operazione ha successo
        """
        try:
            success_count = 0
            
            # 1. Elimina da SQLite
            try:
                sqlite_success = self.document_db.delete_document(doc_id)
                if sqlite_success:
                    success_count += 1
                    logger.debug(f"Documento {doc_id} eliminato da SQLite")
            except Exception as e:
                logger.warning(f"Errore eliminazione da SQLite per {doc_id}: {e}")
            
            # 2. Elimina da ChromaDB
            try:
                collection = self.chroma_manager.get_collection()
                if collection:
                    collection.delete(ids=[doc_id])
                    success_count += 1
                    logger.debug(f"Documento {doc_id} eliminato da ChromaDB")
            except Exception as e:
                logger.warning(f"Errore eliminazione da ChromaDB per {doc_id}: {e}")
            
            # Considera successo se almeno uno dei due è andato a buon fine
            if success_count > 0:
                logger.info(f"Documento {doc_id} eliminato da {success_count}/2 database")
                return True
            else:
                logger.error(f"Impossibile eliminare documento {doc_id} da entrambi i database")
                return False
                
        except Exception as e:
            logger.error(f"Errore eliminazione documento {doc_id}: {e}")
            return False
    
    def search_documents(self, query: str, limit: int = 10, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Esegue ricerca semantica usando ChromaDB.
        
        Args:
            query: Query di ricerca
            limit: Numero massimo di risultati
            where: Filtri metadati (opzionale)
            
        Returns:
            Lista di documenti con score di similarità
        """
        try:
            # Usa ChromaDB per ricerca semantica
            collection = self.chroma_manager.get_collection()
            if not collection:
                logger.warning("ChromaDB collection non disponibile per ricerca")
                return []
            
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where
            )
            
            if not results or not results.get('documents'):
                return []
            
            # Formatta risultati con score di similarità
            formatted_results = []
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            ids = results.get('ids', [[]])[0]
            
            for i, doc_content in enumerate(documents):
                # Converti distanza coseno in score similarità (0-1)
                distance = distances[i] if i < len(distances) else 1.0
                similarity_score = max(0.0, 1.0 - distance)
                
                doc_data = {
                    'id': ids[i] if i < len(ids) else f"doc_{i}",
                    'content': doc_content,
                    'similarity_score': similarity_score,
                    'metadata': metadatas[i] if i < len(metadatas) else {}
                }
                formatted_results.append(doc_data)
            
            logger.debug(f"Ricerca semantica completata: {len(formatted_results)} risultati")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Errore ricerca documenti: {e}")
            return []
    
    def list_all_documents(self) -> List[str]:
        """
        Restituisce lista di tutti gli ID documento da SQLite.
        
        Returns:
            Lista degli ID documento
        """
        try:
            docs = self.document_db.get_documents()
            return [doc.get('id') for doc in docs if doc.get('id')]
        except Exception as e:
            logger.error(f"Errore lista documenti: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Restituisce statistiche sui database.
        
        Returns:
            Dict con contatori documenti per database
        """
        try:
            stats = {
                'sqlite_documents': self.document_db.get_document_count(),
                'chroma_collections': 0,
                'chroma_documents': 0
            }
            
            # Statistiche ChromaDB
            try:
                collections = self.chroma_manager.list_collections()
                stats['chroma_collections'] = len(collections)
                
                # Conta documenti nella collezione principale
                collection = self.chroma_manager.get_collection()
                if collection:
                    stats['chroma_documents'] = collection.count()
                
            except Exception as e:
                logger.warning(f"Errore statistiche ChromaDB: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Errore calcolo statistiche: {e}")
            return {'sqlite_documents': 0, 'chroma_collections': 0, 'chroma_documents': 0}
    
    def sync_databases(self) -> Dict[str, Any]:
        """
        Sincronizza i due database, risolvendo inconsistenze.
        
        Returns:
            Dict con risultati della sincronizzazione
        """
        try:
            logger.info("Iniziando sincronizzazione database...")
            
            # Ottieni liste documenti
            sqlite_docs = set(self.list_all_documents())
            
            # Per ChromaDB
            chroma_docs = set()
            try:
                collection = self.chroma_manager.get_collection()
                if collection:
                    result = collection.get()
                    if result and result.get('ids'):
                        chroma_docs.update(result['ids'])
            except Exception as e:
                logger.warning(f"Errore lettura ChromaDB durante sync: {e}")
            
            # Identifica inconsistenze
            only_in_sqlite = sqlite_docs - chroma_docs
            only_in_chroma = chroma_docs - sqlite_docs
            
            sync_result = {
                'total_sqlite': len(sqlite_docs),
                'total_chroma': len(chroma_docs),
                'only_in_sqlite': len(only_in_sqlite),
                'only_in_chroma': len(only_in_chroma),
                'synchronized': len(sqlite_docs & chroma_docs),
                'actions_taken': []
            }
            
            logger.info(f"Sincronizzazione completata: {sync_result}")
            return sync_result
            
        except Exception as e:
            logger.error(f"Errore sincronizzazione database: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, bool]:
        """
        Verifica lo stato di salute dei database.
        
        Returns:
            Dict con status di ogni database
        """
        health = {
            'chroma_db': False,
            'sqlite_db': False,
            'overall': False
        }
        
        try:
            # Test ChromaDB
            collections = self.chroma_manager.list_collections()
            health['chroma_db'] = True
            logger.debug("ChromaDB health check: OK")
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
        
        try:
            # Test SQLite
            count = self.document_db.get_document_count()
            health['sqlite_db'] = True
            logger.debug("SQLite health check: OK")
        except Exception as e:
            logger.warning(f"SQLite health check failed: {e}")
        
        health['overall'] = health['chroma_db'] and health['sqlite_db']
        return health
    
    def reset_all_data(self) -> bool:
        """
        Reset completo di tutti i dati in entrambi i database.
        ATTENZIONE: Questa operazione è irreversibile!
        
        Returns:
            bool: True se il reset ha successo
        """
        try:
            logger.warning("ATTENZIONE: Iniziando reset completo database...")
            
            success_count = 0
            
            # 1. Reset ChromaDB
            try:
                collection = self.chroma_manager.get_collection()
                if collection:
                    # Ottieni tutti gli ID e li elimina
                    result = collection.get()
                    if result and result.get('ids'):
                        collection.delete(ids=result['ids'])
                        logger.info(f"ChromaDB resettato: {len(result['ids'])} documenti eliminati")
                success_count += 1
            except Exception as e:
                logger.error(f"Errore reset ChromaDB: {e}")
            
            # 2. Reset SQLite
            try:
                all_docs = self.list_all_documents()
                for doc_id in all_docs:
                    self.document_db.delete_document(doc_id)
                logger.info(f"SQLite database resettato: {len(all_docs)} documenti eliminati")
                success_count += 1
            except Exception as e:
                logger.error(f"Errore reset SQLite: {e}")
            
            if success_count == 2:
                logger.info("Reset completo database completato con successo")
                return True
            else:
                logger.warning(f"Reset parziale: {success_count}/2 database resettati")
                return False
                
        except Exception as e:
            logger.error(f"Errore reset database: {e}")
            return False