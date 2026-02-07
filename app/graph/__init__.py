"""
Graph Module - Gestione Knowledge Graph (Entità, Relazioni, Normalizzazione)

Questo modulo fornisce:
- Data models per entità e relazioni (StoredEntity, StoredRelationship)
- Normalizzazione predicati RAW → categorie semantiche
- Normalizzazione tipi entità (nome → persona/organizzazione/luogo/...)
- Decay service per decadimento confidence/strength
- Query avanzate per pattern detection

Migrato da PramaIA-Mind/world_model/
"""

from app.graph.data_models import (
    EntityType,
    RelationCategory,
    StoredEntity,
    StoredRelationship,
    RelationshipEvent,
    PREDICATE_TO_CATEGORY_HINTS,
    CATEGORY_EXEMPLARS
)

from app.graph.predicate_normalizer import PredicateNormalizer, get_predicate_normalizer
from app.graph.entity_type_normalizer import EntityTypeNormalizer, EntityTypeResult, get_entity_type_normalizer

__all__ = [
    "EntityType",
    "RelationCategory", 
    "StoredEntity",
    "StoredRelationship",
    "RelationshipEvent",
    "PREDICATE_TO_CATEGORY_HINTS",
    "CATEGORY_EXEMPLARS",
    "PredicateNormalizer",
    "get_predicate_normalizer",
    "EntityTypeNormalizer",
    "EntityTypeResult",
    "get_entity_type_normalizer"
]
