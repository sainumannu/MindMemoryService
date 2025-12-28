"""
Pulisce i metadata orfani nel database SQLite.
I metadata orfani sono righe in document_metadata che non hanno un documento corrispondente in documents.
"""

import sqlite3

def clean_orphan_metadata():
    """Rimuove tutti i metadata orfani dal database."""
    conn = sqlite3.connect('data/documents.db')
    cursor = conn.cursor()
    
    # Conta metadata orfani
    cursor.execute("""
        SELECT COUNT(*) 
        FROM document_metadata 
        WHERE document_id NOT IN (SELECT id FROM documents)
    """)
    orphan_count = cursor.fetchone()[0]
    
    print(f"Metadata orfani trovati: {orphan_count}")
    
    if orphan_count > 0:
        # Mostra alcuni esempi
        cursor.execute("""
            SELECT DISTINCT document_id 
            FROM document_metadata 
            WHERE document_id NOT IN (SELECT id FROM documents)
            LIMIT 5
        """)
        examples = [row[0] for row in cursor.fetchall()]
        print(f"Esempi di document_id orfani: {examples}")
        
        # Rimuovi
        print("\nRimozione metadata orfani...")
        cursor.execute("""
            DELETE FROM document_metadata 
            WHERE document_id NOT IN (SELECT id FROM documents)
        """)
        removed = cursor.rowcount
        conn.commit()
        
        print(f"✅ Rimossi {removed} metadata orfani")
    else:
        print("✅ Nessun metadata orfano trovato")
    
    # Verifica finale
    cursor.execute("SELECT COUNT(*) FROM document_metadata")
    remaining = cursor.fetchone()[0]
    print(f"\nMetadata totali rimanenti: {remaining}")
    
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    print(f"Documenti totali: {doc_count}")
    
    conn.close()

if __name__ == "__main__":
    clean_orphan_metadata()
