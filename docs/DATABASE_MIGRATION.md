# Migrazione Database per VectorstoreService

## Panoramica

Questa documentazione descrive il processo di migrazione dallo storage basato su JSON al database SQLite per il servizio VectorstoreService.

## Motivazione

La versione originale del VectorstoreService utilizzava un file JSON (`documents.json`) per memorizzare i metadati dei documenti indicizzati. Questo approccio presenta vari problemi, tra cui:

1. **Scalabilità limitata**: Con l'aumentare del numero di documenti, il file JSON diventa sempre più grande, causando rallentamenti nelle operazioni di lettura/scrittura.
2. **Problemi di concorrenza**: Gli accessi concorrenti al file JSON possono causare corruzione dei dati o perdita di informazioni.
3. **Inefficienza delle query**: L'intero file deve essere caricato in memoria per eseguire anche semplici operazioni di ricerca.
4. **Rischio di corruzione**: Il file JSON potrebbe corrompersi se il processo viene interrotto durante una scrittura.

L'implementazione basata su SQLite risolve questi problemi offrendo:

- Migliore gestione della concorrenza
- Query ottimizzate e indicizzate
- Minore utilizzo di memoria
- Maggiore robustezza contro la corruzione dei dati
- Transazioni atomiche

## Componenti Implementati

### 1. DocumentDatabase

La classe `DocumentDatabase` è responsabile della gestione del database SQLite e fornisce metodi per:

- Creazione e inizializzazione del database
- Inserimento, aggiornamento e eliminazione di documenti
- Recupero di documenti singoli o multipli
- Migrazione dei dati dal formato JSON
- Esportazione dei dati in formato JSON

### 2. VectorstoreManager (versione DB)

La versione aggiornata di `VectorstoreManager` utilizza `DocumentDatabase` invece del file JSON, mantenendo la stessa interfaccia esterna per garantire compatibilità con il codice esistente.

## Strumenti di Migrazione

Sono stati implementati i seguenti script per facilitare la migrazione:

### 1. migrate_to_sqlite.py

Script per migrare i dati dal file JSON esistente al database SQLite.

```bash
python scripts/migrate_to_sqlite.py --data-dir app/data --force --vacuum
```

Opzioni:
- `--data-dir`: Directory contenente i dati (default: './data')
- `--backup`: Crea solo un backup del file JSON senza eseguire la migrazione
- `--force`: Forza la migrazione anche se il database contiene già dati
- `--export`: Esporta i dati dal database a JSON dopo la migrazione
- `--vacuum`: Esegue VACUUM sul database dopo la migrazione per ottimizzare lo spazio

### 2. update_api_routes.py

Script per aggiornare le route API per utilizzare il nuovo gestore basato su database.

```bash
python scripts/update_api_routes.py --app-dir app --dry-run
```

Opzioni:
- `--app-dir`: Directory dell'applicazione (default: './app')
- `--backup`: Crea solo un backup dei file senza applicare i cambiamenti
- `--dry-run`: Mostra i cambiamenti che verrebbero applicati senza modificare i file

### 3. test_db_implementation.py

Script per testare l'implementazione del database SQLite.

```bash
python scripts/test_db_implementation.py
```

## Procedura di Migrazione

### Fase 1: Preparazione

1. Verificare che tutti i servizi che utilizzano VectorstoreService siano fermi
2. Creare un backup completo della directory dei dati

```bash
cd PramaIA-VectorstoreService
cp -r app/data app/data.backup.$(date +%Y%m%d)
```

### Fase 2: Test Preliminari

Eseguire i test sull'implementazione del database:

```bash
python scripts/test_db_implementation.py
```

### Fase 3: Migrazione dei Dati

Eseguire lo script di migrazione:

```bash
python scripts/migrate_to_sqlite.py --data-dir app/data --force --vacuum
```

### Fase 4: Aggiornamento delle Route API

Prima di applicare i cambiamenti, eseguire in modalità dry-run:

```bash
python scripts/update_api_routes.py --app-dir app --dry-run
```

Se tutto sembra corretto, applicare i cambiamenti:

```bash
python scripts/update_api_routes.py --app-dir app
```

### Fase 5: Verifica

Avviare il servizio in ambiente di test e verificare che tutte le funzionalità siano operative:

```bash
cd PramaIA-VectorstoreService
uvicorn app.main:app --reload
```

Eseguire richieste di test alle API per verificare che i documenti siano accessibili e che tutte le operazioni CRUD funzionino correttamente.

## Rollback

In caso di problemi, è possibile eseguire un rollback:

1. Ripristinare il file JSON originale:

```bash
cd PramaIA-VectorstoreService
cp app/data.backup.YYYYMMDD/documents.json app/data/
```

2. Ripristinare le versioni originali dei file delle route API (dai backup creati durante l'aggiornamento).

## Monitoraggio e Manutenzione

### Backup Periodici

Configurare backup periodici del file del database:

```bash
# Esempio di script di backup
sqlite3 app/data/documents.db ".backup app/data/documents.backup.db"
```

### Ottimizzazione Periodica

Eseguire VACUUM periodicamente per ottimizzare le prestazioni del database:

```bash
sqlite3 app/data/documents.db "VACUUM;"
```

## Conclusioni

Questa migrazione migliora significativamente la scalabilità, l'affidabilità e le prestazioni del VectorstoreService, permettendo di gestire un numero molto maggiore di documenti senza degradazione delle prestazioni.
