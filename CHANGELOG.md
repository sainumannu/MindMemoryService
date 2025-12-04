# Changelog

Tutti i cambiamenti notevoli al VectorstoreService saranno documentati in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e questo progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-09-20

### 🐛 Fixed
- **CRITICO**: Risolto bug nella conversione dei tipi metadati boolean che causava `invalid literal for int() with base 10: 'False'`
- **CRITICO**: Risolto problema di recupero documenti per ID - i documenti ora vengono salvati correttamente nel database SQLite
- Migliorata gestione errori robusta nella conversione tipi metadati con try/catch
- Corretto calcolo similarity score per ricerca semantica (ora valori positivi 0.0-1.0)
- Implementato fallback automatico da ChromaDB a SQLite per documenti non sincronizzati

### ✨ Added
- Nuova documentazione completa dell'architettura in `docs/VECTORSTORE_ARCHITECTURE.md`
- Configurazione .gitignore completa per escludere file temporanei e dati
- Supporto per conversione robusta dei tipi metadati con gestione errori
- Logging migliorato per diagnostica problemi di sincronizzazione database

### 🔧 Changed
- Migliorato metodo `get_document()` con recupero automatico da ChromaDB se non trovato in SQLite
- Ottimizzato calcolo similarity score usando formula corretta per distanze coseno ChromaDB
- Standardizzato formato risposta API ricerca semantica (`matches` invece di `results`)

### 🏗️ Technical
- Refactoring completo gestione tipi metadati in `DocumentDatabase`
- Implementata sincronizzazione automatica tra ChromaDB e SQLite
- Migliorata robustezza operazioni database con gestione eccezioni

### 📚 Documentation
- Aggiunta documentazione dettagliata architettura sistema
- Documentati flussi di inserimento, recupero e ricerca semantica
- Inclusi esempi di codice e diagrammi di sequenza
- Guida troubleshooting per problemi comuni

## [1.0.0] - 2025-09-11

### ✨ Added
- Implementazione iniziale VectorstoreService
- Integrazione ChromaDB per ricerca semantica
- Database SQLite per gestione metadati
- API FastAPI per operazioni CRUD documenti
- Sistema di vettorizzazione automatica documenti testuali
- Gestione collezioni multiple
- Endpoint per statistiche e monitoraggio

### 🏗️ Architecture
- Architettura ibrida ChromaDB + SQLite
- MetadataStoreManager come coordinatore centrale
- ChromaDBManager per operazioni vettoriali
- DocumentDatabase per operazioni relazionali

### 📋 Features
- Upload e processamento documenti
- Ricerca semantica avanzata
- Recupero documenti per ID
- Gestione metadati estensibile
- Supporto multiple collection
- Monitoraggio stato sistema