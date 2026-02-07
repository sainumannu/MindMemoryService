"""
Graph API Routes - Endpoint per gestione Knowledge Graph con normalizzazione

Endpoints:
- POST /graph/relationships - Crea relazione con normalizzazione predicato
- GET /graph/relationships - Query relazioni con filtri
- POST /graph/relationships/query - Query avanzate con group_by
- POST /graph/decay - Trigger decay service
- GET /graph/stats - Statistiche normalizer e decay

Author: MindMemoryService Team
Date: February 2026
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging

from app.graph.graph_service import get_graph_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class RawRelation(BaseModel):
    """Relazione raw da Thalamus"""
    subject: str = Field(..., description="Subject entity ID (es. 'user_admin')")
    predicate: str = Field(..., description="Raw predicate (es. 'esprimere_gradimento_per')")
    object: str = Field(..., description="Object entity ID (es. 'pizza_margherita')")
    source_sentence: Optional[str] = Field(None, description="Original user sentence")


class CreateRelationshipRequest(BaseModel):
    """Request per creare relazione normalizzata"""
    user_id: str = Field("default", description="User identifier")
    raw_relation: RawRelation


class QueryFilters(BaseModel):
    """Filtri per query avanzate"""
    relation_type: Optional[str] = Field(None, description="Filter by relation type (sentiment, ownership, etc.)")
    valence: Optional[str] = Field(None, description="Filter by valence (positive, negative, neutral)")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence")
    min_strength: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum strength")
    from_entity_id: Optional[str] = Field(None, description="Filter by source entity")


class QueryRelationshipsRequest(BaseModel):
    """Request per query avanzate"""
    user_id: str = Field("default", description="User identifier")
    filters: Optional[QueryFilters] = None
    group_by: Optional[str] = Field(None, description="Field to group by (es. 'target_type')")
    limit: int = Field(100, ge=1, le=1000, description="Max results")


class DecayRequest(BaseModel):
    """Request per trigger decay"""
    user_id: Optional[str] = Field(None, description="User identifier (optional)")
    options: Optional[Dict[str, Any]] = Field(None, description="Decay options override")


# ==================== Top-K Search Models ====================

class TopKSearchRequest(BaseModel):
    """Request base per ricerche Top-K"""
    query: str = Field(..., description="Testo di ricerca (semantic search)")
    k: int = Field(5, ge=1, le=50, description="Numero di risultati da ritornare")
    user_id: str = Field("default", description="User identifier")
    min_similarity: float = Field(0.0, ge=0.0, le=1.0, description="Soglia minima similarity (0-1)")


class TopKEpisodicRequest(TopKSearchRequest):
    """Request per Top-K Episodic Memory"""
    session_id: Optional[str] = Field(None, description="Filtra per sessione specifica")
    time_range_hours: Optional[int] = Field(None, description="Limita a ultime N ore")


class TopKSemanticRequest(TopKSearchRequest):
    """Request per Top-K Semantic Memory"""
    document_type: Optional[str] = Field(None, description="Filtra per tipo documento")
    tags: Optional[List[str]] = Field(None, description="Filtra per tags")


class TopKEntitiesRequest(TopKSearchRequest):
    """Request per Top-K Entity Search"""
    entity_type: Optional[str] = Field(None, description="Filtra per tipo entità")
    include_aliases: bool = Field(True, description="Cerca anche negli alias")


class TopKRelationshipsRequest(TopKSearchRequest):
    """Request per Top-K Relationships"""
    relation_type: Optional[str] = Field(None, description="Filtra per tipo relazione")
    valence: Optional[str] = Field(None, description="Filtra per valence")
    entity_id: Optional[str] = Field(None, description="Filtra per entità coinvolta")


class TopKUnifiedRequest(BaseModel):
    """Request per ricerca Top-K unificata su tutte le memorie"""
    query: str = Field(..., description="Testo di ricerca")
    k_per_memory: int = Field(3, ge=1, le=20, description="Risultati per ogni memoria")
    user_id: str = Field("default", description="User identifier")
    min_similarity: float = Field(0.3, ge=0.0, le=1.0, description="Soglia minima similarity")
    include_episodic: bool = Field(True, description="Includi Episodic Memory")
    include_semantic: bool = Field(True, description="Includi Semantic Memory")
    include_entities: bool = Field(True, description="Includi Entity Graph")
    include_relationships: bool = Field(True, description="Includi Relationships")


# ==================== Relationship CRUD Models ====================

class UpdateRelationshipRequest(BaseModel):
    """Request per aggiornare una relazione"""
    strength: Optional[float] = Field(None, ge=0.0, le=1.0, description="Strength (0-1)")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence (0-1)")
    valence: Optional[str] = Field(None, description="Valence: positive, negative, neutral")
    intensity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Intensity (0-1)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata da mergere")
    status: Optional[str] = Field(None, description="Status: active, archived, deleted")
    source_sentence: Optional[str] = Field(None, description="Frase sorgente aggiornata")


class ReinforceRelationshipRequest(BaseModel):
    """Request per rinforzare una relazione"""
    strength_boost: float = Field(0.1, ge=0.0, le=0.5, description="Incremento strength")
    source_sentence: Optional[str] = Field(None, description="Nuova frase sorgente")


class CreateEntityRequest(BaseModel):
    """Request per creare una nuova entità"""
    name: str = Field(..., description="Nome primario dell'entità")
    entity_type: str = Field("auto", description="Tipo: person, organization, location, object, event, food, etc. Usa 'auto' per inferenza automatica")
    aliases: Optional[List[str]] = Field(None, description="Nomi alternativi")
    identifiers: Optional[Dict[str, str]] = Field(None, description="email, phone, user_id, etc.")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Attributi aggiuntivi")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="Confidence score")
    source: str = Field("extraction", description="Fonte: extraction, user_declared, inferred")
    context: str = Field("", description="Contesto opzionale per inferenza tipo (frase in cui appare)")
    hints: Optional[Dict[str, Any]] = Field(None, description="Hint da Thalamus: {category: 'soggetto'}")


class FindOrCreateEntityRequest(BaseModel):
    """Request per find-or-create entità"""
    name: str = Field(..., description="Nome dell'entità da cercare/creare")
    entity_type: str = Field("auto", description="Tipo entità o 'auto' per inferenza")
    aliases: Optional[List[str]] = Field(None)
    identifiers: Optional[Dict[str, str]] = Field(None)
    attributes: Optional[Dict[str, Any]] = Field(None)
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    context: str = Field("", description="Contesto per inferenza tipo")
    hints: Optional[Dict[str, Any]] = Field(None, description="Hint da Thalamus")


class ResolveEntityRequest(BaseModel):
    """Request per risolvere un'entità cercando in tutte le memorie persistenti"""
    entity_name: str = Field(..., description="Nome dell'entità da risolvere (es. 'Fabrizio')")
    entity_type: Optional[str] = Field(None, description="Tipo probabile: person, place, thing, food, etc.")
    user_id: str = Field("default", description="User identifier")
    context_hint: Optional[str] = Field(None, description="Contesto aggiuntivo per disambiguazione (es. 'pizza preferita')")
    include_episodic: bool = Field(True, description="Cerca anche in Episodic Memory")
    include_semantic: bool = Field(True, description="Cerca anche in Semantic Memory")
    include_relationships: bool = Field(True, description="Cerca anche nelle relazioni esistenti")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0, description="Soglia minima confidence per match")


class ExpectedRelation(BaseModel):
    """
    Relazione attesa per la disambiguazione.
    
    Esempio: Se la frase è "Fabrizio, il compagno di Rosella", 
    si passa: {"relation_type": "partner", "target_name": "Rosella"}
    """
    relation_type: str = Field(..., description="Tipo di relazione: partner, sibling, parent, friend, etc.")
    target_name: Optional[str] = Field(None, description="Nome del target atteso (es. 'Rosella')")
    target_entity_id: Optional[str] = Field(None, description="Entity ID del target se noto")


class DisambiguateEntityRequest(BaseModel):
    """
    Request per disambiguare un'entità basandosi su nome, attributi e relazioni.
    
    Quando Mind chiede informazioni su "Fabrizio", il sistema cerca tutti i "Fabrizio"
    nel Knowledge Graph e li ordina per grado di correlazione con il contesto fornito.
    
    Esempio con verifica coerenza:
    - Frase: "Fabrizio, il compagno di Rosella. Sua sorella si chiama Maria"
    - expected_relations: [
        {"relation_type": "partner", "target_name": "Rosella"},
        {"relation_type": "sibling", "target_name": "Maria"}
      ]
    - Se nel grafo Fabrizio ha partner=Rosella ma sorella=Giovanna (non Maria),
      il sistema segnala l'inconsistenza.
    """
    name: str = Field(..., description="Nome da cercare (es. 'Fabrizio', 'pizza')")
    entity_type: Optional[str] = Field(None, description="Tipo atteso: person, food, organization, etc.")
    
    # Contesto per disambiguazione
    related_entities: Optional[List[str]] = Field(
        None, 
        description="Entity IDs con cui l'entità cercata ha relazioni (es. ['food:pizza_margherita', 'organization:google'])"
    )
    expected_relations: Optional[List[ExpectedRelation]] = Field(
        None,
        description="Relazioni attese con verifica coerenza (es. [{'relation_type': 'partner', 'target_name': 'Rosella'}])"
    )
    attributes: Optional[Dict[str, Any]] = Field(
        None, 
        description="Attributi attesi (es. {'role': 'developer', 'city': 'Milano'})"
    )
    context_sentence: Optional[str] = Field(
        None, 
        description="Frase di contesto per semantic matching (es. 'Fabrizio che ama la pizza')"
    )
    
    # Opzioni
    min_confidence: float = Field(0.2, ge=0.0, le=1.0, description="Soglia minima confidence")
    max_results: int = Field(5, ge=1, le=20, description="Numero massimo di candidati")
    ambiguity_threshold: float = Field(0.1, ge=0.0, le=0.5, description="Se i top 2 candidati hanno score entro questa soglia, il risultato è ambiguo")


class RelationInconsistency(BaseModel):
    """Incoerenza rilevata tra relazioni attese e relazioni nel grafo"""
    relation_type: str = Field(..., description="Tipo di relazione con incoerenza")
    expected_target: str = Field(..., description="Target atteso dalla query")
    found_target: str = Field(..., description="Target trovato nel grafo")
    found_entity_id: str = Field(..., description="Entity ID del target trovato")
    message: str = Field(..., description="Messaggio descrittivo dell'incoerenza")


class DisambiguationCandidate(BaseModel):
    """Un candidato nella risposta di disambiguazione"""
    entity: Dict[str, Any] = Field(..., description="Entita completa")
    confidence: float = Field(..., description="Score di correlazione (0-1)")
    match_reasons: List[str] = Field(..., description="Motivi del match")
    matching_relations: Optional[List[Dict[str, Any]]] = Field(None, description="Relazioni che hanno contribuito al match")
    inconsistencies: Optional[List[Dict[str, Any]]] = Field(None, description="Incoerenze rilevate tra info attese e grafo")


class DisambiguateEntityResponse(BaseModel):
    """Response per disambiguazione entita"""
    query_name: str = Field(..., description="Nome cercato")
    total_candidates: int = Field(..., description="Numero totale di candidati trovati")
    ambiguous: bool = Field(..., description="True se i top candidati hanno score molto vicino")
    has_inconsistencies: bool = Field(False, description="True se il best_match ha incoerenze con le info fornite")
    best_match: Optional[DisambiguationCandidate] = Field(None, description="Miglior candidato (se non ambiguo)")
    candidates: List[DisambiguationCandidate] = Field(..., description="Lista ordinata di candidati")
    disambiguation_context: Dict[str, Any] = Field(..., description="Contesto usato per disambiguazione")


from typing import List


# ==================== Endpoints ====================

@router.post("/relationships")
async def create_relationship(request: CreateRelationshipRequest):
    """
    Crea una relazione normalizzando il predicato RAW.
    
    Il predicato viene normalizzato in:
    - relation_type: categoria semantica (sentiment, ownership, etc.)
    - valence: positive, negative, neutral
    - intensity: 0.0 - 1.0
    
    Se la relazione esiste già (stesso subject-object-relation_type), 
    viene rinforzata incrementando evidence_count e strength.
    
    Example request:
    ```json
    {
        "user_id": "admin",
        "raw_relation": {
            "subject": "user_admin",
            "predicate": "esprimere_gradimento_per",
            "object": "pizza_margherita",
            "source_sentence": "Mi piace la pizza margherita"
        }
    }
    ```
    
    Example response:
    ```json
    {
        "id": "rel:user_admin_to_pizza_margherita_abc123",
        "source_entity_id": "user_admin",
        "target_entity_id": "pizza_margherita",
        "relation_type": "sentiment",
        "original_predicate": "esprimere_gradimento_per",
        "metadata": {
            "valence": "positive",
            "intensity": 0.7,
            "normalization_method": "direct"
        },
        "strength": 1.0,
        "confidence": 0.95
    }
    ```
    """
    try:
        service = get_graph_service()
        result = await service.create_relationship_from_raw(
            user_id=request.user_id,
            raw_relation=request.raw_relation.model_dump()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships")
async def get_relationships(
    user_id: str = Query("default", description="User identifier"),
    from_entity_id: Optional[str] = Query(None, alias="from", description="Filter by source entity"),
    to_entity_id: Optional[str] = Query(None, alias="to", description="Filter by target entity"),
    relation_type: Optional[str] = Query(None, description="Filter by relation type"),
    valence: Optional[str] = Query(None, description="Filter by valence"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    min_strength: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum strength"),
    status: str = Query("active", description="Status filter"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    Query relazioni con filtri.
    
    Example: GET /graph/relationships?relation_type=sentiment&valence=positive
    
    Returns:
    ```json
    {
        "relationships": [...],
        "count": 10,
        "total": 25
    }
    ```
    """
    try:
        service = get_graph_service()
        result = await service.get_relationships(
            user_id=user_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relation_type=relation_type,
            valence=valence,
            min_confidence=min_confidence,
            min_strength=min_strength,
            status=status,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Error getting relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/query")
async def query_relationships(request: QueryRelationshipsRequest):
    """
    Query avanzate con raggruppamento per pattern detection.
    
    Utile per il Learning Module di Mind per trovare pattern nelle preferenze.
    
    Example request:
    ```json
    {
        "user_id": "admin",
        "filters": {
            "relation_type": "sentiment",
            "valence": "positive",
            "min_confidence": 0.5
        },
        "group_by": "target_type"
    }
    ```
    
    Example response (con group_by):
    ```json
    {
        "groups": {
            "food": [
                {"target_id": "pizza_margherita", "intensity": 0.7},
                {"target_id": "carbonara", "intensity": 0.9}
            ],
            "place": [
                {"target_id": "Roma", "intensity": 0.8}
            ]
        },
        "total_count": 3
    }
    ```
    """
    try:
        service = get_graph_service()
        
        filters = None
        if request.filters:
            filters = request.filters.model_dump(exclude_none=True)
        
        result = await service.query_relationships(
            user_id=request.user_id,
            filters=filters,
            group_by=request.group_by,
            limit=request.limit
        )
        return result
    except Exception as e:
        logger.error(f"Error in query_relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships/{rel_id}")
async def get_relationship(rel_id: str):
    """
    Recupera una singola relazione per ID.
    
    Example: GET /graph/relationships/rel:person:fabrizio_to_food:pizza_abc123
    
    Returns 404 se non trovata.
    """
    try:
        service = get_graph_service()
        result = await service.get_relationship(rel_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Relationship not found: {rel_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/relationships/{rel_id}")
async def update_relationship(rel_id: str, request: UpdateRelationshipRequest):
    """
    Aggiorna una relazione esistente.
    
    Campi aggiornabili:
    - strength, confidence, valence, intensity
    - metadata (merge con esistente)
    - status (active, archived, deleted)
    - source_sentence
    
    Example request:
    ```json
    {
        "strength": 0.9,
        "metadata": {"verified_by": "user"},
        "valence": "positive"
    }
    ```
    
    Returns 404 se non trovata.
    """
    try:
        service = get_graph_service()
        
        # Converti request in dict escludendo None
        updates = request.model_dump(exclude_none=True)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        result = await service.update_relationship(rel_id, updates)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Relationship not found: {rel_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships/{rel_id}")
async def delete_relationship(
    rel_id: str,
    hard: bool = Query(False, description="Se True, elimina fisicamente. Se False, soft delete")
):
    """
    Elimina una relazione.
    
    - **Soft delete** (default): imposta status='deleted', recuperabile
    - **Hard delete** (?hard=true): elimina fisicamente dal database
    
    Example: DELETE /graph/relationships/rel:abc123
    Example: DELETE /graph/relationships/rel:abc123?hard=true
    
    Returns 404 se non trovata.
    """
    try:
        service = get_graph_service()
        success = await service.delete_relationship(rel_id, hard_delete=hard)
        if not success:
            raise HTTPException(status_code=404, detail=f"Relationship not found: {rel_id}")
        return {
            "message": f"Relationship {'permanently deleted' if hard else 'soft deleted'}",
            "rel_id": rel_id,
            "hard_delete": hard
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships/{rel_id}/reinforce")
async def reinforce_relationship(rel_id: str, request: ReinforceRelationshipRequest):
    """
    Rinforza una relazione esistente.
    
    Aumenta strength e evidence_count. Usato quando la stessa relazione
    viene espressa di nuovo dall'utente.
    
    Example request:
    ```json
    {
        "strength_boost": 0.1,
        "source_sentence": "La pizza margherita è ancora la mia preferita"
    }
    ```
    
    Example response:
    ```json
    {
        "id": "rel:...",
        "strength": 0.9,
        "evidence_count": 3,
        "last_reinforced": "2026-02-01T12:00:00Z",
        ...
    }
    ```
    
    Returns 404 se non trovata.
    """
    try:
        service = get_graph_service()
        result = await service.reinforce_relationship(
            rel_id=rel_id,
            strength_boost=request.strength_boost,
            new_source_sentence=request.source_sentence
        )
        if result is None:
            raise HTTPException(status_code=404, detail=f"Relationship not found: {rel_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reinforcing relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RELATIONSHIP EVENT HISTORY ====================

@router.get("/relationships/{rel_id}/events")
async def get_relationship_events(
    rel_id: str,
    limit: int = 50,
    order: str = "desc"
):
    """
    Recupera la storia degli eventi per una relazione.
    
    Ogni volta che una relazione viene aggiornata (es. "amo Maria" → "odio Maria"),
    viene registrato un evento. Questo endpoint restituisce la storia completa.
    
    Query params:
    - limit: max eventi (default 50)
    - order: 'desc' (recenti prima) o 'asc' (cronologico)
    
    Example response:
    ```json
    {
        "rel_id": "rel:user_to_maria_abc123",
        "events": [
            {
                "event_id": "evt:abc123",
                "predicate": "adora",
                "valence": 0.95,
                "intensity": 0.9,
                "source_sentence": "Adoro Maria",
                "timestamp": "2026-02-01T12:00:00Z"
            },
            {
                "event_id": "evt:def456",
                "predicate": "odia",
                "valence": -0.9,
                "source_sentence": "Odio Maria",
                "timestamp": "2026-02-01T10:00:00Z"
            }
        ],
        "total": 2
    }
    ```
    """
    try:
        service = get_graph_service()
        events = await service.get_relationship_events(
            rel_id=rel_id,
            limit=limit,
            order=order
        )
        return {
            "rel_id": rel_id,
            "events": events,
            "total": len(events)
        }
    except Exception as e:
        logger.error(f"Error getting relationship events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships/{rel_id}/trend")
async def get_relationship_trend(
    rel_id: str,
    window_size: int = 3
):
    """
    Analizza il trend recente di una relazione.
    
    Determina se la relazione sta migliorando, peggiorando, è stabile o volatile.
    
    Query params:
    - window_size: numero di eventi recenti da analizzare (default 3)
    
    Example response:
    ```json
    {
        "rel_id": "rel:user_to_maria_abc123",
        "current_valence": 0.95,
        "trend": "improving",
        "avg_valence": 0.5,
        "change": 0.45,
        "events_analyzed": 3,
        "interpretation": "La relazione sta migliorando"
    }
    ```
    
    Trend values:
    - "improving": valence in aumento
    - "worsening": valence in diminuzione
    - "stable": valence relativamente costante
    - "volatile": cambiamenti frequenti e ampi
    - "unknown": dati insufficienti
    """
    try:
        service = get_graph_service()
        trend = await service.get_relationship_trend(
            rel_id=rel_id,
            window_size=window_size
        )
        
        # Aggiungi interpretazione human-readable
        interpretations = {
            "improving": "La relazione sta migliorando",
            "worsening": "La relazione sta peggiorando",
            "stable": "La relazione è stabile",
            "volatile": "La relazione è instabile con frequenti cambiamenti",
            "unknown": "Dati insufficienti per determinare il trend"
        }
        
        return {
            "rel_id": rel_id,
            **trend,
            "interpretation": interpretations.get(trend["trend"], trend["trend"])
        }
    except Exception as e:
        logger.error(f"Error getting relationship trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships/{rel_id}/volatility")
async def get_relationship_volatility(rel_id: str):
    """
    Calcola la volatilità di una relazione.
    
    Una relazione stabile (es. sempre positiva) ha volatilità bassa.
    Una relazione tipo amore/odio ha volatilità alta.
    
    Example response:
    ```json
    {
        "rel_id": "rel:user_to_maria_abc123",
        "volatility": 0.75,
        "stddev": 0.65,
        "sign_changes": 3,
        "total_events": 5,
        "interpretation": "highly_unstable",
        "description": "Relazione molto instabile con frequenti inversioni di sentimento"
    }
    ```
    
    Interpretation values:
    - "stable": volatility < 0.2
    - "fluctuating": volatility 0.2-0.5
    - "highly_unstable": volatility > 0.5
    - "insufficient_data": meno di 2 eventi
    """
    try:
        service = get_graph_service()
        volatility = await service.get_relationship_volatility(rel_id=rel_id)
        
        # Aggiungi descrizione human-readable
        descriptions = {
            "stable": "Relazione stabile con sentimenti costanti",
            "fluctuating": "Relazione con qualche variazione di sentimento",
            "highly_unstable": "Relazione molto instabile con frequenti inversioni di sentimento",
            "insufficient_data": "Dati insufficienti per calcolare la volatilità",
            "error": "Errore nel calcolo"
        }
        
        return {
            "rel_id": rel_id,
            **volatility,
            "description": descriptions.get(volatility["interpretation"], "")
        }
    except Exception as e:
        logger.error(f"Error getting relationship volatility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decay")
async def apply_decay(request: DecayRequest):
    """
    Trigger decay service per decadimento entità e relazioni.
    
    Il decay:
    - Riduce confidence delle entità non usate
    - Riduce strength delle relazioni non rinforzate
    - Rimuove entità/relazioni sotto soglia (garbage collection)
    - Rimuove orphan entities
    
    Le entità con source="user_declared" sono protette dal decay.
    
    Example request:
    ```json
    {
        "user_id": "admin",
        "options": {
            "decay_rate": 0.05,
            "min_confidence_threshold": 0.2
        }
    }
    ```
    
    Example response:
    ```json
    {
        "success": true,
        "entities_decayed": 5,
        "entities_removed": 2,
        "relationships_decayed": 12,
        "relationships_removed": 3,
        "orphans_removed": 1
    }
    ```
    """
    try:
        service = get_graph_service()
        result = await service.apply_decay(
            user_id=request.user_id,
            options=request.options
        )
        return result
    except Exception as e:
        logger.error(f"Error applying decay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_stats():
    """
    Statistiche del graph service.
    
    Returns:
    ```json
    {
        "normalizer": {
            "direct_hits": 100,
            "partial_hits": 25,
            "embedding_hits": 5,
            "defaults": 3,
            "cache_hits": 50
        },
        "decay": {
            "total_decay_runs": 10,
            "entities_decayed": 50,
            "entities_removed": 5,
            "relationships_decayed": 120,
            "relationships_removed": 15,
            "orphans_removed": 3,
            "last_decay_run": "2026-02-01T10:30:00Z"
        }
    }
    ```
    """
    try:
        service = get_graph_service()
        return {
            "normalizer": service.get_normalizer_stats(),
            "decay": service.get_decay_stats()
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Entity Endpoints ====================

@router.post("/entities")
async def create_entity(request: CreateEntityRequest):
    """
    Crea una nuova entità nel Knowledge Graph.
    
    **Auto-inferenza tipo**: Usa `entity_type: "auto"` per inferire automaticamente
    il tipo dal nome e contesto usando l'EntityTypeNormalizer.
    
    Se l'entità esiste già (stesso ID generato da nome+tipo), viene arricchita
    con i nuovi dati (merge di aliases, identifiers, attributes).
    
    L'ID viene generato automaticamente: `{type}:{normalized_name}`
    Es: "Fabrizio" + "person" → `person:fabrizio`
    
    Example request con tipo esplicito:
    ```json
    {
        "name": "Fabrizio Rossi",
        "entity_type": "person",
        "aliases": ["Fabrizio", "Fab"],
        "confidence": 0.95
    }
    ```
    
    Example request con auto-inferenza:
    ```json
    {
        "name": "Google Italia",
        "entity_type": "auto",
        "context": "Lavoro per Google Italia da 3 anni"
    }
    ```
    → Tipo inferito: "organization" (confidence 0.95)
    
    Example response:
    ```json
    {
        "entity_id": "organization:google_italia",
        "type": "organization",
        "primary_name": "Google Italia",
        "attributes": {
            "_type_inference": {
                "inferred_type": "organization",
                "inference_confidence": 0.95,
                "inference_method": "direct",
                "inference_signals": ["known_organization:google"]
            }
        },
        ...
    }
    ```
    """
    try:
        service = get_graph_service()
        result = await service.create_entity(
            name=request.name,
            entity_type=request.entity_type,
            aliases=request.aliases,
            identifiers=request.identifiers,
            attributes=request.attributes,
            confidence=request.confidence,
            source=request.source,
            context=request.context,
            hints=request.hints
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id:path}")
async def get_entity(entity_id: str):
    """
    Recupera un'entità per ID.
    
    Example: GET /graph/entities/person:fabrizio_rossi
    
    Returns 404 se non trovata.
    """
    try:
        service = get_graph_service()
        result = await service.get_entity(entity_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities")
async def search_entities(
    q: str = Query(..., description="Stringa di ricerca (nome o parte di nome)"),
    entity_type: Optional[str] = Query(None, alias="type", description="Filtra per tipo"),
    include_aliases: bool = Query(True, description="Cerca anche negli alias"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Soglia minima confidence"),
    limit: int = Query(10, ge=1, le=100, description="Max risultati")
):
    """
    Cerca entità per nome (con match parziale).
    
    Example: GET /graph/entities?q=Fabri&type=person
    
    Returns:
    ```json
    {
        "entities": [...],
        "count": 3,
        "exact_match": {
            "entity_id": "person:fabrizio",
            ...
        }
    }
    ```
    
    `exact_match` è l'entità con nome esattamente uguale alla query (se trovata).
    """
    try:
        service = get_graph_service()
        result = await service.search_entities(
            query=q,
            entity_type=entity_type,
            include_aliases=include_aliases,
            min_confidence=min_confidence,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error searching entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities/find-or-create")
async def find_or_create_entity(request: FindOrCreateEntityRequest):
    """
    Cerca un'entità per nome, la crea se non esiste.
    
    **Questo è l'endpoint principale che Mind dovrebbe usare.**
    
    Comportamento:
    1. Cerca match esatto (nome o alias)
    2. Se trovato, ritorna l'entità esistente (arricchita con nuovi dati se forniti)
    3. Se non trovato, cerca match parziale
    4. Se nessun match, crea nuova entità
    
    Example request:
    ```json
    {
        "name": "Fabrizio",
        "entity_type": "person",
        "identifiers": {"email": "fab@example.com"}
    }
    ```
    
    Example response:
    ```json
    {
        "entity": {
            "entity_id": "person:fabrizio_rossi",
            "type": "person",
            "primary_name": "Fabrizio Rossi",
            ...
        },
        "created": false,
        "matched_by": "exact"
    }
    ```
    
    `matched_by` può essere:
    - `"exact"`: match esatto su nome o alias
    - `"partial"`: match parziale (es. "Fabri" → "Fabrizio")
    - `"created"`: nessun match, entità creata
    """
    try:
        service = get_graph_service()
        result = await service.find_or_create_entity(
            name=request.name,
            entity_type=request.entity_type,
            aliases=request.aliases,
            identifiers=request.identifiers,
            attributes=request.attributes,
            confidence=request.confidence
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in find_or_create_entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities/resolve")
async def resolve_entity(request: ResolveEntityRequest):
    """
    🔍 **Risolve un'entità cercando in TUTTE le memorie persistenti.**
    
    Questo è l'endpoint centrale per la risoluzione entità. Mind lo chiama
    dopo aver cercato nella Working Memory (che è volatile e resta in Mind).
    
    **Ordine di ricerca:**
    1. **Entity Graph** - entità persistenti (nome + alias)
    2. **Relationships** - entità menzionate in relazioni esistenti
    3. **Episodic Memory** - conversazioni passate (cross-session)
    4. **Semantic Memory** - documenti e conoscenze
    
    **Flusso tipico:**
    ```
    Mind (Working Memory) → se non trovato → MindMemoryService.resolve_entity()
    ```
    
    Example request:
    ```json
    {
        "entity_name": "Fabrizio",
        "entity_type": "person",
        "user_id": "admin",
        "context_hint": "email da inviare",
        "min_confidence": 0.6
    }
    ```
    
    Example response (risolto):
    ```json
    {
        "resolved": true,
        "entity": {
            "entity_id": "person:fabrizio_rossi",
            "type": "person",
            "primary_name": "Fabrizio Rossi",
            "identifiers": {"email": "fabrizio@example.com"},
            ...
        },
        "candidates": [],
        "source": "entity_graph",
        "confidence": 0.95,
        "context": "Entità conosciuta: Fabrizio Rossi (person)"
    }
    ```
    
    Example response (ambiguo):
    ```json
    {
        "resolved": false,
        "entity": null,
        "candidates": [
            {"entity": {...}, "source": "entity_graph", "confidence": 0.7},
            {"entity": {...}, "source": "relationships", "confidence": 0.6}
        ],
        "source": "not_found",
        "confidence": 0.0,
        "suggested_action": "choose_from_candidates"
    }
    ```
    
    **Campi risposta:**
    - `resolved`: true se trovato match definitivo (confidence >= 0.8)
    - `entity`: entità risolta (se resolved=true)
    - `candidates`: altri possibili match ordinati per confidence
    - `source`: dove è stato trovato il match
    - `suggested_action`: "ask_user" | "choose_from_candidates" (se non risolto)
    """
    try:
        service = get_graph_service()
        result = await service.resolve_entity(
            entity_name=request.entity_name,
            entity_type=request.entity_type,
            user_id=request.user_id,
            context_hint=request.context_hint,
            include_episodic=request.include_episodic,
            include_semantic=request.include_semantic,
            include_relationships=request.include_relationships,
            min_confidence=request.min_confidence
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in resolve_entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities/disambiguate")
async def disambiguate_entity(request: DisambiguateEntityRequest):
    """
    **Disambigua un'entità basandosi su nome, attributi e relazioni.**
    
    Quando Mind chiede informazioni su "Fabrizio", questo endpoint:
    1. Cerca tutti i "Fabrizio" nel Knowledge Graph (nome + alias)
    2. Per ogni candidato, calcola uno score di correlazione basato su:
       - Match del nome (exact, partial, alias)
       - Relazioni con le entità fornite in `related_entities`
       - Match degli attributi forniti in `attributes`
       - Similarità semantica con `context_sentence`
    3. Ordina i candidati per score e indica se il risultato è ambiguo
    
    **Quando usarlo:**
    - Quando l'utente menziona un nome senza specificare ulteriori dettagli
    - Quando servono tutti i possibili candidati con ranking
    - Per disambiguare tra omonimi (es. "Fabrizio Rossi" vs "Fabrizio Bianchi")
    
    **Differenza da `/entities/resolve`:**
    - `resolve` cerca di trovare UN'entità definitiva
    - `disambiguate` restituisce TUTTI i candidati con scoring dettagliato
    
    Example request senza contesto:
    ```json
    {
        "name": "Fabrizio"
    }
    ```
    → Restituisce tutti i "Fabrizio" trovati
    
    Example request con contesto relazionale:
    ```json
    {
        "name": "Fabrizio",
        "related_entities": ["food:pizza_margherita"],
        "context_sentence": "Fabrizio che ama la pizza"
    }
    ```
    → Restituisce il "Fabrizio" che ha relazioni con pizza_margherita come best_match
    
    Example response:
    ```json
    {
        "query_name": "Fabrizio",
        "total_candidates": 2,
        "ambiguous": false,
        "best_match": {
            "entity": {
                "entity_id": "person:fabrizio_rossi",
                "primary_name": "Fabrizio Rossi",
                ...
            },
            "confidence": 0.92,
            "match_reasons": ["name_partial", "relation_match:food:pizza_margherita"],
            "matching_relations": [
                {"rel_id": "...", "relation_type": "sentiment", "target": "food:pizza_margherita"}
            ]
        },
        "candidates": [
            {
                "entity": {"entity_id": "person:fabrizio_rossi", ...},
                "confidence": 0.92,
                "match_reasons": ["name_partial", "relation_match:food:pizza_margherita"]
            },
            {
                "entity": {"entity_id": "person:fabrizio_bianchi", ...},
                "confidence": 0.45,
                "match_reasons": ["name_partial"]
            }
        ],
        "disambiguation_context": {
            "related_entities_provided": ["food:pizza_margherita"],
            "attributes_provided": null,
            "context_sentence_used": true
        }
    }
    ```
    
    `ambiguous` è true quando la differenza di score tra i top 2 candidati
    è inferiore a `ambiguity_threshold` (default 0.1).
    
    `has_inconsistencies` è true quando il best_match ha relazioni che esistono
    ma con target diversi da quelli attesi (es. sorella=Giovanna invece di Maria).
    """
    try:
        service = get_graph_service()
        
        # Converti ExpectedRelation models in dicts
        expected_relations_dicts = None
        if request.expected_relations:
            expected_relations_dicts = [
                {
                    "relation_type": er.relation_type,
                    "target_name": er.target_name,
                    "target_entity_id": er.target_entity_id
                }
                for er in request.expected_relations
            ]
        
        result = await service.disambiguate_entity(
            name=request.name,
            entity_type=request.entity_type,
            related_entities=request.related_entities,
            expected_relations=expected_relations_dicts,
            attributes=request.attributes,
            context_sentence=request.context_sentence,
            min_confidence=request.min_confidence,
            max_results=request.max_results,
            ambiguity_threshold=request.ambiguity_threshold
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in disambiguate_entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/normalization/test/{predicate}")
async def test_normalization(predicate: str):
    """
    Test endpoint per verificare come viene normalizzato un predicato.
    
    Example: GET /graph/normalization/test/esprimere_gradimento_per
    
    Returns:
    ```json
    {
        "predicate": "esprimere_gradimento_per",
        "normalized": {
            "relation_type": "sentiment",
            "valence": "positive",
            "intensity": 0.7,
            "method": "direct",
            "confidence": 0.95
        }
    }
    ```
    """
    try:
        service = get_graph_service()
        result = service.normalizer.normalize(predicate)
        return {
            "predicate": predicate,
            "normalized": result.to_dict()
        }
    except Exception as e:
        logger.error(f"Error testing normalization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/normalization/entity-type/{entity_name}")
async def test_entity_type_inference(
    entity_name: str,
    context: str = "",
    category: str = ""
):
    """
    Test endpoint per verificare come viene inferito il tipo di un'entità.
    
    Query params:
    - context: Contesto opzionale (frase in cui appare l'entità)
    - category: Hint opzionale da Thalamus (soggetto, luogo, oggetto, etc.)
    
    Examples:
    - GET /graph/normalization/entity-type/Marco%20Rossi
    - GET /graph/normalization/entity-type/Google?context=lavoro%20per%20Google
    - GET /graph/normalization/entity-type/Roma?category=luogo
    
    Returns:
    ```json
    {
        "entity_name": "Marco Rossi",
        "inferred_type": {
            "entity_type": "person",
            "confidence": 0.95,
            "method": "name_structure",
            "signals": ["name_structure:first=marco,last=rossi"],
            "alternative_types": []
        },
        "context_used": "",
        "hints_used": {}
    }
    ```
    """
    try:
        service = get_graph_service()
        
        hints = {"category": category} if category else None
        
        result = service.entity_type_normalizer.infer_type(
            entity_name=entity_name,
            context=context,
            hints=hints
        )
        
        return {
            "entity_name": entity_name,
            "inferred_type": result.to_dict(),
            "context_used": context,
            "hints_used": hints or {}
        }
    except Exception as e:
        logger.error(f"Error testing entity type inference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/normalization/entity-type-stats")
async def get_entity_type_normalizer_stats():
    """
    Statistiche dell'EntityTypeNormalizer.
    
    Returns:
    ```json
    {
        "direct_hits": 15,
        "pattern_hits": 8,
        "name_structure_hits": 45,
        "context_hits": 12,
        "embedding_hits": 3,
        "defaults": 2,
        "cache_hits": 100,
        "total_inferences": 85,
        "cache_size": 50
    }
    ```
    """
    try:
        service = get_graph_service()
        return service.entity_type_normalizer.get_stats()
    except Exception as e:
        logger.error(f"Error getting entity type normalizer stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Top-K Search Endpoints ====================

@router.post("/search/topk/episodic")
async def topk_episodic_search(request: TopKEpisodicRequest):
    """
    🔎 **Top-K search in Episodic Memory** (conversazioni passate)
    
    Cerca nelle conversazioni passate usando similarity semantica.
    
    Example request:
    ```json
    {
        "query": "pizza preferita",
        "k": 5,
        "user_id": "admin",
        "min_similarity": 0.3
    }
    ```
    
    Example response:
    ```json
    {
        "results": [
            {
                "content": "Mi piace molto la pizza margherita...",
                "similarity": 0.85,
                "metadata": {"session_id": "...", "timestamp": "..."},
                "id": "doc_123"
            }
        ],
        "count": 5,
        "query": "pizza preferita",
        "memory_type": "episodic"
    }
    ```
    """
    try:
        service = get_graph_service()
        result = await service.topk_episodic(
            query=request.query,
            k=request.k,
            user_id=request.user_id,
            session_id=request.session_id,
            time_range_hours=request.time_range_hours,
            min_similarity=request.min_similarity
        )
        return result
    except Exception as e:
        logger.error(f"Error in topk_episodic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/topk/semantic")
async def topk_semantic_search(request: TopKSemanticRequest):
    """
    🔎 **Top-K search in Semantic Memory** (documenti e conoscenze)
    
    Cerca nei documenti e conoscenze persistenti.
    
    Example request:
    ```json
    {
        "query": "ricetta carbonara",
        "k": 5,
        "user_id": "admin",
        "document_type": "recipe",
        "min_similarity": 0.4
    }
    ```
    
    Example response:
    ```json
    {
        "results": [
            {
                "content": "La carbonara si prepara con guanciale...",
                "similarity": 0.92,
                "metadata": {"source": "recipes.pdf", "type": "recipe"},
                "id": "doc_456",
                "source": "recipes.pdf"
            }
        ],
        "count": 3,
        "query": "ricetta carbonara",
        "memory_type": "semantic"
    }
    ```
    """
    try:
        service = get_graph_service()
        result = await service.topk_semantic(
            query=request.query,
            k=request.k,
            user_id=request.user_id,
            document_type=request.document_type,
            tags=request.tags,
            min_similarity=request.min_similarity
        )
        return result
    except Exception as e:
        logger.error(f"Error in topk_semantic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/topk/entities")
async def topk_entities_search(request: TopKEntitiesRequest):
    """
    🔎 **Top-K search nelle Entità** del Knowledge Graph
    
    Cerca entità per nome/alias con scoring basato su match quality.
    
    Example request:
    ```json
    {
        "query": "Fabr",
        "k": 5,
        "entity_type": "person",
        "include_aliases": true,
        "min_similarity": 0.3
    }
    ```
    
    Example response:
    ```json
    {
        "results": [
            {
                "entity": {
                    "entity_id": "person:fabrizio_rossi",
                    "type": "person",
                    "primary_name": "Fabrizio Rossi",
                    ...
                },
                "similarity": 0.95,
                "match_type": "partial"
            }
        ],
        "count": 2,
        "query": "Fabr",
        "memory_type": "entities"
    }
    ```
    """
    try:
        service = get_graph_service()
        result = await service.topk_entities(
            query=request.query,
            k=request.k,
            user_id=request.user_id,
            entity_type=request.entity_type,
            include_aliases=request.include_aliases,
            min_similarity=request.min_similarity
        )
        return result
    except Exception as e:
        logger.error(f"Error in topk_entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/topk/relationships")
async def topk_relationships_search(request: TopKRelationshipsRequest):
    """
    🔎 **Top-K search nelle Relazioni** del Knowledge Graph
    
    Cerca relazioni basandosi su source_sentence, predicato ed entità.
    
    Example request:
    ```json
    {
        "query": "pizza",
        "k": 10,
        "relation_type": "sentiment",
        "valence": "positive",
        "min_similarity": 0.3
    }
    ```
    
    Example response:
    ```json
    {
        "results": [
            {
                "relationship": {
                    "id": "rel:...",
                    "source_entity_id": "person:fabrizio",
                    "target_entity_id": "food:pizza_margherita",
                    "relation_type": "sentiment",
                    "valence": "positive",
                    "source_sentence": "Mi piace la pizza margherita"
                },
                "similarity": 0.88,
                "summary": "person:fabrizio → sentiment → food:pizza_margherita"
            }
        ],
        "count": 3,
        "query": "pizza",
        "memory_type": "relationships"
    }
    ```
    """
    try:
        service = get_graph_service()
        result = await service.topk_relationships(
            query=request.query,
            k=request.k,
            user_id=request.user_id,
            relation_type=request.relation_type,
            valence=request.valence,
            entity_id=request.entity_id,
            min_similarity=request.min_similarity
        )
        return result
    except Exception as e:
        logger.error(f"Error in topk_relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/topk/unified")
async def topk_unified_search(request: TopKUnifiedRequest):
    """
    🔎 **Top-K search UNIFICATA** su tutte le memorie
    
    Esegue ricerche parallele su tutte le memorie e combina i risultati.
    **Ideale per costruire contesto cognitivo completo.**
    
    Example request:
    ```json
    {
        "query": "Fabrizio pizza",
        "k_per_memory": 3,
        "user_id": "admin",
        "min_similarity": 0.3,
        "include_episodic": true,
        "include_semantic": true,
        "include_entities": true,
        "include_relationships": true
    }
    ```
    
    Example response:
    ```json
    {
        "episodic": {
            "results": [...],
            "count": 3,
            "memory_type": "episodic"
        },
        "semantic": {
            "results": [...],
            "count": 2,
            "memory_type": "semantic"
        },
        "entities": {
            "results": [
                {"entity": {"entity_id": "person:fabrizio", ...}, "similarity": 0.95}
            ],
            "count": 1,
            "memory_type": "entities"
        },
        "relationships": {
            "results": [
                {"relationship": {...}, "summary": "person:fabrizio → sentiment → food:pizza"}
            ],
            "count": 2,
            "memory_type": "relationships"
        },
        "total_results": 8,
        "query": "Fabrizio pizza",
        "k_per_memory": 3
    }
    ```
    
    **Uso tipico in Mind:**
    - EntityContextBuilder chiama questo endpoint per arricchire le entità
    - Prefrontal Cortex lo usa per raccogliere contesto per il reasoning
    - Learning Module cerca pattern nelle preferenze
    """
    try:
        service = get_graph_service()
        result = await service.topk_unified(
            query=request.query,
            k_per_memory=request.k_per_memory,
            user_id=request.user_id,
            min_similarity=request.min_similarity,
            include_episodic=request.include_episodic,
            include_semantic=request.include_semantic,
            include_entities=request.include_entities,
            include_relationships=request.include_relationships
        )
        return result
    except Exception as e:
        logger.error(f"Error in topk_unified: {e}")
        raise HTTPException(status_code=500, detail=str(e))
