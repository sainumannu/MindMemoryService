"""
Script di update per aggiungere file API_URLS.js con i nuovi endpoint necessari per la UI.
"""

import json
import argparse
import os
from pathlib import Path

def update_api_urls(frontend_dir):
    """
    Aggiorna il file apiUtils.js per includere i nuovi endpoint.
    """
    # Path del file API_URLS.js
    api_utils_path = os.path.join(frontend_dir, "src", "utils", "apiUtils.js")
    
    if not os.path.exists(api_utils_path):
        print(f"File non trovato: {api_utils_path}")
        return False
    
    with open(api_utils_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica se gli endpoint sono già presenti
    if "'/documents/status'" in content and "'/documents/list'" in content:
        print("Gli endpoint sono già stati aggiunti. Nessuna modifica necessaria.")
        return True
    
    # Aggiungiamo i nuovi endpoint nella sezione DATABASE_MANAGEMENT
    old_section = """export const API_URLS = {
  // Backend principale
  AUTH: buildBackendApiUrl('auth'),
  DOCUMENTS: buildBackendApiUrl('api/database-management/documents'),
  CHAT: buildBackendApiUrl('chat'),
  SESSIONS: buildBackendApiUrl('sessions'),
  USERS: buildBackendApiUrl('users'),
  DATABASE_MANAGEMENT: buildBackendApiUrl('api/database-management'),
  
  // Vectorstore (attraverso il backend che fa da proxy)
  VECTORSTORE: buildBackendApiUrl('api/database-management/vectorstore'),"""
    
    new_section = """export const API_URLS = {
  // Backend principale
  AUTH: buildBackendApiUrl('auth'),
  DOCUMENTS: buildBackendApiUrl('api/database-management/documents'),
  CHAT: buildBackendApiUrl('chat'),
  SESSIONS: buildBackendApiUrl('sessions'),
  USERS: buildBackendApiUrl('users'),
  DATABASE_MANAGEMENT: buildBackendApiUrl('api/database-management'),
  
  // Document DB API endpoints
  DOCUMENT_DB_STATUS: buildBackendApiUrl('api/database-management/documents/status'),
  DOCUMENT_DB_LIST: buildBackendApiUrl('api/database-management/documents/list'),
  DOCUMENT_DB_BACKUP: buildBackendApiUrl('api/database-management/documents/backup'),
  DOCUMENT_DB_RESET: buildBackendApiUrl('api/database-management/documents/reset'),
  
  // Vectorstore (attraverso il backend che fa da proxy)
  VECTORSTORE: buildBackendApiUrl('api/database-management/vectorstore'),
  VECTORSTORE_STATUS: buildBackendApiUrl('api/database-management/vectorstore/status'),
  VECTORSTORE_DOCUMENTS: buildBackendApiUrl('api/database-management/vectorstore/documents'),
  VECTORSTORE_BACKUP: buildBackendApiUrl('api/database-management/vectorstore/backup'),
  VECTORSTORE_RESET: buildBackendApiUrl('api/database-management/vectorstore/reset'),"""
    
    # Sostituisci la sezione
    updated_content = content.replace(old_section, new_section)
    
    # Salva il file aggiornato
    with open(api_utils_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"File aggiornato: {api_utils_path}")
    return True

def update_document_db_management(frontend_dir):
    """
    Aggiorna il file DocumentDBManagement.jsx per utilizzare i nuovi endpoint API_URLS.
    """
    # Path del file DocumentDBManagement.jsx
    doc_db_path = os.path.join(frontend_dir, "src", "components", "DocumentDBManagement.jsx")
    
    if not os.path.exists(doc_db_path):
        print(f"File non trovato: {doc_db_path}")
        return False
    
    with open(doc_db_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Sostituisci gli endpoint
    content = content.replace(
        "`${API_URLS.DATABASE_MANAGEMENT}/documents/list`", 
        "API_URLS.DOCUMENT_DB_LIST"
    )
    content = content.replace(
        "`${API_URLS.DATABASE_MANAGEMENT}/documents/status`", 
        "API_URLS.DOCUMENT_DB_STATUS"
    )
    content = content.replace(
        "`${API_URLS.DATABASE_MANAGEMENT}/documents/reset`", 
        "API_URLS.DOCUMENT_DB_RESET"
    )
    content = content.replace(
        "`${API_URLS.DATABASE_MANAGEMENT}/documents/backup`", 
        "API_URLS.DOCUMENT_DB_BACKUP"
    )
    
    # Salva il file aggiornato
    with open(doc_db_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"File aggiornato: {doc_db_path}")
    return True

def update_vector_db_management(frontend_dir):
    """
    Aggiorna il file VectorDBManagement.jsx per utilizzare i nuovi endpoint API_URLS.
    """
    # Path del file VectorDBManagement.jsx
    vector_db_path = os.path.join(frontend_dir, "src", "components", "VectorDBManagement.jsx")
    
    if not os.path.exists(vector_db_path):
        print(f"File non trovato: {vector_db_path}")
        return False
    
    with open(vector_db_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Sostituisci gli endpoint
    content = content.replace(
        "`${API_URLS.DATABASE_MANAGEMENT}/vectorstore/documents`", 
        "API_URLS.VECTORSTORE_DOCUMENTS"
    )
    content = content.replace(
        "`${API_URLS.DATABASE_MANAGEMENT}/vectorstore/status`", 
        "API_URLS.VECTORSTORE_STATUS"
    )
    content = content.replace(
        "`${API_URLS.DATABASE_MANAGEMENT}/vectorstore/reset`", 
        "API_URLS.VECTORSTORE_RESET"
    )
    content = content.replace(
        "`${API_URLS.DATABASE_MANAGEMENT}/vectorstore/backup`", 
        "API_URLS.VECTORSTORE_BACKUP"
    )
    
    # Salva il file aggiornato
    with open(vector_db_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"File aggiornato: {vector_db_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Aggiorna i file frontend per utilizzare i nuovi endpoint API")
    parser.add_argument("--frontend-dir", type=str, default="../../PramaIAServer/frontend/client", 
                        help="Path della directory frontend client")
    
    args = parser.parse_args()
    
    # Converte path relativo in assoluto
    frontend_dir = os.path.abspath(args.frontend_dir)
    
    print(f"Aggiornamento file frontend in: {frontend_dir}")
    
    # Verifica esistenza directory
    if not os.path.isdir(frontend_dir):
        print(f"La directory non esiste: {frontend_dir}")
        return
    
    # Aggiorna i file
    update_api_urls(frontend_dir)
    update_document_db_management(frontend_dir)
    update_vector_db_management(frontend_dir)
    
    print("Aggiornamento completato.")

if __name__ == "__main__":
    main()
