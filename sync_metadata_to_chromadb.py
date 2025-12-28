"""
Script per sincronizzare i metadati da SQLite a ChromaDB.
Popola i metadati mancanti (incluso tags) in ChromaDB per tutti i documenti.
"""

import sqlite3
import json
import chromadb
from chromadb.config import Settings

def sync_metadata_sqlite_to_chromadb():
    """
    Legge i documenti e metadati da SQLite e sincronizza con ChromaDB.
    """
    # Connetti a SQLite
    sqlite_conn = sqlite3.connect("data/documents.db")
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Leggi tutti i documenti da SQLite
    sqlite_cursor.execute("SELECT id, collection, content FROM documents")
    docs = sqlite_cursor.fetchall()
    
    print(f"[INFO] Trovati {len(docs)} documenti in SQLite")
    
    # Connetti a ChromaDB
    chroma_client = chromadb.PersistentClient(path="data/chroma_db")
    collection = chroma_client.get_collection(name="prama_documents")
    
    synced_count = 0
    for doc_row in docs:
        doc_id = doc_row['id']
        doc_collection = doc_row['collection']
        doc_content = doc_row['content']
        
        # Leggi metadati da SQLite
        sqlite_cursor.execute(
            "SELECT key, value, value_type FROM document_metadata WHERE document_id = ?",
            (doc_id,)
        )
        metadata_rows = sqlite_cursor.fetchall()
        
        # Ricostruisci metadati
        metadata = {}
        for meta_row in metadata_rows:
            key = meta_row['key']
            value = meta_row['value']
            value_type = meta_row['value_type']
            
            if value_type == 'json':
                try:
                    value = json.loads(value)
                except:
                    pass
            elif value_type == 'int':
                try:
                    value = int(value) if value else 0
                except:
                    value = value
            elif value_type == 'float':
                try:
                    value = float(value) if value else 0.0
                except:
                    value = value
            elif value_type == 'bool':
                value = str(value).lower() in ('true', '1', 'yes')
            
            metadata[key] = value
        
        # Se non ci sono metadati in SQLite, crea un metadato minimo (ChromaDB richiede almeno un campo)
        if not metadata:
            metadata = {"collection": doc_collection}
        
        # Verifica se il documento esiste in ChromaDB
        try:
            existing = collection.get(ids=[doc_id])
            if existing['ids']:
                # Il documento esiste, aggiorna i metadati
                collection.update(
                    ids=[doc_id],
                    metadatas=[metadata]
                )
                print(f"[UPDATE] {doc_id}: metadata sincronizzati ({len(metadata)} campi, tags={len(metadata.get('tags', []))})")
                synced_count += 1
            else:
                # Il documento non esiste in ChromaDB, potrebbe essere stato rimosso
                print(f"[SKIP] {doc_id}: non trovato in ChromaDB")
        except Exception as e:
            print(f"[ERROR] {doc_id}: {e}")
    
    sqlite_conn.close()
    print(f"\n[SUCCESS] Sincronizzazione completata: {synced_count} documenti aggiornati")

if __name__ == "__main__":
    sync_metadata_sqlite_to_chromadb()
