# Domande per Collega VectorStore

## Contesto
Stiamo implementando la memoria episodica e semantica per PramaIA-Mind. Abbiamo riscontrato problemi con l'API del VectorStore:
- Errori 405 Method Not Allowed
- Documenti che vanno nella collection "default" invece che nelle collection specificate
- Documentazione non coerente con l'implementazione reale

---

## 1. Endpoint Corretto per Creare Documenti

**Domanda:** Qual è l'endpoint CORRETTO per creare/aggiungere documenti al VectorStore?

Abbiamo trovato diverse versioni nel codice:
- `/documents/` (documentato in VECTORSTORE_API.md)
- `/vectorstore/documents` (usato in workflow_processors.py - SEMBRA FUNZIONARE)
- `/documents/{collection}` (usato in vectorstore_client.py - RITORNA 405)
- `/api/database-management/vectorstore/documents` (API Gateway)

**Quale dobbiamo usare?**

---

## 2. Come Specificare la Collection

**Domanda:** Come si specifica in quale collection salvare un documento?

Opzioni che abbiamo provato:
- Nel campo `metadata.collection` ← **Documenti vanno in "default" comunque**
- Come parametro query string `?collection=nome`
- Nel body principale del documento
- Nel path URL `/documents/{collection}`

**Esempio di quello che stiamo inviando attualmente:**
```json
POST /vectorstore/documents
{
  "content": "Testo dell'episodio o conoscenza",
  "metadata": {
    "collection": "admin_episodic",  // ← QUESTO VIENE IGNORATO?
    "user_id": "admin",
    "importance": 0.85,
    "timestamp": "2025-12-17T10:30:00Z"
  },
  "id": "ep_1234567890"
}
```

**Risultato:** Il documento viene creato ma finisce in "default" invece che in "admin_episodic".

---

## 3. Perché Documenti Vanno in "default"?

**Domanda:** Perché tutti i documenti finiscono nella collection "default" invece che nelle collection specificate?

**Log VectorStore:**
```
Aggiunta documento con ID: ep_1765920971.811276
Collezione: default  // ← DOVREBBE ESSERE "admin_episodic"!
```

**Cosa stiamo sbagliando?**

---

## 4. Formato Esatto del Documento

**Domanda:** Qual è la struttura ESATTA del documento che il VectorStore si aspetta?

**Versione A (quella che usiamo ora):**
```json
{
  "content": "...",
  "metadata": {...},
  "id": "..."
}
```

**Versione B (da vectorstore_client.py):**
```json
{
  "document": "...",    // ← "document" invece di "content"?
  "metadata": {...}
}
```

**Quale è corretta?**

---

## 5. Differenza tra Endpoint

**Domanda:** Qual è la differenza tra questi endpoint?

- `POST /documents/`
- `POST /vectorstore/documents`
- `POST /api/database-management/vectorstore/documents`

Sono la stessa cosa? Uno è deprecato? Hanno comportamenti diversi per quanto riguarda le collections?

---

## 6. Collection Naming e Isolation

**Domanda:** Come funziona l'isolamento per utente con le collections?

**Nostro obiettivo:**
- Ogni utente ha la sua collection episodica: `{user_id}_episodic` (es. "admin_episodic", "john_episodic")
- Ogni utente ha la sua collection semantica: `{user_id}_semantic` (es. "admin_semantic")

**È supportato questo pattern?** Le collections vengono create automaticamente o dobbiamo crearle prima?

---

## 7. Verifica e Debug

**Domanda:** Come possiamo verificare in quale collection è finito un documento?

**Endpoint per:**
- Listare tutte le collections esistenti?
- Vedere documenti in una specifica collection?
- Contare documenti per collection?

---

## Riepilogo - Cosa Abbiamo Bisogno

1. **Endpoint corretto** per POST documenti
2. **Metodo corretto** per specificare la collection
3. **Formato JSON corretto** del documento
4. **Spiegazione** perché va tutto in "default"
5. **Documentazione aggiornata** o esempi funzionanti

---

## Info Aggiuntive

**Ambiente:**
- VectorStore Service: `http://localhost:8090`
- Backend PramaIA-Mind: `http://localhost:8002`
- ChromaDB: Modalità persistente locale

**Codice Sorgente:**
- Episodic Memory: `Mind/memory/episodic/episodic_memory_service.py`
- Semantic Memory: `Mind/memory/semantic/semantic_memory_service.py`
- Client VectorStore: `PramaIAServer/backend/app/clients/vectorstore_client.py`

---

## Grazie! 🙏

Appena abbiamo queste risposte possiamo:
1. Correggere il codice della memoria episodica/semantica
2. Aggiornare il VectorstoreServiceClient
3. Correggere la documentazione
4. Implementare correttamente l'isolamento per utente
