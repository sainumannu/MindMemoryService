# Debug Scripts per PramaIA VectorStoreService

Questa directory contiene script di debug per testare le operazioni CRUD sui database ChromaDB e SQLite.

## Script Disponibili

### 🔵 test_chromadb_crud.py
Testa tutte le operazioni CRUD su ChromaDB:
- ✅ CREATE: Inserimento documenti con metadati
- ✅ READ: Lettura documenti e query semantiche
- ✅ UPDATE: Aggiornamento metadati
- ✅ DELETE: Eliminazione documenti
- 📊 Performance test per inserimenti batch

### 🟡 test_sqlite_crud.py
Testa le operazioni CRUD su SQLite:
- ✅ Test diretto con query SQL
- ✅ Test tramite ORM DocumentDatabase
- ✅ Gestione metadati e relazioni
- 📊 Analisi del database esistente

### 🟢 test_hybrid_operations.py
Testa le operazioni coordinate tra ChromaDB e SQLite:
- ✅ Sincronizzazione tra i due database
- ✅ Operazioni tramite HybridDocumentManager
- ✅ Controlli di consistenza
- 📊 Performance test operazioni ibride

### 🚀 run_all_tests.py
Script master che esegue tutti i test:
- 🔍 Verifica ambiente e dipendenze
- 📋 Esegue tutti i test in sequenza
- 📊 Genera report completo dei risultati

## Come Utilizzare

### Esecuzione Singola
```powershell
# Test ChromaDB
python tools\debug\test_chromadb_crud.py

# Test SQLite
python tools\debug\test_sqlite_crud.py

# Test operazioni ibride
python tools\debug\test_hybrid_operations.py
```

### Esecuzione Completa
```powershell
# Esegue tutti i test con report
python tools\debug\run_all_tests.py
```

## Prerequisiti

1. **Servizio VectorStore**: Non deve essere in esecuzione (gli script accedono direttamente ai database)
2. **Dipendenze Python**: `chromadb`, `sqlalchemy`, ecc.
3. **Directory data/**: Verrà creata automaticamente se non esiste

## Output Atteso

Ogni script produce output dettagliato con:
- ✅ Operazioni completate con successo
- ❌ Errori rilevati
- ⚠️ Warning e avvertimenti
- 📊 Statistiche e performance
- 🔍 Analisi del database

## Struttura Database

### SQLite (documents.db)
```sql
-- Tabella documenti principali
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    collection TEXT,
    content TEXT,
    created_at TEXT,
    last_updated TEXT
);

-- Tabella metadati
CREATE TABLE document_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    key TEXT,
    value TEXT,
    value_type TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);
```

### ChromaDB
- **Collezione**: `prama_documents`
- **Contenuto**: Embeddings vettoriali dei documenti
- **Metadati**: Informazioni associate ai vettori

## Risoluzione Problemi

### Errore "Module not found"
```powershell
# Assicurati di essere nella directory root del progetto
cd C:\PramaIA-VectorStoreService-Single

# Verifica che i moduli siano importabili
python -c "from app.core.vectordb_manager import VectorDBManager; print('OK')"
```

### ChromaDB non si inizializza
- Verifica che la directory `data/chroma_db` sia accessibile
- Controlla i log per errori di binding Rust
- Prova a eliminare `data/chroma_db` per reset completo

### SQLite bloccato
- Chiudi il servizio VectorStore se in esecuzione
- Verifica permessi sulla directory `data/`
- Controlla che `documents.db` non sia in uso

## Debug Avanzato

### Logging Dettagliato
```python
# Aggiungi all'inizio degli script per più dettagli
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Ispezione Database
```powershell
# SQLite diretto
sqlite3 data\documents.db ".schema"
sqlite3 data\documents.db "SELECT COUNT(*) FROM documents;"

# ChromaDB via Python
python -c "from app.core.vectordb_manager import VectorDBManager; print(VectorDBManager().get_collection().count())"
```

## Note Tecniche

- Gli script creano dati di test con prefissi riconoscibili (`test_`, `hybrid_test_`, ecc.)
- I cleanup sono automatici ma verifica sempre manualmente
- Le performance dipendono dalla dimensione del database esistente
- I test sono idempotenti (possono essere eseguiti più volte)