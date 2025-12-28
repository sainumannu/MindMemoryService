# PramaIA-Mind Documents API

API per la gestione di documenti semantici con metadati obbligatori accoppiati.

**Base URL**: `http://127.0.0.1:8090`

---

## 1. Creare un documento

```http
POST /mind/documents/
Content-Type: application/json

{
  "collection": "my_collection",
  "content": "Contenuto semantico del documento",
  "metadata": {
    "tags": ["tag1", "tag2"],
    "source": "mind_system",
    "priority": "high"
  }
}
```

**Risposta** (201 Created):
```json
{
  "id": "doc1234abcd",
  "collection": "my_collection",
  "content": "Contenuto semantico del documento",
  "metadata": {
    "tags": ["tag1", "tag2"],
    "source": "mind_system",
    "priority": "high",
    "created_at": "2025-12-28T10:50:00.000000"
  },
  "message": "Mind document created successfully"
}
```

**Validazione**:
- `content` (string, obbligatorio): non può essere vuoto
- `metadata` (object, obbligatorio): non può essere vuoto
- `collection` (string, opzionale): default "mind_default"
- `id` (string, opzionale): auto-generato se non fornito

**Errori**:
- `400` → content mancante o vuoto
- `400` → metadata mancante o vuoto
- `500` → errore salvataggio

---

## 2. Recuperare un documento

```http
GET /mind/documents/{document_id}
```

**Risposta** (200 OK):
```json
{
  "id": "doc1234abcd",
  "collection": "my_collection",
  "content": "Contenuto semantico del documento",
  "metadata": {
    "tags": ["tag1", "tag2"],
    "source": "mind_system",
    "priority": "high",
    "created_at": "2025-12-28T10:50:00.000000"
  },
  "message": "Mind document retrieved successfully"
}
```

**Errori**:
- `404` → documento non trovato
- `500` → errore lettura

---

## 3. Aggiornare un documento

```http
POST /mind/documents/{document_id}
Content-Type: application/json

{
  "content": "Contenuto aggiornato",
  "metadata": {
    "tags": ["new_tag"],
    "priority": "low"
  }
}
```

**Risposta** (200 OK):
```json
{
  "id": "doc1234abcd",
  "collection": "my_collection",
  "content": "Contenuto aggiornato",
  "metadata": {
    "tags": ["new_tag"],
    "priority": "low",
    "created_at": "2025-12-28T10:50:00.000000",
    "updated_at": "2025-12-28T10:55:00.000000"
  },
  "message": "Mind document updated successfully"
}
```

**Note**:
- `content` e `metadata` sono obbligatori (non puoi aggiornare solo uno)
- `collection` non può essere modificato (elimina e ricrea se necessario)
- `created_at` è preservato, `updated_at` è automatico

**Errori**:
- `400` → content o metadata vuoti/mancanti
- `404` → documento non trovato
- `500` → errore aggiornamento

---

## 4. Eliminare un documento

```http
DELETE /mind/documents/{document_id}
```

**Risposta** (200 OK):
```json
{
  "id": "doc1234abcd",
  "message": "Mind document deleted successfully"
}
```

**Errori**:
- `404` → documento non trovato
- `500` → errore eliminazione

---

## 5. Ricerca semantica (Query)

```http
POST /mind/documents/{collection_name}/query
Content-Type: application/json

{
  "query_text": "ricerca per semantica",
  "limit": 10
}
```

**Risposta** (200 OK):
```json
{
  "collection": "my_collection",
  "query": "ricerca per semantica",
  "matches": [
    {
      "id": "doc1234abcd",
      "content": "Contenuto del documento...",
      "metadata": {
        "tags": ["tag1"],
        "source": "mind_system",
        "created_at": "2025-12-28T10:50:00.000000"
      },
      "similarity_score": 0.95
    }
  ],
  "count": 1,
  "message": "Mind documents query executed successfully"
}
```

**Parametri**:
- `query_text` (string, obbligatorio): il testo da cercare semanticamente
- `limit` (integer, opzionale): numero massimo di risultati (1-100, default 10)

**Note**:
- I risultati sono ordinati per similarity_score decrescente
- Similarity score: 0.0 (nessuna similarità) → 1.0 (identico)

**Errori**:
- `400` → query_text mancante o vuoto
- `400` → limit fuori range (1-100)
- `500` → errore ricerca

---

## 6. Listare documenti

```http
GET /mind/documents/?collection=my_collection&limit=20
```

**Risposta** (200 OK):
```json
{
  "collection": "my_collection",
  "documents": [
    {
      "id": "doc1234abcd",
      "collection": "my_collection",
      "content": "Contenuto del documento...",
      "metadata": {
        "tags": ["tag1"],
        "source": "mind_system"
      }
    }
  ],
  "count": 1,
  "total": 1,
  "message": "Mind documents listed successfully"
}
```

**Parametri**:
- `collection` (string, opzionale): filtro per collection
- `limit` (integer, opzionale): massimo risultati (default 50)

---

## Esempio di utilizzo completo (Python)

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8090"

# 1. Creare un documento
doc_payload = {
    "collection": "knowledge_base",
    "content": "Python è un linguaggio di programmazione versatile",
    "metadata": {
        "tags": ["programming", "python", "tutorial"],
        "source": "internal_docs",
        "category": "education"
    }
}

response = requests.post(
    f"{BASE_URL}/mind/documents/",
    json=doc_payload
)
doc_id = response.json()["id"]
print(f"Documento creato: {doc_id}")

# 2. Fare una ricerca
query_payload = {"query_text": "linguaggio programmazione"}
response = requests.post(
    f"{BASE_URL}/mind/documents/knowledge_base/query",
    json=query_payload
)
results = response.json()["matches"]
print(f"Trovati {len(results)} risultati")
for match in results:
    print(f"- {match['id']}: {match['similarity_score']:.2f}")

# 3. Recuperare il documento
response = requests.get(f"{BASE_URL}/mind/documents/{doc_id}")
doc = response.json()
print(f"Documento: {doc['metadata']}")

# 4. Aggiornare il documento
update_payload = {
    "content": "Python è un linguaggio versatile e potente",
    "metadata": {
        "tags": ["programming", "python", "advanced"],
        "source": "internal_docs",
        "category": "education",
        "updated_by": "admin"
    }
}
response = requests.post(
    f"{BASE_URL}/mind/documents/{doc_id}",
    json=update_payload
)
print(f"Documento aggiornato: {response.json()['message']}")

# 5. Eliminare il documento
response = requests.delete(f"{BASE_URL}/mind/documents/{doc_id}")
print(f"Documento eliminato: {response.json()['message']}")
```

---

## Guida di integrazione

1. **Usa SEMPRE `/mind/documents/*` per Mind**
   - Non usare `/documents/*` (endpoint generico)
   - Endpoint Mind enforza validazione rigorosa

2. **Struttura metadata**
   - Usa `tags` come array per categorie (["tag1", "tag2", ...])
   - Aggiungi `source` per tracciare provenienza
   - Usa `category` per classificazione semantica
   - Aggiungi eventuali campi custom necessari

3. **Gestione della ricerca**
   - Usa `/mind/documents/{collection}/query` per ricerca semantica
   - Filtra per `collection` per organizzare domaines
   - Usa `limit` per gestire performance

4. **Errori common**
   - 400 Bad Request: validazione input fallita
   - 404 Not Found: documento non esiste
   - 500 Internal Server Error: problema server

---

## OpenAPI / Swagger

Per la documentazione interattiva, accedi a:
- **Swagger UI**: `http://127.0.0.1:8090/docs`
- **ReDoc**: `http://127.0.0.1:8090/redoc`
