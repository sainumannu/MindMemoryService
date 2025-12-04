# VectorstoreService - Architettura e Funzionamento Interno

## Panoramica Generale

Il VectorstoreService è un sistema di gestione documenti che combina un database vettoriale (ChromaDB) per la ricerca semantica con un database relazionale (SQLite) per la gestione dei metadati.

## Architettura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    VectorstoreService                       │
├─────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                       │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Documents     │  │   Query/Search  │                  │
│  │   Endpoints     │  │   Endpoints     │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │         MetadataStoreManager                           │ │
│  │    (Coordinatore centrale)                             │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   ChromaDB      │  │   SQLite DB     │                  │
│  │  (Vettoriale)   │  │  (Metadati)     │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Componenti Principali

### 1. MetadataStoreManager
**File**: `app/utils/metadata_store_manager.py`

Coordinatore centrale che gestisce la sincronizzazione tra ChromaDB e SQLite.

### 2. DocumentDatabase
**File**: `app/utils/document_database.py`

Gestisce il database SQLite per metadati e accesso diretto.

**Schema Database**:
```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    collection TEXT,
    content TEXT,
    created_at TEXT,
    last_updated TEXT
);

CREATE TABLE document_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    key TEXT,
    value TEXT,
    value_type TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);
```

### 3. ChromaDBManager
**File**: `app/core/chroma_manager.py`

Gestisce la connessione persistente a ChromaDB per la ricerca vettoriale.

## Flusso di Inserimento Documenti

1. **Ricezione**: API riceve documento con metadati
2. **Analisi Contenuto**: Determina se il contenuto è vettorizzabile
3. **Salvataggio SQLite**: Metadati salvati nel database relazionale
4. **Vettorizzazione**: Se testuale, contenuto vettorizzato in ChromaDB
5. **Aggiornamento**: Flag di vettorizzazione aggiornato

## Flusso di Ricerca

### Ricerca per ID
1. Query SQLite per metadati
2. Se non trovato, fallback su ChromaDB
3. Sincronizzazione automatica se recuperato da ChromaDB

### Ricerca Semantica
1. Embedding della query
2. Ricerca vettoriale in ChromaDB
3. Calcolo similarity score da distanza coseno
4. Formattazione risultati

## Bug Critici Risolti (v1.1.0)

### Problema Conversione Tipi Metadati
**Errore**: `invalid literal for int() with base 10: 'False'`

**Causa**: Metadati boolean salvati come string ma recuperati come int

**Soluzione**:
```python
# PRIMA (errato):
if value_type == 'int':
    value = int('False')  # ERRORE!

# DOPO (corretto):
if value_type == 'bool':
    value = str(value).lower() in ('true', '1', 'yes')
```

### Similarity Score Negativi
**Problema**: Score di similarità negativi (-0.3081)

**Soluzione**: Formula corretta per ChromaDB
```python
distance = results['distances'][0][i]
similarity_score = max(0.0, 1.0 - math.sqrt(distance))
```

## Best Practices per Sviluppatori

1. **Usare sempre MetadataStoreManager** per operazioni sui documenti
2. **Non accedere direttamente** a ChromaDB o SQLite
3. **Gestire errori** con try/catch appropriati
4. **Testare entrambi i database** (ChromaDB + SQLite)
5. **Verificare sincronizzazione** tra i sistemi

## Configurazione

```bash
# Directory dati
VECTORSTORE_DATA_DIR=./data

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma_db

# Database SQLite
SQLITE_DB_PATH=./data/documents.db
```

## Troubleshooting

### Debug Documenti Mancanti
```python
# Verifica presenza in entrambi i database
def debug_document(doc_id):
    # SQLite
    doc = metadata_manager.get_document(doc_id)
    print(f"In SQLite: {doc is not None}")
    
    # ChromaDB
    collection = chroma_manager.get_collection("collection_name")
    chroma_doc = collection.get(ids=[doc_id])
    print(f"In ChromaDB: {bool(chroma_doc.get('ids'))}")
```