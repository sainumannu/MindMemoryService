import sys
sys.path.append('C:\\PramaIA-VectorStoreService-Single')

import sqlite3
from app.core.vectordb_manager import VectorDBManager

print("=" * 60)
print("CONFRONTO COLLECTIONS: SQLite vs ChromaDB")
print("=" * 60)

# 1. Collections in SQLite
conn = sqlite3.connect('data/documents.db')
cursor = conn.cursor()
cursor.execute('SELECT DISTINCT collection FROM documents ORDER BY collection')
sqlite_collections = [row[0] for row in cursor.fetchall()]

print(f"\n[SQLite] Collections distinte nel campo 'collection':")
print(f"   Totale: {len(sqlite_collections)}")
for coll in sqlite_collections:
    cursor.execute('SELECT COUNT(*) FROM documents WHERE collection = ?', (coll,))
    count = cursor.fetchone()[0]
    print(f"   - {coll}: {count} documenti")

conn.close()

# 2. Collections in ChromaDB
vdb = VectorDBManager()
client = vdb._client
chroma_collections = client.list_collections()

print(f"\n[ChromaDB] Collections effettive:")
print(f"   Totale: {len(chroma_collections)}")
for coll in chroma_collections:
    count = coll.count()
    print(f"   - {coll.name}: {count} documenti")

# 3. Verifica endpoint API
import requests
try:
    r = requests.get('http://127.0.0.1:8090/vectorstore/collections')
    if r.status_code == 200:
        api_result = r.json()
        print(f"\n[API] /vectorstore/collections:")
        if isinstance(api_result, dict) and 'collections' in api_result:
            print(f"   Totale: {len(api_result['collections'])}")
            for coll in api_result['collections'][:5]:
                print(f"   - {coll}")
            if len(api_result['collections']) > 5:
                print(f"   ... e altre {len(api_result['collections']) - 5}")
        else:
            print(f"   Response: {api_result}")
    else:
        print(f"\n❌ API non disponibile (status: {r.status_code})")
except Exception as e:
    print(f"\n❌ Errore chiamata API: {e}")

print("\n" + "=" * 60)
print("ANALISI:")
print(f"SQLite collections: {len(sqlite_collections)}")
print(f"ChromaDB collections: {len(chroma_collections)}")
print("=" * 60)
