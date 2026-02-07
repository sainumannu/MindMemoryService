"""
Graph Service - Servizio centrale per operazioni sul Knowledge Graph

Questo modulo fornisce:
- CRUD su entità con normalizzazione automatica del tipo
- CRUD su relazioni con normalizzazione automatica del predicato
- Query avanzate con filtri e raggruppamento
- Integrazione con PredicateNormalizer
- Integrazione con EntityTypeNormalizer
- Integrazione con DecayService

Author: MindMemoryService Team
Date: February 2026
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.graph.data_models import StoredRelationship, RelationCategory, EntityType
from app.graph.predicate_normalizer import PredicateNormalizer, get_predicate_normalizer
from app.graph.entity_type_normalizer import EntityTypeNormalizer, get_entity_type_normalizer
from app.graph.decay_service import GraphDecayService, get_decay_service

logger = logging.getLogger(__name__)


class GraphService:
    """
    Servizio centrale per operazioni sul Knowledge Graph.
    
    Fornisce:
    - create_entity(): Crea entità con tipo normalizzato automaticamente
    - create_relationship_from_raw(): Crea relazione normalizzando predicato RAW
    - get_relationships(): Query con filtri
    - query_relationships(): Query avanzate con group_by
    - apply_decay(): Trigger decay service
    """
    
    def __init__(self, db_manager=None):
        """
        Initialize Graph Service
        
        Args:
            db_manager: SQLiteMetadataManager instance (optional)
        """
        self.db_manager = db_manager
        self.normalizer = get_predicate_normalizer()
        self.entity_type_normalizer = get_entity_type_normalizer()
        self.decay_service = get_decay_service()
        
        logger.info("[GRAPH_SERVICE] Initialized")
    
    def _ensure_entity_exists(self, conn, entity_id: str, entity_type: str = "auto") -> bool:
        """
        Verifica se un'entità esiste e la crea se non esiste.
        
        Args:
            conn: Database connection
            entity_id: ID dell'entità
            entity_type: Tipo dell'entità (default: auto-detected)
            
        Returns:
            True se l'entità esisteva già, False se è stata creata
        """
        cursor = conn.cursor()
        
        # Check se esiste
        cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ?", (entity_id,))
        if cursor.fetchone():
            return True
        
        # Auto-detect tipo se necessario
        if entity_type == "auto":
            entity_type = self._infer_entity_type(entity_id)
        
        # Crea entità minimal
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute("""
            INSERT INTO entities (
                entity_id, type, primary_name, aliases_json, identifiers_json,
                attributes_json, salience, confidence, status, tags_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_id,
            entity_type,
            entity_id,  # primary_name = entity_id
            "[]",       # aliases_json
            "{}",       # identifiers_json  
            "{}",       # attributes_json
            0.5,        # salience
            0.7,        # confidence (auto-created = slightly lower)
            "active",
            "[]",       # tags_json
            now, now
        ))
        
        logger.info(
            f"[GRAPH] AUTO-CREATED entity:\n"
            f"  ID: {entity_id}\n"
            f"  Type: {entity_type} (inferred)\n"
            f"  Confidence: 0.7 (auto-generated)"
        )
        return False
    
    def _infer_entity_type(self, entity_id: str) -> str:
        """
        Inferisce il tipo di entità dall'ID.
        
        Args:
            entity_id: ID dell'entità
            
        Returns:
            Tipo inferito
        """
        entity_id_lower = entity_id.lower()
        
        # Pattern comuni
        if entity_id_lower in ("self", "user", "user_admin", "me", "io"):
            return "person"
        if any(x in entity_id_lower for x in ("person:", "user:")):
            return "person"
        if any(x in entity_id_lower for x in ("place:", "location:", "city:", "country:")):
            return "place"
        if any(x in entity_id_lower for x in ("org:", "company:", "organization:")):
            return "organization"
        if any(x in entity_id_lower for x in ("food:", "dish:", "meal:")):
            return "food"
        if any(x in entity_id_lower for x in ("vehicle:", "car:", "bike:")):
            return "vehicle"
        
        # Default
        return "thing"
    
    def _get_db_manager(self):
        """Get DB manager (lazy loading)"""
        if self.db_manager is None:
            from app.utils.sqlite_metadata_manager import SQLiteMetadataManager
            self.db_manager = SQLiteMetadataManager()
        return self.db_manager
    
    async def create_relationship_from_raw(
        self,
        user_id: str,
        raw_relation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Crea una relazione normalizzando il predicato RAW.
        
        Args:
            user_id: User identifier (per future multi-tenancy)
            raw_relation: Relazione raw da Thalamus:
                {
                    "subject": "user_admin",
                    "predicate": "esprimere_gradimento_per",
                    "object": "pizza_margherita",
                    "source_sentence": "Mi piace la pizza margherita"
                }
                
        Returns:
            Relazione normalizzata salvata
        """
        subject = raw_relation.get("subject", "")
        predicate = raw_relation.get("predicate", "")
        obj = raw_relation.get("object", "")
        source_sentence = raw_relation.get("source_sentence", "")
        
        if not subject or not predicate or not obj:
            raise ValueError("subject, predicate and object are required")
        
        # Normalizza il predicato
        norm_result = self.normalizer.normalize(predicate)
        
        logger.info(
            f"\n{'='*60}\n"
            f"[GRAPH] PROCESSING RELATIONSHIP\n"
            f"{'='*60}\n"
            f"  Subject:   {subject}\n"
            f"  Predicate: '{predicate}'\n"
            f"  Object:    {obj}\n"
            f"  -------------------------------------------\n"
            f"  Normalized: {norm_result.relation_type} / {norm_result.valence}\n"
            f"  Intensity:  {norm_result.intensity}\n"
            f"  Method:     {norm_result.method}\n"
            f"  Source:     '{source_sentence[:100]}...'\n"
            f"{'='*60}"
        )
        
        # Genera ID relazione (solo per nuove relazioni)
        rel_id = f"rel:{subject}_to_{obj}_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat() + "Z"
        
        # Costruisci metadata
        metadata = {
            "valence": norm_result.valence,
            "intensity": norm_result.intensity,
            "normalization_method": norm_result.method,
            "normalization_confidence": norm_result.confidence,
            **norm_result.metadata
        }
        
        # Genera event_id per il log
        event_id = f"evt:{uuid.uuid4().hex[:12]}"
        
        # Salva nel database
        db = self._get_db_manager()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Assicura che le entità esistano (crea automaticamente se necessario)
                self._ensure_entity_exists(conn, subject)
                self._ensure_entity_exists(conn, obj)
                
                # Check se esiste già una relazione simile (stesso tipo)
                cursor.execute("""
                    SELECT rel_id, evidence_count, strength, valence, intensity
                    FROM relationships 
                    WHERE from_entity_id = ? AND to_entity_id = ? AND relation_type = ?
                    AND status = 'active'
                """, (subject, obj, norm_result.relation_type))
                
                existing = cursor.fetchone()
                
                if existing:
                    # ======== RELAZIONE ESISTENTE ========
                    # Pattern: Last Value Wins + Event Log
                    # - UPDATE valence/intensity con NUOVO valore (non media)
                    # - INSERT evento per tracciare la storia
                    
                    existing_id = existing["rel_id"]
                    old_valence = existing["valence"]
                    new_evidence_count = existing["evidence_count"] + 1
                    new_strength = min(1.0, existing["strength"] + 0.1)
                    
                    # UPDATE con NUOVO valence (last value wins)
                    cursor.execute("""
                        UPDATE relationships 
                        SET evidence_count = ?, 
                            strength = ?, 
                            valence = ?,
                            intensity = ?,
                            original_predicate = ?,
                            source_sentence = ?,
                            metadata_json = ?,
                            last_reinforced = ?, 
                            updated_at = ?
                        WHERE rel_id = ?
                    """, (
                        new_evidence_count, 
                        new_strength, 
                        norm_result.valence,      # NUOVO valence
                        norm_result.intensity,    # NUOVA intensity
                        predicate,                # Ultimo predicato usato
                        source_sentence,
                        json.dumps(metadata),
                        now, 
                        now, 
                        existing_id
                    ))
                    
                    # INSERT evento nella storia
                    cursor.execute("""
                        INSERT INTO relationship_events (
                            event_id, rel_id, predicate, valence, intensity,
                            source_sentence, timestamp, normalization_method,
                            normalization_confidence, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event_id,
                        existing_id,
                        predicate,
                        norm_result.valence,
                        norm_result.intensity,
                        source_sentence,
                        now,
                        norm_result.method,
                        norm_result.confidence,
                        json.dumps(metadata)
                    ))
                    
                    conn.commit()
                    
                    valence_change = ""
                    if old_valence != norm_result.valence:
                        valence_change = f" | VALENCE CHANGED: {old_valence}→{norm_result.valence}"
                    
                    logger.info(
                        f"\n{'*'*60}\n"
                        f"[GRAPH] RELATIONSHIP UPDATED (REINFORCED)\n"
                        f"{'*'*60}\n"
                        f"  Rel ID:      {existing_id}\n"
                        f"  From:        {subject}\n"
                        f"  To:          {obj}\n"
                        f"  Type:        {norm_result.relation_type}\n"
                        f"  Valence:     {norm_result.valence} (intensity={norm_result.intensity})\n"
                        f"  Evidence:    {existing['evidence_count']} -> {new_evidence_count}\n"
                        f"  Strength:    {existing['strength']:.2f} -> {new_strength:.2f}\n"
                        f"  Event ID:    {event_id}{valence_change}\n"
                        f"{'*'*60}"
                    )
                    
                    # Ritorna la relazione aggiornata
                    cursor.execute("SELECT * FROM relationships WHERE rel_id = ?", (existing_id,))
                    row = cursor.fetchone()
                    return self._row_to_relationship_dict(row)
                
                else:
                    # ======== NUOVA RELAZIONE ========
                    cursor.execute("""
                        INSERT INTO relationships (
                            rel_id, from_entity_id, to_entity_id, type, relation_type,
                            original_predicate, source_sentence, metadata_json,
                            strength, confidence, valence, intensity,
                            evidence_count, status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rel_id, subject, obj,
                        norm_result.relation_type,
                        norm_result.relation_type,
                        predicate,
                        source_sentence,
                        json.dumps(metadata),
                        1.0,  # strength iniziale
                        norm_result.confidence,
                        norm_result.valence,
                        norm_result.intensity,
                        1,  # evidence_count
                        "active",
                        now, now
                    ))
                    
                    # INSERT primo evento nella storia
                    cursor.execute("""
                        INSERT INTO relationship_events (
                            event_id, rel_id, predicate, valence, intensity,
                            source_sentence, timestamp, normalization_method,
                            normalization_confidence, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event_id,
                        rel_id,
                        predicate,
                        norm_result.valence,
                        norm_result.intensity,
                        source_sentence,
                        now,
                        norm_result.method,
                        norm_result.confidence,
                        json.dumps(metadata)
                    ))
                    
                    conn.commit()
                    
                    logger.info(
                        f"\n{'+'*60}\n"
                        f"[GRAPH] NEW RELATIONSHIP CREATED\n"
                        f"{'+'*60}\n"
                        f"  Rel ID:      {rel_id}\n"
                        f"  From:        {subject}\n"
                        f"  To:          {obj}\n"
                        f"  Type:        {norm_result.relation_type}\n"
                        f"  Valence:     {norm_result.valence} (intensity={norm_result.intensity})\n"
                        f"  Predicate:   '{predicate}'\n"
                        f"  Normalized:  via {norm_result.method}\n"
                        f"  Confidence:  {norm_result.confidence:.2f}\n"
                        f"  Strength:    1.0\n"
                        f"  Event ID:    {event_id}\n"
                        f"{'+'*60}"
                    )
                    
                    return {
                        "id": rel_id,
                        "source_entity_id": subject,
                        "target_entity_id": obj,
                        "relation_type": norm_result.relation_type,
                        "original_predicate": predicate,
                        "source_sentence": source_sentence,
                        "metadata": metadata,
                        "strength": 1.0,
                        "confidence": norm_result.confidence,
                        "valence": norm_result.valence,
                        "intensity": norm_result.intensity,
                        "evidence_count": 1,
                        "status": "active",
                        "created_at": now,
                        "updated_at": now
                    }
                    
        except Exception as e:
            logger.error(f"[GRAPH] Error creating relationship: {e}")
            raise
    
    async def get_relationships(
        self,
        user_id: Optional[str] = None,
        from_entity_id: Optional[str] = None,
        to_entity_id: Optional[str] = None,
        relation_type: Optional[str] = None,
        valence: Optional[str] = None,
        min_confidence: Optional[float] = None,
        min_strength: Optional[float] = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Query relazioni con filtri.
        
        Args:
            user_id: (future) User filter
            from_entity_id: Filter by source entity
            to_entity_id: Filter by target entity
            relation_type: Filter by normalized relation type (sentiment, ownership, etc.)
            valence: Filter by valence (positive, negative, neutral)
            min_confidence: Minimum confidence threshold
            min_strength: Minimum strength threshold
            status: Status filter (default: active)
            limit: Max results
            offset: Pagination offset
            
        Returns:
            {"relationships": [...], "count": N, "total": M}
        """
        db = self._get_db_manager()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                query = "SELECT * FROM relationships WHERE 1=1"
                count_query = "SELECT COUNT(*) FROM relationships WHERE 1=1"
                params = []
                
                if from_entity_id:
                    query += " AND from_entity_id = ?"
                    count_query += " AND from_entity_id = ?"
                    params.append(from_entity_id)
                
                if to_entity_id:
                    query += " AND to_entity_id = ?"
                    count_query += " AND to_entity_id = ?"
                    params.append(to_entity_id)
                
                if relation_type:
                    query += " AND relation_type = ?"
                    count_query += " AND relation_type = ?"
                    params.append(relation_type)
                
                if valence:
                    query += " AND valence = ?"
                    count_query += " AND valence = ?"
                    params.append(valence)
                
                if min_confidence is not None:
                    query += " AND confidence >= ?"
                    count_query += " AND confidence >= ?"
                    params.append(min_confidence)
                
                if min_strength is not None:
                    query += " AND strength >= ?"
                    count_query += " AND strength >= ?"
                    params.append(min_strength)
                
                if status:
                    query += " AND status = ?"
                    count_query += " AND status = ?"
                    params.append(status)
                
                # Get total count
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Add ordering and pagination
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                relationships = [self._row_to_relationship_dict(row) for row in rows]
                
                # Log dettagliato per search
                if relationships:
                    logger.info(
                        f"\n{'-'*60}\n"
                        f"[GRAPH] RELATIONSHIPS SEARCH RESULTS\n"
                        f"{'-'*60}\n"
                        f"  Filters: from={from_entity or 'any'}, to={to_entity or 'any'}, "
                        f"type={relation_type or 'any'}, valence={valence or 'any'}\n"
                        f"  Found: {len(relationships)} (total: {total})\n"
                        + "\n".join([
                            f"    - {r['source_entity_id']} --[{r['relation_type']}/{r['valence']}]--> {r['target_entity_id']}"
                            for r in relationships[:5]
                        ])
                        + (f"\n    ... and {len(relationships)-5} more" if len(relationships) > 5 else "")
                        + f"\n{'-'*60}"
                    )
                else:
                    logger.info(f"[GRAPH] RELATIONSHIPS SEARCH: no results for filters")
                
                return {
                    "relationships": relationships,
                    "count": len(relationships),
                    "total": total
                }
                
        except Exception as e:
            logger.error(f"[GRAPH] Error querying relationships: {e}")
            raise
    
    async def query_relationships(
        self,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        group_by: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Query avanzate con raggruppamento per pattern detection.
        
        Args:
            user_id: (future) User filter
            filters: Filtri da applicare
                {
                    "relation_type": "sentiment",
                    "valence": "positive",
                    "min_confidence": 0.5
                }
            group_by: Campo per raggruppamento (es. "target_type" per raggruppare per tipo target)
            limit: Max results per group
            
        Returns:
            Se group_by:
                {"groups": {"food": [...], "place": [...]}, "total_count": N}
            Altrimenti:
                {"relationships": [...], "count": N}
        """
        db = self._get_db_manager()
        filters = filters or {}
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build base query
                query = """
                    SELECT r.*, e.type as target_type 
                    FROM relationships r
                    LEFT JOIN entities e ON r.to_entity_id = e.entity_id
                    WHERE r.status = 'active'
                """
                params = []
                
                if filters.get("relation_type"):
                    query += " AND r.relation_type = ?"
                    params.append(filters["relation_type"])
                
                if filters.get("valence"):
                    query += " AND r.valence = ?"
                    params.append(filters["valence"])
                
                if filters.get("min_confidence"):
                    query += " AND r.confidence >= ?"
                    params.append(filters["min_confidence"])
                
                if filters.get("min_strength"):
                    query += " AND r.strength >= ?"
                    params.append(filters["min_strength"])
                
                if filters.get("from_entity_id"):
                    query += " AND r.from_entity_id = ?"
                    params.append(filters["from_entity_id"])
                
                query += " ORDER BY r.intensity DESC, r.confidence DESC"
                query += f" LIMIT {limit}"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                if group_by == "target_type":
                    # Raggruppa per tipo di target entity
                    groups = {}
                    for row in rows:
                        target_type = row["target_type"] or "unknown"
                        if target_type not in groups:
                            groups[target_type] = []
                        
                        groups[target_type].append({
                            "target_id": row["to_entity_id"],
                            "intensity": row["intensity"],
                            "confidence": row["confidence"],
                            "strength": row["strength"],
                            "valence": row["valence"],
                            "original_predicate": row["original_predicate"]
                        })
                    
                    return {
                        "groups": groups,
                        "total_count": len(rows)
                    }
                
                else:
                    # Risultati flat
                    relationships = [self._row_to_relationship_dict(row) for row in rows]
                    return {
                        "relationships": relationships,
                        "count": len(relationships)
                    }
                
        except Exception as e:
            logger.error(f"[GRAPH] Error in query_relationships: {e}")
            raise
    
    async def get_relationship(self, rel_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera una singola relazione per ID.
        
        Args:
            rel_id: ID della relazione
            
        Returns:
            Relazione o None se non trovata
        """
        db = self._get_db_manager()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM relationships WHERE rel_id = ?", (rel_id,))
                row = cursor.fetchone()
                
                if row:
                    rel = self._row_to_relationship_dict(row)
                    logger.info(
                        f"\n{'-'*60}\n"
                        f"[GRAPH] RELATIONSHIP RETRIEVED\n"
                        f"{'-'*60}\n"
                        f"  Rel ID:      {rel['id']}\n"
                        f"  From:        {rel['source_entity_id']}\n"
                        f"  To:          {rel['target_entity_id']}\n"
                        f"  Type:        {rel['relation_type']}\n"
                        f"  Valence:     {rel['valence']} (intensity={rel['intensity']})\n"
                        f"  Strength:    {rel['strength']:.2f}\n"
                        f"  Evidence:    {rel['evidence_count']}\n"
                        f"  Predicate:   '{rel.get('original_predicate', '')}'\n"
                        f"{'-'*60}"
                    )
                    return rel
                else:
                    logger.info(f"[GRAPH] Relationship NOT FOUND: {rel_id}")
                return None
                
        except Exception as e:
            logger.error(f"[GRAPH] Error getting relationship: {e}")
            raise
    
    async def update_relationship(
        self,
        rel_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Aggiorna una relazione esistente.
        
        Args:
            rel_id: ID della relazione
            updates: Campi da aggiornare:
                - strength: float (0-1)
                - confidence: float (0-1)
                - valence: str (positive, negative, neutral)
                - intensity: float (0-1)
                - metadata: dict (merge con esistente)
                - status: str (active, archived, deleted)
                
        Returns:
            Relazione aggiornata o None se non trovata
        """
        db = self._get_db_manager()
        now = datetime.utcnow().isoformat() + "Z"
        
        # Campi ammessi per update
        allowed_fields = {
            "strength", "confidence", "valence", "intensity", 
            "status", "source_sentence"
        }
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Verifica che esista
                cursor.execute("SELECT * FROM relationships WHERE rel_id = ?", (rel_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Costruisci UPDATE
                set_clauses = ["updated_at = ?"]
                params = [now]
                
                for field, value in updates.items():
                    if field in allowed_fields:
                        set_clauses.append(f"{field} = ?")
                        params.append(value)
                    elif field == "metadata":
                        # Merge metadata
                        existing_metadata = {}
                        if row["metadata_json"]:
                            try:
                                existing_metadata = json.loads(row["metadata_json"])
                            except:
                                pass
                        existing_metadata.update(value)
                        set_clauses.append("metadata_json = ?")
                        params.append(json.dumps(existing_metadata))
                
                params.append(rel_id)
                
                sql = f"UPDATE relationships SET {', '.join(set_clauses)} WHERE rel_id = ?"
                cursor.execute(sql, params)
                conn.commit()
                
                logger.info(f"[GRAPH] Updated relationship: {rel_id}")
                
                # Ritorna la relazione aggiornata
                cursor.execute("SELECT * FROM relationships WHERE rel_id = ?", (rel_id,))
                row = cursor.fetchone()
                return self._row_to_relationship_dict(row)
                
        except Exception as e:
            logger.error(f"[GRAPH] Error updating relationship: {e}")
            raise
    
    async def delete_relationship(
        self,
        rel_id: str,
        hard_delete: bool = False
    ) -> bool:
        """
        Elimina una relazione.
        
        Args:
            rel_id: ID della relazione
            hard_delete: Se True, elimina fisicamente. Se False, soft delete (status='deleted')
            
        Returns:
            True se eliminata, False se non trovata
        """
        db = self._get_db_manager()
        now = datetime.utcnow().isoformat() + "Z"
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Verifica che esista
                cursor.execute("SELECT rel_id FROM relationships WHERE rel_id = ?", (rel_id,))
                if not cursor.fetchone():
                    return False
                
                if hard_delete:
                    cursor.execute("DELETE FROM relationships WHERE rel_id = ?", (rel_id,))
                    logger.info(f"[GRAPH] Hard deleted relationship: {rel_id}")
                else:
                    cursor.execute(
                        "UPDATE relationships SET status = 'deleted', updated_at = ? WHERE rel_id = ?",
                        (now, rel_id)
                    )
                    logger.info(f"[GRAPH] Soft deleted relationship: {rel_id}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"[GRAPH] Error deleting relationship: {e}")
            raise
    
    async def reinforce_relationship(
        self,
        rel_id: str,
        strength_boost: float = 0.1,
        new_source_sentence: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Rinforza una relazione esistente (aumenta strength e evidence_count).
        
        Usato quando la stessa relazione viene espressa di nuovo.
        
        Args:
            rel_id: ID della relazione
            strength_boost: Incremento strength (default 0.1)
            new_source_sentence: Nuova frase sorgente (opzionale)
            
        Returns:
            Relazione rinforzata o None se non trovata
        """
        db = self._get_db_manager()
        now = datetime.utcnow().isoformat() + "Z"
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Recupera relazione
                cursor.execute("SELECT * FROM relationships WHERE rel_id = ?", (rel_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Calcola nuovi valori
                old_strength = row["strength"]
                old_evidence_count = row["evidence_count"]
                new_strength = min(1.0, row["strength"] + strength_boost)
                new_evidence_count = row["evidence_count"] + 1
                
                # Update
                if new_source_sentence:
                    cursor.execute("""
                        UPDATE relationships 
                        SET strength = ?, evidence_count = ?, last_reinforced = ?, 
                            updated_at = ?, source_sentence = ?
                        WHERE rel_id = ?
                    """, (new_strength, new_evidence_count, now, now, new_source_sentence, rel_id))
                else:
                    cursor.execute("""
                        UPDATE relationships 
                        SET strength = ?, evidence_count = ?, last_reinforced = ?, updated_at = ?
                        WHERE rel_id = ?
                    """, (new_strength, new_evidence_count, now, now, rel_id))
                
                conn.commit()
                
                # Log dettagliato
                source_info = ""
                if new_source_sentence:
                    source_info = f"\n  Source: '{new_source_sentence[:60]}...'"
                
                logger.info(
                    f"[GRAPH] REINFORCED relationship:\n"
                    f"  ID: {rel_id}\n"
                    f"  {row['from_entity_id']} -> {row['to_entity_id']}\n"
                    f"  Type: {row['relation_type']}/{row['valence']}\n"
                    f"  Strength: {old_strength:.2f}->{new_strength:.2f} (+{strength_boost:.2f})\n"
                    f"  Evidence: {old_evidence_count}->{new_evidence_count}{source_info}"
                )
                
                # Ritorna relazione aggiornata
                cursor.execute("SELECT * FROM relationships WHERE rel_id = ?", (rel_id,))
                row = cursor.fetchone()
                return self._row_to_relationship_dict(row)
                
        except Exception as e:
            logger.error(f"[GRAPH] Error reinforcing relationship: {e}")
            raise

    # ==================== RELATIONSHIP EVENT HISTORY ====================
    
    async def get_relationship_events(
        self,
        rel_id: str,
        limit: int = 50,
        order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Recupera la storia degli eventi per una relazione.
        
        Args:
            rel_id: ID della relazione
            limit: Numero massimo di eventi
            order: 'desc' (più recenti prima) o 'asc' (cronologico)
            
        Returns:
            Lista di eventi con predicate, valence, timestamp, etc.
        """
        db = self._get_db_manager()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                order_dir = "DESC" if order == "desc" else "ASC"
                cursor.execute(f"""
                    SELECT * FROM relationship_events 
                    WHERE rel_id = ?
                    ORDER BY timestamp {order_dir}
                    LIMIT ?
                """, (rel_id, limit))
                
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    metadata = {}
                    if row["metadata_json"]:
                        try:
                            metadata = json.loads(row["metadata_json"])
                        except:
                            pass
                    
                    events.append({
                        "event_id": row["event_id"],
                        "rel_id": row["rel_id"],
                        "predicate": row["predicate"],
                        "valence": row["valence"],
                        "intensity": row["intensity"],
                        "source_sentence": row["source_sentence"],
                        "timestamp": row["timestamp"],
                        "normalization_method": row["normalization_method"],
                        "normalization_confidence": row["normalization_confidence"],
                        "metadata": metadata
                    })
                
                return events
                
        except Exception as e:
            logger.error(f"[GRAPH] Error getting relationship events: {e}")
            return []
    
    async def get_relationship_trend(
        self,
        rel_id: str,
        window_size: int = 3
    ) -> Dict[str, Any]:
        """
        Calcola il trend recente di una relazione.
        
        Analizza gli ultimi N eventi per determinare se la relazione
        sta migliorando, peggiorando o è stabile.
        
        Args:
            rel_id: ID della relazione
            window_size: Numero di eventi recenti da analizzare
            
        Returns:
            {
                "current_valence": 0.9,
                "trend": "improving" | "worsening" | "stable" | "volatile",
                "avg_valence": 0.5,
                "change": +0.4,
                "events_analyzed": 3
            }
        """
        db = self._get_db_manager()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Recupera ultimi N eventi
                cursor.execute("""
                    SELECT valence, timestamp FROM relationship_events 
                    WHERE rel_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (rel_id, window_size))
                
                rows = cursor.fetchall()
                
                if not rows:
                    return {
                        "current_valence": None,
                        "trend": "unknown",
                        "avg_valence": None,
                        "change": 0,
                        "events_analyzed": 0
                    }
                
                valences = [row["valence"] for row in rows]
                current = valences[0]  # Più recente
                avg_valence = sum(valences) / len(valences)
                
                # Determina trend
                if len(valences) == 1:
                    trend = "stable"
                    change = 0
                else:
                    oldest = valences[-1]  # Meno recente nella window
                    change = current - oldest
                    
                    # Calcola volatilità
                    if len(valences) >= 2:
                        diffs = [abs(valences[i] - valences[i+1]) for i in range(len(valences)-1)]
                        avg_diff = sum(diffs) / len(diffs)
                    else:
                        avg_diff = 0
                    
                    if avg_diff > 0.5:
                        trend = "volatile"
                    elif change > 0.2:
                        trend = "improving"
                    elif change < -0.2:
                        trend = "worsening"
                    else:
                        trend = "stable"
                
                return {
                    "current_valence": current,
                    "trend": trend,
                    "avg_valence": round(avg_valence, 3),
                    "change": round(change, 3),
                    "events_analyzed": len(valences)
                }
                
        except Exception as e:
            logger.error(f"[GRAPH] Error calculating trend: {e}")
            return {
                "current_valence": None,
                "trend": "error",
                "avg_valence": None,
                "change": 0,
                "events_analyzed": 0
            }
    
    async def get_relationship_volatility(
        self,
        rel_id: str
    ) -> Dict[str, Any]:
        """
        Calcola la volatilità di una relazione (quanto cambia nel tempo).
        
        Una relazione stabile ha volatilità bassa.
        Una relazione instabile (amore/odio) ha volatilità alta.
        
        Args:
            rel_id: ID della relazione
            
        Returns:
            {
                "volatility": 0.0-1.0 (0=stabile, 1=molto instabile),
                "stddev": standard deviation of valences,
                "sign_changes": numero di volte che il segno è cambiato,
                "total_events": numero totale di eventi,
                "interpretation": "stable" | "fluctuating" | "highly_unstable"
            }
        """
        db = self._get_db_manager()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Recupera tutti gli eventi
                cursor.execute("""
                    SELECT valence FROM relationship_events 
                    WHERE rel_id = ?
                    ORDER BY timestamp ASC
                """, (rel_id,))
                
                rows = cursor.fetchall()
                
                if len(rows) < 2:
                    return {
                        "volatility": 0.0,
                        "stddev": 0.0,
                        "sign_changes": 0,
                        "total_events": len(rows),
                        "interpretation": "insufficient_data"
                    }
                
                valences = [row["valence"] for row in rows]
                
                # Calcola standard deviation
                mean = sum(valences) / len(valences)
                variance = sum((v - mean) ** 2 for v in valences) / len(valences)
                stddev = variance ** 0.5
                
                # Conta cambi di segno (positivo ↔ negativo)
                sign_changes = 0
                for i in range(1, len(valences)):
                    if (valences[i-1] >= 0) != (valences[i] >= 0):
                        sign_changes += 1
                
                # Normalizza volatilità (0-1)
                # stddev max teorico = 1.0 (oscillazione -1 a +1)
                volatility = min(1.0, stddev)
                
                # Bonus per sign_changes
                sign_change_ratio = sign_changes / (len(valences) - 1) if len(valences) > 1 else 0
                volatility = min(1.0, volatility + sign_change_ratio * 0.3)
                
                # Interpretazione
                if volatility < 0.2:
                    interpretation = "stable"
                elif volatility < 0.5:
                    interpretation = "fluctuating"
                else:
                    interpretation = "highly_unstable"
                
                return {
                    "volatility": round(volatility, 3),
                    "stddev": round(stddev, 3),
                    "sign_changes": sign_changes,
                    "total_events": len(valences),
                    "interpretation": interpretation
                }
                
        except Exception as e:
            logger.error(f"[GRAPH] Error calculating volatility: {e}")
            return {
                "volatility": 0.0,
                "stddev": 0.0,
                "sign_changes": 0,
                "total_events": 0,
                "interpretation": "error"
            }

    async def apply_decay(
        self,
        user_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger decay service.
        
        Args:
            user_id: (future) Apply only to specific user
            options: Override decay configuration
            
        Returns:
            Decay results
        """
        return await self.decay_service.apply_decay(user_id=user_id, options=options)
    
    def get_normalizer_stats(self) -> Dict[str, Any]:
        """Get predicate normalizer statistics"""
        return self.normalizer.get_stats()
    
    def get_decay_stats(self) -> Dict[str, Any]:
        """Get decay service statistics"""
        return self.decay_service.get_stats()
    
    def _row_to_relationship_dict(self, row) -> Dict[str, Any]:
        """Convert SQLite row to relationship dict"""
        metadata = {}
        if row["metadata_json"]:
            try:
                metadata = json.loads(row["metadata_json"])
            except:
                pass
        
        return {
            "id": row["rel_id"],
            "source_entity_id": row["from_entity_id"],
            "target_entity_id": row["to_entity_id"],
            "relation_type": row["relation_type"] or row["type"],
            "original_predicate": row["original_predicate"] or row["type"],
            "source_sentence": row["source_sentence"],
            "metadata": metadata,
            "strength": row["strength"],
            "confidence": row["confidence"] if "confidence" in row.keys() else 0.8,
            "valence": row["valence"] if "valence" in row.keys() else "neutral",
            "intensity": row["intensity"] if "intensity" in row.keys() else 0.5,
            "evidence_count": row["evidence_count"] if "evidence_count" in row.keys() else 1,
            "trust": row["trust"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_reinforced": row["last_reinforced"] if "last_reinforced" in row.keys() else None
        }
    
    def _row_to_entity_dict(self, row) -> Dict[str, Any]:
        """Convert SQLite row to entity dict"""
        aliases = []
        identifiers = {}
        attributes = {}
        tags = []
        
        try:
            if row["aliases_json"]:
                aliases = json.loads(row["aliases_json"])
            if row["identifiers_json"]:
                identifiers = json.loads(row["identifiers_json"])
            if row["attributes_json"]:
                attributes = json.loads(row["attributes_json"])
            if row["tags_json"]:
                tags = json.loads(row["tags_json"])
        except:
            pass
        
        return {
            "entity_id": row["entity_id"],
            "type": row["type"],
            "primary_name": row["primary_name"],
            "aliases": aliases,
            "identifiers": identifiers,
            "attributes": attributes,
            "salience": row["salience"],
            "confidence": row["confidence"],
            "status": row["status"],
            "tags": tags,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    
    def _generate_entity_id(self, name: str, entity_type: str) -> str:
        """
        Genera un ID univoco per un'entità basato sul nome e tipo.
        
        Args:
            name: Nome grezzo dell'entità
            entity_type: Tipo dell'entità
            
        Returns:
            ID normalizzato (es. "person:fabrizio_rossi")
        """
        # Normalizza il nome
        normalized = name.lower().strip()
        normalized = normalized.replace(" ", "_")
        normalized = "".join(c for c in normalized if c.isalnum() or c == "_")
        
        # Prefisso tipo
        type_prefix = entity_type.lower() if entity_type else "entity"
        
        return f"{type_prefix}:{normalized}"
    
    async def create_entity(
        self,
        name: str,
        entity_type: str = "auto",
        aliases: Optional[List[str]] = None,
        identifiers: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8,
        source: str = "extraction",
        context: str = "",
        hints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crea una nuova entità nel Knowledge Graph.
        
        Il tipo può essere:
        - Specificato esplicitamente (person, organization, location, etc.)
        - "auto" → inferito automaticamente dall'EntityTypeNormalizer
        
        Args:
            name: Nome primario dell'entità (es. "Fabrizio Rossi")
            entity_type: Tipo entità o "auto" per inferenza automatica
            aliases: Nomi alternativi (es. ["Fab", "Fabrizio"])
            identifiers: Identificatori univoci (email, phone, user_id)
            attributes: Attributi aggiuntivi
            confidence: Confidence score
            source: Fonte (extraction, user_declared, inferred)
            context: Contesto opzionale (frase in cui appare l'entità)
            hints: Hint opzionali da Thalamus (es. {"category": "soggetto"})
            
        Returns:
            Entità creata con metadati di normalizzazione se auto-inferita
        """
        db = self._get_db_manager()
        
        # ===== AUTO-INFERENZA TIPO =====
        type_inference_metadata = None
        if entity_type == "auto" or entity_type is None:
            type_result = self.entity_type_normalizer.infer_type(
                entity_name=name,
                context=context,
                hints=hints
            )
            entity_type = type_result.entity_type.value
            type_inference_metadata = {
                "inferred_type": type_result.entity_type.value,
                "inference_confidence": type_result.confidence,
                "inference_method": type_result.method,
                "inference_signals": type_result.signals,
                "alternative_types": [
                    {"type": t.value, "confidence": c} 
                    for t, c in type_result.alternative_types
                ]
            }
            logger.info(
                f"[GRAPH] Auto-inferred type for '{name}': "
                f"{entity_type} (confidence={type_result.confidence:.2f}, method={type_result.method})"
            )
        
        # Genera ID
        entity_id = self._generate_entity_id(name, entity_type)
        now = datetime.utcnow().isoformat() + "Z"
        
        # Se c'è metadata di inferenza, aggiungilo agli attributes
        if type_inference_metadata:
            if attributes is None:
                attributes = {}
            attributes["_type_inference"] = type_inference_metadata
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check se esiste già
                cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Entità esistente: aggiorna/arricchisci
                    existing_aliases = json.loads(existing["aliases_json"] or "[]")
                    existing_identifiers = json.loads(existing["identifiers_json"] or "{}")
                    existing_attributes = json.loads(existing["attributes_json"] or "{}")
                    
                    # Merge aliases
                    if aliases:
                        existing_aliases = list(set(existing_aliases + aliases))
                    
                    # Merge identifiers (nuovi sovrascrivono)
                    if identifiers:
                        existing_identifiers.update(identifiers)
                    
                    # Merge attributes
                    if attributes:
                        existing_attributes.update(attributes)
                    
                    # Aggiorna confidence se maggiore
                    new_confidence = max(existing["confidence"], confidence)
                    
                    cursor.execute("""
                        UPDATE entities 
                        SET aliases_json = ?, identifiers_json = ?, attributes_json = ?,
                            confidence = ?, updated_at = ?
                        WHERE entity_id = ?
                    """, (
                        json.dumps(existing_aliases),
                        json.dumps(existing_identifiers),
                        json.dumps(existing_attributes),
                        new_confidence,
                        now,
                        entity_id
                    ))
                    
                    conn.commit()
                    
                    logger.info(
                        f"\n{'*'*60}\n"
                        f"[GRAPH] ENTITY UPDATED (MERGED)\n"
                        f"{'*'*60}\n"
                        f"  Entity ID:   {entity_id}\n"
                        f"  Name:        {name}\n"
                        f"  Type:        {entity_type}\n"
                        f"  Aliases:     {existing_aliases if existing_aliases else 'none'}\n"
                        f"  Identifiers: {list(existing_identifiers.keys()) if existing_identifiers else 'none'}\n"
                        f"  Confidence:  {existing['confidence']:.2f} -> {new_confidence:.2f}\n"
                        f"{'*'*60}"
                    )
                    
                    cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
                    row = cursor.fetchone()
                    return self._row_to_entity_dict(row)
                
                else:
                    # Nuova entità
                    cursor.execute("""
                        INSERT INTO entities (
                            entity_id, type, primary_name, aliases_json, identifiers_json,
                            attributes_json, salience, confidence, status, tags_json,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entity_id,
                        entity_type,
                        name,
                        json.dumps(aliases or []),
                        json.dumps(identifiers or {}),
                        json.dumps(attributes or {}),
                        0.5,  # salience iniziale
                        confidence,
                        "active",
                        json.dumps([]),  # tags
                        now, now
                    ))
                    
                    conn.commit()
                    
                    # Prepara log per type inference
                    type_info = f" ({entity_type})"
                    if type_inference_metadata:
                        type_info = f" ({entity_type}, auto-inferred via {type_inference_metadata['inference_method']}, conf={type_inference_metadata['inference_confidence']:.2f})"
                    
                    logger.info(
                        f"\n{'+'*60}\n"
                        f"[GRAPH] NEW ENTITY CREATED\n"
                        f"{'+'*60}\n"
                        f"  Entity ID:   {entity_id}\n"
                        f"  Name:        {name}\n"
                        f"  Type:        {type_info}\n"
                        f"  Aliases:     {aliases if aliases else 'none'}\n"
                        f"  Identifiers: {list(identifiers.keys()) if identifiers else 'none'}\n"
                        f"  Confidence:  {confidence:.2f}\n"
                        f"  Source:      {source}\n"
                        f"{'+'*60}"
                    )
                    
                    return {
                        "entity_id": entity_id,
                        "type": entity_type,
                        "primary_name": name,
                        "aliases": aliases or [],
                        "identifiers": identifiers or {},
                        "attributes": attributes or {},
                        "salience": 0.5,
                        "confidence": confidence,
                        "status": "active",
                        "tags": [],
                        "created_at": now,
                        "updated_at": now
                    }
                    
        except Exception as e:
            logger.error(f"[GRAPH] Error creating entity: {e}")
            raise
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera un'entità per ID.
        
        Args:
            entity_id: ID dell'entità
            
        Returns:
            Entità o None se non trovata
        """
        db = self._get_db_manager()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
                row = cursor.fetchone()
                
                if row:
                    entity = self._row_to_entity_dict(row)
                    logger.info(
                        f"\n{'-'*60}\n"
                        f"[GRAPH] ENTITY RETRIEVED\n"
                        f"{'-'*60}\n"
                        f"  Entity ID:   {entity['entity_id']}\n"
                        f"  Name:        {entity['primary_name']}\n"
                        f"  Type:        {entity['type']}\n"
                        f"  Aliases:     {entity.get('aliases', [])}\n"
                        f"  Identifiers: {list(entity.get('identifiers', {}).keys())}\n"
                        f"  Confidence:  {entity.get('confidence', 0):.2f}\n"
                        f"  Salience:    {entity.get('salience', 0):.2f}\n"
                        f"{'-'*60}"
                    )
                    return entity
                else:
                    logger.info(f"[GRAPH] Entity NOT FOUND: {entity_id}")
                return None
                
        except Exception as e:
            logger.error(f"[GRAPH] Error getting entity: {e}")
            raise
    
    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        include_aliases: bool = True,
        min_confidence: float = 0.0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Cerca entità per nome (con match parziale).
        
        Args:
            query: Stringa di ricerca (es. "Fabri")
            entity_type: Filtra per tipo (person, place, etc.)
            include_aliases: Cerca anche negli alias
            min_confidence: Soglia minima confidence
            limit: Numero massimo risultati
            
        Returns:
            {"entities": [...], "count": N, "exact_match": entity|None}
        """
        db = self._get_db_manager()
        query_lower = query.lower().strip()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Query base con LIKE per match parziale
                sql = """
                    SELECT * FROM entities 
                    WHERE status = 'active' 
                    AND confidence >= ?
                    AND (
                        LOWER(primary_name) LIKE ?
                        OR LOWER(entity_id) LIKE ?
                """
                params = [min_confidence, f"%{query_lower}%", f"%{query_lower}%"]
                
                if include_aliases:
                    sql += " OR LOWER(aliases_json) LIKE ?"
                    params.append(f"%{query_lower}%")
                
                sql += ")"
                
                if entity_type:
                    sql += " AND type = ?"
                    params.append(entity_type)
                
                sql += " ORDER BY confidence DESC, salience DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                entities = [self._row_to_entity_dict(row) for row in rows]
                
                # Cerca match esatto
                exact_match = None
                for entity in entities:
                    if entity["primary_name"].lower() == query_lower:
                        exact_match = entity
                        break
                    # Check aliases
                    for alias in entity.get("aliases", []):
                        if alias.lower() == query_lower:
                            exact_match = entity
                            break
                
                # Log dettagliato per search
                if entities:
                    logger.info(
                        f"\n{'-'*60}\n"
                        f"[GRAPH] ENTITIES SEARCH RESULTS\n"
                        f"{'-'*60}\n"
                        f"  Query: '{query}' (type={entity_type or 'any'})\n"
                        f"  Found: {len(entities)} entities\n"
                        + "\n".join([
                            f"    - {e['entity_id']} | {e['primary_name']} ({e['type']}) conf={e['confidence']:.2f}"
                            for e in entities[:5]
                        ])
                        + (f"\n    ... and {len(entities)-5} more" if len(entities) > 5 else "")
                        + (f"\n  EXACT MATCH: {exact_match['entity_id']}" if exact_match else "")
                        + f"\n{'-'*60}"
                    )
                else:
                    logger.info(f"[GRAPH] ENTITIES SEARCH: no results for '{query}'")
                
                return {
                    "entities": entities,
                    "count": len(entities),
                    "exact_match": exact_match
                }
                
        except Exception as e:
            logger.error(f"[GRAPH] Error searching entities: {e}")
            raise
    
    async def find_or_create_entity(
        self,
        name: str,
        entity_type: str,
        aliases: Optional[List[str]] = None,
        identifiers: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        confidence: float = 0.8
    ) -> Dict[str, Any]:
        """
        Cerca un'entità per nome, la crea se non esiste.
        
        Questo è il metodo principale che Mind dovrebbe usare.
        
        Args:
            name: Nome dell'entità (es. "Fabrizio")
            entity_type: Tipo (person, place, thing, etc.)
            aliases, identifiers, attributes, confidence: come create_entity
            
        Returns:
            {"entity": {...}, "created": bool, "matched_by": "exact|alias|partial|created"}
        """
        # Prima cerca match esatto
        search_result = await self.search_entities(
            query=name,
            entity_type=entity_type,
            include_aliases=True,
            min_confidence=0.3,
            limit=5
        )
        
        if search_result["exact_match"]:
            # Match esatto trovato
            entity = search_result["exact_match"]
            
            # Arricchisci con nuovi dati se forniti
            if aliases or identifiers or attributes:
                entity = await self.create_entity(
                    name=entity["primary_name"],
                    entity_type=entity["type"],
                    aliases=aliases,
                    identifiers=identifiers,
                    attributes=attributes,
                    confidence=confidence
                )
            
            return {
                "entity": entity,
                "created": False,
                "matched_by": "exact"
            }
        
        # Cerca match parziale con alta confidence
        if search_result["entities"]:
            # Il primo risultato ha la confidence più alta
            best_match = search_result["entities"][0]
            
            # Se il match è buono (nome inizia con query o contiene query)
            name_lower = name.lower()
            best_name_lower = best_match["primary_name"].lower()
            
            if (best_name_lower.startswith(name_lower) or 
                name_lower.startswith(best_name_lower) or
                best_match["confidence"] > 0.7):
                return {
                    "entity": best_match,
                    "created": False,
                    "matched_by": "partial"
                }
        
        # Nessun match: crea nuova entità
        entity = await self.create_entity(
            name=name,
            entity_type=entity_type,
            aliases=aliases,
            identifiers=identifiers,
            attributes=attributes,
            confidence=confidence
        )
        
        return {
            "entity": entity,
            "created": True,
            "matched_by": "created"
        }
    
    async def resolve_entity(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        user_id: str = "default",
        context_hint: Optional[str] = None,
        include_episodic: bool = True,
        include_semantic: bool = True,
        include_relationships: bool = True,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        Risolve un'entità cercando in tutte le memorie persistenti.
        
        Questo metodo è il cuore della risoluzione entità. Mind chiama questo
        endpoint dopo aver cercato nella Working Memory (che è volatile).
        
        Ordine di ricerca:
        1. Entity Graph - entità persistenti (nome + alias)
        2. Relationships - entità menzionate in relazioni
        3. Episodic Memory - conversazioni passate (se abilitato)
        4. Semantic Memory - documenti e conoscenze (se abilitato)
        
        Args:
            entity_name: Nome dell'entità da risolvere (es. "Fabrizio")
            entity_type: Tipo probabile (person, place, thing, food, etc.)
            user_id: User identifier
            context_hint: Contesto aggiuntivo per disambiguazione
            include_episodic: Cerca anche in Episodic Memory
            include_semantic: Cerca anche in Semantic Memory
            include_relationships: Cerca anche nelle relazioni
            min_confidence: Soglia minima per considerare un match valido
            
        Returns:
            {
                "resolved": bool,
                "entity": {...} | None,
                "candidates": [...],  # Altri possibili match
                "source": "entity_graph" | "relationships" | "episodic" | "semantic" | "not_found",
                "confidence": float,
                "context": str | None  # Contesto trovato
            }
        """
        logger.info(f"[RESOLVE] Resolving entity: '{entity_name}' (type={entity_type})")
        
        candidates = []
        db = self._get_db_manager()
        
        # ===== STEP 1: Entity Graph (entità persistenti) =====
        logger.info(f"[RESOLVE] Step 1: Searching Entity Graph...")
        
        search_result = await self.search_entities(
            query=entity_name,
            entity_type=entity_type,
            include_aliases=True,
            min_confidence=min_confidence,
            limit=5
        )
        
        if search_result["exact_match"]:
            entity = search_result["exact_match"]
            logger.info(f"[RESOLVE] EXACT MATCH in Entity Graph: {entity['entity_id']}")
            return {
                "resolved": True,
                "entity": entity,
                "candidates": [],
                "source": "entity_graph",
                "confidence": entity["confidence"],
                "context": f"Entità conosciuta: {entity['primary_name']} ({entity['type']})"
            }
        
        # Aggiungi candidati parziali
        for entity in search_result["entities"]:
            candidates.append({
                "entity": entity,
                "source": "entity_graph",
                "confidence": entity["confidence"],
                "match_type": "partial"
            })
        
        # ===== STEP 2: Relationships (entità in relazioni) =====
        if include_relationships:
            logger.info(f"[RESOLVE] Step 2: Searching Relationships...")
            
            try:
                with db._get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Cerca nelle relazioni come source o target
                    entity_name_lower = entity_name.lower()
                    cursor.execute("""
                        SELECT DISTINCT 
                            CASE 
                                WHEN LOWER(from_entity_id) LIKE ? THEN from_entity_id
                                WHEN LOWER(to_entity_id) LIKE ? THEN to_entity_id
                            END as found_entity_id,
                            source_sentence,
                            confidence
                        FROM relationships
                        WHERE status = 'active'
                        AND (LOWER(from_entity_id) LIKE ? OR LOWER(to_entity_id) LIKE ?)
                        ORDER BY confidence DESC
                        LIMIT 5
                    """, (
                        f"%{entity_name_lower}%", f"%{entity_name_lower}%",
                        f"%{entity_name_lower}%", f"%{entity_name_lower}%"
                    ))
                    
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        if row["found_entity_id"]:
                            # Recupera l'entità completa
                            entity = await self.get_entity(row["found_entity_id"])
                            if entity:
                                # Check match esatto
                                if entity["primary_name"].lower() == entity_name_lower:
                                    logger.info(f"[RESOLVE] MATCH in Relationships: {entity['entity_id']}")
                                    return {
                                        "resolved": True,
                                        "entity": entity,
                                        "candidates": candidates,
                                        "source": "relationships",
                                        "confidence": row["confidence"],
                                        "context": f"Menzionato in: '{row['source_sentence'][:80]}'" if row["source_sentence"] else None
                                    }
                                else:
                                    # Candidato parziale
                                    candidates.append({
                                        "entity": entity,
                                        "source": "relationships",
                                        "confidence": row["confidence"] * 0.9,
                                        "match_type": "partial",
                                        "context": row["source_sentence"][:80] if row["source_sentence"] else None
                                    })
                                    
            except Exception as e:
                logger.warning(f"[RESOLVE] Relationship search failed: {e}")
        
        # ===== STEP 3: Episodic Memory (conversazioni passate) =====
        if include_episodic:
            logger.info(f"[RESOLVE] Step 3: Searching Episodic Memory...")
            
            try:
                # Cerca usando il vectorstore per similarity search
                from app.core.vectordb_manager import get_vectordb_manager
                vectordb = get_vectordb_manager()
                
                # Query semantica per trovare menzioni dell'entità
                query_text = f"{entity_name}"
                if context_hint:
                    query_text = f"{entity_name} {context_hint}"
                
                results = vectordb.query_documents(
                    query_text=query_text,
                    n_results=5,
                    where={"type": "episodic"} if entity_type else None
                )
                
                if results and results.get("documents"):
                    for i, doc in enumerate(results["documents"][0][:3]):
                        distance = results["distances"][0][i] if results.get("distances") else 1.0
                        similarity = 1 - distance  # Converti distanza in similarity
                        
                        if similarity >= min_confidence:
                            # Check se il documento menziona l'entità
                            if entity_name.lower() in doc.lower():
                                logger.info(f"[RESOLVE] Found in Episodic: sim={similarity:.2f}")
                                candidates.append({
                                    "entity": None,  # Non è un'entità strutturata
                                    "source": "episodic",
                                    "confidence": similarity,
                                    "match_type": "mention",
                                    "context": doc[:150]
                                })
                                
            except Exception as e:
                logger.warning(f"[RESOLVE] Episodic search failed: {e}")
        
        # ===== STEP 4: Semantic Memory (documenti e conoscenze) =====
        if include_semantic:
            logger.info(f"[RESOLVE] Step 4: Searching Semantic Memory...")
            
            try:
                from app.core.vectordb_manager import get_vectordb_manager
                vectordb = get_vectordb_manager()
                
                query_text = f"{entity_name}"
                if context_hint:
                    query_text = f"{entity_name} {context_hint}"
                
                results = vectordb.query_documents(
                    query_text=query_text,
                    n_results=5,
                    where={"type": "semantic"} if entity_type else None
                )
                
                if results and results.get("documents"):
                    for i, doc in enumerate(results["documents"][0][:3]):
                        distance = results["distances"][0][i] if results.get("distances") else 1.0
                        similarity = 1 - distance
                        
                        if similarity >= min_confidence and entity_name.lower() in doc.lower():
                            logger.info(f"[RESOLVE] Found in Semantic: sim={similarity:.2f}")
                            candidates.append({
                                "entity": None,
                                "source": "semantic",
                                "confidence": similarity,
                                "match_type": "mention",
                                "context": doc[:150]
                            })
                            
            except Exception as e:
                logger.warning(f"[RESOLVE] Semantic search failed: {e}")
        
        # ===== Valutazione finale =====
        
        # Ordina candidati per confidence
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Se abbiamo un candidato con alta confidence, consideralo risolto
        if candidates and candidates[0]["confidence"] >= 0.8:
            best = candidates[0]
            logger.info(f"[RESOLVE] Best candidate accepted (conf={best['confidence']:.2f})")
            
            return {
                "resolved": True,
                "entity": best.get("entity"),
                "candidates": candidates[1:5],  # Altri candidati
                "source": best["source"],
                "confidence": best["confidence"],
                "context": best.get("context")
            }
        
        # Nessun match definitivo
        logger.info(f"[RESOLVE] Entity NOT RESOLVED: '{entity_name}' - {len(candidates)} candidates found")
        
        return {
            "resolved": False,
            "entity": None,
            "candidates": candidates[:5],
            "source": "not_found",
            "confidence": 0.0,
            "context": None,
            "suggested_action": "ask_user" if not candidates else "choose_from_candidates"
        }
    
    # ==================== Entity Disambiguation ====================
    
    async def disambiguate_entity(
        self,
        name: str,
        entity_type: Optional[str] = None,
        related_entities: Optional[List[str]] = None,
        expected_relations: Optional[List[Dict[str, Any]]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        context_sentence: Optional[str] = None,
        min_confidence: float = 0.2,
        max_results: int = 5,
        ambiguity_threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Disambigua un'entita basandosi su nome, attributi e relazioni.
        
        A differenza di resolve_entity che cerca di trovare UN'entita definitiva,
        questo metodo restituisce TUTTI i candidati con scoring dettagliato
        e RILEVA INCOERENZE tra le informazioni attese e quelle nel grafo.
        
        Algoritmo di scoring:
        1. Base score da match nome (exact=1.0, partial=0.6, alias=0.8)
        2. Bonus per ogni relazione matchata con related_entities (+0.2 ciascuna)
        3. Bonus per expected_relations verificate (+0.25 se match, incoerenza se diverso)
        4. Bonus per ogni attributo matchato (+0.1 ciascuno)
        5. Bonus da similarita semantica con context_sentence (+0.15 max)
        
        Args:
            name: Nome da cercare (es. "Fabrizio")
            entity_type: Tipo atteso (opzionale)
            related_entities: Lista di entity_id con cui l'entita cercata ha relazioni
            expected_relations: Lista di relazioni attese con target specifico per verifica coerenza
                               [{"relation_type": "sibling", "target_name": "Maria"}]
            attributes: Attributi attesi
            context_sentence: Frase di contesto per semantic matching
            min_confidence: Soglia minima per includere un candidato
            max_results: Numero massimo di candidati da ritornare
            ambiguity_threshold: Se top 2 hanno diff < threshold, risultato e ambiguo
            
        Returns:
            {
                "query_name": str,
                "total_candidates": int,
                "ambiguous": bool,
                "has_inconsistencies": bool,
                "best_match": {...} or None,
                "candidates": [...],
                "disambiguation_context": {...}
            }
        """
        db = self._get_db_manager()
        name_lower = name.lower().strip()
        candidates = []
        
        logger.info(f"[DISAMBIGUATE] Starting disambiguation for '{name}'")
        logger.info(f"[DISAMBIGUATE]   Type filter: {entity_type}")
        logger.info(f"[DISAMBIGUATE]   Related entities: {related_entities}")
        logger.info(f"[DISAMBIGUATE]   Expected relations: {expected_relations}")
        logger.info(f"[DISAMBIGUATE]   Attributes: {attributes}")
        logger.info(f"[DISAMBIGUATE]   Context: '{context_sentence[:50]}...'" if context_sentence else "[DISAMBIGUATE]   Context: None")
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # ===== STEP 1: Cerca candidati per nome =====
                sql = """
                    SELECT * FROM entities 
                    WHERE status = 'active' 
                    AND (
                        LOWER(primary_name) LIKE ?
                        OR LOWER(entity_id) LIKE ?
                        OR LOWER(aliases_json) LIKE ?
                    )
                """
                params = [f"%{name_lower}%", f"%{name_lower}%", f"%{name_lower}%"]
                
                if entity_type:
                    sql += " AND type = ?"
                    params.append(entity_type)
                
                sql += " ORDER BY confidence DESC, salience DESC LIMIT 50"
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                logger.info(f"[DISAMBIGUATE] Found {len(rows)} initial candidates by name")
                
                # ===== STEP 2: Calcola score per ogni candidato =====
                for row in rows:
                    entity = self._row_to_entity_dict(row)
                    entity_id = entity["entity_id"]
                    primary_name = entity["primary_name"].lower()
                    aliases = [a.lower() for a in entity.get("aliases", [])]
                    
                    score = 0.0
                    match_reasons = []
                    matching_relations = []
                    inconsistencies = []
                    
                    # --- Score da nome ---
                    if primary_name == name_lower:
                        score += 1.0
                        match_reasons.append("name_exact")
                    elif name_lower in primary_name or primary_name in name_lower:
                        score += 0.6
                        match_reasons.append("name_partial")
                    
                    # Check alias
                    for alias in aliases:
                        if alias == name_lower:
                            score += 0.8
                            match_reasons.append(f"alias_exact:{alias}")
                            break
                        elif name_lower in alias or alias in name_lower:
                            score += 0.4
                            match_reasons.append(f"alias_partial:{alias}")
                            break
                    
                    # --- Score da related_entities (lista semplice di entity_id) ---
                    if related_entities:
                        for rel_entity_id in related_entities:
                            cursor.execute("""
                                SELECT rel_id, relation_type, valence, to_entity_id, from_entity_id
                                FROM relationships
                                WHERE status = 'active'
                                AND (
                                    (from_entity_id = ? AND to_entity_id = ?)
                                    OR (from_entity_id = ? AND to_entity_id = ?)
                                )
                            """, (entity_id, rel_entity_id, rel_entity_id, entity_id))
                            
                            rel_rows = cursor.fetchall()
                            if rel_rows:
                                for rel_row in rel_rows:
                                    score += 0.2
                                    match_reasons.append(f"relation_match:{rel_entity_id}")
                                    matching_relations.append({
                                        "rel_id": rel_row["rel_id"],
                                        "relation_type": rel_row["relation_type"],
                                        "valence": rel_row["valence"],
                                        "target": rel_row["to_entity_id"] if rel_row["from_entity_id"] == entity_id else rel_row["from_entity_id"]
                                    })
                    
                    # --- Score da expected_relations (con verifica coerenza) ---
                    if expected_relations:
                        for exp_rel in expected_relations:
                            rel_type = exp_rel.get("relation_type", "").lower()
                            expected_target_name = exp_rel.get("target_name", "").lower() if exp_rel.get("target_name") else None
                            expected_target_id = exp_rel.get("target_entity_id")
                            
                            # Cerca relazioni di questo tipo per questa entita
                            cursor.execute("""
                                SELECT r.rel_id, r.relation_type, r.valence, r.to_entity_id, r.from_entity_id,
                                       e.primary_name as target_name, e.entity_id as target_entity_id
                                FROM relationships r
                                JOIN entities e ON (
                                    CASE 
                                        WHEN r.from_entity_id = ? THEN r.to_entity_id = e.entity_id
                                        ELSE r.from_entity_id = e.entity_id
                                    END
                                )
                                WHERE r.status = 'active'
                                AND (r.from_entity_id = ? OR r.to_entity_id = ?)
                                AND LOWER(r.relation_type) = ?
                            """, (entity_id, entity_id, entity_id, rel_type))
                            
                            found_rels = cursor.fetchall()
                            
                            if found_rels:
                                # Relazione di questo tipo esiste
                                found_match = False
                                for found_rel in found_rels:
                                    # Determina il target effettivo
                                    if found_rel["from_entity_id"] == entity_id:
                                        actual_target_id = found_rel["to_entity_id"]
                                    else:
                                        actual_target_id = found_rel["from_entity_id"]
                                    
                                    # Recupera info sul target
                                    cursor.execute("""
                                        SELECT entity_id, primary_name, aliases_json 
                                        FROM entities WHERE entity_id = ?
                                    """, (actual_target_id,))
                                    target_row = cursor.fetchone()
                                    
                                    if target_row:
                                        actual_target_name = target_row["primary_name"].lower()
                                        target_aliases = []
                                        if target_row["aliases_json"]:
                                            try:
                                                target_aliases = [a.lower() for a in json.loads(target_row["aliases_json"])]
                                            except:
                                                pass
                                        
                                        # Verifica match
                                        target_matches = False
                                        if expected_target_id and actual_target_id == expected_target_id:
                                            target_matches = True
                                        elif expected_target_name:
                                            if expected_target_name == actual_target_name:
                                                target_matches = True
                                            elif expected_target_name in actual_target_name or actual_target_name in expected_target_name:
                                                target_matches = True
                                            elif expected_target_name in target_aliases:
                                                target_matches = True
                                        
                                        if target_matches:
                                            # Match confermato!
                                            found_match = True
                                            score += 0.25
                                            match_reasons.append(f"expected_relation_confirmed:{rel_type}={target_row['primary_name']}")
                                            matching_relations.append({
                                                "rel_id": found_rel["rel_id"],
                                                "relation_type": rel_type,
                                                "valence": found_rel["valence"],
                                                "target": actual_target_id,
                                                "verified": True
                                            })
                                            break
                                
                                # Se relazione esiste ma target diverso -> INCOERENZA
                                if not found_match and expected_target_name:
                                    # Prendi il primo target trovato per segnalare l'incoerenza
                                    cursor.execute("""
                                        SELECT entity_id, primary_name FROM entities 
                                        WHERE entity_id = ?
                                    """, (found_rels[0]["to_entity_id"] if found_rels[0]["from_entity_id"] == entity_id else found_rels[0]["from_entity_id"],))
                                    actual_target_row = cursor.fetchone()
                                    
                                    if actual_target_row:
                                        inconsistencies.append({
                                            "relation_type": rel_type,
                                            "expected_target": exp_rel.get("target_name", ""),
                                            "found_target": actual_target_row["primary_name"],
                                            "found_entity_id": actual_target_row["entity_id"],
                                            "message": f"Relazione '{rel_type}' esiste ma con target diverso: atteso '{exp_rel.get('target_name')}', trovato '{actual_target_row['primary_name']}'"
                                        })
                                        logger.warning(f"[DISAMBIGUATE] INCONSISTENCY for {entity_id}: {rel_type} -> expected '{exp_rel.get('target_name')}', found '{actual_target_row['primary_name']}'")
                                        # Piccolo bonus perche comunque la relazione esiste
                                        score += 0.1
                                        match_reasons.append(f"expected_relation_exists_different_target:{rel_type}")
                    
                    # --- Score da attributi ---
                    if attributes:
                        entity_attrs = entity.get("attributes", {})
                        for attr_key, attr_value in attributes.items():
                            if attr_key in entity_attrs:
                                if str(entity_attrs[attr_key]).lower() == str(attr_value).lower():
                                    score += 0.15
                                    match_reasons.append(f"attribute_match:{attr_key}")
                                elif str(attr_value).lower() in str(entity_attrs[attr_key]).lower():
                                    score += 0.08
                                    match_reasons.append(f"attribute_partial:{attr_key}")
                    
                    # --- Score da context_sentence (semantic similarity) ---
                    if context_sentence and score > 0:
                        try:
                            from chromadb.utils import embedding_functions
                            emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                                model_name='paraphrase-multilingual-MiniLM-L12-v2',
                                normalize_embeddings=True
                            )
                            
                            entity_desc = f"{entity['primary_name']} ({entity['type']})"
                            emb_context = emb_fn([context_sentence])[0]
                            emb_entity = emb_fn([entity_desc])[0]
                            
                            similarity = sum(a * b for a, b in zip(emb_context, emb_entity))
                            
                            if similarity > 0.5:
                                bonus = min(0.15, (similarity - 0.5) * 0.3)
                                score += bonus
                                match_reasons.append(f"context_similarity:{similarity:.2f}")
                        except Exception as e:
                            logger.warning(f"[DISAMBIGUATE] Context similarity failed: {e}")
                    
                    # Normalizza score
                    normalized_score = min(1.0, score / 2.0)
                    
                    if normalized_score >= min_confidence:
                        candidates.append({
                            "entity": entity,
                            "confidence": round(normalized_score, 3),
                            "match_reasons": match_reasons,
                            "matching_relations": matching_relations if matching_relations else None,
                            "inconsistencies": inconsistencies if inconsistencies else None,
                            "_raw_score": score
                        })
                
                # Ordina per confidence
                candidates.sort(key=lambda x: x["confidence"], reverse=True)
                
                # Limita risultati
                candidates = candidates[:max_results]
                
                # Determina se il risultato e ambiguo
                ambiguous = False
                best_match = None
                has_inconsistencies = False
                
                if len(candidates) >= 2:
                    diff = candidates[0]["confidence"] - candidates[1]["confidence"]
                    if diff < ambiguity_threshold:
                        ambiguous = True
                        logger.info(f"[DISAMBIGUATE] AMBIGUOUS: top 2 candidates diff={diff:.3f} < threshold={ambiguity_threshold}")
                
                if candidates and not ambiguous:
                    best_match = candidates[0]
                    if best_match.get("inconsistencies"):
                        has_inconsistencies = True
                        logger.warning(f"[DISAMBIGUATE] Best match has {len(best_match['inconsistencies'])} inconsistencies")
                
                # Cleanup: rimuovi _raw_score
                for c in candidates:
                    c.pop("_raw_score", None)
                
                logger.info(f"[DISAMBIGUATE] Result: {len(candidates)} candidates, ambiguous={ambiguous}, has_inconsistencies={has_inconsistencies}")
                if best_match:
                    logger.info(f"[DISAMBIGUATE] Best match: {best_match['entity']['entity_id']} (conf={best_match['confidence']})")
                
                return {
                    "query_name": name,
                    "total_candidates": len(candidates),
                    "ambiguous": ambiguous,
                    "has_inconsistencies": has_inconsistencies,
                    "best_match": best_match,
                    "candidates": candidates,
                    "disambiguation_context": {
                        "entity_type_filter": entity_type,
                        "related_entities_provided": related_entities,
                        "expected_relations_provided": expected_relations,
                        "attributes_provided": attributes,
                        "context_sentence_used": context_sentence is not None
                    }
                }
                
        except Exception as e:
            logger.error(f"[DISAMBIGUATE] Error: {e}")
            raise
    
    # ==================== Top-K Search Methods ====================
    
    async def topk_episodic(
        self,
        query: str,
        k: int = 5,
        user_id: str = "default",
        session_id: Optional[str] = None,
        time_range_hours: Optional[int] = None,
        min_similarity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Top-K search in Episodic Memory (conversazioni passate).
        
        Args:
            query: Testo di ricerca
            k: Numero di risultati
            user_id: User identifier
            session_id: Filtra per sessione specifica
            time_range_hours: Limita a ultime N ore
            min_similarity: Soglia minima similarity
            
        Returns:
            {"results": [...], "count": N, "query": str}
        """
        logger.info(f"🔎 [TOP-K] Episodic search: '{query[:50]}' (k={k})")
        
        try:
            from app.core.vectordb_manager import get_vectordb_manager
            vectordb = get_vectordb_manager()
            
            # Build where filter
            where_filter = {}
            if session_id:
                where_filter["session_id"] = session_id
            
            results = vectordb.query_documents(
                query_text=query,
                n_results=k * 2,  # Richiedi di più per filtrare dopo
                where=where_filter if where_filter else None
            )
            
            items = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results.get("distances") else 1.0
                    similarity = max(0, 1 - distance)  # Converti distanza in similarity
                    
                    if similarity >= min_similarity:
                        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                        items.append({
                            "content": doc,
                            "similarity": round(similarity, 4),
                            "metadata": metadata,
                            "id": results["ids"][0][i] if results.get("ids") else None
                        })
            
            # Ordina per similarity e limita a k
            items.sort(key=lambda x: x["similarity"], reverse=True)
            items = items[:k]
            
            logger.info(f"🔎 [TOP-K] Episodic: found {len(items)} results")
            
            return {
                "results": items,
                "count": len(items),
                "query": query,
                "memory_type": "episodic"
            }
            
        except Exception as e:
            logger.error(f"🔎 [TOP-K] Episodic search failed: {e}")
            return {"results": [], "count": 0, "query": query, "memory_type": "episodic", "error": str(e)}
    
    async def topk_semantic(
        self,
        query: str,
        k: int = 5,
        user_id: str = "default",
        document_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_similarity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Top-K search in Semantic Memory (documenti e conoscenze).
        
        Args:
            query: Testo di ricerca
            k: Numero di risultati
            user_id: User identifier
            document_type: Filtra per tipo documento
            tags: Filtra per tags
            min_similarity: Soglia minima similarity
            
        Returns:
            {"results": [...], "count": N, "query": str}
        """
        logger.info(f"🔎 [TOP-K] Semantic search: '{query[:50]}' (k={k})")
        
        try:
            from app.core.vectordb_manager import get_vectordb_manager
            vectordb = get_vectordb_manager()
            
            # Build where filter
            where_filter = {}
            if document_type:
                where_filter["type"] = document_type
            
            results = vectordb.query_documents(
                query_text=query,
                n_results=k * 2,
                where=where_filter if where_filter else None
            )
            
            items = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results.get("distances") else 1.0
                    similarity = max(0, 1 - distance)
                    
                    if similarity >= min_similarity:
                        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                        
                        # Filtra per tags se specificati
                        if tags:
                            doc_tags = metadata.get("tags", [])
                            if isinstance(doc_tags, str):
                                doc_tags = [doc_tags]
                            if not any(t in doc_tags for t in tags):
                                continue
                        
                        items.append({
                            "content": doc,
                            "similarity": round(similarity, 4),
                            "metadata": metadata,
                            "id": results["ids"][0][i] if results.get("ids") else None,
                            "source": metadata.get("source", "unknown")
                        })
            
            items.sort(key=lambda x: x["similarity"], reverse=True)
            items = items[:k]
            
            logger.info(f"🔎 [TOP-K] Semantic: found {len(items)} results")
            
            return {
                "results": items,
                "count": len(items),
                "query": query,
                "memory_type": "semantic"
            }
            
        except Exception as e:
            logger.error(f"🔎 [TOP-K] Semantic search failed: {e}")
            return {"results": [], "count": 0, "query": query, "memory_type": "semantic", "error": str(e)}
    
    async def topk_entities(
        self,
        query: str,
        k: int = 5,
        user_id: str = "default",
        entity_type: Optional[str] = None,
        include_aliases: bool = True,
        min_similarity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Top-K search nelle Entità del Knowledge Graph.
        
        Usa sia match testuale che embedding similarity.
        
        Args:
            query: Testo di ricerca
            k: Numero di risultati
            entity_type: Filtra per tipo
            include_aliases: Cerca anche negli alias
            min_similarity: Soglia minima
            
        Returns:
            {"results": [...], "count": N, "query": str}
        """
        logger.info(f"🔎 [TOP-K] Entities search: '{query[:50]}' (k={k})")
        
        db = self._get_db_manager()
        query_lower = query.lower().strip()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Query testuale con scoring basato su match quality
                sql = """
                    SELECT *,
                        CASE 
                            WHEN LOWER(primary_name) = ? THEN 1.0
                            WHEN LOWER(primary_name) LIKE ? THEN 0.9
                            WHEN LOWER(primary_name) LIKE ? THEN 0.7
                            WHEN LOWER(aliases_json) LIKE ? THEN 0.6
                            ELSE 0.5
                        END as match_score
                    FROM entities 
                    WHERE status = 'active'
                    AND (
                        LOWER(primary_name) LIKE ?
                        OR LOWER(entity_id) LIKE ?
                """
                params = [
                    query_lower,
                    f"{query_lower}%",
                    f"%{query_lower}%",
                    f"%{query_lower}%",
                    f"%{query_lower}%",
                    f"%{query_lower}%"
                ]
                
                if include_aliases:
                    sql += " OR LOWER(aliases_json) LIKE ?"
                    params.append(f"%{query_lower}%")
                
                sql += ")"
                
                if entity_type:
                    sql += " AND type = ?"
                    params.append(entity_type)
                
                sql += " ORDER BY match_score DESC, confidence DESC, salience DESC LIMIT ?"
                params.append(k * 2)
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                items = []
                for row in rows:
                    entity = self._row_to_entity_dict(row)
                    match_score = row["match_score"]
                    
                    # Calcola similarity combinata
                    similarity = match_score * entity["confidence"]
                    
                    if similarity >= min_similarity:
                        items.append({
                            "entity": entity,
                            "similarity": round(similarity, 4),
                            "match_type": "exact" if match_score == 1.0 else "partial"
                        })
                
                items = items[:k]
                
                logger.info(f"🔎 [TOP-K] Entities: found {len(items)} results")
                
                return {
                    "results": items,
                    "count": len(items),
                    "query": query,
                    "memory_type": "entities"
                }
                
        except Exception as e:
            logger.error(f"🔎 [TOP-K] Entities search failed: {e}")
            return {"results": [], "count": 0, "query": query, "memory_type": "entities", "error": str(e)}
    
    async def topk_relationships(
        self,
        query: str,
        k: int = 5,
        user_id: str = "default",
        relation_type: Optional[str] = None,
        valence: Optional[str] = None,
        entity_id: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> Dict[str, Any]:
        """
        Top-K search nelle Relazioni del Knowledge Graph.
        
        Cerca nelle relazioni usando la source_sentence e i metadata.
        
        Args:
            query: Testo di ricerca
            k: Numero di risultati
            relation_type: Filtra per tipo relazione
            valence: Filtra per valence
            entity_id: Filtra per entità coinvolta (source o target)
            min_similarity: Soglia minima
            
        Returns:
            {"results": [...], "count": N, "query": str}
        """
        logger.info(f"🔎 [TOP-K] Relationships search: '{query[:50]}' (k={k})")
        
        db = self._get_db_manager()
        query_lower = query.lower().strip()
        
        try:
            with db._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Query con scoring basato su match nella source_sentence
                sql = """
                    SELECT r.*,
                        CASE 
                            WHEN LOWER(source_sentence) LIKE ? THEN 0.9
                            WHEN LOWER(original_predicate) LIKE ? THEN 0.8
                            WHEN LOWER(from_entity_id) LIKE ? THEN 0.7
                            WHEN LOWER(to_entity_id) LIKE ? THEN 0.7
                            ELSE 0.5
                        END as match_score
                    FROM relationships r
                    WHERE status = 'active'
                    AND (
                        LOWER(source_sentence) LIKE ?
                        OR LOWER(original_predicate) LIKE ?
                        OR LOWER(from_entity_id) LIKE ?
                        OR LOWER(to_entity_id) LIKE ?
                    )
                """
                params = [
                    f"%{query_lower}%", f"%{query_lower}%",
                    f"%{query_lower}%", f"%{query_lower}%",
                    f"%{query_lower}%", f"%{query_lower}%",
                    f"%{query_lower}%", f"%{query_lower}%"
                ]
                
                if relation_type:
                    sql += " AND relation_type = ?"
                    params.append(relation_type)
                
                if valence:
                    sql += " AND valence = ?"
                    params.append(valence)
                
                if entity_id:
                    sql += " AND (from_entity_id = ? OR to_entity_id = ?)"
                    params.extend([entity_id, entity_id])
                
                sql += " ORDER BY match_score DESC, confidence DESC, strength DESC LIMIT ?"
                params.append(k * 2)
                
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                items = []
                for row in rows:
                    rel = self._row_to_relationship_dict(row)
                    match_score = row["match_score"]
                    
                    similarity = match_score * rel["confidence"]
                    
                    if similarity >= min_similarity:
                        items.append({
                            "relationship": rel,
                            "similarity": round(similarity, 4),
                            "summary": f"{rel['source_entity_id']} → {rel['relation_type']} → {rel['target_entity_id']}"
                        })
                
                items = items[:k]
                
                logger.info(f"🔎 [TOP-K] Relationships: found {len(items)} results")
                
                return {
                    "results": items,
                    "count": len(items),
                    "query": query,
                    "memory_type": "relationships"
                }
                
        except Exception as e:
            logger.error(f"🔎 [TOP-K] Relationships search failed: {e}")
            return {"results": [], "count": 0, "query": query, "memory_type": "relationships", "error": str(e)}
    
    async def topk_unified(
        self,
        query: str,
        k_per_memory: int = 3,
        user_id: str = "default",
        min_similarity: float = 0.3,
        include_episodic: bool = True,
        include_semantic: bool = True,
        include_entities: bool = True,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """
        Top-K search UNIFICATA su tutte le memorie.
        
        Esegue ricerche parallele su tutte le memorie e combina i risultati.
        Ideale per costruire contesto cognitivo completo.
        
        Args:
            query: Testo di ricerca
            k_per_memory: Risultati per ogni memoria
            user_id: User identifier
            min_similarity: Soglia minima
            include_*: Flag per includere/escludere memorie
            
        Returns:
            {
                "episodic": {"results": [...], "count": N},
                "semantic": {"results": [...], "count": N},
                "entities": {"results": [...], "count": N},
                "relationships": {"results": [...], "count": N},
                "total_results": N,
                "query": str
            }
        """
        logger.info(f"🔎 [TOP-K] Unified search: '{query[:50]}' (k={k_per_memory})")
        
        import asyncio
        
        results = {
            "query": query,
            "k_per_memory": k_per_memory
        }
        
        tasks = []
        task_names = []
        
        if include_episodic:
            tasks.append(self.topk_episodic(query, k_per_memory, user_id, min_similarity=min_similarity))
            task_names.append("episodic")
        
        if include_semantic:
            tasks.append(self.topk_semantic(query, k_per_memory, user_id, min_similarity=min_similarity))
            task_names.append("semantic")
        
        if include_entities:
            tasks.append(self.topk_entities(query, k_per_memory, user_id, min_similarity=min_similarity))
            task_names.append("entities")
        
        if include_relationships:
            tasks.append(self.topk_relationships(query, k_per_memory, user_id, min_similarity=min_similarity))
            task_names.append("relationships")
        
        # Esegui in parallelo
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_results = 0
        for name, result in zip(task_names, task_results):
            if isinstance(result, Exception):
                results[name] = {"results": [], "count": 0, "error": str(result)}
            else:
                results[name] = result
                total_results += result.get("count", 0)
        
        results["total_results"] = total_results
        
        logger.info(f"🔎 [TOP-K] Unified: found {total_results} total results across {len(task_names)} memories")
        
        return results


# Singleton instance
_graph_service_instance: Optional[GraphService] = None

def get_graph_service() -> GraphService:
    """Get or create singleton GraphService instance"""
    global _graph_service_instance
    if _graph_service_instance is None:
        _graph_service_instance = GraphService()
    return _graph_service_instance
