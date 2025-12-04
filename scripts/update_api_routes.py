#!/usr/bin/env python3
"""
Script per l'aggiornamento delle route API per utilizzare il nuovo gestore basato su database.
Questo script aggiorna i file necessari per utilizzare il nuovo MetadataStoreManager 
basato su SQLite invece della versione basata su JSON.
"""

import os
import sys
import re
import logging
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("api_updater")

def setup_argument_parser():
    """Configura il parser degli argomenti da linea di comando."""
    parser = argparse.ArgumentParser(
        description="Aggiornamento delle route API per utilizzare il gestore basato su database"
    )
    
    parser.add_argument(
        "--app-dir", 
        type=str, 
        default=os.path.join(os.getcwd(), "app"),
        help="Directory dell'applicazione (default: './app')"
    )
    
    parser.add_argument(
        "--backup", 
        action="store_true",
        help="Crea solo un backup dei file senza applicare i cambiamenti"
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Mostra i cambiamenti che verrebbero applicati senza modificare i file"
    )
    
    return parser

def create_backup(file_path):
    """Crea un backup di un file."""
    try:
        # Nome del file di backup con timestamp
        backup_file = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Copia il file
        shutil.copy2(file_path, backup_file)
        
        logger.info(f"Backup creato: {backup_file}")
        return True, backup_file
    except Exception as e:
        logger.error(f"Errore durante la creazione del backup: {str(e)}")
        return False, None

def update_api_routes(app_dir, dry_run=False):
    """Aggiorna i file delle route API per utilizzare il nuovo gestore."""
    try:
        # File da aggiornare
        api_files = [
            os.path.join(app_dir, "api", "routes", "vectorstore.py"),
            os.path.join(app_dir, "api", "routes", "documents.py"),
            os.path.join(os.path.dirname(app_dir), "main.py")
        ]
        
        # Verifica l'esistenza dei file
        for file_path in api_files:
            if not os.path.exists(file_path):
                logger.warning(f"File non trovato: {file_path}")
        
        # Pattern di sostituzione
        substitutions = [
            # Aggiorna import
            (
                r"from app\.utils\.vectorstore_manager import VectorstoreManager", 
                "from app.utils.metadata_store_manager import MetadataStoreManager"
            ),
            # Aggiorna eventuali altri import specifici per JSON
            (
                r"import json\s*?(?=#|$|import|\n\n)", 
                "import json\nimport sqlite3"
            ),
            # Eventuali riferimenti specifici a documents.json
            (
                r"documents\.json", 
                "documents.db"
            )
        ]
        
        updated_files = []
        
        # Processa ogni file
        for file_path in api_files:
            if not os.path.exists(file_path):
                continue
                
            logger.info(f"Elaborazione file: {file_path}")
            
            # Crea backup
            backup_success, backup_file = create_backup(file_path)
            if not backup_success:
                logger.error(f"Impossibile creare backup per {file_path}, salta aggiornamento")
                continue
            
            # Leggi il contenuto
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Applica le sostituzioni
            original_content = content
            for pattern, replacement in substitutions:
                content = re.sub(pattern, replacement, content)
            
            # Verifica se ci sono stati cambiamenti
            if content == original_content:
                logger.info(f"Nessun cambiamento necessario per {file_path}")
                continue
            
            # In modalità dry-run, mostra solo i cambiamenti
            if dry_run:
                logger.info(f"Cambiamenti per {file_path}:")
                for line_num, (old_line, new_line) in enumerate(zip(
                    original_content.splitlines(), 
                    content.splitlines()
                ), 1):
                    if old_line != new_line:
                        logger.info(f"Linea {line_num}:")
                        logger.info(f"  - {old_line}")
                        logger.info(f"  + {new_line}")
                continue
            
            # Scrivi il contenuto aggiornato
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"File aggiornato: {file_path}")
            updated_files.append(file_path)
        
        return True, updated_files
        
    except Exception as e:
        logger.error(f"Errore durante l'aggiornamento delle route API: {str(e)}", exc_info=True)
        return False, []

def main():
    """Funzione principale."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    logger.info(f"Directory applicazione: {args.app_dir}")
    
    # Verifica se la directory app esiste
    if not os.path.exists(args.app_dir):
        logger.error(f"La directory {args.app_dir} non esiste!")
        return 1
    
    # Se è richiesto solo il backup
    if args.backup:
        api_files = [
            os.path.join(args.app_dir, "routers", "vectorstore.py"),
            os.path.join(args.app_dir, "routers", "documents.py"),
            os.path.join(args.app_dir, "main.py")
        ]
        
        backup_success = True
        for file_path in api_files:
            if os.path.exists(file_path):
                success, _ = create_backup(file_path)
                if not success:
                    backup_success = False
        
        return 0 if backup_success else 1
    
    # Altrimenti aggiorna le route API
    success, updated_files = update_api_routes(
        app_dir=args.app_dir,
        dry_run=args.dry_run
    )
    
    if args.dry_run:
        logger.info("Operazione completata in modalità dry-run. Nessun file è stato modificato.")
        return 0
    
    if success:
        logger.info(f"Aggiornamento completato con successo. File aggiornati: {len(updated_files)}")
        for file in updated_files:
            logger.info(f" - {file}")
    else:
        logger.error("Aggiornamento fallito!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
