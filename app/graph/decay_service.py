"""
Entity Graph Decay Service - Decadimento entità e relazioni

Gestisce il decadimento graduale di entità e relazioni nel grafo persistente.

BIOLOGICAMENTE CORRETTO:
- Entità non referenziate perdono confidence nel tempo
- Relazioni non confermate decay strength
- Entità con interaction_count basso decadono più velocemente
- Garbage collection: rimozione entità/relazioni sotto soglia

Source: PramaIA-Mind/Mind/world_model/entity_decay_service.py
Adapted: February 2026
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GraphDecayService:
    """
    Service per decadimento entità e relazioni nel grafo persistente
    
    Decay logic:
    - Entità non usate → confidence decade verso 0
    - Relazioni non confermate → strength decade verso 0
    - Decay rate dipende da:
      1. Tempo da last_interaction / last_reinforced
      2. Interaction count (entità usate di più decadono più lentamente)
      3. Confidence/strength attuale
      4. Source (user_declared protette da decay)
    
    Garbage Collection:
    - Entità con confidence < threshold → rimosse
    - Relazioni con strength < threshold → rimosse
    - Orphan entities (nessuna relazione) → rimosse dopo N giorni
    """
    
    def __init__(self, db_manager=None):
        """
        Initialize Graph Decay Service
        
        Args:
            db_manager: SQLiteMetadataManager instance (optional, will use singleton if not provided)
        """
        self.db_manager = db_manager
        
        # Decay configuration
        self.config = {
            "decay_rate": 0.05,                    # 5% decay per ciclo
            "decay_interval_days": 30,             # Decay dopo 30 giorni di inattività
            "min_confidence_threshold": 0.2,       # Sotto questa soglia → garbage collection
            "min_strength_threshold": 0.2,         # Relazioni sotto questa → rimosse
            "interaction_protection_threshold": 5, # Entità con 5+ interazioni decadono più lentamente
            "orphan_removal_days": 90,            # Orphan entities rimosse dopo 90 giorni
        }
        
        # Sources protette da decay (non decadono mai)
        self.protected_sources = ["user_declared", "system"]
        
        # Statistics
        self.stats = {
            "total_decay_runs": 0,
            "entities_decayed": 0,
            "entities_removed": 0,
            "relationships_decayed": 0,
            "relationships_removed": 0,
            "orphans_removed": 0,
            "last_decay_run": None
        }
        
        logger.info("[GRAPH_DECAY] Service initialized")
    
    def _get_db_manager(self):
        """Get DB manager (lazy loading)"""
        if self.db_manager is None:
            from app.utils.sqlite_metadata_manager import SQLiteMetadataManager
            self.db_manager = SQLiteMetadataManager()
        return self.db_manager
    
    def update_config(self, **kwargs):
        """Update decay configuration"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                logger.info(f"[GRAPH_DECAY] Config updated: {key}={value}")
    
    async def apply_decay(self, user_id: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Applica decay a tutte le entità e relazioni.
        
        Args:
            user_id: Optional - se specificato, applica solo a questo utente (non implementato ancora)
            options: Override temporaneo della configurazione
            
        Returns:
            Risultati del decay con statistiche
        """
        logger.info(f"[GRAPH_DECAY] Starting decay run...")
        
        # Merge options con config
        config = self.config.copy()
        if options:
            config.update(options)
        
        result = {
            "success": True,
            "entities_processed": 0,
            "entities_decayed": 0,
            "entities_removed": 0,
            "relationships_processed": 0,
            "relationships_decayed": 0,
            "relationships_removed": 0,
            "orphans_removed": 0,
            "errors": [],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            # Step 1: Decay entities
            entity_results = await self._decay_entities(config)
            result["entities_processed"] = entity_results["processed"]
            result["entities_decayed"] = entity_results["decayed"]
            result["entities_removed"] = entity_results["removed"]
            result["errors"].extend(entity_results.get("errors", []))
            
            # Step 2: Decay relationships
            rel_results = await self._decay_relationships(config)
            result["relationships_processed"] = rel_results["processed"]
            result["relationships_decayed"] = rel_results["decayed"]
            result["relationships_removed"] = rel_results["removed"]
            result["errors"].extend(rel_results.get("errors", []))
            
            # Step 3: Remove orphan entities
            orphan_results = await self._remove_orphans(config)
            result["orphans_removed"] = orphan_results["removed"]
            result["errors"].extend(orphan_results.get("errors", []))
            
            # Update stats
            self.stats["total_decay_runs"] += 1
            self.stats["entities_decayed"] += result["entities_decayed"]
            self.stats["entities_removed"] += result["entities_removed"]
            self.stats["relationships_decayed"] += result["relationships_decayed"]
            self.stats["relationships_removed"] += result["relationships_removed"]
            self.stats["orphans_removed"] += result["orphans_removed"]
            self.stats["last_decay_run"] = result["timestamp"]
            
            logger.info(
                f"[GRAPH_DECAY] Completed: "
                f"{result['entities_decayed']} entities decayed, "
                f"{result['entities_removed']} removed, "
                f"{result['relationships_decayed']} relationships decayed, "
                f"{result['relationships_removed']} removed, "
                f"{result['orphans_removed']} orphans removed"
            )
            
        except Exception as e:
            logger.error(f"[GRAPH_DECAY] Failed: {e}")
            result["success"] = False
            result["errors"].append(str(e))
        
        return result
    
    async def _decay_entities(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply decay to entities"""
        result = {"processed": 0, "decayed": 0, "removed": 0, "errors": []}
        
        db = self._get_db_manager()
        now = datetime.utcnow()
        decay_threshold_date = now - timedelta(days=config["decay_interval_days"])
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get all active entities
                cursor.execute("""
                    SELECT entity_id, confidence, salience, updated_at, 
                           attributes_json, tags_json
                    FROM entities 
                    WHERE status = 'active'
                """)
                entities = cursor.fetchall()
                result["processed"] = len(entities)
                
                for entity in entities:
                    entity_id = entity["entity_id"]
                    confidence = entity["confidence"] or 1.0
                    updated_at_str = entity["updated_at"]
                    
                    # Parse updated_at
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00").replace("+00:00", ""))
                    except:
                        updated_at = now  # Se non parsabile, assume recente
                    
                    # Check if entity should be decayed
                    if updated_at > decay_threshold_date:
                        continue  # Entità recente, skip
                    
                    # Check if protected (from tags or attributes)
                    import json
                    tags = json.loads(entity["tags_json"]) if entity["tags_json"] else []
                    attrs = json.loads(entity["attributes_json"]) if entity["attributes_json"] else {}
                    source = attrs.get("source", "extraction")
                    
                    if source in self.protected_sources or "protected" in tags:
                        continue  # Entità protetta
                    
                    # Calculate decay factor
                    days_inactive = (now - updated_at).days
                    decay_multiplier = min(days_inactive / config["decay_interval_days"], 3.0)  # Max 3x decay
                    decay_factor = config["decay_rate"] * decay_multiplier
                    
                    # Apply decay
                    new_confidence = confidence * (1.0 - decay_factor)
                    
                    if new_confidence < config["min_confidence_threshold"]:
                        # Remove entity
                        cursor.execute("DELETE FROM entities WHERE entity_id = ?", (entity_id,))
                        result["removed"] += 1
                        logger.debug(f"   Removed entity: {entity_id} (confidence={new_confidence:.3f})")
                    else:
                        # Update confidence
                        cursor.execute(
                            "UPDATE entities SET confidence = ?, updated_at = ? WHERE entity_id = ?",
                            (new_confidence, now.isoformat() + "Z", entity_id)
                        )
                        result["decayed"] += 1
                        logger.debug(f"   📉 Decayed entity: {entity_id} ({confidence:.3f} → {new_confidence:.3f})")
                
                conn.commit()
                
        except Exception as e:
            result["errors"].append(f"Entity decay error: {e}")
            logger.error(f"Entity decay error: {e}")
        
        return result
    
    async def _decay_relationships(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply decay to relationships"""
        result = {"processed": 0, "decayed": 0, "removed": 0, "errors": []}
        
        db = self._get_db_manager()
        now = datetime.utcnow()
        decay_threshold_date = now - timedelta(days=config["decay_interval_days"])
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get all active relationships
                cursor.execute("""
                    SELECT rel_id, strength, updated_at
                    FROM relationships 
                    WHERE status = 'active'
                """)
                relationships = cursor.fetchall()
                result["processed"] = len(relationships)
                
                for rel in relationships:
                    rel_id = rel["rel_id"]
                    strength = rel["strength"] or 1.0
                    updated_at_str = rel["updated_at"]
                    
                    # Parse updated_at
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00").replace("+00:00", ""))
                    except:
                        updated_at = now
                    
                    # Check if should be decayed
                    if updated_at > decay_threshold_date:
                        continue
                    
                    # Calculate decay factor
                    days_inactive = (now - updated_at).days
                    decay_multiplier = min(days_inactive / config["decay_interval_days"], 3.0)
                    decay_factor = config["decay_rate"] * decay_multiplier
                    
                    # Apply decay
                    new_strength = strength * (1.0 - decay_factor)
                    
                    if new_strength < config["min_strength_threshold"]:
                        # Remove relationship
                        cursor.execute("DELETE FROM relationships WHERE rel_id = ?", (rel_id,))
                        result["removed"] += 1
                        logger.debug(f"   Removed relationship: {rel_id}")
                    else:
                        # Update strength
                        cursor.execute(
                            "UPDATE relationships SET strength = ?, updated_at = ? WHERE rel_id = ?",
                            (new_strength, now.isoformat() + "Z", rel_id)
                        )
                        result["decayed"] += 1
                        logger.debug(f"   📉 Decayed relationship: {rel_id} ({strength:.3f} → {new_strength:.3f})")
                
                conn.commit()
                
        except Exception as e:
            result["errors"].append(f"Relationship decay error: {e}")
            logger.error(f"Relationship decay error: {e}")
        
        return result
    
    async def _remove_orphans(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove orphan entities (entities with no relationships and old)"""
        result = {"removed": 0, "errors": []}
        
        db = self._get_db_manager()
        now = datetime.utcnow()
        orphan_threshold_date = now - timedelta(days=config["orphan_removal_days"])
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Find orphan entities (no relationships pointing to/from them)
                cursor.execute("""
                    SELECT e.entity_id, e.updated_at, e.attributes_json, e.tags_json
                    FROM entities e
                    WHERE e.status = 'active'
                    AND NOT EXISTS (
                        SELECT 1 FROM relationships r 
                        WHERE r.from_entity_id = e.entity_id 
                        OR r.to_entity_id = e.entity_id
                    )
                """)
                orphans = cursor.fetchall()
                
                import json
                for orphan in orphans:
                    entity_id = orphan["entity_id"]
                    updated_at_str = orphan["updated_at"]
                    
                    # Parse updated_at
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00").replace("+00:00", ""))
                    except:
                        updated_at = now
                    
                    # Check if old enough to remove
                    if updated_at > orphan_threshold_date:
                        continue
                    
                    # Check if protected
                    tags = json.loads(orphan["tags_json"]) if orphan["tags_json"] else []
                    attrs = json.loads(orphan["attributes_json"]) if orphan["attributes_json"] else {}
                    source = attrs.get("source", "extraction")
                    
                    if source in self.protected_sources or "protected" in tags:
                        continue
                    
                    # Remove orphan
                    cursor.execute("DELETE FROM entities WHERE entity_id = ?", (entity_id,))
                    result["removed"] += 1
                    logger.debug(f"   Removed orphan entity: {entity_id}")
                
                conn.commit()
                
        except Exception as e:
            result["errors"].append(f"Orphan removal error: {e}")
            logger.error(f"Orphan removal error: {e}")
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get decay service statistics"""
        return self.stats.copy()
    
    def get_config(self) -> Dict[str, Any]:
        """Get current decay configuration"""
        return self.config.copy()


# Singleton instance
_decay_service_instance: Optional[GraphDecayService] = None

def get_decay_service() -> GraphDecayService:
    """Get or create singleton GraphDecayService instance"""
    global _decay_service_instance
    if _decay_service_instance is None:
        _decay_service_instance = GraphDecayService()
    return _decay_service_instance
