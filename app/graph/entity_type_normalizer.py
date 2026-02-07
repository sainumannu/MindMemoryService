"""
Entity Type Normalizer - Inferenza tipo entità basata su Embedding Similarity

Questo modulo inferisce il tipo di un'entità (persona, organizzazione, luogo, etc.)
usando EMBEDDING SIMILARITY come metodo primario, con regole come validazione/boost.

Architettura:
1. **Embedding Similarity** (PRIMARIO): Confronta nome+contesto con exemplars di ogni tipo
2. **Rule Validation**: Regole usate per confermare/boostare il risultato embedding
3. **Fallback**: Default a UNKNOWN con bassa confidence

Progettato per futura integrazione con LLM locale per migliorare accuracy.

Author: MindMemoryService Team
Date: February 2026
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from app.graph.data_models import EntityType

logger = logging.getLogger(__name__)


@dataclass
class EntityTypeResult:
    """Risultato della classificazione del tipo di entità"""
    entity_type: EntityType         # Tipo inferito
    confidence: float               # 0.0 - 1.0
    method: str                     # embedding, embedding+rules, llm, default
    signals: List[str] = field(default_factory=list)  # Segnali che hanno portato alla decisione
    alternative_types: List[Tuple[EntityType, float]] = field(default_factory=list)  # Altri tipi possibili
    embedding_scores: Dict[str, float] = field(default_factory=dict)  # Scores per debug
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type.value,
            "confidence": self.confidence,
            "method": self.method,
            "signals": self.signals,
            "alternative_types": [(t.value, c) for t, c in self.alternative_types],
            "embedding_scores": {k: round(v, 4) for k, v in self.embedding_scores.items()}
        }


# ==================== EMBEDDING EXEMPLARS (PRIMARIO) ====================
# Questi exemplars definiscono il "concetto" di ogni tipo tramite esempi rappresentativi.
# L'embedding similarity confronta l'entità query con questi exemplars.

TYPE_EXEMPLARS: Dict[EntityType, List[str]] = {
    EntityType.PERSON: [
        # Nomi propri
        "Marco Rossi", "Maria Bianchi", "Giuseppe Verdi", "Anna Ferrari",
        "Fabrizio", "Giulia", "Alessandro", "Francesca",
        # Ruoli/descrizioni
        "il dottore", "mia moglie", "il cliente", "un amico",
        "la professoressa", "il collega", "mio padre", "sua sorella",
        "il paziente", "l'avvocato", "lo studente", "la segretaria",
        # Pattern comuni
        "una persona di nome", "qualcuno chiamato", "un uomo", "una donna"
    ],
    EntityType.ORGANIZATION: [
        # Aziende tech
        "Google", "Microsoft", "Apple", "Amazon", "Meta", "Netflix",
        # Aziende italiane
        "Fiat", "Ferrari", "Eni", "Enel", "Telecom Italia", "Intesa Sanpaolo",
        "Unicredit", "Generali", "Poste Italiane", "Alitalia",
        # Pattern
        "l'azienda", "la società", "il gruppo", "la ditta",
        "una startup", "la multinazionale", "l'impresa", "la compagnia",
        "Banca X", "Assicurazione Y", "S.p.A.", "S.r.l.",
        # Istituzioni
        "Università di Milano", "Ospedale San Raffaele", "Comune di Roma"
    ],
    EntityType.LOCATION: [
        # Città
        "Roma", "Milano", "Napoli", "Torino", "Firenze", "Venezia",
        "New York", "Londra", "Parigi", "Tokyo",
        # Indirizzi
        "Via Garibaldi 15", "Piazza del Duomo", "Corso Vittorio Emanuele",
        "Via Roma", "Viale della Repubblica",
        # Pattern
        "l'ufficio", "casa mia", "il ristorante", "l'aeroporto",
        "la stazione", "il negozio", "l'hotel", "il centro commerciale",
        "un luogo chiamato", "il posto dove", "la sede di"
    ],
    EntityType.OBJECT: [
        # Veicoli
        "la mia auto", "la BMW", "la moto", "la bici",
        # Dispositivi
        "il portatile", "l'iPhone", "il computer", "lo smartphone", "il tablet",
        # Oggetti comuni
        "la borsa", "l'orologio", "il documento", "la valigia",
        "il libro", "la chiave", "il portafoglio",
        # Pattern
        "un oggetto", "una cosa", "il mio", "la mia"
    ],
    EntityType.EVENT: [
        # Eventi specifici
        "la riunione di domani", "il matrimonio di Luca", "la conferenza",
        "il meeting", "l'appuntamento delle 15", "la festa di compleanno",
        # Pattern
        "un evento", "l'incontro", "la presentazione", "il corso",
        "la lezione", "il concerto", "la partita", "il viaggio"
    ],
    EntityType.FOOD: [
        # Piatti
        "pizza margherita", "pasta al pomodoro", "lasagne", "risotto",
        "tiramisù", "carbonara", "amatriciana", "parmigiana",
        # Bevande
        "caffè espresso", "vino rosso", "birra", "cappuccino",
        # Pattern
        "un piatto di", "qualcosa da mangiare", "cibo", "il pranzo",
        "la cena", "la colazione", "uno spuntino"
    ],
    EntityType.TIME: [
        # Momenti
        "domani", "ieri", "la prossima settimana", "il mese scorso",
        "lunedì", "alle 15:00", "nel 2025", "questa mattina",
        # Pattern
        "un momento", "il periodo", "la data", "l'ora",
        "quando", "il giorno in cui"
    ],
    EntityType.CONCEPT: [
        # Idee astratte
        "l'idea di", "il concetto di", "la teoria", "il principio",
        "la strategia", "il metodo", "l'approccio", "la filosofia",
        # Pattern
        "un progetto", "un piano", "un obiettivo", "un problema",
        "una soluzione", "una decisione"
    ],
    EntityType.TOOL: [
        # Strumenti software/PDK
        "lo strumento", "il tool", "l'applicazione", "il software",
        "la funzione", "il comando", "l'API", "il servizio"
    ]
}

# ==================== RULE VALIDATORS (SECONDARIO - per boost) ====================
# Queste regole NON determinano il tipo, ma possono BOOSTARE la confidence
# quando l'embedding già suggerisce un tipo.

# Pattern regex per validazione
ORGANIZATION_PATTERNS = [
    r".*\s+(s\.?p\.?a\.?|s\.?r\.?l\.?|s\.?n\.?c\.?|s\.?a\.?s\.?)$",
    r".*\s+(inc\.?|corp\.?|ltd\.?|llc\.?|gmbh\.?)$",
    r"^(università|politecnico|istituto|ospedale|banca|banco)\s+",
]

LOCATION_PATTERNS = [
    r"^(via|viale|piazza|corso|largo|vicolo)\s+",
    r"^(strada|contrada|località)\s+",
]

PERSON_PATTERNS = [
    r"^(dott\.?|dr\.?|prof\.?|ing\.?|avv\.?|sig\.?)\s+",
    r"^(signor|signora|mister|mr\.?|mrs\.?)\s+",
]

# Nomi propri italiani (per boost PERSON)
ITALIAN_FIRST_NAMES = {
    "marco", "luca", "giuseppe", "giovanni", "francesco", "andrea", "alessandro",
    "stefano", "matteo", "lorenzo", "roberto", "riccardo", "fabio", "fabrizio",
    "paolo", "massimo", "davide", "simone", "antonio", "mario", "pietro",
    "maria", "giulia", "francesca", "anna", "sara", "laura", "valentina",
    "chiara", "federica", "elena", "alessandra", "silvia", "martina", "elisa"
}


class EntityTypeNormalizer:
    """
    Inferisce il tipo di un'entità usando EMBEDDING SIMILARITY come metodo primario.
    
    Architettura Embedding-First:
    1. Calcola embedding di (nome + contesto)
    2. Confronta con embedding medi di ogni tipo (da exemplars)
    3. Applica regole per boost/validazione (opzionale)
    4. Ritorna tipo con confidence più alta
    
    Progettato per futura integrazione con LLM locale.
    
    Usage:
        normalizer = EntityTypeNormalizer()
        result = normalizer.infer_type("Marco Rossi", context="il mio collega Marco")
        # → EntityTypeResult(entity_type=PERSON, confidence=0.87, method="embedding")
    """
    
    def __init__(self, use_rule_boost: bool = True):
        """
        Initialize EntityTypeNormalizer.
        
        Args:
            use_rule_boost: Se True, usa regole per boost confidence (non per determinare tipo)
        """
        self.use_rule_boost = use_rule_boost
        self._cache: Dict[str, EntityTypeResult] = {}
        
        # Embedding function (lazy loading)
        self._embedding_function = None
        self._type_embeddings: Optional[Dict[EntityType, List[float]]] = None
        self._embeddings_ready = False
        
        # Compile regex patterns per boost
        self._org_patterns = [re.compile(p, re.IGNORECASE) for p in ORGANIZATION_PATTERNS]
        self._loc_patterns = [re.compile(p, re.IGNORECASE) for p in LOCATION_PATTERNS]
        self._person_patterns = [re.compile(p, re.IGNORECASE) for p in PERSON_PATTERNS]
        
        # Statistics
        self.stats = {
            "embedding_inferences": 0,
            "rule_boosts": 0,
            "cache_hits": 0,
            "fallbacks": 0,
            "llm_inferences": 0  # Per futuro LLM
        }
        
        logger.info("EntityTypeNormalizer initialized (embedding-first mode)")
    
    def _get_embedding_function(self):
        """Lazy loading dell'embedding function"""
        if self._embedding_function is None:
            try:
                from chromadb.utils import embedding_functions
                self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name='paraphrase-multilingual-MiniLM-L12-v2',
                    normalize_embeddings=True
                )
                logger.info("Embedding function loaded for entity type inference")
            except Exception as e:
                logger.error(f"CRITICAL: Could not load embedding function: {e}")
                raise RuntimeError(f"Embedding function required but failed to load: {e}")
        return self._embedding_function
    
    def _ensure_type_embeddings(self):
        """Pre-calcola embeddings medi per ogni tipo (lazy, una volta)"""
        if self._embeddings_ready:
            return
        
        emb_fn = self._get_embedding_function()
        self._type_embeddings = {}
        
        logger.info("Pre-computing type embeddings from exemplars...")
        
        for entity_type, exemplars in TYPE_EXEMPLARS.items():
            try:
                # Calcola embedding per ogni exemplar
                embeddings = emb_fn(exemplars)
                
                # Media degli embedding
                num_dims = len(embeddings[0])
                avg_embedding = [
                    sum(emb[i] for emb in embeddings) / len(embeddings)
                    for i in range(num_dims)
                ]
                
                self._type_embeddings[entity_type] = avg_embedding
                logger.debug(f"Computed embedding for {entity_type.value} ({len(exemplars)} exemplars)")
                
            except Exception as e:
                logger.warning(f"Failed to compute embedding for {entity_type.value}: {e}")
        
        self._embeddings_ready = True
        logger.info(f"Type embeddings ready ({len(self._type_embeddings)} types)")
    
    def infer_type(
        self,
        entity_name: str,
        context: str = "",
        hints: Optional[Dict[str, Any]] = None
    ) -> EntityTypeResult:
        """
        Inferisce il tipo di un'entità usando embedding similarity.
        
        Args:
            entity_name: Nome dell'entità (es. "Marco Rossi", "Google", "Roma")
            context: Contesto opzionale (frase in cui appare l'entità)
            hints: Hint opzionali (es. {"category": "soggetto"} da Thalamus)
            
        Returns:
            EntityTypeResult con tipo, confidence, scores embedding
        """
        # Cache check
        cache_key = f"{entity_name.lower()}|{context[:100] if context else ''}"
        if cache_key in self._cache:
            self.stats["cache_hits"] += 1
            return self._cache[cache_key]
        
        signals: List[str] = []
        
        # ===== STEP 1: EMBEDDING SIMILARITY (PRIMARIO) =====
        try:
            self._ensure_type_embeddings()
            
            # Costruisci query: nome + contesto
            if context:
                query = f"{entity_name} - {context[:150]}"
            else:
                query = entity_name
            
            # Calcola embedding query
            emb_fn = self._get_embedding_function()
            query_embedding = list(emb_fn([query])[0])
            
            # Calcola similarity con ogni tipo
            similarities: Dict[EntityType, float] = {}
            if self._type_embeddings:
                for entity_type, type_embedding in self._type_embeddings.items():
                    sim = self._cosine_similarity(query_embedding, type_embedding)
                    similarities[entity_type] = sim
            
            # Ordina per similarity
            sorted_types = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            best_type, best_sim = sorted_types[0]
            
            signals.append(f"embedding_top:{best_type.value}={best_sim:.3f}")
            
            # ===== STEP 2: RULE BOOST (opzionale) =====
            confidence = best_sim
            method = "embedding"
            
            if self.use_rule_boost:
                boost = self._calculate_rule_boost(entity_name, best_type)
                if boost > 0:
                    confidence = min(0.98, confidence + boost)
                    method = "embedding+rules"
                    signals.append(f"rule_boost:+{boost:.2f}")
                    self.stats["rule_boosts"] += 1
            
            # ===== STEP 3: VALIDA RISULTATO =====
            # Se confidence troppo bassa, considera UNKNOWN
            if confidence < 0.35:
                signals.append("low_confidence_fallback")
                self.stats["fallbacks"] += 1
                result = EntityTypeResult(
                    entity_type=EntityType.UNKNOWN,
                    confidence=confidence,
                    method="fallback",
                    signals=signals,
                    alternative_types=[(t, s) for t, s in sorted_types[:3]],
                    embedding_scores={t.value: s for t, s in similarities.items()}
                )
            else:
                self.stats["embedding_inferences"] += 1
                result = EntityTypeResult(
                    entity_type=best_type,
                    confidence=round(confidence, 3),
                    method=method,
                    signals=signals,
                    alternative_types=[(t, s) for t, s in sorted_types[1:4] if s >= 0.25],
                    embedding_scores={t.value: round(s, 4) for t, s in similarities.items()}
                )
            
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Embedding inference failed: {e}")
            # Fallback totale
            self.stats["fallbacks"] += 1
            return EntityTypeResult(
                entity_type=EntityType.UNKNOWN,
                confidence=0.2,
                method="error_fallback",
                signals=[f"error:{str(e)[:50]}"]
            )
    
    def _calculate_rule_boost(self, entity_name: str, suggested_type: EntityType) -> float:
        """
        Calcola boost basato su regole per CONFERMARE il tipo suggerito dall'embedding.
        
        NON determina il tipo, solo AUMENTA confidence se le regole concordano.
        
        Returns:
            Boost value (0.0 - 0.15)
        """
        boost = 0.0
        name_lower = entity_name.lower().strip()
        
        if suggested_type == EntityType.PERSON:
            # Boost se nome italiano riconosciuto
            parts = name_lower.split()
            if any(p in ITALIAN_FIRST_NAMES for p in parts):
                boost += 0.1
            # Boost se pattern titolo (Dott., Ing., etc.)
            for pattern in self._person_patterns:
                if pattern.match(entity_name):
                    boost += 0.05
                    break
        
        elif suggested_type == EntityType.ORGANIZATION:
            # Boost se suffisso societario
            for pattern in self._org_patterns:
                if pattern.match(entity_name):
                    boost += 0.1
                    break
        
        elif suggested_type == EntityType.LOCATION:
            # Boost se pattern indirizzo
            for pattern in self._loc_patterns:
                if pattern.match(entity_name):
                    boost += 0.1
                    break
        
        return min(0.15, boost)  # Cap al 15% boost
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calcola cosine similarity tra due vettori"""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
    
    # ==================== FUTURE: LLM INTEGRATION ====================
    
    async def infer_type_with_llm(
        self,
        entity_name: str,
        context: str = "",
        llm_client = None
    ) -> EntityTypeResult:
        """
        [FUTURE] Inferisce tipo usando LLM locale.
        
        Placeholder per futura integrazione con LLM locale (es. Ollama, llama.cpp).
        
        Args:
            entity_name: Nome entità
            context: Contesto
            llm_client: Client LLM (da implementare)
            
        Returns:
            EntityTypeResult con method="llm"
        """
        # TODO: Implementare quando LLM locale disponibile
        # 
        # Prompt suggerito:
        # """
        # Classifica il tipo dell'entità "{entity_name}" nel contesto: "{context}"
        # 
        # Tipi possibili: person, organization, location, object, event, food, time, concept
        # 
        # Rispondi SOLO con il tipo e un confidence score (0-1).
        # Formato: {"type": "person", "confidence": 0.9}
        # """
        #
        # response = await llm_client.generate(prompt)
        # return parse_llm_response(response)
        
        logger.warning("LLM inference not yet implemented, falling back to embedding")
        return self.infer_type(entity_name, context)
    
    # ==================== UTILITIES ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche d'uso"""
        total = (
            self.stats["embedding_inferences"] + 
            self.stats["fallbacks"] + 
            self.stats["cache_hits"]
        )
        return {
            **self.stats,
            "total_inferences": total,
            "cache_size": len(self._cache),
            "types_loaded": len(self._type_embeddings) if self._type_embeddings else 0,
            "embedding_ready": self._embeddings_ready
        }
    
    def clear_cache(self):
        """Svuota la cache"""
        self._cache.clear()
        logger.info("Entity type cache cleared")
    
    def add_exemplars(self, entity_type: EntityType, exemplars: List[str]):
        """
        Aggiunge exemplars per un tipo (per fine-tuning).
        
        Richiede re-compute degli embeddings.
        """
        if entity_type in TYPE_EXEMPLARS:
            TYPE_EXEMPLARS[entity_type].extend(exemplars)
        else:
            TYPE_EXEMPLARS[entity_type] = exemplars
        
        # Invalida embeddings pre-calcolati
        self._embeddings_ready = False
        self._type_embeddings = None
        
        logger.info(f"Added {len(exemplars)} exemplars for {entity_type.value}, embeddings invalidated")


# Singleton instance
_normalizer_instance: Optional[EntityTypeNormalizer] = None


def get_entity_type_normalizer() -> EntityTypeNormalizer:
    """Get singleton instance of EntityTypeNormalizer"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = EntityTypeNormalizer()
    return _normalizer_instance
