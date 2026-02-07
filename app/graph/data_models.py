"""
Data Models for Entity Graph - Adapted for MindMemoryService

These dataclasses define the canonical structure for entities and relationships
in the Knowledge Graph.

Source: PramaIA-Mind/Mind/world_model/entity_graph_store.py
Adapted: February 2026
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class EntityType(str, Enum):
    """Types of entities in the knowledge graph"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    CONCEPT = "concept"
    OBJECT = "object"
    TIME = "time"
    TOOL = "tool"       # PDK tool/capability
    SELF = "self"       # Mind itself (singleton)
    FOOD = "food"       # Food items (pizza, etc.)
    UNKNOWN = "unknown"


class RelationCategory(str, Enum):
    """
    Normalized relation categories.
    
    MindMemoryService maps raw predicates to these categories:
    
    esprimere_gradimento_per → SENTIMENT (positive)
    amare → SENTIMENT (positive, high intensity)
    detestare → SENTIMENT (negative, high intensity)
    possedere → OWNERSHIP
    lavorare_presso → EMPLOYMENT
    abitare_in → LOCATION
    essere_figlio_di → FAMILY
    """
    SENTIMENT = "sentiment"          # Feelings, preferences, opinions
    OWNERSHIP = "ownership"          # Possessions, belongings
    EMPLOYMENT = "employment"        # Work relationships
    LOCATION = "location"            # Where entities are
    FAMILY = "family"                # Family relationships
    FRIENDSHIP = "friendship"        # Friend relationships
    PROFESSIONAL = "professional"    # Business relationships
    TEMPORAL = "temporal"            # Time-based relationships
    IDENTITY = "identity"            # Is-a, same-as relationships
    ATTRIBUTE = "attribute"          # Has-property relationships
    ASSOCIATION = "association"      # Generic association
    UNKNOWN = "unknown"              # Cannot categorize


@dataclass
class StoredEntity:
    """
    Persistent entity representation for storage.
    
    This is the canonical entity format stored in MindMemoryService.
    """
    id: str
    name: str
    canonical_name: str  # Normalized lowercase name for matching
    entity_type: EntityType
    aliases: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Memory enrichment (cached from episodic/semantic)
    memory_summary: str = ""
    last_interaction: Optional[str] = None
    interaction_count: int = 0
    sentiment_score: float = 0.0  # -1.0 to 1.0
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    confidence: float = 1.0
    source: str = "extraction"  # extraction, user_declared, inferred
    status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "name": self.name,
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type.value if isinstance(self.entity_type, EntityType) else self.entity_type,
            "aliases": self.aliases,
            "attributes": self.attributes,
            "memory_summary": self.memory_summary,
            "last_interaction": self.last_interaction,
            "interaction_count": self.interaction_count,
            "sentiment_score": self.sentiment_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "confidence": self.confidence,
            "source": self.source,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredEntity":
        """Create from dictionary"""
        entity_type = data.get("entity_type", "unknown")
        if isinstance(entity_type, str):
            try:
                entity_type = EntityType(entity_type)
            except ValueError:
                entity_type = EntityType.UNKNOWN
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            canonical_name=data.get("canonical_name", data.get("name", "").lower()),
            entity_type=entity_type,
            aliases=data.get("aliases", []),
            attributes=data.get("attributes", {}),
            memory_summary=data.get("memory_summary", ""),
            last_interaction=data.get("last_interaction"),
            interaction_count=data.get("interaction_count", 0),
            sentiment_score=data.get("sentiment_score", 0.0),
            created_at=data.get("created_at", datetime.utcnow().isoformat() + "Z"),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat() + "Z"),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", "extraction"),
            status=data.get("status", "active")
        )


@dataclass
class StoredRelationship:
    """
    Persistent relationship representation for storage.
    
    NORMALIZED FORMAT (v4.0):
    Instead of specific predicates (esprimere_gradimento_per, amare, detestare...),
    we use generic relation_type + metadata:
    
    - relation_type: "sentiment", "ownership", "employment", "location", etc.
    - metadata.valence: "positive", "negative", "neutral"
    - metadata.intensity: 0.0 - 1.0
    - metadata.aspect: "preference", "opinion", "emotion", etc.
    - original_predicate: preserved for reference
    """
    id: str
    source_entity_id: str
    target_entity_id: str
    
    # Normalized relation type (NOT raw predicate!)
    relation_type: str  # sentiment, ownership, employment, location, family, etc.
    
    # Original extraction (for debugging/learning)
    original_predicate: str  # Raw predicate from Thalamus
    predicate_surface: Optional[str] = None  # Surface form before canonicalization
    source_sentence: Optional[str] = None    # Original user sentence
    
    # Normalized metadata (varies by relation_type)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # For sentiment: {"valence": "positive", "intensity": 0.8, "aspect": "preference"}
    # For ownership: {"acquired_date": "...", "shared_with": [...]}
    # For employment: {"role": "developer", "since": "2020"}
    # For family: {"relation": "mother", "confirmed": True}
    
    # Relationship properties
    strength: float = 1.0  # 0.0 to 1.0, decays over time
    confidence: float = 1.0  # 0.0 to 1.0, extraction confidence
    bidirectional: bool = False
    
    # Evidence tracking
    evidence_count: int = 1
    last_evidence: Optional[str] = None
    
    # Temporal qualifiers (from Thalamus v3.0)
    valid_from: Optional[str] = None  # ISO date or null
    valid_to: Optional[str] = None    # null = still valid
    negation: bool = False             # "NON più", "NON è"
    modality: str = "asserted"         # asserted, uncertain, inferred, negated
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_reinforced: Optional[str] = None  # Last confirmation/mention
    source: str = "extraction"  # extraction, user_declared, inferred
    status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relation_type": self.relation_type,
            "original_predicate": self.original_predicate,
            "predicate_surface": self.predicate_surface,
            "source_sentence": self.source_sentence,
            "metadata": self.metadata,
            "strength": self.strength,
            "confidence": self.confidence,
            "bidirectional": self.bidirectional,
            "evidence_count": self.evidence_count,
            "last_evidence": self.last_evidence,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "negation": self.negation,
            "modality": self.modality,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_reinforced": self.last_reinforced,
            "source": self.source,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredRelationship":
        """Create from dictionary"""
        return cls(
            id=data.get("id", ""),
            source_entity_id=data.get("source_entity_id", data.get("from_entity_id", "")),
            target_entity_id=data.get("target_entity_id", data.get("to_entity_id", "")),
            relation_type=data.get("relation_type", data.get("type", "unknown")),
            original_predicate=data.get("original_predicate", data.get("predicate", "")),
            predicate_surface=data.get("predicate_surface"),
            source_sentence=data.get("source_sentence"),
            metadata=data.get("metadata", {}),
            strength=data.get("strength", 1.0),
            confidence=data.get("confidence", 1.0),
            bidirectional=data.get("bidirectional", False),
            evidence_count=data.get("evidence_count", 1),
            last_evidence=data.get("last_evidence"),
            valid_from=data.get("valid_from"),
            valid_to=data.get("valid_to"),
            negation=data.get("negation", False),
            modality=data.get("modality", "asserted"),
            created_at=data.get("created_at", datetime.utcnow().isoformat() + "Z"),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat() + "Z"),
            last_reinforced=data.get("last_reinforced"),
            source=data.get("source", "extraction"),
            status=data.get("status", "active")
        )


# ==================== PREDICATE NORMALIZATION HINTS ====================
# These are hints for implementing normalization in MindMemoryService

PREDICATE_TO_CATEGORY_HINTS: Dict[str, Dict[str, Any]] = {
    # Sentiment (positive)
    "esprimere_gradimento_per": {"category": "sentiment", "valence": "positive", "intensity": 0.7},
    "piacere": {"category": "sentiment", "valence": "positive", "intensity": 0.6},
    "amare": {"category": "sentiment", "valence": "positive", "intensity": 0.95},
    "adorare": {"category": "sentiment", "valence": "positive", "intensity": 0.9},
    "preferire": {"category": "sentiment", "valence": "positive", "intensity": 0.8, "aspect": "preference"},
    "apprezzare": {"category": "sentiment", "valence": "positive", "intensity": 0.7},
    "gradire": {"category": "sentiment", "valence": "positive", "intensity": 0.65},
    "desiderare": {"category": "sentiment", "valence": "positive", "intensity": 0.75, "aspect": "desire"},
    "volere": {"category": "sentiment", "valence": "positive", "intensity": 0.7, "aspect": "desire"},
    "interessare": {"category": "sentiment", "valence": "positive", "intensity": 0.6, "aspect": "interest"},
    
    # Sentiment (negative)
    "detestare": {"category": "sentiment", "valence": "negative", "intensity": 0.9},
    "odiare": {"category": "sentiment", "valence": "negative", "intensity": 0.95},
    "non_sopportare": {"category": "sentiment", "valence": "negative", "intensity": 0.85},
    "non_gradire": {"category": "sentiment", "valence": "negative", "intensity": 0.6},
    "disprezzare": {"category": "sentiment", "valence": "negative", "intensity": 0.8},
    "temere": {"category": "sentiment", "valence": "negative", "intensity": 0.7, "aspect": "fear"},
    "evitare": {"category": "sentiment", "valence": "negative", "intensity": 0.6, "aspect": "avoidance"},
    
    # Ownership
    "possedere": {"category": "ownership", "valence": "neutral", "intensity": 0.8},
    "avere": {"category": "ownership", "valence": "neutral", "intensity": 0.7},
    "appartenere_a": {"category": "ownership", "valence": "neutral", "intensity": 0.7, "direction": "reverse"},
    "comprare": {"category": "ownership", "valence": "neutral", "intensity": 0.8, "aspect": "acquisition"},
    "vendere": {"category": "ownership", "valence": "neutral", "intensity": 0.8, "aspect": "disposal"},
    
    # Employment
    "lavorare_presso": {"category": "employment", "valence": "neutral", "intensity": 0.8},
    "lavorare_per": {"category": "employment", "valence": "neutral", "intensity": 0.8},
    "essere_impiegato_da": {"category": "employment", "valence": "neutral", "intensity": 0.8},
    "dirigere": {"category": "employment", "valence": "neutral", "intensity": 0.9, "role": "manager"},
    "collaborare_con": {"category": "employment", "valence": "neutral", "intensity": 0.7, "aspect": "collaboration"},
    
    # Location
    "abitare_in": {"category": "location", "valence": "neutral", "intensity": 0.8, "type": "residence"},
    "vivere_a": {"category": "location", "valence": "neutral", "intensity": 0.8, "type": "residence"},
    "trovarsi_a": {"category": "location", "valence": "neutral", "intensity": 0.6, "type": "current"},
    "essere_nato_a": {"category": "location", "valence": "neutral", "intensity": 0.9, "type": "birth"},
    "risiedere_a": {"category": "location", "valence": "neutral", "intensity": 0.85, "type": "residence"},
    
    # Family
    "essere_figlio_di": {"category": "family", "valence": "neutral", "intensity": 0.95, "relation": "child"},
    "essere_padre_di": {"category": "family", "valence": "neutral", "intensity": 0.95, "relation": "father"},
    "essere_madre_di": {"category": "family", "valence": "neutral", "intensity": 0.95, "relation": "mother"},
    "essere_fratello_di": {"category": "family", "valence": "neutral", "intensity": 0.9, "relation": "sibling"},
    "essere_sorella_di": {"category": "family", "valence": "neutral", "intensity": 0.9, "relation": "sibling"},
    "essere_coniuge_di": {"category": "family", "valence": "neutral", "intensity": 0.95, "relation": "spouse"},
    "essere_sposato_con": {"category": "family", "valence": "neutral", "intensity": 0.95, "relation": "spouse"},
    
    # Friendship / Social
    "conoscere": {"category": "friendship", "valence": "neutral", "intensity": 0.5},
    "essere_amico_di": {"category": "friendship", "valence": "positive", "intensity": 0.8},
    "frequentare": {"category": "friendship", "valence": "neutral", "intensity": 0.6},
    
    # Professional
    "essere_cliente_di": {"category": "professional", "valence": "neutral", "intensity": 0.7, "role": "client"},
    "essere_fornitore_di": {"category": "professional", "valence": "neutral", "intensity": 0.7, "role": "supplier"},
    "essere_commercialista_di": {"category": "professional", "valence": "neutral", "intensity": 0.8, "role": "accountant"},
    "essere_medico_di": {"category": "professional", "valence": "neutral", "intensity": 0.8, "role": "doctor"},
    "essere_avvocato_di": {"category": "professional", "valence": "neutral", "intensity": 0.8, "role": "lawyer"},
    
    # Identity / Attribute
    "essere": {"category": "identity", "valence": "neutral", "intensity": 0.9},
    "chiamarsi": {"category": "identity", "valence": "neutral", "intensity": 0.95, "aspect": "name"},
}

# For unknown predicates, use embedding similarity to these category exemplars
CATEGORY_EXEMPLARS: Dict[str, List[str]] = {
    "sentiment": ["piacere", "amare", "odiare", "preferire", "apprezzare", "gradire", "detestare", "adorare"],
    "ownership": ["possedere", "avere", "appartenere", "comprare", "vendere", "proprietà"],
    "employment": ["lavorare", "impiegare", "dirigere", "assumere", "licenziare", "collaborare"],
    "location": ["abitare", "vivere", "trovarsi", "stare", "risiedere", "nascere"],
    "family": ["figlio", "padre", "madre", "fratello", "sorella", "coniuge", "sposato", "parente"],
    "friendship": ["amico", "conoscere", "frequentare", "amicizia"],
    "professional": ["cliente", "fornitore", "commercialista", "medico", "avvocato", "consulente"],
    "identity": ["essere", "chiamarsi", "nome", "identità"],
}


# ==================== RELATIONSHIP EVENT MODEL ====================

@dataclass
class RelationshipEvent:
    """
    Event log entry for relationship changes.
    
    Tracks the history of changes to a relationship over time.
    The relationship table holds the CURRENT state (last value wins),
    while this event log holds the full history.
    
    This enables:
    - "What does user feel NOW about X?" → relationships table
    - "How has the feeling changed over time?" → relationship_events table
    - "Is the relationship stable?" → STDDEV(valence) over events
    - "When did the opinion change?" → events with sign change
    """
    event_id: str
    rel_id: str  # Foreign key to relationships.rel_id
    
    # Event data
    predicate: str  # The raw predicate for this event (ama, odia, etc.)
    valence: float  # Numeric valence: -1.0 (negative) to +1.0 (positive)
    intensity: float  # 0.0 to 1.0
    source_sentence: Optional[str] = None  # Original sentence that triggered this event
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    normalization_method: str = "direct"  # direct, partial, embedding
    normalization_confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "event_id": self.event_id,
            "rel_id": self.rel_id,
            "predicate": self.predicate,
            "valence": self.valence,
            "intensity": self.intensity,
            "source_sentence": self.source_sentence,
            "timestamp": self.timestamp,
            "normalization_method": self.normalization_method,
            "normalization_confidence": self.normalization_confidence,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipEvent":
        """Create from dictionary"""
        return cls(
            event_id=data.get("event_id", ""),
            rel_id=data.get("rel_id", ""),
            predicate=data.get("predicate", ""),
            valence=data.get("valence", 0.0),
            intensity=data.get("intensity", 0.5),
            source_sentence=data.get("source_sentence"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            normalization_method=data.get("normalization_method", "direct"),
            normalization_confidence=data.get("normalization_confidence", 1.0),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_row(cls, row) -> "RelationshipEvent":
        """Create from SQLite row"""
        metadata = {}
        if row["metadata_json"]:
            try:
                metadata = json.loads(row["metadata_json"])
            except:
                pass
        
        return cls(
            event_id=row["event_id"],
            rel_id=row["rel_id"],
            predicate=row["predicate"],
            valence=row["valence"],
            intensity=row["intensity"],
            source_sentence=row["source_sentence"],
            timestamp=row["timestamp"],
            normalization_method=row["normalization_method"],
            normalization_confidence=row["normalization_confidence"],
            metadata=metadata
        )
