#!/usr/bin/env python
"""
Script master per eseguire tutti i test di debug.
Esegue i test su ChromaDB, SQLite e operazioni ibride.
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("debug_test_runner")

def run_test_script(script_name):
    """Esegue uno script di test e restituisce il risultato."""
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        logger.error(f"❌ Script non trovato: {script_path}")
        return False
        
    logger.info(f"\n🔄 Esecuzione: {script_name}")
    logger.info("=" * 60)
    
    try:
        # Esegui lo script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(script_path.parent.parent.parent)  # Directory root del progetto
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {script_name} completato con successo")
            
            # Mostra output se interessante
            if result.stdout:
                # Mostra solo le righe con risultati importanti
                important_lines = []
                for line in result.stdout.split('\n'):
                    if any(marker in line for marker in ['✅', '❌', '⚠️', '📊', 'INFO', 'ERROR', 'WARNING']):
                        important_lines.append(line)
                
                if important_lines:
                    logger.info("📋 Output rilevante:")
                    for line in important_lines[-10:]:  # Ultime 10 righe rilevanti
                        print(f"   {line}")
                        
            return True
        else:
            logger.error(f"❌ {script_name} fallito (exit code: {result.returncode})")
            
            if result.stderr:
                logger.error(f"Errori: {result.stderr}")
                
            return False
            
    except Exception as e:
        logger.error(f"❌ Errore esecuzione {script_name}: {e}")
        return False

def check_environment():
    """Verifica che l'ambiente sia pronto per i test."""
    logger.info("🔍 Verifica ambiente...")
    
    # Verifica directory del progetto
    project_root = Path(__file__).parent.parent.parent
    if not (project_root / "main.py").exists():
        logger.error("❌ Directory del progetto non trovata")
        return False
        
    # Verifica che i moduli chiave siano importabili
    sys.path.append(str(project_root))
    
    missing_modules = []
    
    try:
        import chromadb
        logger.info("✅ ChromaDB disponibile")
    except ImportError:
        missing_modules.append("chromadb")
        
    try:
        from app.core.vectordb_manager import VectorDBManager
        logger.info("✅ VectorDBManager disponibile")
    except ImportError:
        missing_modules.append("VectorDBManager")
        
    try:
        from app.utils.document_database import DocumentDatabase
        logger.info("✅ DocumentDatabase disponibile")
    except ImportError:
        missing_modules.append("DocumentDatabase")
        
    if missing_modules:
        logger.warning(f"⚠️  Moduli non disponibili: {missing_modules}")
        logger.warning("Alcuni test potrebbero fallire")
        
    # Verifica directory data
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    logger.info(f"✅ Directory data: {data_dir}")
    
    return True

def generate_report(results):
    """Genera un report dei risultati dei test."""
    logger.info("\n" + "=" * 60)
    logger.info("📊 REPORT RISULTATI TEST DEBUG")
    logger.info("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    failed_tests = total_tests - passed_tests
    
    logger.info(f"📈 Test totali: {total_tests}")
    logger.info(f"✅ Test passati: {passed_tests}")
    logger.info(f"❌ Test falliti: {failed_tests}")
    
    if failed_tests == 0:
        logger.info("\n🎉 TUTTI I TEST COMPLETATI CON SUCCESSO!")
    else:
        logger.warning(f"\n⚠️  {failed_tests} test hanno avuto problemi")
        
    logger.info("\n📋 Dettaglio per test:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
        
    # Timestamp del report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"\n🕐 Report generato: {timestamp}")
    
    return failed_tests == 0

def main():
    """Funzione principale per eseguire tutti i test."""
    logger.info("🚀 AVVIO TEST DEBUG COMPLETI")
    logger.info(f"📅 Data/Ora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verifica ambiente
    if not check_environment():
        logger.error("❌ Ambiente non pronto per i test")
        return False
        
    # Lista dei test da eseguire
    test_scripts = [
        "test_sqlite_crud.py",
        "test_chromadb_crud.py",
        "test_hybrid_operations.py"
    ]
    
    # Esegui i test
    results = {}
    
    for script in test_scripts:
        success = run_test_script(script)
        results[script] = success
        
        if not success:
            logger.warning(f"⚠️  Test {script} fallito, ma continuiamo...")
            
    # Genera report finale
    all_passed = generate_report(results)
    
    if all_passed:
        logger.info("\n🎯 MISSIONE COMPIUTA: Tutti i test debug completati!")
        return True
    else:
        logger.warning("\n🔧 ATTENZIONE: Alcuni test necessitano di revisione")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⏹️  Test interrotti dall'utente")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Errore critico: {e}")
        sys.exit(1)