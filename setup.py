#!/usr/bin/env python
"""
Script di configurazione per PramaIA-VectorstoreService.

Questo script configura l'ambiente per il VectorstoreService:
1. Verifica i prerequisiti
2. Installa le dipendenze
3. Installa il client PramaIA-LogService
4. Configura il file .env
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Verifica che la versione di Python sia compatibile."""
    required_version = (3, 10)
    current_version = sys.version_info

    if current_version < required_version:
        print(f"ERRORE: Python {required_version[0]}.{required_version[1]} o superiore richiesto. "
              f"Versione attuale: {current_version[0]}.{current_version[1]}")
        return False
    
    print(f"✓ Python {current_version[0]}.{current_version[1]} OK")
    return True

def check_log_service():
    """Verifica che PramaIA-LogService sia disponibile."""
    log_service_path = Path("../PramaIA-LogService")
    log_service_client_path = log_service_path / "clients" / "python"
    
    if not log_service_path.exists():
        print("AVVISO: PramaIA-LogService non trovato nella directory parent. "
              "Il logging centralizzato non sarà disponibile.")
        return False
    
    if not log_service_client_path.exists():
        print("AVVISO: Client PramaIA-LogService non trovato. "
              "Il logging centralizzato non sarà disponibile.")
        return False
    
    print("✓ PramaIA-LogService trovato")
    return True

def install_dependencies():
    """Installa le dipendenze dal file requirements.txt."""
    print("\nInstallazione delle dipendenze...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("✓ Dipendenze installate con successo")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERRORE: Impossibile installare le dipendenze: {e}")
        return False

def install_log_service_client():
    """Installa il client PramaIA-LogService."""
    log_service_client_path = Path("../PramaIA-LogService/clients/python")
    
    if not log_service_client_path.exists():
        print("AVVISO: Client PramaIA-LogService non trovato. Saltando...")
        return False
    
    print("\nInstallazione del client PramaIA-LogService...")
    
    try:
        # Cambia directory per l'installazione
        cwd = os.getcwd()
        os.chdir(log_service_client_path)
        
        # Installa in modalità development
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            check=True
        )
        
        # Ritorna alla directory originale
        os.chdir(cwd)
        
        print("✓ Client PramaIA-LogService installato con successo")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERRORE: Impossibile installare il client PramaIA-LogService: {e}")
        # Ritorna alla directory originale in caso di errore
        os.chdir(cwd)
        return False

def setup_env_file():
    """Configura il file .env se non esiste."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    # Se .env esiste già, non sovrascrivere
    if env_file.exists():
        print("\n✓ File .env già esistente. Mantieni la configurazione esistente.")
        return True
    
    # Se .env.example esiste, copia in .env
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("\n✓ File .env creato da .env.example")
        return True
    
    # Altrimenti, crea un .env con valori di default
    print("\nCreazione di un file .env con valori di default...")
    
    default_env = """# Configurazione VectorstoreService
HOST=0.0.0.0
PORT=8090
LOG_LEVEL=INFO

# Configurazione ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Configurazione Scheduler
SCHEDULE_ENABLED=True
SCHEDULE_TIME=03:00

# Configurazione Database
DATABASE_URL=sqlite:///./vectorstore_service.db

# Configurazione PramaIA-LogService
PRAMAIALOG_HOST=http://localhost:8081
PRAMAIALOG_API_KEY=vectorstore_service_key
"""
    
    with open(env_file, "w") as f:
        f.write(default_env)
    
    print("✓ File .env creato con valori di default")
    return True

def create_directory_structure():
    """Crea la struttura delle directory se non esistono."""
    print("\nCreazione delle directory necessarie...")
    
    directories = [
        "logs",
        "app/db/migrations"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Directory {directory} creata")
    
    return True

def main():
    """Funzione principale."""
    print("=== Configurazione PramaIA-VectorstoreService ===\n")
    
    # Verifica requisiti
    if not check_python_version():
        return 1
    
    has_log_service = check_log_service()
    
    # Installa dipendenze
    if not install_dependencies():
        return 1
    
    # Installa client LogService se disponibile
    if has_log_service:
        if not install_log_service_client():
            print("AVVISO: Client PramaIA-LogService non installato. "
                  "Il logging centralizzato non sarà disponibile.")
    
    # Configura .env
    if not setup_env_file():
        return 1
    
    # Crea struttura directory
    if not create_directory_structure():
        return 1
    
    print("\n=== Configurazione completata con successo ===")
    print("\nPer avviare il servizio eseguire:")
    print("python main.py")
    print("\noppure:")
    print("uvicorn main:app --reload --host 0.0.0.0 --port 8090")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
