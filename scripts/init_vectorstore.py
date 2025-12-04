"""
Script di inizializzazione del Vectorstore.
Da eseguire per rilevare lo stato iniziale o aggiornare le informazioni.
"""

import os
import json
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Assicurati che il modulo app sia nel percorso Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.document_manager import DocumentManager

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("vectorstore_init.log")
    ]
)

logger = logging.getLogger("vectorstore_init")

def scan_pdf_directory(directory_path=None, recursive=True):
    """
    Scansiona una directory per i file PDF e li aggiunge al vectorstore.
    
    Args:
        directory_path: Percorso della directory da scansionare. Se None, usa la directory corrente.
        recursive: Se True, scansiona ricorsivamente le sottodirectory.
    """
    if directory_path is None:
        directory_path = os.getcwd()
    
    manager = DocumentManager()
    
    # Crea un elenco di file PDF nella directory
    pdf_files = []
    
    if recursive:
        # Scansiona ricorsivamente
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
    else:
        # Scansiona solo la directory specificata
        for file in os.listdir(directory_path):
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(directory_path, file))
    
    logger.info(f"Trovati {len(pdf_files)} file PDF nella directory {directory_path}")
    
    # Aggiungi i file PDF al vectorstore
    for pdf_file in pdf_files:
        file_name = os.path.basename(pdf_file)
        file_size = os.path.getsize(pdf_file) // 1024  # Dimensione in KB
        
        # Calcola il numero di pagine (qui potremmo usare PyPDF2 o un'altra libreria)
        # Per ora usiamo un valore segnaposto
        pages = 1
        
        # Crea un documento per il file PDF
        document = {
            "id": f"doc{hash(pdf_file) % 100000:05d}",
            "filename": file_name,
            "collection": "pdf_documents",
            "metadata": {
                "size_kb": file_size,
                "pages": pages,
                "created_at": datetime.now().isoformat(),
                "path": pdf_file,
                "type": "application/pdf"
            }
        }
        
        # Aggiungi il documento
        manager.add_document(document)
        logger.info(f"Aggiunto documento: {document['id']} - {file_name}")
    
    logger.info(f"Aggiunti {len(pdf_files)} documenti al vectorstore")
    return len(pdf_files)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Inizializza il vectorstore con documenti reali')
    parser.add_argument('--dir', '-d', type=str, default=None, 
                        help='Directory da scansionare per i file PDF')
    parser.add_argument('--no-recursive', action='store_true',
                        help='Disabilita la scansione ricorsiva delle sottodirectory')
    
    args = parser.parse_args()
    
    logger.info("Inizializzazione del vectorstore...")
    
    directory = args.dir or os.getcwd()
    recursive = not args.no_recursive
    
    # Scansiona la directory per file PDF
    count = scan_pdf_directory(directory, recursive)
    
    if count == 0:
        logger.warning(f"Nessun documento PDF trovato nella directory {directory}")
        logger.info("Suggerimento: specifica una directory diversa con --dir /percorso/ai/documenti")
    
    logger.info("Inizializzazione del vectorstore completata.")
