# PramaIA-VectorstoreService

Servizio centralizzato per la gestione del vectorstore e la riconciliazione con il filesystem.

## Descrizione

PramaIA-VectorstoreService fornisce un'API REST completa per operazioni CRUD sul vectorstore, gestione delle collezioni, generazione di embeddings e riconciliazione periodica tra filesystem e vectorstore.

Il servizio è progettato per:
1. Centralizzare tutte le operazioni sul vectorstore
2. Fornire un'interfaccia uniforme per tutti i componenti che necessitano di interagire con il vectorstore
3. Assicurare la coerenza dei dati tra filesystem e vectorstore tramite riconciliazione programmata
4. Supportare la scalabilità attraverso operazioni batch e in background

## Funzionalità principali

- **Gestione Collezioni**: Creazione, lettura, aggiornamento ed eliminazione di collezioni nel vectorstore
- **Gestione Documenti**: Aggiunta, recupero, ricerca ed eliminazione di documenti nelle collezioni
- **Generazione Embeddings**: Creazione di embeddings per documenti testuali
- **Riconciliazione**: Sincronizzazione bidirezionale tra filesystem e vectorstore
- **Pianificazione**: Supporto per l'esecuzione programmata di attività come la riconciliazione
- **Monitoraggio**: Endpoint per il monitoraggio dello stato del servizio e delle sue dipendenze

## Architettura

Il servizio è basato su FastAPI e utilizza ChromaDB come backend per il vectorstore. È organizzato nei seguenti moduli:

- **API**: Endpoint REST per interagire con il servizio
- **Core**: Logica di business per le operazioni sul vectorstore e la riconciliazione
- **DB**: Gestione del database per la persistenza delle configurazioni e dei job
- **Scheduler**: Pianificazione di attività ricorrenti
- **Utils**: Utilità comuni come configurazione, logging, ecc.

## Installazione

### Prerequisiti

- Python 3.10 o superiore
- PramaIA-LogService installato e in esecuzione (per il logging centralizzato)

### Passaggi

1. Clona il repository:
```bash
git clone https://github.com/your-org/PramaIA-VectorstoreService.git
cd PramaIA-VectorstoreService
```

2. Crea e attiva un ambiente virtuale (opzionale ma consigliato):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Installa le dipendenze:
```bash
pip install -r requirements.txt

# Installa il client PramaIA-LogService
cd ../PramaIA-LogService/clients/python
pip install -e .
cd ../../../PramaIA-VectorstoreService
```

4. Configura le variabili d'ambiente copiando il file `.env.example` in `.env` e modificando i valori secondo necessità.

## Utilizzo

### Avvio del servizio

```bash
# Avvio in modalità sviluppo
python main.py

# Alternativa con uvicorn diretto
uvicorn main:app --reload --host 0.0.0.0 --port 8090
```

### Utilizzo dell'API

La documentazione OpenAPI è disponibile all'indirizzo `/docs` o `/redoc` dopo l'avvio del servizio.

Esempi di utilizzo:

```python
import requests

# Crea una nuova collezione
response = requests.post(
    "http://localhost:8090/collections",
    json={"name": "mia_collezione", "metadata": {"description": "Descrizione"}}
)

# Aggiungi documenti alla collezione
response = requests.post(
    "http://localhost:8090/documents/mia_collezione",
    json={
        "documents": ["Questo è un documento di esempio", "Questo è un altro documento"],
        "metadatas": [{"source": "file1.txt"}, {"source": "file2.txt"}]
    }
)

# Cerca documenti simili
response = requests.post(
    "http://localhost:8090/documents/mia_collezione/query",
    json={
        "query_texts": ["documento esempio"],
        "n_results": 5
    }
)
```

## Integrazione con LogService

Il servizio utilizza PramaIA-LogService per il logging centralizzato. Tutti i log vengono inviati sia al file locale che al servizio di logging centralizzato.

La configurazione del logging è gestita dal modulo `app/utils/logger.py`, che implementa un adapter per inviare i log a entrambi i sistemi.

Per utilizzare il logger:

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Esempi di utilizzo
logger.info("Messaggio informativo")
logger.warning("Attenzione!", details={"dettaglio": "valore"})
logger.error("Errore durante l'operazione", 
             details={"operation": "add_document"}, 
             context={"collection": "mia_collezione"})
```

## Configurazione

Il servizio può essere configurato tramite variabili d'ambiente o file `.env`:

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `HOST` | Host su cui avviare il servizio | `0.0.0.0` |
| `PORT` | Porta su cui avviare il servizio | `8090` |
| `LOG_LEVEL` | Livello di logging | `INFO` |
| `CHROMA_HOST` | Host del server ChromaDB | `localhost` |
| `CHROMA_PORT` | Porta del server ChromaDB | `8000` |
| `SCHEDULE_ENABLED` | Abilita/disabilita lo scheduler | `True` |
| `SCHEDULE_TIME` | Orario per la riconciliazione pianificata | `03:00` |
| `DATABASE_URL` | URL di connessione al database | `sqlite:///./vectorstore_service.db` |
| `PRAMAIALOG_HOST` | Host del servizio PramaIA-LogService | `http://localhost:8081` |
| `PRAMAIALOG_API_KEY` | API key per PramaIA-LogService | `vectorstore_service_key` |

## Licenza

Proprietario - PramaIA
