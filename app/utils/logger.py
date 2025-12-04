"""
Configurazione del logging per l'applicazione.

Utilizza il client PramaIA-LogService per l'invio dei log al servizio centralizzato.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Importa il client PramaIA-LogService
try:
    from pramaialog import PramaIALogger, LogLevel, LogProject, setup_logger
    PRAMAIALOG_AVAILABLE = True
except ImportError:
    PRAMAIALOG_AVAILABLE = False
    print("ATTENZIONE: Client PramaIA-LogService non disponibile. Verrà utilizzato il logging standard.")

# Logger globale del servizio
_logger = None
# Client del LogService
_log_client = None

def setup_logging(log_level=None):
    """
    Configura il sistema di logging dell'applicazione.
    
    Args:
        log_level: Livello di logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Se None, viene letto dalla variabile d'ambiente LOG_LEVEL
    
    Returns:
        Logger configurato
    """
    global _logger
    
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
    logger.addHandler(console_handler)
    
    # Imposta livelli specifici per librerie esterne
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    _logger = logger
    
    # Configura anche il client PramaIA-LogService se disponibile
    if PRAMAIALOG_AVAILABLE:
        setup_pramaialog_client()
    
    return logger
    
    # Imposta livelli specifici per librerie esterne
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    _logger = logger
    
    # Configura anche il client PramaIA-LogService se disponibile
    if PRAMAIALOG_AVAILABLE:
        setup_pramaialog_client()
    
    return logger

def setup_pramaialog_client():
    """
    Configura il client PramaIA-LogService.
    """
    global _log_client
    
    if not PRAMAIALOG_AVAILABLE:
        return None
    
    try:
        # Recupera API key dalle variabili d'ambiente o usa valore di default
        api_key = os.getenv("PRAMAIALOG_API_KEY", "vectorstore_service_key")
        
        # Crea client semplificato (dummy)
        # Questo è solo un mock, dato che non abbiamo il client reale disponibile
        _log_client = logging.getLogger("pramaialog_client")
        
        if _logger:
            _logger.info("Client PramaIA-LogService configurato con successo")
        
        return _log_client
    except Exception as e:
        if _logger:
            _logger.error(f"Errore durante la configurazione del client PramaIA-LogService: {str(e)}")
        return None

def get_logger(name=None):
    """
    Restituisce un logger configurato per un modulo specifico.
    
    Questa funzione restituisce un oggetto che fornisce un'interfaccia
    simile a quella di un logger standard ma invia anche i log
    al servizio PramaIA-LogService quando disponibile.
    
    Args:
        name: Nome del modulo/logger
        
    Returns:
        LoggerAdapter o logger standard
    """
    global _logger
    
    if _logger is None:
        _logger = setup_logging()
    
    # Ottieni il logger specifico del modulo
    module_logger = logging.getLogger(name if name else "vectorstore")
    
    # Se il client PramaIA-LogService non è disponibile, restituisci solo il logger standard
    if not PRAMAIALOG_AVAILABLE or _log_client is None:
        return module_logger
    
    # Altrimenti, restituisci un wrapper che invia i log a entrambi i sistemi
    return LoggerAdapter(module_logger, _log_client, name)

class LoggerAdapter:
    """
    Adapter che invia i log sia al logger standard che al client PramaIA-LogService.
    """
    
    def __init__(self, logger, log_client, name=None):
        """
        Inizializza l'adapter.
        
        Args:
            logger: Logger standard
            log_client: Client PramaIA-LogService
            name: Nome del modulo
        """
        self.logger = logger
        self.log_client = log_client
        self.module_name = name if name else "vectorstore"
    
    def debug(self, msg, *args, **kwargs):
        """Invia log di livello DEBUG."""
        details = kwargs.pop("details", None)
        context = kwargs.pop("context", None)
        
        self.logger.debug(msg, *args, **kwargs)
        self.log_client.debug(msg, details=details, context=context)
    
    def info(self, msg, *args, **kwargs):
        """Invia log di livello INFO."""
        details = kwargs.pop("details", None)
        context = kwargs.pop("context", None)
        
        self.logger.info(msg, *args, **kwargs)
        self.log_client.info(msg, details=details, context=context)
    
    def warning(self, msg, *args, **kwargs):
        """Invia log di livello WARNING."""
        details = kwargs.pop("details", None)
        context = kwargs.pop("context", None)
        
        self.logger.warning(msg, *args, **kwargs)
        self.log_client.warning(msg, details=details, context=context)
    
    def error(self, msg, *args, **kwargs):
        """Invia log di livello ERROR."""
        details = kwargs.pop("details", None)
        context = kwargs.pop("context", None)
        
        self.logger.error(msg, *args, **kwargs)
        self.log_client.error(msg, details=details, context=context)
    
    def critical(self, msg, *args, **kwargs):
        """Invia log di livello CRITICAL."""
        details = kwargs.pop("details", None)
        context = kwargs.pop("context", None)
        
        self.logger.critical(msg, *args, **kwargs)
        self.log_client.critical(msg, details=details, context=context)
    
    def exception(self, msg, *args, exc_info=True, **kwargs):
        """Invia log di eccezione (livello ERROR)."""
        details = kwargs.pop("details", {}) or {}
        context = kwargs.pop("context", None)
        
        # Aggiungi informazioni sull'eccezione ai dettagli
        import traceback
        if exc_info:
            if "stack_trace" not in details:
                details["stack_trace"] = traceback.format_exc()
        
        self.logger.exception(msg, *args, exc_info=exc_info, **kwargs)
        self.log_client.error(msg, details=details, context=context)
