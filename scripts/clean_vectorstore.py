"""
Script per pulire il vectorstore.
"""

import os
import json
import logging
import sys
import shutil
from pathlib import Path

# Assicurati che il modulo app sia nel percorso Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("vectorstore_clean.log")
    ]
)

logger = logging.getLogger("vectorstore_clean")

def clean_vectorstore():
    """
    Pulisce il vectorstore rimuovendo tutti i dati.
    Utile per test e reset.
    """
    data_dir = os.path.join(os.getcwd(), "data")
    
    if os.path.exists(data_dir):
        logger.info(f"Rimozione della directory dei dati: {data_dir}")
        try:
            shutil.rmtree(data_dir)
            logger.info(f"Directory dei dati rimossa con successo: {data_dir}")
        except Exception as e:
            logger.error(f"Errore durante la rimozione della directory dei dati: {str(e)}")
    else:
        logger.info(f"La directory dei dati non esiste: {data_dir}")
    
    # Ricrea la directory dei dati
    os.makedirs(data_dir, exist_ok=True)
    logger.info(f"Directory dei dati ricreata: {data_dir}")

if __name__ == "__main__":
    logger.info("Pulizia del vectorstore...")
    
    # Chiedi conferma all'utente
    confirm = input("Questa operazione eliminerà tutti i dati del vectorstore. Confermare? (s/N): ")
    
    if confirm.lower() == "s":
        clean_vectorstore()
        logger.info("Pulizia del vectorstore completata.")
    else:
        logger.info("Operazione annullata.")
