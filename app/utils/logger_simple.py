"""
Configurazione del logging semplificata per l'applicazione.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_level=None):
    """
    Configura il sistema di logging dell'applicazione.
    
    Args:
        log_level: Livello di logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Se None, viene letto dalla variabile d'ambiente LOG_LEVEL
    
    Returns:
        Logger configurato
    """
    # Crea directory logs se non esiste
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Determina il livello di log
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        print(f"Livello di logging non valido: {log_level}. Uso INFO come default.")
    
    # Configura logger root
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # Rimuovi handler esistenti per evitare duplicati
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Formattazione dei log
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Handler per log su file con rotazione
    file_handler = RotatingFileHandler(
        log_dir / "vectorstore_service.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # Handler per console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(numeric_level)
    logger.addHandler(console_handler)
    
    # FORZA il logger di app.graph a mostrare i log
    graph_logger = logging.getLogger("app.graph")
    graph_logger.setLevel(logging.INFO)
    graph_logger.propagate = True
    
    # Imposta livelli specifici per librerie esterne
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # FORZA flush immediato
    sys.stdout.reconfigure(line_buffering=True)
    
    return logger
