"""
File Watcher personalizzato per VectorstoreService

Questo modulo fornisce funzionalità di monitoraggio dei file
con log dettagliati su quali file sono stati modificati e che tipo di modifiche sono avvenute.
"""

import os
import time
import threading
import logging
from pathlib import Path
from typing import Dict, Set, Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("vectorstore.file_watcher")

class ChangeType(Enum):
    """Tipi di cambiamenti che possono essere rilevati."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNKNOWN = "unknown"

@dataclass
class FileChange:
    """Rappresenta un cambiamento rilevato su un file."""
    path: str
    change_type: ChangeType
    timestamp: float
    metadata: Optional[dict] = None
    
    def __str__(self) -> str:
        """Restituisce una rappresentazione stringa leggibile del cambiamento."""
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))
        metadata_str = f", metadata: {self.metadata}" if self.metadata else ""
        return f"[{timestamp_str}] {self.change_type.value.upper()}: {self.path}{metadata_str}"

class FileWatcher:
    """
    Un watcher di file che monitora una directory per cambiamenti
    e registra dettagli su quali file sono stati modificati.
    """
    
    def __init__(
        self, 
        paths: List[str],
        interval: float = 1.0,
        recursive: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        on_change_callback: Optional[Callable[[FileChange], None]] = None
    ):
        """
        Inizializza il FileWatcher.
        
        Args:
            paths: Lista di percorsi da monitorare
            interval: Intervallo in secondi tra le verifiche
            recursive: Se monitorare anche le sottodirectory
            include_patterns: Lista di pattern glob da includere
            exclude_patterns: Lista di pattern glob da escludere
            on_change_callback: Callback da chiamare quando viene rilevata una modifica
        """
        self.paths = [Path(p) for p in paths]
        self.interval = interval
        self.recursive = recursive
        self.include_patterns = include_patterns or ["*"]
        self.exclude_patterns = exclude_patterns or [".git/*", "__pycache__/*", "*.pyc", "*.pyo", "*.pyd", ".DS_Store"]
        self.on_change_callback = on_change_callback
        self._file_stats: Dict[str, float] = {}  # path -> mtime
        self._known_files: Set[str] = set()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._initial_scan()
    
    def _initial_scan(self) -> None:
        """Esegue una scansione iniziale dei file monitorati."""
        logger.info(f"Esecuzione scansione iniziale di {len(self.paths)} percorsi")
        for path in self.paths:
            self._scan_path(path)
        logger.info(f"Scansione iniziale completata. {len(self._known_files)} file indicizzati.")
    
    def _should_monitor(self, file_path: str) -> bool:
        """Controlla se un file dovrebbe essere monitorato in base ai pattern di inclusione/esclusione."""
        from fnmatch import fnmatch
        
        # Prima applica i pattern di esclusione
        for pattern in self.exclude_patterns:
            if fnmatch(file_path, pattern):
                return False
        
        # Poi applica i pattern di inclusione
        for pattern in self.include_patterns:
            if fnmatch(file_path, pattern):
                return True
        
        return False
    
    def _scan_path(self, path: Path) -> None:
        """Scansiona un percorso e aggiorna i file conosciuti."""
        if not path.exists():
            logger.warning(f"Il percorso {path} non esiste")
            return
            
        if path.is_file() and self._should_monitor(str(path)):
            try:
                self._known_files.add(str(path))
                self._file_stats[str(path)] = path.stat().st_mtime
            except (FileNotFoundError, PermissionError) as e:
                logger.debug(f"Errore durante l'accesso a {path}: {e}")
        elif path.is_dir():
            try:
                for item in path.iterdir():
                    if item.is_file() and self._should_monitor(str(item)):
                        self._known_files.add(str(item))
                        try:
                            self._file_stats[str(item)] = item.stat().st_mtime
                        except (FileNotFoundError, PermissionError) as e:
                            logger.debug(f"Errore durante l'accesso a {item}: {e}")
                    elif item.is_dir() and self.recursive:
                        self._scan_path(item)
            except (PermissionError, FileNotFoundError) as e:
                logger.debug(f"Errore durante la scansione della directory {path}: {e}")
    
    def _check_for_changes(self) -> List[FileChange]:
        """Controlla se ci sono cambiamenti nei file monitorati."""
        changes = []
        current_files = set()
        
        # Controlla tutti i percorsi monitorati
        for path in self.paths:
            if not path.exists():
                continue
                
            self._scan_current_files(path, current_files)
        
        # Trova i file creati (nei file correnti ma non conosciuti)
        for file_path in current_files - self._known_files:
            if self._should_monitor(file_path):
                try:
                    stat = Path(file_path).stat()
                    changes.append(FileChange(
                        path=file_path,
                        change_type=ChangeType.CREATED,
                        timestamp=time.time(),
                        metadata={
                            "size": stat.st_size,
                            "created": stat.st_ctime,
                            "extension": os.path.splitext(file_path)[1]
                        }
                    ))
                    self._file_stats[file_path] = stat.st_mtime
                except (FileNotFoundError, PermissionError):
                    pass
        
        # Trova i file eliminati (nei file conosciuti ma non correnti)
        for file_path in self._known_files - current_files:
            changes.append(FileChange(
                path=file_path,
                change_type=ChangeType.DELETED,
                timestamp=time.time(),
                metadata={
                    "extension": os.path.splitext(file_path)[1]
                }
            ))
            if file_path in self._file_stats:
                del self._file_stats[file_path]
        
        # Trova i file modificati (file che esistono ma con orario di modifica diverso)
        for file_path in current_files.intersection(self._known_files):
            try:
                current_mtime = Path(file_path).stat().st_mtime
                if file_path in self._file_stats and current_mtime > self._file_stats[file_path]:
                    stat = Path(file_path).stat()
                    changes.append(FileChange(
                        path=file_path,
                        change_type=ChangeType.MODIFIED,
                        timestamp=time.time(),
                        metadata={
                            "size": stat.st_size,
                            "previous_mtime": self._file_stats.get(file_path),
                            "current_mtime": current_mtime,
                            "extension": os.path.splitext(file_path)[1]
                        }
                    ))
                    self._file_stats[file_path] = current_mtime
            except (FileNotFoundError, PermissionError):
                pass
        
        # Aggiorna i file conosciuti
        self._known_files = current_files
        
        return changes
    
    def _scan_current_files(self, path: Path, current_files: Set[str]) -> None:
        """Scansiona i file attuali e li aggiunge al set fornito."""
        if path.is_file() and self._should_monitor(str(path)):
            current_files.add(str(path))
        elif path.is_dir():
            try:
                for item in path.iterdir():
                    if item.is_file() and self._should_monitor(str(item)):
                        current_files.add(str(item))
                    elif item.is_dir() and self.recursive:
                        self._scan_current_files(item, current_files)
            except (PermissionError, FileNotFoundError) as e:
                logger.debug(f"Errore durante la scansione della directory {path}: {e}")
    
    def _watch_thread(self) -> None:
        """Thread principale per il monitoraggio dei file."""
        logger.info(f"Avvio monitoraggio file su {len(self.paths)} percorsi con intervallo di {self.interval}s")
        
        while self._running:
            changes = self._check_for_changes()
            
            if changes:
                for change in changes:
                    logger.info(f"Modifica rilevata: {change}")
                    if self.on_change_callback:
                        try:
                            self.on_change_callback(change)
                        except Exception as e:
                            logger.error(f"Errore nella callback di modifica: {e}")
            
            time.sleep(self.interval)
    
    def start(self) -> None:
        """Avvia il monitoraggio dei file in un thread separato."""
        if self._running:
            logger.warning("FileWatcher è già in esecuzione")
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._watch_thread, daemon=True)
        self._thread.start()
        logger.info("FileWatcher avviato")
    
    def stop(self) -> None:
        """Arresta il monitoraggio dei file."""
        if not self._running:
            logger.warning("FileWatcher non è in esecuzione")
            return
            
        self._running = False
        if self._thread:
            self._thread.join(timeout=self.interval * 2)
        logger.info("FileWatcher arrestato")

# Funzione di aiuto per creare e avviare un watcher configurato
def start_file_watcher(
    paths: List[str],
    on_change_callback: Optional[Callable[[FileChange], None]] = None,
    **kwargs
) -> FileWatcher:
    """
    Crea e avvia un FileWatcher configurato.
    
    Args:
        paths: Lista di percorsi da monitorare
        on_change_callback: Callback opzionale da chiamare quando viene rilevata una modifica
        **kwargs: Altri parametri da passare a FileWatcher
    
    Returns:
        L'istanza FileWatcher avviata
    """
    watcher = FileWatcher(paths=paths, on_change_callback=on_change_callback, **kwargs)
    watcher.start()
    return watcher
