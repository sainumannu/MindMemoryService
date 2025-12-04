"""
Modulo per la gestione degli hash dei file nel VectorstoreService.
"""
import os
import hashlib
import sqlite3
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

class FileHashManager:
    """
    Gestore degli hash dei file per il rilevamento dei duplicati.
    Questa classe gestisce il database degli hash dei file nel VectorstoreService.
    """
    
    def __init__(self, db_path: str = None):
        """
        Inizializza il FileHashManager.
        
        Args:
            db_path: Percorso al database SQLite. Se None, viene usato il percorso predefinito.
        """
        if db_path is None:
            # Usa il percorso del database documenti ma con un nome diverso
            from app.core.config import get_settings
            settings = get_settings()
            base_dir = os.path.dirname(settings.SQLITE_DB_PATH)
            self.db_path = os.path.join(base_dir, "file_hashes.db")
        else:
            self.db_path = db_path
            
        self._init_db()
        logger.info(f"FileHashManager inizializzato con database: {self.db_path}")
        
    def _init_db(self):
        """
        Inizializza il database degli hash se non esiste.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Crea la tabella file_hashes se non esiste
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_hashes (
                file_hash TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                document_id TEXT NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT DEFAULT '',
                client_id TEXT DEFAULT 'system',
                original_path TEXT DEFAULT ''
            )
        ''')
        
        # Crea indici per migliorare le prestazioni
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON file_hashes (file_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_id ON file_hashes (document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_path ON file_hashes (client_id, original_path)')
        
        conn.commit()
        conn.close()
        
    def check_duplicate(self, file_hash: str, client_id: str = "system", 
                       original_path: str = "") -> Tuple[bool, Optional[str], bool]:
        """
        Verifica se un file è un duplicato basandosi sull'hash.
        
        Args:
            file_hash: L'hash MD5 del file
            client_id: ID del client che ha inviato il file
            original_path: Percorso originale del file
            
        Returns:
            Tuple (is_duplicate, document_id, is_path_duplicate)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Cerca prima il file con lo stesso hash, client_id e percorso originale (duplicato esatto)
            cursor.execute(
                "SELECT document_id FROM file_hashes WHERE file_hash = ? AND client_id = ? AND original_path = ?", 
                (file_hash, client_id, original_path)
            )
            result = cursor.fetchone()
            
            if result:
                # Duplicato esatto trovato (stesso hash, stesso client, stesso percorso)
                document_id = result[0]
                logger.info(f"Duplicato esatto rilevato, document_id: {document_id}")
                conn.close()
                return True, document_id, True
            
            # Se non è un duplicato esatto, cerca un duplicato di contenuto (stesso hash, client diverso o percorso diverso)
            cursor.execute(
                "SELECT document_id FROM file_hashes WHERE file_hash = ? LIMIT 1", 
                (file_hash,)
            )
            result = cursor.fetchone()
            
            if result:
                # Duplicato di contenuto trovato
                document_id = result[0]
                logger.info(f"Duplicato di contenuto rilevato, document_id originale: {document_id}")
                conn.close()
                return True, document_id, False
            
            logger.info(f"File non è un duplicato, hash={file_hash}")
            conn.close()
            return False, None, False
            
        except Exception as e:
            logger.error(f"Errore durante il controllo dei duplicati: {e}")
            return False, None, False
            
    def save_file_hash(self, file_hash: str, filename: str, document_id: str, 
                      client_id: str = "system", original_path: str = "") -> bool:
        """
        Salva l'hash di un file nel database.
        
        Args:
            file_hash: L'hash MD5 del file
            filename: Il nome del file
            document_id: L'ID del documento
            client_id: ID del client che ha inviato il file
            original_path: Percorso originale del file
            
        Returns:
            bool: True se il salvataggio è avvenuto con successo, False altrimenti
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Controlla se la combinazione di hash, client_id e original_path è già presente
            cursor.execute(
                "SELECT 1 FROM file_hashes WHERE file_hash = ? AND client_id = ? AND original_path = ?", 
                (file_hash, client_id, original_path)
            )
            if cursor.fetchone():
                logger.info(f"Combinazione hash/client/path già presente, nessun salvataggio effettuato.")
                conn.close()
                return False
                
            # Inserisci i dati
            cursor.execute(
                "INSERT INTO file_hashes (file_hash, file_name, document_id, file_path, client_id, original_path) VALUES (?, ?, ?, ?, ?, ?)",
                (file_hash, filename, document_id, filename, client_id, original_path)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Hash salvato per il file '{filename}', document_id: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante il salvataggio dell'hash: {e}")
            return False
            
    def get_all_hashes(self) -> List[Dict[str, Any]]:
        """
        Ottiene tutti gli hash dal database.
        
        Returns:
            Lista di dizionari contenenti gli hash e i metadati associati
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Permette di accedere alle colonne per nome
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM file_hashes ORDER BY upload_time DESC")
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Errore durante il recupero degli hash: {e}")
            return []
            
    def delete_hash(self, file_hash: str) -> bool:
        """
        Elimina un hash dal database.
        
        Args:
            file_hash: L'hash MD5 del file da eliminare
            
        Returns:
            bool: True se l'eliminazione è avvenuta con successo, False altrimenti
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM file_hashes WHERE file_hash = ?", (file_hash,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            if deleted:
                logger.info(f"Hash {file_hash} eliminato con successo")
            else:
                logger.warning(f"Nessun hash {file_hash} trovato da eliminare")
                
            return deleted
        except Exception as e:
            logger.error(f"Errore durante l'eliminazione dell'hash: {e}")
            return False