"""
Modulo per la gestione dello scheduler dei job di riconciliazione.
"""

import logging

# Configurazione logging
logger = logging.getLogger(__name__)

# Singleton pattern per lo scheduler
_scheduler_instance = None

def get_scheduler():
    """
    Ottiene l'istanza singleton dello scheduler.
    
    Returns:
        Istanza di scheduler semplificato
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = {}
        
    return _scheduler_instance

def start_scheduler():
    """Avvia lo scheduler."""
    logger.info("Scheduler avviato (semplificato)")

def stop_scheduler():
    """Ferma lo scheduler."""
    logger.info("Scheduler fermato (semplificato)")
