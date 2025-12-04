"""
Reconciliation Service - Servizio per la riconciliazione tra il file system e il vectorstore.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

# Logger
logger = logging.getLogger(__name__)

def get_next_scheduled_run(schedule_time: str) -> Optional[datetime]:
    """
    Calcola quando sarà la prossima esecuzione pianificata.
    
    Args:
        schedule_time: Orario pianificato nel formato HH:MM.
        
    Returns:
        Datetime della prossima esecuzione pianificata.
    """
    now = datetime.now()
    
    # Parsa l'orario pianificato
    try:
        hour, minute = map(int, schedule_time.split(":"))
    except:
        hour, minute = 3, 0  # Default alle 3:00
    
    # Crea l'orario pianificato di oggi
    scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Se l'orario è già passato per oggi, pianifica per domani
    if now >= scheduled_time:
        scheduled_time += timedelta(days=1)
        
    return scheduled_time
