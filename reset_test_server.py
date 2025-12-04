"""
Server di test per verificare la funzionalità dell'endpoint reset con tipo.
"""

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import uvicorn
from datetime import datetime

# Configurazione logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea l'app FastAPI
app = FastAPI(title="Reset Test Server")

# Aggiungi middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea router
api_router = APIRouter()

@api_router.get("/health")
async def health_check():
    """Endpoint di controllo dello stato del server."""
    return {"status": "ok"}

@api_router.post("/api/database-management/reset")
async def reset_database():
    """Endpoint di reset database generico."""
    logger.info("Richiesta reset database generale ricevuta")
    return {
        "success": True,
        "message": "Database SQL resettato con successo (generale)",
        "timestamp": datetime.now().isoformat()
    }

@api_router.post("/api/database-management/reset/{type}")
async def reset_database_by_type(type: str):
    """Endpoint di reset database con tipo specifico."""
    logger.info(f"Richiesta reset database tipo '{type}' ricevuta")
    
    if type.lower() == "sql":
        return {
            "success": True,
            "message": f"Database SQL resettato con successo (tipo: {type})",
            "timestamp": datetime.now().isoformat()
        }
    elif type.lower() == "chroma":
        return {
            "success": True,
            "message": f"Vector store (ChromaDB) resettato con successo (tipo: {type})",
            "timestamp": datetime.now().isoformat()
        }
    else:
        logger.warning(f"Tipo di reset non valido: {type}")
        return {
            "success": False,
            "message": f"Tipo di reset non valido: {type}. Valori supportati: 'sql' o 'chroma'",
            "timestamp": datetime.now().isoformat()
        }

# Registra il router
app.include_router(api_router)

# Entry point
if __name__ == "__main__":
    port = 8091  # Porta diversa per non interferire con il server principale
    logger.info(f"Avvio Reset Test Server su http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)