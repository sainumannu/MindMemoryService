import sys
sys.path.append('C:\\PramaIA-VectorStoreService-Single')

from app.core.vectordb_manager import VectorDBManager

vdb = VectorDBManager()
collection = vdb.get_collection('prama_documents')
result = collection.get(ids=['doc1ed3902f'])

print('In ChromaDB:', len(result['ids']) > 0 if result else False)
if result and result['ids']:
    print('Content:', result['documents'][0][:100])
    print('ChromaDB Metadata:', result['metadatas'][0])
else:
    print('Document NOT in ChromaDB!')
