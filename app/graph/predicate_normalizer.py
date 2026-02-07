"""
Predicate Normalizer - Normalizzazione predicati RAW in categorie semantiche

Questo modulo converte predicati raw da Thalamus (es. "esprimere_gradimento_per")
in categorie normalizzate (es. "sentiment" con valence="positive").

Metodi di normalizzazione:
1. Lookup diretto: mapping predicati noti → categoria
2. Partial match: cerca keyword nel predicato
3. Embedding similarity: per predicati sconosciuti (fallback)

Author: MindMemoryService Team
Date: February 2026
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

from app.graph.data_models import (
    RelationCategory,
    PREDICATE_TO_CATEGORY_HINTS,
    CATEGORY_EXEMPLARS
)

logger = logging.getLogger(__name__)


@dataclass
class NormalizationResult:
    """Risultato della normalizzazione di un predicato"""
    relation_type: str          # Categoria normalizzata (sentiment, ownership, etc.)
    valence: str                # positive, negative, neutral
    intensity: float            # 0.0 - 1.0
    metadata: Dict[str, Any]    # Metadata aggiuntivi (aspect, role, etc.)
    method: str                 # direct, partial, embedding, default
    confidence: float           # Confidence della normalizzazione

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relation_type": self.relation_type,
            "valence": self.valence,
            "intensity": self.intensity,
            "metadata": self.metadata,
            "method": self.method,
            "confidence": self.confidence
        }


class PredicateNormalizer:
    """
    Normalizza predicati RAW da Thalamus in categorie semantiche.
    
    Usage:
        normalizer = PredicateNormalizer()
        result = normalizer.normalize("esprimere_gradimento_per")
        # → NormalizationResult(relation_type="sentiment", valence="positive", ...)
    """
    
    def __init__(self, use_embeddings: bool = True):
        """
        Initialize PredicateNormalizer.
        
        Args:
            use_embeddings: Se True, usa embedding similarity per predicati sconosciuti
        """
        self.use_embeddings = use_embeddings
        self._cache: Dict[str, NormalizationResult] = {}
        
        # Embedding function (lazy loading)
        self._embedding_function = None
        self._category_embeddings: Optional[Dict[str, Any]] = None
        
        # Statistiche
        self.stats = {
            "direct_hits": 0,
            "partial_hits": 0,
            "embedding_hits": 0,
            "defaults": 0,
            "cache_hits": 0
        }
        
        logger.info("PredicateNormalizer initialized")
    
    def _get_embedding_function(self):
        """Lazy loading dell'embedding function"""
        if self._embedding_function is None and self.use_embeddings:
            try:
                from chromadb.utils import embedding_functions
                self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name='paraphrase-multilingual-MiniLM-L12-v2',
                    normalize_embeddings=True
                )
                logger.info("Embedding function loaded for predicate normalization")
            except Exception as e:
                logger.warning(f"Could not load embedding function: {e}")
                self.use_embeddings = False
        return self._embedding_function
    
    def _compute_category_embeddings(self):
        """Calcola embeddings per ogni categoria (una volta)"""
        if self._category_embeddings is not None:
            return self._category_embeddings
        
        ef = self._get_embedding_function()
        if ef is None:
            return None
        
        self._category_embeddings = {}
        for category, exemplars in CATEGORY_EXEMPLARS.items():
            # Calcola embedding medio degli exemplars
            text = " ".join(exemplars)
            try:
                embedding = ef([text])[0]
                self._category_embeddings[category] = embedding
            except Exception as e:
                logger.warning(f"Could not compute embedding for category {category}: {e}")
        
        logger.info(f"Computed embeddings for {len(self._category_embeddings)} categories")
        return self._category_embeddings
    
    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calcola cosine similarity tra due vettori"""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def normalize(self, predicate: str) -> NormalizationResult:
        """
        Normalizza un predicato RAW in categoria semantica.
        
        Args:
            predicate: Predicato raw da Thalamus (es. "esprimere_gradimento_per")
            
        Returns:
            NormalizationResult con categoria, valence, intensity e metadata
        """
        # Normalizza il predicato (lowercase, rimuovi spazi extra)
        predicate_clean = predicate.lower().strip().replace(" ", "_")
        
        # Check cache
        if predicate_clean in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[predicate_clean]
        
        # 1. Direct lookup
        result = self._try_direct_lookup(predicate_clean)
        if result:
            self.stats["direct_hits"] += 1
            self._cache[predicate_clean] = result
            return result
        
        # 2. Partial match (cerca keyword nel predicato)
        result = self._try_partial_match(predicate_clean)
        if result:
            self.stats["partial_hits"] += 1
            self._cache[predicate_clean] = result
            return result
        
        # 3. Embedding similarity (se abilitato)
        if self.use_embeddings:
            result = self._try_embedding_similarity(predicate_clean)
            if result:
                self.stats["embedding_hits"] += 1
                self._cache[predicate_clean] = result
                return result
        
        # 4. Default fallback
        self.stats["defaults"] += 1
        result = NormalizationResult(
            relation_type=RelationCategory.UNKNOWN.value,
            valence="neutral",
            intensity=0.5,
            metadata={"original": predicate},
            method="default",
            confidence=0.3
        )
        self._cache[predicate_clean] = result
        return result
    
    def _try_direct_lookup(self, predicate: str) -> Optional[NormalizationResult]:
        """Prova lookup diretto nel mapping"""
        if predicate in PREDICATE_TO_CATEGORY_HINTS:
            hint = PREDICATE_TO_CATEGORY_HINTS[predicate]
            return NormalizationResult(
                relation_type=hint.get("category", RelationCategory.UNKNOWN.value),
                valence=hint.get("valence", "neutral"),
                intensity=hint.get("intensity", 0.7),
                metadata={k: v for k, v in hint.items() if k not in ["category", "valence", "intensity"]},
                method="direct",
                confidence=0.95
            )
        return None
    
    def _try_partial_match(self, predicate: str) -> Optional[NormalizationResult]:
        """Cerca keyword nel predicato per match parziale"""
        
        # Pattern per sentiment positive (preferenze, gusti)
        positive_patterns = [
            (r"(piacere|piace)", 0.7),
            (r"(amare|amo|ama)", 0.95),
            (r"(adorare|adoro|adora)", 0.9),
            (r"(preferire|preferisco|preferisce)", 0.8),
            (r"(preferit[oa])", 0.8),  # colore_preferito, pizza_preferita
            (r"(colore_preferito|cibo_preferito|piatto_preferito)", 0.85),
            (r"(dichiarare.*preferit)", 0.8),  # dichiarare_colore_preferito
            (r"(apprezzare|apprezzo|apprezza)", 0.7),
            (r"(gradire|gradisco|gradisce)", 0.65),
            (r"(gradimento)", 0.7),
            (r"(volere|voglio|vuole)", 0.7),
            (r"(desiderare|desidero|desidera)", 0.75),
            (r"(favorit[oa])", 0.8),  # favorito/favorita
        ]
        
        for pattern, intensity in positive_patterns:
            if re.search(pattern, predicate):
                return NormalizationResult(
                    relation_type=RelationCategory.SENTIMENT.value,
                    valence="positive",
                    intensity=intensity,
                    metadata={"matched_pattern": pattern},
                    method="partial",
                    confidence=0.8
                )
        
        # Pattern per sentiment negative
        negative_patterns = [
            (r"(odiare|odio|odia)", 0.95),
            (r"(detestare|detesto|detesta)", 0.9),
            (r"(disprezzare|disprezzo|disprezza)", 0.8),
            (r"(non_sopportare|non_sopporto)", 0.85),
            (r"(temere|temo|teme)", 0.7),
            (r"(evitare|evito|evita)", 0.6),
        ]
        
        for pattern, intensity in negative_patterns:
            if re.search(pattern, predicate):
                return NormalizationResult(
                    relation_type=RelationCategory.SENTIMENT.value,
                    valence="negative",
                    intensity=intensity,
                    metadata={"matched_pattern": pattern},
                    method="partial",
                    confidence=0.8
                )
        
        # Pattern per ownership
        ownership_patterns = [
            (r"(possedere|possiedo|possiede)", 0.8),
            (r"(avere|ho|ha)(?!.*amico)", 0.7),  # "avere" ma non "avere come amico"
            (r"(comprare|compro|compra)", 0.8),
            (r"(acquistare|acquisto|acquista)", 0.8),
        ]
        
        for pattern, intensity in ownership_patterns:
            if re.search(pattern, predicate):
                return NormalizationResult(
                    relation_type=RelationCategory.OWNERSHIP.value,
                    valence="neutral",
                    intensity=intensity,
                    metadata={"matched_pattern": pattern},
                    method="partial",
                    confidence=0.75
                )
        
        # Pattern per location
        location_patterns = [
            (r"(abitare|abito|abita)", 0.8),
            (r"(vivere|vivo|vive)_(?:a|in)", 0.8),
            (r"(trovarsi|mi_trovo|si_trova)", 0.6),
            (r"(risiedere|risiedo|risiede)", 0.85),
            (r"(nato_a|nascere)", 0.9),
        ]
        
        for pattern, intensity in location_patterns:
            if re.search(pattern, predicate):
                return NormalizationResult(
                    relation_type=RelationCategory.LOCATION.value,
                    valence="neutral",
                    intensity=intensity,
                    metadata={"matched_pattern": pattern},
                    method="partial",
                    confidence=0.75
                )
        
        # Pattern per employment
        employment_patterns = [
            (r"(lavorare|lavoro|lavora)", 0.8),
            (r"(impiegare|impiego|impiega)", 0.8),
            (r"(dirigere|dirigo|dirige)", 0.9),
            (r"(collaborare|collaboro|collabora)", 0.7),
        ]
        
        for pattern, intensity in employment_patterns:
            if re.search(pattern, predicate):
                return NormalizationResult(
                    relation_type=RelationCategory.EMPLOYMENT.value,
                    valence="neutral",
                    intensity=intensity,
                    metadata={"matched_pattern": pattern},
                    method="partial",
                    confidence=0.75
                )
        
        # Pattern per family
        family_patterns = [
            (r"(figlio|figlia)", 0.95),
            (r"(padre|papà)", 0.95),
            (r"(madre|mamma)", 0.95),
            (r"(fratello|sorella)", 0.9),
            (r"(coniuge|sposato|sposata|marito|moglie)", 0.95),
            (r"(nonno|nonna|zio|zia|cugino|cugina)", 0.85),
        ]
        
        for pattern, intensity in family_patterns:
            if re.search(pattern, predicate):
                return NormalizationResult(
                    relation_type=RelationCategory.FAMILY.value,
                    valence="neutral",
                    intensity=intensity,
                    metadata={"matched_pattern": pattern},
                    method="partial",
                    confidence=0.85
                )
        
        # Pattern per professional
        professional_patterns = [
            (r"(cliente)", 0.7),
            (r"(fornitore)", 0.7),
            (r"(commercialista|contabile)", 0.8),
            (r"(medico|dottore)", 0.8),
            (r"(avvocato|legale)", 0.8),
            (r"(consulente)", 0.75),
        ]
        
        for pattern, intensity in professional_patterns:
            if re.search(pattern, predicate):
                return NormalizationResult(
                    relation_type=RelationCategory.PROFESSIONAL.value,
                    valence="neutral",
                    intensity=intensity,
                    metadata={"matched_pattern": pattern},
                    method="partial",
                    confidence=0.75
                )
        
        # Pattern per friendship
        friendship_patterns = [
            (r"(amico|amica|amicizia)", 0.8),
            (r"(conoscere|conosco|conosce)", 0.5),
            (r"(frequentare|frequento|frequenta)", 0.6),
        ]
        
        for pattern, intensity in friendship_patterns:
            if re.search(pattern, predicate):
                return NormalizationResult(
                    relation_type=RelationCategory.FRIENDSHIP.value,
                    valence="neutral",
                    intensity=intensity,
                    metadata={"matched_pattern": pattern},
                    method="partial",
                    confidence=0.7
                )
        
        return None
    
    def _try_embedding_similarity(self, predicate: str) -> Optional[NormalizationResult]:
        """Usa embedding similarity per predicati sconosciuti"""
        ef = self._get_embedding_function()
        if ef is None:
            return None
        
        category_embeddings = self._compute_category_embeddings()
        if not category_embeddings:
            return None
        
        try:
            # Calcola embedding del predicato
            # Converti underscore in spazi per migliore embedding
            predicate_text = predicate.replace("_", " ")
            predicate_embedding = ef([predicate_text])[0]
            
            # Trova categoria più simile
            best_category = None
            best_similarity = -1.0
            
            for category, cat_embedding in category_embeddings.items():
                similarity = self._cosine_similarity(predicate_embedding, cat_embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_category = category
            
            # Se similarity è troppo bassa, ritorna None
            if best_similarity < 0.3:
                return None
            
            # Determina valence basato su keyword
            valence = "neutral"
            if best_category == "sentiment":
                # Cerca indicatori di positività/negatività
                if any(neg in predicate for neg in ["non", "odio", "detest", "disprezz"]):
                    valence = "negative"
                else:
                    valence = "positive"  # Default per sentiment
            
            return NormalizationResult(
                relation_type=best_category,
                valence=valence,
                intensity=min(0.9, best_similarity),  # Cap a 0.9 per embedding match
                metadata={"similarity": round(best_similarity, 3)},
                method="embedding",
                confidence=round(best_similarity * 0.8, 2)  # Confidence più bassa per embedding
            )
            
        except Exception as e:
            logger.warning(f"Embedding similarity failed for '{predicate}': {e}")
            return None
    
    def get_stats(self) -> Dict[str, int]:
        """Ritorna statistiche di normalizzazione"""
        return self.stats.copy()
    
    def clear_cache(self):
        """Pulisce la cache"""
        self._cache.clear()
        logger.info("PredicateNormalizer cache cleared")


# Singleton instance
_normalizer_instance: Optional[PredicateNormalizer] = None

def get_predicate_normalizer(use_embeddings: bool = True) -> PredicateNormalizer:
    """Get or create singleton PredicateNormalizer instance"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = PredicateNormalizer(use_embeddings=use_embeddings)
    return _normalizer_instance
