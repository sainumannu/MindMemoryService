"""
Dashboard di monitoraggio per il servizio VectorstoreService.

Questo script:
- Raccoglie metriche dal servizio VectorstoreService
- Visualizza lo stato attuale del servizio
- Mostra statistiche delle collezioni
- Traccia le operazioni di riconciliazione
"""

import os
import sys
import time
import datetime
import requests
import argparse
import json
from tabulate import tabulate
import logging
from pathlib import Path

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vectorstore_monitor")

class VectorstoreMonitor:
    """Monitora il servizio VectorstoreService."""
    
    def __init__(self, service_url="http://localhost:8090", output_dir="./monitor_data"):
        """
        Inizializza il monitor.
        
        Args:
            service_url: URL del servizio VectorstoreService
            output_dir: Directory dove salvare i dati di monitoraggio
        """
        self.service_url = service_url.rstrip('/')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.last_stats = {}
        self.history = []
        
        # Carica la storia precedente se esiste
        history_file = self.output_dir / "history.json"
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    self.history = json.load(f)
                logger.info(f"Caricata storia precedente: {len(self.history)} record")
            except Exception as e:
                logger.warning(f"Impossibile caricare la storia: {str(e)}")
    
    def check_health(self):
        """
        Verifica lo stato di salute del servizio.
        
        Returns:
            Dict con lo stato di salute
        """
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            response.raise_for_status()
            health_data = response.json()
            
            # Aggiungi timestamp
            health_data["timestamp"] = datetime.datetime.now().isoformat()
            
            return {
                "status": "ok" if health_data.get("status") == "ok" else "error",
                "response_time": response.elapsed.total_seconds(),
                "details": health_data
            }
        except Exception as e:
            logger.error(f"Errore health check: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def get_stats(self):
        """
        Ottiene le statistiche generali del servizio.
        
        Returns:
            Dict con le statistiche
        """
        try:
            response = requests.get(f"{self.service_url}/stats", timeout=5)
            response.raise_for_status()
            stats = response.json()
            
            # Aggiungi timestamp
            stats["timestamp"] = datetime.datetime.now().isoformat()
            
            # Salva per riferimento
            self.last_stats = stats
            
            return stats
        except Exception as e:
            logger.error(f"Errore raccolta statistiche: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def get_collection_stats(self, collection_name):
        """
        Ottiene le statistiche di una collezione.
        
        Args:
            collection_name: Nome della collezione
            
        Returns:
            Dict con le statistiche della collezione
        """
        try:
            response = requests.get(f"{self.service_url}/stats/{collection_name}", timeout=5)
            response.raise_for_status()
            stats = response.json()
            
            # Aggiungi timestamp
            stats["timestamp"] = datetime.datetime.now().isoformat()
            
            return stats
        except Exception as e:
            logger.error(f"Errore statistiche collezione {collection_name}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "collection": collection_name,
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def get_reconciliation_status(self):
        """
        Ottiene lo stato della riconciliazione.
        
        Returns:
            Dict con lo stato della riconciliazione
        """
        try:
            response = requests.get(f"{self.service_url}/reconciliation/status", timeout=5)
            response.raise_for_status()
            status = response.json()
            
            # Aggiungi timestamp
            status["timestamp"] = datetime.datetime.now().isoformat()
            
            return status
        except Exception as e:
            logger.error(f"Errore stato riconciliazione: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
    
    def collect_metrics(self):
        """
        Raccoglie tutte le metriche in un unico oggetto.
        
        Returns:
            Dict con tutte le metriche
        """
        health = self.check_health()
        stats = self.get_stats()
        
        metrics = {
            "timestamp": datetime.datetime.now().isoformat(),
            "health": health,
            "stats": stats,
            "collections": {}
        }
        
        # Raccogli statistiche per ogni collezione
        if stats.get("status") != "error" and "collections" in stats:
            for collection in stats["collections"]:
                collection_name = collection.get("name")
                if collection_name:
                    collection_stats = self.get_collection_stats(collection_name)
                    metrics["collections"][collection_name] = collection_stats
        
        # Raccogli stato riconciliazione
        reconciliation = self.get_reconciliation_status()
        metrics["reconciliation"] = reconciliation
        
        # Aggiungi alle metriche storiche
        self.history.append(metrics)
        
        # Limita la storia a 1000 record
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        
        # Salva la storia
        try:
            with open(self.output_dir / "history.json", "w") as f:
                json.dump(self.history, f)
        except Exception as e:
            logger.error(f"Errore salvataggio storia: {str(e)}")
        
        return metrics
    
    def display_dashboard(self):
        """Visualizza una dashboard delle metriche attuali."""
        metrics = self.collect_metrics()
        
        print("\n" + "=" * 80)
        print(f"DASHBOARD VECTORSTORE SERVICE - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Stato di salute
        health = metrics["health"]
        health_status = "✅ ONLINE" if health.get("status") == "ok" else "❌ OFFLINE"
        print(f"\nSTATO SERVIZIO: {health_status}")
        print(f"URL: {self.service_url}")
        print(f"Tempo di risposta: {health.get('response_time', 'N/A'):.3f}s")
        
        # Statistiche generali
        stats = metrics["stats"]
        if stats.get("status") != "error":
            print("\nSTATISTICHE GENERALI:")
            print(f"- Collezioni totali: {stats.get('collection_count', 'N/A')}")
            print(f"- Documenti totali: {stats.get('total_documents', 'N/A')}")
            print(f"- Spazio su disco: {stats.get('disk_usage', 'N/A')}")
        
        # Collezioni
        if stats.get("status") != "error" and "collections" in stats:
            print("\nCOLLEZIONI:")
            collections_data = []
            for collection in stats["collections"]:
                collection_name = collection.get("name", "N/A")
                doc_count = collection.get("document_count", "N/A")
                
                # Ottieni dettagli specifici della collezione
                coll_details = metrics["collections"].get(collection_name, {})
                embedding_dim = coll_details.get("embedding_dimension", "N/A")
                last_updated = coll_details.get("last_updated", "N/A")
                
                collections_data.append([
                    collection_name, 
                    doc_count, 
                    embedding_dim,
                    last_updated
                ])
            
            print(tabulate(
                collections_data, 
                headers=["Nome", "Documenti", "Dim. Embedding", "Ultimo aggiornamento"],
                tablefmt="grid"
            ))
        
        # Stato riconciliazione
        reconciliation = metrics["reconciliation"]
        if reconciliation.get("status") != "error":
            print("\nSTATO RICONCILIAZIONE:")
            recon_status = reconciliation.get("reconciliation_status", "N/A")
            last_run = reconciliation.get("last_run", "N/A")
            documents_added = reconciliation.get("documents_added", "N/A")
            documents_removed = reconciliation.get("documents_removed", "N/A")
            
            print(f"- Stato: {recon_status}")
            print(f"- Ultima esecuzione: {last_run}")
            print(f"- Documenti aggiunti: {documents_added}")
            print(f"- Documenti rimossi: {documents_removed}")
        
        print("\n" + "=" * 80)

def main():
    """Funzione principale."""
    parser = argparse.ArgumentParser(description="Monitor per VectorstoreService")
    parser.add_argument(
        "--url", 
        default="http://localhost:8090",
        help="URL del servizio VectorstoreService"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=60,
        help="Intervallo di aggiornamento in secondi"
    )
    parser.add_argument(
        "--output", 
        default="./monitor_data",
        help="Directory di output per i dati di monitoraggio"
    )
    parser.add_argument(
        "--once", 
        action="store_true",
        help="Esegui una sola volta e termina"
    )
    
    args = parser.parse_args()
    
    monitor = VectorstoreMonitor(
        service_url=args.url,
        output_dir=args.output
    )
    
    if args.once:
        monitor.display_dashboard()
        return
    
    try:
        while True:
            monitor.display_dashboard()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitoraggio terminato.")

if __name__ == "__main__":
    main()
