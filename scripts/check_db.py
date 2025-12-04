import sqlite3
import os

# Percorso del database
db_path = os.path.join(os.getcwd(), 'data', 'documents.db')

# Connessione al database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Conteggio documenti
cursor.execute("SELECT COUNT(*) FROM documents")
count = cursor.fetchone()[0]
print(f"Numero di documenti nel database: {count}")

# Info tabella
cursor.execute("PRAGMA table_info(documents)")
columns = cursor.fetchall()
print("\nStruttura della tabella documents:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Dimensione del database
db_size = os.path.getsize(db_path)
print(f"\nDimensione del database: {db_size / 1024:.2f} KB")

# Chiudi la connessione
conn.close()
