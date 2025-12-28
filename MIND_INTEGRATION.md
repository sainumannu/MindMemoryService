# Mind Documents API - Riepilogo della soluzione

## Problema iniziale

Il VectorstoreService era nato per essere generico:
- Poteva salvare **solo contenuto** (per file semantici tipo PDF)
- Poteva salvare **solo metadata** (per file non semanticamente processabili tipo DWG)
- Oppure entrambi accoppiati

Questo causava incoerenza nei dati e impossibilità per Mind (il progetto del collega) di garantire che contenuto e metadati fossero sempre sincronizzati.

## Soluzione implementata

### 1. Nuovi endpoint dedicati a Mind (`POST /mind/documents/*`)

Creato nuovo file [app/api/routes/mind_documents.py](app/api/routes/mind_documents.py) con endpoint che impongono **validazione rigorosa**:

#### Creazione documento
```http
POST /mind/documents/
```

**OBBLIGATORIO**: `content` + `metadata` (entrambi non vuoti)
**OPZIONALE**: `id`, `collection` (default: "mind_default")

**Validazione**:
- ❌ Rifiuta: documento con **solo content** (no metadata)
- ❌ Rifiuta: documento con **solo metadata** (no content)
- ❌ Rifiuta: content vuoto
- ❌ Rifiuta: metadata vuoto
- ✅ Accetta: content + metadata validi

Codice di validazione in `validate_document_input()`:

```python
def validate_document_input(data, require_collection=True):
    # Verifica content non vuoto
    if not data.get('content', '').strip():
        raise HTTPException(400, "Campo 'content' obbligatorio e non vuoto")
    
    # Verifica metadata non vuoto
    if not isinstance(data.get('metadata'), dict) or len(data['metadata']) == 0:
        raise HTTPException(400, "Campo 'metadata' obbligatorio e non vuoto")
```

#### Operazioni supportate

1. **CREATE**: `POST /mind/documents/` 
   - Crea nuovo documento con content + metadata obbligatori
   - Auto-genera ID se non fornito
   - Aggiunge `created_at` timestamp

2. **GET**: `GET /mind/documents/{id}`
   - Recupera documento con metadati completi
   - Restituisce 404 se non trovato

3. **UPDATE**: `POST /mind/documents/{id}`
   - Aggiorna content + metadata (entrambi obbligatori)
   - Preserva `created_at` e aggiunge `updated_at`
   - Collection non può essere modificata

4. **DELETE**: `DELETE /mind/documents/{id}`
   - Elimina documento
   - Restituisce 404 se non trovato

5. **QUERY**: `POST /mind/documents/{collection}/query`
   - Ricerca semantica con full metadata in response
   - Input: JSON con `{ "query_text": "..." }`
   - Output: lista documenti con similarity score + metadati completi

### 2. Integrazione nei router

Nel file [app/api/__init__.py](app/api/__init__.py):

```python
from app.api.routes import mind_documents

# Include Mind-specific router with strict validation
api_router.include_router(mind_documents.router, tags=["mind"])
```

Le route sono prefissate automaticamente con `/mind/documents` grazie al router prefix.

### 3. Stato dei database

I documenti creati tramite endpoint Mind hanno:

**SQLite**: 
- `documents` table: id, collection, content, created_at, last_updated
- `document_metadata` table: document_id, key, value, value_type
  - Sempre presente almeno `created_at`
  - Tutti i metadata della payload salvati

**ChromaDB**:
- Embedding generato automaticamente
- Metadata salvati (non sincroni con SQLite)

### 4. Test results

Eseguito script [test_mind_endpoints.py](test_mind_endpoints.py):

✅ **TEST 1**: Create con content+metadata → Status 201 OK
✅ **TEST 2**: Create con solo content → Status 400 (Metadata obbligatorio)
✅ **TEST 3**: Create con solo metadata → Status 400 (Content obbligatorio)
✅ **TEST 4**: Create con content vuoto → Status 400
✅ **TEST 5**: Create con metadata vuoto → Status 400
✅ **TEST 6**: GET documento → Status 200 con metadati completi
✅ **TEST 7**: Query semantica → Status 200 con risultati
✅ **TEST 8**: Create con ID auto-generato → Status 201 OK

## Nota importante: Documenti legacy

I documenti creati PRIMA di questa implementazione (ep_*, kn_*, doc* da cromosomi PramaIA-Mind):
- Sono in **ChromaDB** con metadati vuoti o sparsi
- NON hanno metadata rows in **SQLite**
- Continuano a funzionare tramite endpoint vecchi (`/documents/`)
- Query tramite Mind API non ritorna metadati completi per questi (restituisce {})

**Per il futuro**: 
- Tutti i documenti creati via `/mind/documents/` avranno content + metadata accoppiati e sincronizzati
- Eventuali documenti legacy possono essere migrati creando metadata rows in SQLite

## Architettura risultante

```
┌─────────────────────────────────────────┐
│   PramaIA-Mind (client)                 │
│                                         │
│  POST /mind/documents/                  │
│     + content + metadata (obbligatori)  │
│                                         │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│   VectorstoreService                    │
│                                         │
│   • Validazione rigorosa                │
│   • Content + metadata accoppiati       │
│   • Salva in SQLite + ChromaDB sync     │
│                                         │
└────────────┬────────────────────────────┘
             │
      ┌──────┴──────┐
      ▼             ▼
┌─────────────┐ ┌──────────────┐
│  SQLite DB  │ │  ChromaDB    │
│  (metadata) │ │  (embeddings)│
└─────────────┘ └──────────────┘
```

## Prossimi step

Per il collega (Mind integration):
1. Usare i nuovi endpoint `/mind/documents/*` per tutte le operazioni future
2. Documentazione API: `/docs` (Swagger) o `/redoc` (ReDoc)
3. Eventuali documenti legacy da migrare: script SQL per popolare SQLite metadata dalle informazioni disponibili

Per il VectorstoreService:
1. Mantenere compatibilità con endpoint vecchi (`/documents/*`) per uso generico
2. Considerare deprecation progressivo se Mind diventa primary use case
