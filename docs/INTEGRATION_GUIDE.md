# Guida all'integrazione del VectorstoreService

Questa guida descrive come integrare il VectorstoreService nell'ecosistema PramaIA.

## Introduzione

Il VectorstoreService è un microservizio dedicato alla gestione centralizzata del database vettoriale ChromaDB per PramaIA. Questo documento spiega come integrarlo con l'applicazione principale e il PDK.

## Integrazione con l'applicazione principale

### 1. Utilizzo del client Python

L'applicazione principale può interagire con il VectorstoreService utilizzando il client Python fornito:

```python
from app.clients.vectorstore_client import VectorstoreServiceClient

# Inizializza il client
client = VectorstoreServiceClient(base_url="http://localhost:8090")

# Esempio: elenca le collezioni
collections = client.list_collections()
print(f"Collezioni disponibili: {collections}")

# Esempio: query
results = client.query(
    collection_name="pdf_documents", 
    query_text="Esempio di query", 
    top_k=5
)
```

### 2. Configurazione

Aggiungi le seguenti variabili d'ambiente nel file `.env` dell'applicazione principale:

```
# Configurazione VectorstoreService
VECTORSTORE_SERVICE_PORT=8090
VECTORSTORE_SERVICE_BASE_URL=http://localhost:8090
USE_VECTORSTORE_SERVICE=true
```

### 3. Gestione delle eccezioni

Quando utilizzi il client, gestisci adeguatamente le eccezioni per garantire la robustezza dell'applicazione:

```python
try:
    result = client.query(collection_name="pdf_documents", query_text="query")
except ConnectionError:
    # Gestisci il caso in cui il servizio non sia disponibile
    logging.error("Impossibile connettersi al VectorstoreService")
    # Notifica all'utente
except Exception as e:
    # Gestisci altri errori
    logging.error(f"Errore durante la query: {str(e)}")
```

## Integrazione con PDK

### 1. Nodi processor

Il PDK include due nuovi nodi processor per interagire con il VectorstoreService:

1. **Vectorstore Writer**: Salva documenti ed embeddings nel servizio
   - File: `plugins/pdf-semantic-complete-plugin/src/vectorstore_writer_processor.py`
   - Definizione: `plugins/pdf-semantic-complete-plugin/node-types/vectorstore-writer.json`

2. **Vectorstore Retriever**: Recupera documenti simili basati su una query
   - File: `plugins/pdf-semantic-complete-plugin/src/vectorstore_retriever_processor.py`
   - Definizione: `plugins/pdf-semantic-complete-plugin/node-types/vectorstore-retriever.json`

### 2. Utilizzo nei workflow

Nei workflow PDK, sostituisci i nodi `ChromaDBWriter` e `ChromaDBRetriever` con i nuovi nodi `Vectorstore Writer` e `Vectorstore Retriever`.

#### Configurazione dei nodi

**Vectorstore Writer**:
- `collection_name`: Nome della collezione dove salvare i documenti (default: "pdf_documents")
- `service_url`: URL del servizio VectorstoreService (default: "http://localhost:8090")

**Vectorstore Retriever**:
- `collection_name`: Nome della collezione da cui recuperare i documenti (default: "pdf_documents")
- `service_url`: URL del servizio VectorstoreService (default: "http://localhost:8090")
- `max_results`: Numero massimo di risultati da restituire (default: 5)
- `similarity_threshold`: Soglia di similarità minima (0-1) (default: 0.7)
- `include_metadata`: Includere i metadati nei risultati (default: true)

## Monitoraggio

### 1. Dashboard di monitoraggio

Il servizio include uno script di monitoraggio che raccoglie metriche e visualizza una dashboard:

```bash
python tools/vectorstore_monitor.py --url http://localhost:8090 --interval 60
```

### 2. Endpoint di stato

Per verificare lo stato del servizio:

```bash
curl http://localhost:8090/health
```

Risposta di esempio:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime": "2d 3h 45m",
  "chroma_status": "connected"
}
```

### 3. Metriche

Per ottenere statistiche sul servizio:

```bash
curl http://localhost:8090/stats
```

Risposta di esempio:
```json
{
  "collection_count": 3,
  "total_documents": 1250,
  "disk_usage": "45.2 MB",
  "collections": [
    {
      "name": "pdf_documents",
      "document_count": 850
    },
    {
      "name": "user_queries",
      "document_count": 400
    }
  ]
}
```

## Troubleshooting

### Problemi comuni

1. **Errore di connessione**:
   - Verifica che il servizio VectorstoreService sia in esecuzione
   - Controlla che l'URL sia corretto
   - Verifica che non ci siano firewall che bloccano la connessione

2. **Errore "module 'app.api.routes.stats' has no attribute 'router'"**:
   - Assicurati di utilizzare l'ultima versione del servizio
   - Questo errore è stato risolto nella versione più recente

3. **Prestazioni lente**:
   - Utilizza operazioni batch per aggiungere documenti in grandi quantità
   - Limita il numero di risultati nelle query
   - Aumenta la soglia di similarità per filtrare risultati meno rilevanti

## FAQ

**D: Come posso migrare i dati dal vecchio sistema integrato al nuovo microservizio?**

R: Se desideri partire da zero, non è necessaria alcuna migrazione. Se invece vuoi preservare i dati esistenti, puoi sviluppare uno script di migrazione che:
1. Legge i dati dal vectorstore esistente
2. Li invia al nuovo servizio tramite l'API REST

**D: Come posso verificare se il servizio è disponibile prima di utilizzarlo?**

R: Utilizza l'endpoint `/health` per verificare lo stato del servizio prima di effettuare operazioni:

```python
try:
    response = requests.get("http://localhost:8090/health", timeout=5)
    if response.status_code == 200 and response.json().get("status") == "ok":
        # Il servizio è disponibile
    else:
        # Il servizio non è disponibile o ha problemi
except Exception:
    # Il servizio non è raggiungibile
```

**D: Come posso configurare il servizio per utilizzare una porta diversa?**

R: Modifica la variabile d'ambiente `PORT` nel file `.env` del VectorstoreService e aggiorna di conseguenza la configurazione nell'applicazione principale.

**D: Posso utilizzare il servizio in un ambiente di produzione?**

R: Sì, ma è consigliabile:
1. Utilizzare un server WSGI/ASGI come Gunicorn o Hypercorn
2. Configurare un reverse proxy come Nginx
3. Implementare autenticazione e autorizzazione
4. Utilizzare HTTPS per le comunicazioni
