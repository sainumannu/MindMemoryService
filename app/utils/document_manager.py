"""
DocumentManager - Coordinatore centrale per gestione documenti

Questo modulo implementa il pattern di coordinamento per la gestione dei documenti
tra ChromaDB (vector database) e SQLite (metadata database).
"""

import logging
import os
from typing import Dict, List, Optional, Any, Union
from app.core.vectordb_manager import VectorDBManager
from app.utils.sqlite_metadata_manager import SQLiteMetadataManager

logger = logging.getLogger(__name__)

class DocumentManager:
    """
    Gestore centralizzato per documenti e metadati.
    
    Responsabilità:
    - Coordinamento operazioni documenti tra vector DB e metadata DB
    - Sincronizzazione contenuti e metadati tra i database
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
        self.vector_db = VectorDBManager()
        self.metadata_db = SQLiteMetadataManager(data_dir=data_dir)
        
        logger.info(f"DocumentManager inizializzato con data_dir: {data_dir}")
    
    def _should_vectorize_content(self, content: str, metadata: Dict[str, Any]) -> bool:
        """
        Determina se un contenuto dovrebbe essere vettorizzato e aggiunto al VectorStore.
        
        Args:
            content: Contenuto del documento
            metadata: Metadati del documento
            
        Returns:
            bool: True se il contenuto deve essere vettorizzato, False altrimenti
        """
        # Controlla se è esplicitamente marcato come binario
        if metadata.get('is_binary', False):
            return False
        
        # Controlla se il content_type indica un file binario
        content_type = metadata.get('content_type', '').lower()
        if content_type in ['binary', 'image', 'audio', 'video']:
            return False
        
        # Controlla se il file_type indica un formato binario
        file_type = metadata.get('file_type', '').lower()
        binary_types = ['image/', 'audio/', 'video/', 'application/zip', 'application/octet-stream']
        for binary_type in binary_types:
            if file_type.startswith(binary_type):
                return False
        
        # Controlla se il contenuto inizia con marcatori binari
        if content.startswith('BINARY_FILE:'):
            return False
        
        # Controlla se il contenuto è troppo corto o vuoto
        if not content or len(content.strip()) < 10:
            return False
        
        # Se passa tutti i controlli, è vettorizzabile
        return True
    
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
            
            # 1. Aggiungi sempre a SQLite per metadati e accesso diretto
            sqlite_success = self.metadata_db.add_document(document_data)
            if not sqlite_success:
                logger.error(f"Errore aggiunta documento {doc_id} a SQLite")
                return False
            
            # 2. Verifica se il contenuto è vettorizzabile prima di aggiungerlo a ChromaDB
            should_vectorize = self._should_vectorize_content(content, metadata)
            
            if should_vectorize:
                try:
                    collection = self.vector_db.get_collection()
                    if collection:
                        collection.add(
                            documents=[content],
                            metadatas=[metadata],
                            ids=[doc_id]
                        )
                        logger.info(f"Documento {doc_id} aggiunto anche a ChromaDB (vettorizzato)")
                    else:
                        logger.warning(f"ChromaDB collection non disponibile per {doc_id}")
                except Exception as e:
                    logger.warning(f"Errore aggiunta a ChromaDB per {doc_id}: {e}")
                    # Non fallire se ChromaDB ha problemi
            else:
                logger.info(f"Documento {doc_id} NON aggiunto a ChromaDB (contenuto non vettorizzabile)")
            
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
            document = self.metadata_db.get_document(doc_id)
            if document:
                logger.debug(f"Documento {doc_id} trovato in SQLite")
                return document
            
            # 2. Fallback su ChromaDB
            try:
                collection = self.vector_db.get_collection()
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
                    success = self.metadata_db.update_metadata(doc_id, key, value)
                    if not success:
                        logger.warning(f"Errore aggiornamento metadato {key} per {doc_id}")
            
            # 2. Per ChromaDB, devo rimuovere e riaggiungi (update pattern)
            if content is not None:
                try:
                    collection = self.vector_db.get_collection()
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
                sqlite_success = self.metadata_db.delete_document(doc_id)
                if sqlite_success:
                    success_count += 1
                    logger.debug(f"Documento {doc_id} eliminato da SQLite")
            except Exception as e:
                logger.warning(f"Errore eliminazione da SQLite per {doc_id}: {e}")
            
            # 2. Elimina da ChromaDB
            try:
                collection = self.vector_db.get_collection()
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
            collection = self.vector_db.get_collection()
            if not collection:
                logger.warning("ChromaDB collection non disponibile per ricerca")
                return []
            
            # 🔧 FIX: Genera embedding con lo stesso modello usato per l'indicizzazione
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
                query_embedding = model.encode([query], normalize_embeddings=True)[0].tolist()
                
                # Usa query_embeddings invece di query_texts per consistenza del modello
                results = collection.query(
                    query_embeddings=[query_embedding],  # ✅ Stesso modello dell'indicizzazione
                    n_results=limit,
                    where=where
                )
                
                print(f"[DEBUG] Usato embedding generato con sentence-transformers per query: '{query}'")
                
            except ImportError:
                logger.warning("sentence-transformers non disponibile, fallback a query_texts")
                # Fallback al metodo originale
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
                
                # 🔧 FIX: Usa formula normalizzata per distanze > 1.0
                # ChromaDB può restituire distanze > 1.0 con certi embedding models
                import math
                if distance <= 1.0:
                    similarity_score = max(0.0, 1.0 - distance)
                else:
                    # Normalizzazione con radice quadrata per distanze > 1.0
                    similarity_score = max(0.0, 1.0 - math.sqrt(distance) / 2.0)
                
                # DEBUG: Log delle distanze
                print(f"[DEBUG] Doc {i}: distance={distance}, similarity={similarity_score}")
                
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
            Lista degli ID documento (sempre una lista, mai None)
        """
        try:
            # Prova a ottenere documenti da SQLite
            docs = self.metadata_db.get_documents()
            if docs is None:
                logger.warning("get_documents ha restituito None, ritorno lista vuota")
                return []
            
            doc_ids = [doc.get('id') for doc in docs if doc and doc.get('id') is not None]
            # Filtra solo le stringhe valide
            valid_ids = [str(doc_id) for doc_id in doc_ids if doc_id]
            logger.info(f"Trovati {len(valid_ids)} documenti in SQLite")
            return valid_ids
            
        except Exception as e:
            logger.error(f"Errore lista documenti SQLite: {e}")
            # Fallback: prova a leggere da ChromaDB
            try:
                collection = self.vector_db.get_collection()
                if collection:
                    chroma_data = collection.get()
                    chroma_ids = chroma_data.get('ids', []) if chroma_data else []
                    logger.info(f"Fallback ChromaDB: trovati {len(chroma_ids)} documenti")
                    return chroma_ids if isinstance(chroma_ids, list) else []
            except Exception as e2:
                logger.error(f"Errore fallback ChromaDB: {e2}")
            
            return []  # Sempre restituire una lista, mai None
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Restituisce statistiche sui database.
        
        Returns:
            Dict con contatori documenti per database
        """
        try:
            # Ottieni documenti completi dal metadata database
            all_docs = self.metadata_db.get_documents()
            if all_docs is None:
                all_docs = []
            
            # Calcola documenti creati oggi
            from datetime import datetime, date
            today = date.today()
            documents_today = 0
            
            for doc in all_docs:
                if doc and isinstance(doc, dict) and 'created_at' in doc:
                    try:
                        # Parse della data di creazione
                        created_date_str = doc['created_at']
                        if created_date_str:
                            created_date = datetime.fromisoformat(created_date_str.replace('Z', '+00:00')).date()
                            if created_date == today:
                                documents_today += 1
                    except (ValueError, AttributeError, TypeError):
                        continue
            
            stats = {
                'sqlite_documents': self.metadata_db.get_document_count(),
                'chroma_collections': 0,
                'chroma_documents': 0,
                'documents_total': len(all_docs),
                'documents_today': documents_today,
                'collections': 0,
                'processing_queue': 0
            }
            
            # Statistiche ChromaDB
            try:
                collections = self.vector_db.list_collections()
                stats['chroma_collections'] = len(collections)
                stats['collections'] = len(collections)
                
                # Conta documenti nella collezione principale
                collection = self.vector_db.get_collection()
                if collection:
                    stats['chroma_documents'] = collection.count()
                
            except Exception as e:
                logger.warning(f"Errore statistiche ChromaDB: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Errore calcolo statistiche: {e}")
            return {'sqlite_documents': 0, 'chroma_collections': 0, 'chroma_documents': 0, 'documents_total': 0, 'documents_today': 0, 'collections': 0, 'processing_queue': 0}
    
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
                collection = self.vector_db.get_collection()
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
            collections = self.vector_db.list_collections()
            health['chroma_db'] = True
            logger.debug("ChromaDB health check: OK")
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
        
        try:
            # Test SQLite
            count = self.metadata_db.get_document_count()
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
                collection = self.vector_db.get_collection()
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
                    self.metadata_db.delete_document(doc_id)
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
