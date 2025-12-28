import sqlite3
import json
import os

# --- SQLite: Estrai tags dai metadata ---
def get_sqlite_tags(db_path, limit=20):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, d.collection, m.value, m.value_type
        FROM documents d
        LEFT JOIN document_metadata m ON d.id = m.document_id
        WHERE m.key = 'tags'
        ORDER BY d.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    result = []
    for doc_id, collection, value, value_type in rows:
        tags = None
        if value is not None:
            if value_type == 'json':
                try:
                    tags = json.loads(value)
                except Exception:
                    tags = value
            else:
                tags = value
        result.append({'id': doc_id, 'collection': collection, 'tags': tags})
    conn.close()
    return result

# --- ChromaDB: Estrai tags dai metadati ---
def get_chromadb_tags(collection_name=None, limit=20):
    try:
        import chromadb
        client = chromadb.PersistentClient(path="data/chroma_db")
        colls = client.list_collections()
        results = []
        for coll in colls:
            if collection_name and coll.name != collection_name:
                continue
            collection = client.get_collection(coll.name)
            docs = collection.get(limit=limit)
            for i, doc_id in enumerate(docs['ids']):
                meta = docs['metadatas'][i] if docs['metadatas'] else {}
                tags = meta.get('tags')
                results.append({'id': doc_id, 'collection': coll.name, 'tags': tags})
        return results
    except Exception as e:
        print(f"[ChromaDB] Errore: {e}")
        return []

if __name__ == "__main__":
    print("=== TAGS SU SQLITE ===")
    sqlite_path = os.path.join("data", "documents.db")
    if os.path.exists(sqlite_path):
        sqlite_docs = get_sqlite_tags(sqlite_path)
        if sqlite_docs:
            for doc in sqlite_docs:
                print(json.dumps(doc, indent=2, ensure_ascii=False))
        else:
            print("Nessun documento con tag trovato su SQLite.")
    else:
        print("Database SQLite non trovato.")

    print("\n=== TAGS SU CHROMADB ===")
    chromadb_docs = get_chromadb_tags()
    if chromadb_docs:
        for doc in chromadb_docs:
            print(json.dumps(doc, indent=2, ensure_ascii=False))
    else:
        print("Nessun documento con tag trovato su ChromaDB.")
