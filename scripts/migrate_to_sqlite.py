#!/usr/bin/env python3
"""
Script di migrazione dal vecchio formato JSON al nuovo database SQLite.
Esegue la migrazione dei dati dal file documents.json al database SQLite,
mantenendo un backup del file originale.
"""

import os
import sys
import logging
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

logger = logging.getLogger("db_migration")

def setup_argument_parser():
    """Configura il parser degli argomenti da linea di comando."""
    parser = argparse.ArgumentParser(
        description="Migrazione da JSON a SQLite per i documenti del VectorstoreService"
    )
    
    parser.add_argument(
        "--data-dir", 
        type=str, 
        default=os.path.join(os.getcwd(), "data"),
        help="Directory contenente i dati (default: './data')"
    )
    
    parser.add_argument(
        "--backup", 
        action="store_true",
        help="Crea solo un backup del file JSON senza eseguire la migrazione"
    )
    
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Forza la migrazione anche se il database contiene già dati"
    )
    
    parser.add_argument(
        "--export", 
        action="store_true",
        help="Esporta i dati dal database a JSON dopo la migrazione"
    )
    
    parser.add_argument(
        "--vacuum", 
        action="store_true",
        help="Esegue VACUUM sul database dopo la migrazione per ottimizzare lo spazio"
    )
    
    return parser

def create_backup(json_file_path):
    """Crea un backup del file JSON originale."""
    try:
        import shutil
        
        # Nome del file di backup con timestamp
        backup_file = f"{json_file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Copia il file
        shutil.copy2(json_file_path, backup_file)
        
        logger.info(f"Backup creato: {backup_file}")
        return True, backup_file
    except Exception as e:
        logger.error(f"Errore durante la creazione del backup: {str(e)}")
        return False, None

def perform_migration(data_dir, force=False, export=False, vacuum=False):
    """Esegue la migrazione da JSON a SQLite."""
    try:
        # Importa il gestore del database
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from app.utils.document_database import DocumentDatabase
        
        # Verifica se il file JSON esiste
        json_file = os.path.join(data_dir, "documents.json")
        if not os.path.exists(json_file):
            logger.error(f"File JSON non trovato: {json_file}")
            return False
        
        # Crea un backup prima di procedere
        backup_success, backup_file = create_backup(json_file)
        if not backup_success:
            logger.error("Migrazione annullata: impossibile creare backup")
            return False
        
        # Inizializza il database con l'opzione di migrazione
        logger.info(f"Inizializzazione del database con migrate_from_json={force}")
        db = DocumentDatabase(data_dir=data_dir, migrate_from_json=force)
        
        # Verifica se ci sono già documenti nel database
        if not force:
            doc_count = db.get_document_count()
            if doc_count > 0:
                logger.warning(f"Il database contiene già {doc_count} documenti.")
                logger.warning("Usa --force per forzare la migrazione e sovrascrivere il database.")
                return False
        
        # Esegui migrazione
        logger.info("Avvio migrazione...")
        db = DocumentDatabase(data_dir=data_dir, migrate_from_json=True)
        
        # Verifica il risultato
        doc_count = db.get_document_count()
        logger.info(f"Migrazione completata: {doc_count} documenti nel database")
        
        # Esporta in JSON se richiesto
        if export:
            export_file = os.path.join(data_dir, f"documents.export.{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
            logger.info(f"Esportazione dati in {export_file}...")
            export_success = db.export_to_json(output_file=export_file)
            if export_success:
                logger.info("Esportazione completata con successo")
            else:
                logger.error("Errore durante l'esportazione")
        
        # Esegui VACUUM se richiesto
        if vacuum:
            logger.info("Esecuzione VACUUM sul database...")
            vacuum_success = db.vacuum_database()
            if vacuum_success:
                logger.info("VACUUM completato con successo")
            else:
                logger.error("Errore durante l'esecuzione di VACUUM")
        
        logger.info("MIGRAZIONE COMPLETATA CON SUCCESSO")
        return True
        
    except Exception as e:
        logger.error(f"Errore durante la migrazione: {str(e)}", exc_info=True)
        return False

def main():
    """Funzione principale."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    logger.info(f"Directory dati: {args.data_dir}")
    
    # Verifica se la directory dati esiste
    if not os.path.exists(args.data_dir):
        logger.error(f"La directory {args.data_dir} non esiste!")
        return 1
    
    # Verifica i file nella directory
    json_file = os.path.join(args.data_dir, "documents.json")
    db_file = os.path.join(args.data_dir, "documents.db")
    
    logger.info(f"File JSON: {json_file} (esiste: {os.path.exists(json_file)})")
    logger.info(f"File DB: {db_file} (esiste: {os.path.exists(db_file)})")
    
    # Se è richiesto solo il backup
    if args.backup:
        if not os.path.exists(json_file):
            logger.error(f"Impossibile creare backup: il file {json_file} non esiste")
            return 1
        
        backup_success, backup_file = create_backup(json_file)
        if backup_success:
            logger.info(f"Backup completato: {backup_file}")
            return 0
        else:
            logger.error("Backup fallito")
            return 1
    
    # Altrimenti esegui la migrazione
    success = perform_migration(
        data_dir=args.data_dir,
        force=args.force,
        export=args.export,
        vacuum=args.vacuum
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
