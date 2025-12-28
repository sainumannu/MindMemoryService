#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script per allineare documenti tra ChromaDB e SQLite.

Identifica:
- Documenti presenti solo in ChromaDB (non in SQLite)
- Documenti presenti solo in SQLite (non in ChromaDB)
- Documenti presenti in entrambi

Opzioni:
- --dry-run: Mostra solo cosa verrebbe fatto senza modificare
- --sync-to-sqlite: Sincronizza documenti da ChromaDB a SQLite
- --sync-to-chromadb: Sincronizza documenti da SQLite a ChromaDB
- --sync-both: Sincronizza in entrambe le direzioni
"""

import argparse
import sys
import io
from datetime import datetime
from typing import Set, Dict, Any, List

# Fix encoding on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app.core.vectordb_manager import VectorDBManager
from app.utils.sqlite_metadata_manager import SQLiteMetadataManager


def get_chromadb_document_ids() -> Set[str]:
    """Ottiene tutti gli ID documenti da ChromaDB."""
    try:
        vector_db = VectorDBManager()
        collection = vector_db.get_collection()
        if not collection:
            print("❌ Nessuna collezione ChromaDB trovata")
            return set()
        
        data = collection.get()
        ids = set(data.get('ids', []))
        print(f"✓ ChromaDB: {len(ids)} documenti")
        return ids
    except Exception as e:
        print(f"❌ Errore lettura ChromaDB: {e}")
        return set()


def get_sqlite_document_ids() -> Set[str]:
    """Ottiene tutti gli ID documenti da SQLite."""
    try:
        metadata_db = SQLiteMetadataManager()
        docs = metadata_db.get_documents(limit=100000)  # Get all
        ids = set(doc.get('id') for doc in docs if doc and doc.get('id'))
        print(f"✓ SQLite: {len(ids)} documenti")
        return ids
    except Exception as e:
        print(f"❌ Errore lettura SQLite: {e}")
        return set()


def get_chromadb_document(doc_id: str) -> Dict[str, Any]:
    """Recupera un documento completo da ChromaDB."""
    try:
        vector_db = VectorDBManager()
        collection = vector_db.get_collection()
        if not collection:
            return {}
        
        data = collection.get(ids=[doc_id])
        if not data or not data.get('ids'):
            return {}
        
        return {
            'id': doc_id,
            'content': data['documents'][0] if data.get('documents') else '',
            'metadata': data['metadatas'][0] if data.get('metadatas') else {},
            'embedding': data['embeddings'][0] if data.get('embeddings') else None
        }
    except Exception as e:
        print(f"  ⚠️  Errore lettura documento {doc_id} da ChromaDB: {e}")
        return {}


def get_sqlite_document(doc_id: str) -> Dict[str, Any]:
    """Recupera un documento completo da SQLite."""
    try:
        metadata_db = SQLiteMetadataManager()
        return metadata_db.get_document(doc_id)
    except Exception as e:
        print(f"  ⚠️  Errore lettura documento {doc_id} da SQLite: {e}")
        return {}


def remove_orphan_sqlite_documents(doc_ids: List[str], dry_run: bool = True) -> int:
    """
    Rimuove documenti presenti solo in SQLite (senza corrispondenza in ChromaDB).
    
    Args:
        doc_ids: Lista di ID documenti da rimuovere
        dry_run: Se True, mostra solo cosa verrebbe fatto
    
    Returns:
        Numero di documenti rimossi
    """
    if not doc_ids:
        return 0
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Rimozione documenti orfani da SQLite...")
    metadata_db = SQLiteMetadataManager()
    removed = 0
    
    for i, doc_id in enumerate(doc_ids, 1):
        print(f"  [{i}/{len(doc_ids)}] {doc_id}...", end=' ')
        
        if dry_run:
            print(f"✓ Verrebbe rimosso")
        else:
            try:
                success = metadata_db.delete_document(doc_id)
                if success:
                    print(f"✅ Rimosso")
                    removed += 1
                else:
                    print(f"❌ Errore rimozione")
            except Exception as e:
                print(f"❌ Errore: {e}")
    
    return removed


def sync_chromadb_to_sqlite(doc_ids: List[str], dry_run: bool = True) -> int:
    """
    Sincronizza documenti da ChromaDB a SQLite.
    
    Args:
        doc_ids: Lista di ID documenti da sincronizzare
        dry_run: Se True, mostra solo cosa verrebbe fatto
    
    Returns:
        Numero di documenti sincronizzati
    """
    if not doc_ids:
        return 0
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Sincronizzazione ChromaDB → SQLite...")
    metadata_db = SQLiteMetadataManager()
    synced = 0
    
    for i, doc_id in enumerate(doc_ids, 1):
        print(f"  [{i}/{len(doc_ids)}] {doc_id}...", end=' ')
        
        # Ottieni documento da ChromaDB
        chroma_doc = get_chromadb_document(doc_id)
        if not chroma_doc:
            print("❌ Skip (non trovato in ChromaDB)")
            continue
        
        # Prepara documento per SQLite
        metadata = chroma_doc.get('metadata', {})
        if not metadata or not isinstance(metadata, dict):
            # Fallback: crea metadata minimo con collection
            metadata = {
                'collection': metadata.get('collection', 'default') if isinstance(metadata, dict) else 'default',
                'imported_from_chromadb': True,
                'import_date': datetime.now().isoformat()
            }
        
        sqlite_doc = {
            'id': doc_id,
            'collection': metadata.get('collection', 'default'),
            'content': chroma_doc.get('content', ''),
            'metadata': metadata
        }
        
        if dry_run:
            print(f"✓ Verrebbe creato (content: {len(sqlite_doc['content'])} chars, metadata: {len(metadata)} keys)")
        else:
            try:
                success = metadata_db.add_document(sqlite_doc)
                if success:
                    print(f"✅ Creato")
                    synced += 1
                else:
                    print(f"❌ Errore creazione")
            except Exception as e:
                print(f"❌ Errore: {e}")
    
    return synced


def sync_sqlite_to_chromadb(doc_ids: List[str], dry_run: bool = True) -> int:
    """
    Sincronizza documenti da SQLite a ChromaDB.
    
    Args:
        doc_ids: Lista di ID documenti da sincronizzare
        dry_run: Se True, mostra solo cosa verrebbe fatto
    
    Returns:
        Numero di documenti sincronizzati
    """
    if not doc_ids:
        return 0
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Sincronizzazione SQLite → ChromaDB...")
    vector_db = VectorDBManager()
    collection = vector_db.get_collection()
    
    if not collection:
        print("❌ Collezione ChromaDB non disponibile")
        return 0
    
    synced = 0
    
    for i, doc_id in enumerate(doc_ids, 1):
        print(f"  [{i}/{len(doc_ids)}] {doc_id}...", end=' ')
        
        # Ottieni documento da SQLite
        sqlite_doc = get_sqlite_document(doc_id)
        if not sqlite_doc:
            print("❌ Skip (non trovato in SQLite)")
            continue
        
        content = sqlite_doc.get('content', '')
        if not content or not content.strip():
            print("⚠️  Skip (contenuto vuoto, ChromaDB richiede contenuto per embedding)")
            continue
        
        metadata = sqlite_doc.get('metadata', {})
        if not metadata or not isinstance(metadata, dict):
            metadata = {'collection': sqlite_doc.get('collection', 'default')}
        
        # Assicurati che metadata non sia vuoto (ChromaDB può rifiutare)
        if len(metadata) == 0:
            metadata = {
                'collection': sqlite_doc.get('collection', 'default'),
                'imported_from_sqlite': True,
                'import_date': datetime.now().isoformat()
            }
        
        if dry_run:
            print(f"✓ Verrebbe aggiunto (content: {len(content)} chars, metadata: {list(metadata.keys())})")
        else:
            try:
                collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[metadata]
                )
                print(f"✅ Aggiunto")
                synced += 1
            except Exception as e:
                print(f"❌ Errore: {e}")
    
    return synced


def main():
    parser = argparse.ArgumentParser(
        description="Allinea documenti tra ChromaDB e SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  # Mostra solo lo stato (dry-run)
  python align_databases.py --dry-run
  
  # Sincronizza documenti da ChromaDB a SQLite
  python align_databases.py --sync-to-sqlite
  
  # Sincronizza documenti da SQLite a ChromaDB
  python align_databases.py --sync-to-chromadb
  
  # Sincronizza in entrambe le direzioni
  python align_databases.py --sync-both
  
  # Rimuove documenti orfani da SQLite (senza corrispondenza in ChromaDB)
  python align_databases.py --remove-orphan-sqlite
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mostra cosa verrebbe fatto senza modificare i database'
    )
    
    parser.add_argument(
        '--sync-to-sqlite',
        action='store_true',
        help='Sincronizza documenti da ChromaDB a SQLite'
    )
    
    parser.add_argument(
        '--sync-to-chromadb',
        action='store_true',
        help='Sincronizza documenti da SQLite a ChromaDB'
    )
    
    parser.add_argument(
        '--sync-both',
        action='store_true',
        help='Sincronizza in entrambe le direzioni'
    )
    
    parser.add_argument(
        '--remove-orphan-sqlite',
        action='store_true',
        help='Rimuove documenti presenti solo in SQLite (senza corrispondenza in ChromaDB)'
    )
    
    args = parser.parse_args()
    
    # Se nessuna opzione sync specificata, abilita dry-run
    if not (args.sync_to_sqlite or args.sync_to_chromadb or args.sync_both or args.remove_orphan_sqlite):
        args.dry_run = True
    
    print("=" * 70)
    print("ALLINEAMENTO DATABASE: ChromaDB <-> SQLite")
    print("=" * 70)
    
    # Ottieni gli ID da entrambi i database
    print("\n[ANALISI] Scansione database...")
    chromadb_ids = get_chromadb_document_ids()
    sqlite_ids = get_sqlite_document_ids()
    
    # Calcola differenze
    only_in_chromadb = chromadb_ids - sqlite_ids
    only_in_sqlite = sqlite_ids - chromadb_ids
    in_both = chromadb_ids & sqlite_ids
    
    # Report
    print(f"\n[RIEPILOGO]")
    print(f"  - Documenti in ChromaDB: {len(chromadb_ids)}")
    print(f"  - Documenti in SQLite: {len(sqlite_ids)}")
    print(f"  - Documenti in entrambi: {len(in_both)}")
    print(f"  - Solo in ChromaDB: {len(only_in_chromadb)}")
    print(f"  - Solo in SQLite: {len(only_in_sqlite)}")
    
    if only_in_chromadb:
        print(f"\n[!] Documenti SOLO in ChromaDB (primi 10):")
        for doc_id in list(only_in_chromadb)[:10]:
            print(f"    - {doc_id}")
        if len(only_in_chromadb) > 10:
            print(f"    ... e altri {len(only_in_chromadb) - 10}")
    
    if only_in_sqlite:
        print(f"\n[!] Documenti SOLO in SQLite (primi 10):")
        for doc_id in list(only_in_sqlite)[:10]:
            print(f"    - {doc_id}")
        if len(only_in_sqlite) > 10:
            print(f"    ... e altri {len(only_in_sqlite) - 10}")
    
    # Sincronizzazione
    total_synced = 0
    
    if args.remove_orphan_sqlite:
        removed = remove_orphan_sqlite_documents(
            list(only_in_sqlite),
            dry_run=args.dry_run
        )
        total_synced += removed
        if not args.dry_run:
            print(f"\n✅ {removed}/{len(only_in_sqlite)} documenti orfani rimossi da SQLite")
    
    if args.sync_to_sqlite or args.sync_both:
        synced = sync_chromadb_to_sqlite(
            list(only_in_chromadb),
            dry_run=args.dry_run
        )
        total_synced += synced
        if not args.dry_run:
            print(f"\n[OK] {synced}/{len(only_in_chromadb)} documenti sincronizzati a SQLite")
    
    if args.sync_to_chromadb or args.sync_both:
        synced = sync_sqlite_to_chromadb(
            list(only_in_sqlite),
            dry_run=args.dry_run
        )
        total_synced += synced
        if not args.dry_run:
            print(f"\n[OK] {synced}/{len(only_in_sqlite)} documenti sincronizzati a ChromaDB")
    
    # Summary finale
    print("\n" + "=" * 70)
    if args.dry_run:
        print("[DRY RUN] Completato - nessuna modifica effettuata")
        print("\nPer sincronizzare:")
        if only_in_chromadb:
            print(f"  python align_databases.py --sync-to-sqlite")
        if only_in_sqlite:
            print(f"  python align_databases.py --sync-to-chromadb")
            print(f"  # Oppure per rimuovere gli orfani:")
            print(f"  python align_databases.py --remove-orphan-sqlite")
        if only_in_chromadb and only_in_sqlite:
            print(f"  python align_databases.py --sync-both")
    else:
        if args.remove_orphan_sqlite:
            print(f"✅ Pulizia completata: {total_synced} documenti orfani rimossi da SQLite")
        else:
            print(f"✅ Sincronizzazione completata: {total_synced} documenti allineati")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
