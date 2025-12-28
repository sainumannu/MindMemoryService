import sys
sys.path.append('C:\\PramaIA-VectorStoreService-Single')

from app.core.vectordb_manager import VectorDBManager

vdb = VectorDBManager()

# Lista tutte le collections
client = vdb._client
collections = client.list_collections()

print(f"Totale collections: {len(collections)}\n")

total_docs = 0
for coll in collections:
    count = coll.count()
    total_docs += count
    print(f"📁 {coll.name}")
    print(f"   Documenti: {count}")
    
    # Mostra alcuni esempi di document IDs
    if count > 0:
        result = coll.get(limit=3)
        if result and result['ids']:
            print(f"   Esempi: {', '.join(result['ids'][:3])}")
    print()

print(f"━" * 50)
print(f"TOTALE DOCUMENTI in ChromaDB: {total_docs}")
