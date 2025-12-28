"""
Normalizza le collection in SQLite per allinearle a ChromaDB.
Tutti i 272 documenti sono in ChromaDB collection 'prama_documents',
quindi aggiorniamo anche SQLite per avere la stessa collection.
"""

import sqlite3
import sys
sys.path.append('C:\\PramaIA-VectorStoreService-Single')

from app.core.vectordb_manager import VectorDBManager

# 1. Ottieni tutti gli ID da ChromaDB collection prama_documents
print("=" * 60)
print("NORMALIZZAZIONE COLLECTIONS SQLite <- ChromaDB")
print("=" * 60)

vdb = VectorDBManager()
collection = vdb.get_collection('prama_documents')
result = collection.get()
chromadb_ids = set(result['ids']) if result and result['ids'] else set()

print(f"\nDocumenti in ChromaDB 'prama_documents': {len(chromadb_ids)}")

# 2. Aggiorna SQLite per allineare le collection
conn = sqlite3.connect('data/documents.db')
cursor = conn.cursor()

# Conta documenti per collection prima dell'update
cursor.execute('SELECT collection, COUNT(*) FROM documents GROUP BY collection ORDER BY collection')
before = cursor.fetchall()
print(f"\nPRIMA - Collections in SQLite:")
for coll, count in before:
    print(f"  {coll or '(vuoto)'}: {count}")

# Aggiorna tutti i documenti che sono in ChromaDB prama_documents
print(f"\nAggiornamento in corso...")
for doc_id in chromadb_ids:
    cursor.execute(
        "UPDATE documents SET collection = 'prama_documents' WHERE id = ?",
        (doc_id,)
    )

conn.commit()

# Conta documenti per collection dopo l'update
cursor.execute('SELECT collection, COUNT(*) FROM documents GROUP BY collection ORDER BY collection')
after = cursor.fetchall()
print(f"\nDOPO - Collections in SQLite:")
for coll, count in after:
    print(f"  {coll or '(vuoto)'}: {count}")

conn.close()

print("\n" + "=" * 60)
print("✅ Normalizzazione completata!")
print("=" * 60)
