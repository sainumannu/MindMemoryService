"""
SQLite Metadata Manager - Gestore metadati documenti in database SQLite.
Sostituisce la precedente implementazione basata su JSON file con un database SQLite.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Configurazione logger
logger = logging.getLogger(__name__)

class SQLiteMetadataManager:
    """
    Gestore metadati documenti in database SQLite.
    Utilizza SQLite come backend per scalabilità e performance migliori rispetto al file JSON.
    """
    
    def __init__(self, data_dir: Optional[str] = None, migrate_from_json: bool = True):
        """
        Inizializza il gestore del database documenti.
        
        Args:
            data_dir: Directory per la memorizzazione dei dati. Default alla directory 'data' nella directory corrente.
            migrate_from_json: Se True, tenta di migrare i dati dal vecchio file JSON se presente.
        """
        self.data_dir = data_dir or os.path.join(os.getcwd(), "data")
        self.db_file = os.path.join(self.data_dir, "documents.db")
        self.json_file = os.path.join(self.data_dir, "documents.json")
        
        # Assicurarsi che le directory esistano
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Inizializzare il database
        self._init_database()
        
        # Migrare dal JSON se necessario
        if migrate_from_json and os.path.exists(self.json_file):
            self._migrate_from_json()
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """
        Ottiene una connessione al database SQLite.
        
        Returns:
            Connessione SQLite.
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Per ottenere risultati come dizionari
        return conn
    
    def _init_database(self) -> None:
        """
        Inizializza il database creando le tabelle necessarie se non esistono.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Tabella principale dei documenti
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    collection TEXT NOT NULL,
                    content TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabella dei metadati (relazione one-to-many con documenti)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS document_metadata (
                    document_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    value_type TEXT NOT NULL,
                    PRIMARY KEY (document_id, key),
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            ''')
            
            # Indici per migliorare le performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_metadata_key ON document_metadata(key)')
            
            # Verifica se la colonna content esiste già
            try:
                cursor.execute("SELECT content FROM documents LIMIT 1")
            except sqlite3.OperationalError:
                # La colonna non esiste, aggiungiamola
                logger.info("Aggiunta colonna 'content' alla tabella documents")
                cursor.execute('ALTER TABLE documents ADD COLUMN content TEXT')
            
            conn.commit()
            conn.close()
            logger.info(f"Database inizializzato con successo: {self.db_file}")
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione del database: {str(e)}")
            raise
    
    def _migrate_from_json(self) -> None:
        """
        Migra i dati dal vecchio formato JSON al nuovo database SQLite.
        """
        try:
            # Verifica se la migrazione è già stata eseguita controllando se ci sono documenti nel DB
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            conn.close()
            
            # Se ci sono già documenti nel database, salta la migrazione
            if doc_count > 0:
                logger.info("Migrazione JSON -> SQLite saltata: documenti già presenti nel database")
                return
            
            # Carica i dati dal file JSON
            if not os.path.exists(self.json_file):
                logger.info(f"File JSON non trovato, migrazione saltata: {self.json_file}")
                return
                
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                documents = data.get("documents", [])
            
            if not documents:
                logger.info("Nessun documento trovato nel file JSON, migrazione saltata")
                return
            
            # Migra i documenti al database
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Usa una transazione per migliorare le performance e garantire l'atomicità
            conn.execute("BEGIN TRANSACTION")
            
            count = 0
            for doc in documents:
                try:
                    # Inserisci il documento principale
                    cursor.execute(
                        "INSERT INTO documents (id, filename, collection, created_at) VALUES (?, ?, ?, ?)",
                        (
                            doc.get("id", ""),
                            doc.get("filename", ""),
                            doc.get("collection", ""),
                            doc.get("metadata", {}).get("created_at", datetime.now().isoformat())
                        )
                    )
                    
                    # Inserisci i metadati
                    metadata = doc.get("metadata", {})
                    for key, value in metadata.items():
                        value_type = "str"
                        if isinstance(value, int):
                            value_type = "int"
                        elif isinstance(value, float):
                            value_type = "float"
                        elif isinstance(value, bool):
                            value_type = "bool"
                        elif isinstance(value, dict) or isinstance(value, list):
                            value = json.dumps(value)
                            value_type = "json"
                        
                        cursor.execute(
                            "INSERT INTO document_metadata (document_id, key, value, value_type) VALUES (?, ?, ?, ?)",
                            (doc.get("id", ""), key, str(value), value_type)
                        )
                    
                    count += 1
                except Exception as doc_error:
                    logger.warning(f"Errore durante la migrazione del documento {doc.get('id')}: {str(doc_error)}")
            
            conn.commit()
            conn.close()
            
            # Crea un backup del file JSON originale
            backup_file = f"{self.json_file}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            import shutil
            shutil.copy2(self.json_file, backup_file)
            
            logger.info(f"Migrazione completata: {count} documenti migrati dal JSON al database SQLite")
            logger.info(f"Backup del file JSON originale creato: {backup_file}")
            
        except Exception as e:
            logger.error(f"Errore durante la migrazione dal JSON al database: {str(e)}")
            raise
    
    def get_documents(self, collection: Optional[str] = None, limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Ottiene tutti i documenti, opzionalmente filtrati per collezione.
        
        Args:
            collection: Nome della collezione per filtrare i risultati (opzionale)
            limit: Numero massimo di documenti da restituire
            offset: Offset per la paginazione
        
        Returns:
            Lista di documenti con i relativi metadati.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Query di base
            query = "SELECT * FROM documents"
            params = []
            
            # Aggiungi filtro per collezione se specificato
            if collection:
                query += " WHERE collection = ?"
                params.append(collection)
            
            # Aggiungi limit e offset
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            documents_rows = cursor.fetchall()
            
            # Converti i risultati in dizionari
            documents = []
            for doc_row in documents_rows:
                doc = dict(doc_row)
                
                # Ottieni i metadati per questo documento
                cursor.execute(
                    "SELECT key, value, value_type FROM document_metadata WHERE document_id = ?",
                    (doc['id'],)
                )
                metadata_rows = cursor.fetchall()
                
                # Converti i metadati in un dizionario
                metadata = {}
                for meta_row in metadata_rows:
                    key = meta_row['key']
                    value = meta_row['value']
                    value_type = meta_row['value_type']
                    
                    # Converti il valore nel tipo corretto
                    if value_type == 'int':
                        try:
                            value = int(value)
                        except ValueError:
                            # Se non può essere convertito, mantieni come stringa
                            pass
                    elif value_type == 'float':
                        try:
                            value = float(value)
                        except ValueError:
                            # Se non può essere convertito, mantieni come stringa
                            pass
                    elif value_type == 'bool':
                        value = str(value).lower() in ('true', '1', 'yes')
                    elif value_type == 'json':
                        try:
                            value = json.loads(value)
                        except:
                            pass
                    
                    metadata[key] = value
                
                # Aggiungi metadati al documento
                doc['metadata'] = metadata
                documents.append(doc)
            
            conn.close()
            return documents
            
        except Exception as e:
            logger.error(f"Errore nel recupero dei documenti: {str(e)}")
            return []
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene un documento specifico dal database.
        
        Args:
            document_id: ID del documento da recuperare
            
        Returns:
            Il documento con i relativi metadati, o None se non trovato.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Ottieni il documento principale
            cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            doc_row = cursor.fetchone()
            
            print(f"Ricerca documento {document_id} nel DB: {doc_row is not None}")
            
            if not doc_row:
                # Controlliamo se esistono documenti nel database
                cursor.execute("SELECT COUNT(*) FROM documents")
                count = cursor.fetchone()[0]
                print(f"Il database contiene {count} documenti")
                
                # Elenchiamo i primi 5 documenti per diagnostica
                if count > 0:
                    cursor.execute("SELECT id FROM documents LIMIT 5")
                    ids = [row[0] for row in cursor.fetchall()]
                    print(f"Primi 5 documenti nel DB: {ids}")
                
                conn.close()
                return None
            
            # Converti in dizionario
            doc = dict(doc_row)
            
            # Aggiungi il contenuto direttamente al documento se presente
            if "content" in doc and doc["content"]:
                print(f"Documento {document_id} ha contenuto: {len(doc['content'])} caratteri")
            else:
                print(f"Documento {document_id} non ha contenuto nel campo 'content'")
            
            # Ottieni i metadati
            cursor.execute(
                "SELECT key, value, value_type FROM document_metadata WHERE document_id = ?",
                (document_id,)
            )
            metadata_rows = cursor.fetchall()
            
            print(f"Documento {document_id} ha {len(metadata_rows)} metadati")
            
            # Converti i metadati in un dizionario
            metadata = {}
            for meta_row in metadata_rows:
                key = meta_row['key']
                value = meta_row['value']
                value_type = meta_row['value_type']
                
                # Converti il valore nel tipo corretto
                if value_type == 'int':
                    try:
                        value = int(value)
                    except ValueError:
                        # Se non può essere convertito, mantieni come stringa
                        pass
                elif value_type == 'float':
                    try:
                        value = float(value)
                    except ValueError:
                        # Se non può essere convertito, mantieni come stringa
                        pass
                elif value_type == 'bool':
                    value = str(value).lower() in ('true', '1', 'yes')
                elif value_type == 'json':
                    try:
                        value = json.loads(value)
                    except:
                        pass
                
                metadata[key] = value
            
            # Aggiungi metadati al documento
            doc['metadata'] = metadata
            
            conn.close()
            return doc
            
        except Exception as e:
            print(f"Errore nel recupero del documento {document_id}: {str(e)}")
            return None
    
    def add_document(self, document: Dict[str, Any]) -> bool:
        """
        Aggiunge o aggiorna un documento nel database.
        
        Args:
            document: Documento da aggiungere/aggiornare (deve contenere almeno id, filename, collection)
            
        Returns:
            True se l'operazione è avvenuta con successo, False altrimenti.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Verifica se il documento esiste già
            cursor.execute("SELECT id FROM documents WHERE id = ?", (document.get('id', ''),))
            existing = cursor.fetchone()
            
            logger.debug(f"Aggiunta documento con ID: {document.get('id', '')}. Esiste già: {existing is not None}")
            
            # Preparazione campi
            doc_id = document.get('id', '')
            filename = document.get('filename', '')
            collection = document.get('collection', document.get('collection_name', ''))
            content = document.get('content', '')  # Salviamo anche il contenuto
            
            conn.execute("BEGIN TRANSACTION")
            
            if existing:
                # Aggiorna il documento esistente
                cursor.execute(
                    "UPDATE documents SET filename = ?, collection = ?, content = ?, last_updated = ? WHERE id = ?",
                    (
                        filename,
                        collection,
                        content,
                        datetime.now().isoformat(),
                        doc_id
                    )
                )
                logger.debug(f"Documento {doc_id} aggiornato nel database")
                
                # Elimina i metadati esistenti
                cursor.execute("DELETE FROM document_metadata WHERE document_id = ?", (doc_id,))
            else:
                # Inserisci nuovo documento
                cursor.execute(
                    "INSERT INTO documents (id, filename, collection, content, created_at, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        doc_id,
                        filename,
                        collection,
                        content,
                        document.get('metadata', {}).get('created_at', datetime.now().isoformat()),
                        datetime.now().isoformat()
                    )
                )
                logger.debug(f"Nuovo documento {doc_id} inserito nel database")
            
            # Inserisci i metadati
            metadata = document.get('metadata', {})
            for key, value in metadata.items():
                value_type = "str"
                if isinstance(value, int):
                    value_type = "int"
                elif isinstance(value, float):
                    value_type = "float"
                elif isinstance(value, bool):
                    value_type = "bool"
                elif isinstance(value, dict) or isinstance(value, list):
                    value = json.dumps(value)
                    value_type = "json"
                
                cursor.execute(
                    "INSERT INTO document_metadata (document_id, key, value, value_type) VALUES (?, ?, ?, ?)",
                    (document.get('id', ''), key, str(value), value_type)
                )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Errore nell'aggiunta/aggiornamento del documento {document.get('id', '')}: {str(e)}")
            return False
    
    def delete_document(self, document_id: str) -> bool:
        """
        Elimina un documento dal database.
        
        Args:
            document_id: ID del documento da eliminare
            
        Returns:
            True se l'eliminazione è avvenuta con successo, False altrimenti.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Elimina il documento (i metadati verranno eliminati automaticamente grazie alla foreign key con ON DELETE CASCADE)
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Errore nell'eliminazione del documento {document_id}: {str(e)}")
            return False
            
    def update_metadata(self, document_id: str, key: str, value: Any) -> bool:
        """
        Aggiorna un singolo campo di metadati per un documento.
        
        Args:
            document_id: ID del documento
            key: Chiave del metadato da aggiornare
            value: Nuovo valore
            
        Returns:
            True se l'aggiornamento è avvenuto con successo, False altrimenti.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Verifica se il metadato esiste già
            cursor.execute(
                "SELECT id FROM document_metadata WHERE document_id = ? AND key = ?", 
                (document_id, key)
            )
            existing = cursor.fetchone()
            
            # Determina il tipo di valore
            value_type = "str"
            if isinstance(value, int):
                value_type = "int"
            elif isinstance(value, float):
                value_type = "float"
            elif isinstance(value, bool):
                value_type = "bool"
            elif isinstance(value, dict) or isinstance(value, list):
                value = json.dumps(value)
                value_type = "json"
            
            if existing:
                # Aggiorna il metadato esistente
                cursor.execute(
                    "UPDATE document_metadata SET value = ?, value_type = ? WHERE document_id = ? AND key = ?",
                    (str(value), value_type, document_id, key)
                )
            else:
                # Inserisce un nuovo metadato
                cursor.execute(
                    "INSERT INTO document_metadata (document_id, key, value, value_type) VALUES (?, ?, ?, ?)",
                    (document_id, key, str(value), value_type)
                )
            
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento del metadato {key} per il documento {document_id}: {str(e)}")
            return False
    
    def get_collections(self) -> List[str]:
        """
        Ottiene tutte le collezioni presenti nel database.
        
        Returns:
            Lista di nomi di collezioni.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT collection FROM documents")
            collections = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return collections
            
        except Exception as e:
            logger.error(f"Errore nel recupero delle collezioni: {str(e)}")
            return []
    
    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Ottiene statistiche su una collezione o su tutte le collezioni.
        
        Args:
            collection_name: Nome della collezione (opzionale, se None vengono restituite statistiche globali)
            
        Returns:
            Dizionario con statistiche sulla collezione.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            if collection_name:
                # Statistiche per una collezione specifica
                cursor.execute("SELECT COUNT(*) FROM documents WHERE collection = ?", (collection_name,))
                stats["document_count"] = cursor.fetchone()[0]
                
                # Documenti più recenti
                cursor.execute(
                    "SELECT created_at FROM documents WHERE collection = ? ORDER BY created_at DESC LIMIT 1",
                    (collection_name,)
                )
                latest = cursor.fetchone()
                stats["latest_document"] = latest[0] if latest else None
                
                # Metadati più comuni
                cursor.execute("""
                    SELECT key, COUNT(*) as count 
                    FROM document_metadata 
                    WHERE document_id IN (SELECT id FROM documents WHERE collection = ?) 
                    GROUP BY key 
                    ORDER BY count DESC
                """, (collection_name,))
                metadata_stats = {row[0]: row[1] for row in cursor.fetchall()}
                stats["metadata_keys"] = metadata_stats
                
            else:
                # Statistiche globali
                cursor.execute("SELECT COUNT(*) FROM documents")
                stats["total_documents"] = cursor.fetchone()[0]
                
                # Conteggio per collezione
                cursor.execute("SELECT collection, COUNT(*) FROM documents GROUP BY collection")
                collection_counts = {row[0]: row[1] for row in cursor.fetchall()}
                stats["collections"] = collection_counts
                
                # Documenti più recenti
                cursor.execute("SELECT created_at FROM documents ORDER BY created_at DESC LIMIT 1")
                latest = cursor.fetchone()
                stats["latest_document"] = latest[0] if latest else None
                
                # Totale metadati
                cursor.execute("SELECT COUNT(*) FROM document_metadata")
                stats["total_metadata_entries"] = cursor.fetchone()[0]
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Errore nel recupero delle statistiche della collezione: {str(e)}")
            return {}
    
    def search_documents(self, 
                        query: str, 
                        collection: Optional[str] = None,
                        metadata_filters: Optional[Dict[str, Any]] = None,
                        limit: int = 100,
                        offset: int = 0) -> List[Dict[str, Any]]:
        """
        Esegue una ricerca sui documenti in base al testo e ai metadati.
        
        Args:
            query: Testo da cercare nel nome del file
            collection: Nome della collezione (opzionale)
            metadata_filters: Filtri sui metadati (opzionale)
            limit: Numero massimo di documenti da restituire
            offset: Offset per la paginazione
            
        Returns:
            Lista di documenti che corrispondono ai criteri di ricerca.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Query di base
            query_parts = ["1=1"]  # Trick per iniziare sempre con AND
            params = []
            
            # Aggiungi filtro per testo
            if query:
                query_parts.append("filename LIKE ?")
                params.append(f"%{query}%")
            
            # Aggiungi filtro per collezione
            if collection:
                query_parts.append("collection = ?")
                params.append(collection)
            
            # Costruisci la query SQL
            sql_query = f"""
                SELECT DISTINCT d.* 
                FROM documents d
                WHERE {' AND '.join(query_parts)}
                ORDER BY d.created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            cursor.execute(sql_query, params)
            document_rows = cursor.fetchall()
            
            # Se ci sono filtri sui metadati, filtra ulteriormente i risultati
            results = []
            for doc_row in document_rows:
                doc = dict(doc_row)
                
                # Ottieni metadati
                cursor.execute(
                    "SELECT key, value, value_type FROM document_metadata WHERE document_id = ?",
                    (doc['id'],)
                )
                metadata_rows = cursor.fetchall()
                
                # Costruisci dizionario metadati
                metadata = {}
                for meta_row in metadata_rows:
                    key = meta_row['key']
                    value = meta_row['value']
                    value_type = meta_row['value_type']
                    
                    # Converti il valore nel tipo corretto
                    if value_type == 'int':
                        try:
                            value = int(value)
                        except ValueError:
                            # Se non può essere convertito, mantieni come stringa
                            pass
                    elif value_type == 'float':
                        try:
                            value = float(value)
                        except ValueError:
                            # Se non può essere convertito, mantieni come stringa
                            pass
                    elif value_type == 'bool':
                        value = str(value).lower() in ('true', '1', 'yes')
                    elif value_type == 'json':
                        try:
                            value = json.loads(value)
                        except:
                            pass
                    
                    metadata[key] = value
                
                doc['metadata'] = metadata
                
                # Applica filtri sui metadati
                include_doc = True
                if metadata_filters:
                    for meta_key, meta_value in metadata_filters.items():
                        if meta_key not in metadata or metadata[meta_key] != meta_value:
                            include_doc = False
                            break
                
                if include_doc:
                    results.append(doc)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Errore nella ricerca dei documenti: {str(e)}")
            return []
    
    def export_to_json(self, output_file: Optional[str] = None) -> bool:
        """
        Esporta tutti i documenti in un file JSON.
        Utile per backup o migrazione.
        
        Args:
            output_file: Percorso del file di output (opzionale, default al file JSON originale)
            
        Returns:
            True se l'esportazione è avvenuta con successo, False altrimenti.
        """
        try:
            if output_file is None:
                output_file = self.json_file
            
            documents = self.get_documents(limit=100000)  # Prendi tutti i documenti
            
            data = {"documents": documents}
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Esportazione in JSON completata: {len(documents)} documenti esportati in {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Errore nell'esportazione in JSON: {str(e)}")
            return False
    
    def get_document_count(self, collection: Optional[str] = None) -> int:
        """
        Ottiene il numero totale di documenti, opzionalmente filtrati per collezione.
        
        Args:
            collection: Nome della collezione (opzionale)
            
        Returns:
            Numero di documenti.
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            if collection:
                cursor.execute("SELECT COUNT(*) FROM documents WHERE collection = ?", (collection,))
            else:
                cursor.execute("SELECT COUNT(*) FROM documents")
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Errore nel conteggio dei documenti: {str(e)}")
            return 0
    
    def vacuum_database(self) -> bool:
        """
        Esegue un'operazione VACUUM sul database per ottimizzare lo spazio.
        Utile dopo molte operazioni di eliminazione.
        
        Returns:
            True se l'operazione è avvenuta con successo, False altrimenti.
        """
        try:
            conn = sqlite3.connect(self.db_file)
            conn.execute("VACUUM")
            conn.close()
            
            logger.info(f"Operazione VACUUM completata con successo sul database {self.db_file}")
            return True
            
        except Exception as e:
            logger.error(f"Errore nell'esecuzione di VACUUM sul database: {str(e)}")
            return False
