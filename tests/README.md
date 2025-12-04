# PramaIA VectorstoreService Tests

Questa cartella contiene i test per il VectorstoreService.

## File di test

### `test_get_document.py`
Test per verificare il recupero di documenti dal VectorstoreService:
- Test di connessione all'API
- Test di recupero documenti per ID
- Test di gestione errori

## Come eseguire i test

```bash
# Dalla directory del VectorstoreService
cd C:\PramaIA\PramaIA-VectorstoreService

# Esegui il test specifico
python tests\test_get_document.py

# Oppure usa pytest se installato
pytest tests\
```

## Prerequisiti

- VectorstoreService in esecuzione sulla porta 8090
- Documenti di test presenti nel sistema
- Librerie Python: requests, json

## Note

I test verificano che:
1. Il servizio sia raggiungibile
2. I documenti siano recuperabili correttamente
3. L'anteprima dei contenuti funzioni
4. Gli errori siano gestiti appropriatamente