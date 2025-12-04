"""
Modulo per la gestione delle dipendenze di autenticazione.
"""

from fastapi import Depends, HTTPException, status, Header
import os
from typing import Optional

# Ottieni l'API key dall'ambiente o usa un valore predefinito per lo sviluppo
API_KEY = os.getenv("VECTORSTORE_API_KEY", "dev_api_key")

async def get_api_key(api_key: Optional[str] = Header(None, convert_underscores=False)) -> str:
    """
    Verifica che l'API key sia valida.
    In produzione, implementare una logica più robusta qui.
    
    Args:
        api_key: Chiave API fornita nell'header
        
    Returns:
        La chiave API validata
        
    Raises:
        HTTPException: Se la chiave API non è valida
    """
    if API_KEY == "dev_api_key" or not api_key:
        # In modalità sviluppo, non richiedere l'API key
        return "dev_api_key"
        
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key non valida"
        )
        
    return api_key