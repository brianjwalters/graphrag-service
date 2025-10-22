"""
Entity Deduplication Module
Implements smart entity merging using similarity scoring and legal entity type awareness
"""

import asyncio
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
import numpy as np
from rapidfuzz import fuzz, process
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re


@dataclass
class Entity:
    """Entity data structure for deduplication."""
    entity_id: str
    entity_text: str
    entity_type: str
    confidence: float
    attributes: Dict[str, Any]
    document_ids: Set[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "entity_text": self.entity_text,
            "entity_type": self.entity_type,
            "confidence": self.confidence,
            "attributes": self.attributes,
            "document_ids": list(self.document_ids)
        }


class EntityDeduplicator:
    """
    Entity deduplication using multiple similarity measures and legal context.
    Follows Microsoft GraphRAG methodology for entity resolution.
    """
    
    # Legal entity type hierarchy for type-aware matching
    LEGAL_TYPE_HIERARCHY = {
        "PARTY": ["INDIVIDUAL", "CORPORATION", "ORGANIZATION", "GOVERNMENT"],
        "COURT": ["SUPREME_COURT", "APPELLATE_COURT", "DISTRICT_COURT", "STATE_COURT"],
        "JUDGE": ["CHIEF_JUSTICE", "ASSOCIATE_JUSTICE", "MAGISTRATE"],
        "ATTORNEY": ["PROSECUTOR", "DEFENSE_ATTORNEY", "COUNSEL"],
        "CITATION": ["CASE_CITATION", "STATUTE_CITATION", "REGULATION_CITATION"]
    }
    
    # Type-specific similarity thresholds
    TYPE_THRESHOLDS = {
        "PARTY": 0.85,
        "COURT": 0.90,
        "JUDGE": 0.88,
        "ATTORNEY": 0.85,
        "CITATION": 0.95,
        "STATUTE": 0.92,
        "DEFAULT": 0.85
    }
    
    def __init__(self, 
                 default_threshold: float = 0.85,
                 legal_entity_boost: float = 1.2):
        """
        Initialize entity deduplicator.
        
        Args:
            default_threshold: Default similarity threshold for deduplication
            legal_entity_boost: Boost factor for legal entity matching
        """
        self.default_threshold = default_threshold
        self.legal_entity_boost = legal_entity_boost
        self.tfidf_vectorizer = None
        self.canonical_forms = {}  # Cache for canonical entity forms
        
    async def deduplicate_entities(self, 
                                  entities: List[Dict[str, Any]],
                                  document_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Deduplicate entities using similarity scoring and type awareness.
        
        Args:
            entities: List of entity dictionaries
            document_id: Current document ID
            
        Returns:
            Tuple of (deduplicated entities, deduplication metadata)
        """
        if not entities:
            return [], {"original_count": 0, "deduplicated_count": 0}
        
        # Convert to Entity objects
        entity_objects = self._create_entity_objects(entities, document_id)
        
        # Group entities by type for type-aware deduplication
        entities_by_type = self._group_by_type(entity_objects)
        
        # Deduplicate within each type group
        deduplicated = []
        merge_operations = []
        canonical_mappings = {}
        
        for entity_type, type_entities in entities_by_type.items():
            if len(type_entities) == 1:
                deduplicated.extend(type_entities)
                continue
            
            # Get similarity threshold for this type
            threshold = self.TYPE_THRESHOLDS.get(entity_type, self.default_threshold)
            
            # Find similar entities and merge
            merged, merges, mappings = await self._merge_similar_entities(
                type_entities, threshold, entity_type
            )
            
            deduplicated.extend(merged)
            merge_operations.extend(merges)
            canonical_mappings.update(mappings)
        
        # Convert back to dictionaries
        result_entities = [e.to_dict() for e in deduplicated]
        
        # Build deduplication metadata
        metadata = {
            "original_count": len(entities),
            "deduplicated_count": len(result_entities),
            "merge_operations": len(merge_operations),
            "merged_entities": merge_operations,
            "canonical_mappings": canonical_mappings,
            "deduplication_rate": 1 - (len(result_entities) / len(entities)) if entities else 0
        }
        
        return result_entities, metadata
    
    def _create_entity_objects(self, entities: List[Dict[str, Any]], document_id: str) -> List[Entity]:
        """Convert entity dictionaries to Entity objects."""
        entity_objects = []
        for e in entities:
            entity_objects.append(Entity(
                entity_id=e.get("entity_id"),
                entity_text=e.get("entity_text", ""),
                entity_type=e.get("entity_type", "UNKNOWN"),
                confidence=e.get("confidence", 0.95),
                attributes=e.get("attributes", {}),
                document_ids={document_id}
            ))
        return entity_objects
    
    def _group_by_type(self, entities: List[Entity]) -> Dict[str, List[Entity]]:
        """Group entities by their type."""
        groups = {}
        for entity in entities:
            entity_type = entity.entity_type
            
            # Check if type belongs to a hierarchy
            for parent_type, child_types in self.LEGAL_TYPE_HIERARCHY.items():
                if entity_type in child_types:
                    entity_type = parent_type
                    break
            
            if entity_type not in groups:
                groups[entity_type] = []
            groups[entity_type].append(entity)
        
        return groups
    
    async def _merge_similar_entities(self, 
                                     entities: List[Entity], 
                                     threshold: float,
                                     entity_type: str) -> Tuple[List[Entity], List[Dict], Dict[str, str]]:
        """
        Merge similar entities within a type group.
        
        Returns:
            Tuple of (merged entities, merge operations, canonical mappings)
        """
        if len(entities) <= 1:
            return entities, [], {}
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(entities, entity_type)
        
        # Find clusters of similar entities
        clusters = self._find_entity_clusters(entities, similarity_matrix, threshold)
        
        # Merge entities within each cluster
        merged_entities = []
        merge_operations = []
        canonical_mappings = {}
        
        for cluster in clusters:
            if len(cluster) == 1:
                merged_entities.append(cluster[0])
            else:
                # Merge cluster into single canonical entity
                canonical, merge_info = self._merge_entity_cluster(cluster, entity_type)
                merged_entities.append(canonical)
                merge_operations.append(merge_info)
                
                # Track canonical mappings
                for entity in cluster:
                    if entity.entity_id != canonical.entity_id:
                        canonical_mappings[entity.entity_id] = canonical.entity_id
        
        return merged_entities, merge_operations, canonical_mappings
    
    def _calculate_similarity_matrix(self, entities: List[Entity], entity_type: str) -> np.ndarray:
        """
        Calculate pairwise similarity matrix for entities.
        Uses multiple similarity measures combined.
        """
        n = len(entities)
        similarity_matrix = np.zeros((n, n))
        
        # Extract entity texts for vectorization
        texts = [e.entity_text for e in entities]
        
        # TF-IDF similarity (semantic)
        if len(texts) > 1:
            if not self.tfidf_vectorizer:
                self.tfidf_vectorizer = TfidfVectorizer(
                    analyzer='char_wb',
                    ngram_range=(2, 4),
                    max_features=1000
                )
            
            try:
                tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
                tfidf_sim = cosine_similarity(tfidf_matrix)
            except:
                # Fallback if TF-IDF fails
                tfidf_sim = np.eye(n)
        else:
            tfidf_sim = np.eye(n)
        
        # Calculate combined similarity
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    # Fuzzy string matching
                    fuzzy_sim = fuzz.ratio(texts[i], texts[j]) / 100.0
                    
                    # Token set ratio (handles word order variations)
                    token_sim = fuzz.token_set_ratio(texts[i], texts[j]) / 100.0
                    
                    # Combine similarities with weights
                    combined_sim = (
                        0.3 * tfidf_sim[i][j] +
                        0.4 * fuzzy_sim +
                        0.3 * token_sim
                    )
                    
                    # Apply legal entity boost if applicable
                    if entity_type in ["PARTY", "COURT", "JUDGE", "ATTORNEY"]:
                        combined_sim *= self.legal_entity_boost
                        combined_sim = min(combined_sim, 1.0)
                    
                    # Consider confidence scores
                    confidence_factor = (entities[i].confidence + entities[j].confidence) / 2
                    combined_sim *= confidence_factor
                    
                    similarity_matrix[i][j] = combined_sim
                    similarity_matrix[j][i] = combined_sim
        
        return similarity_matrix
    
    def _find_entity_clusters(self, 
                             entities: List[Entity], 
                             similarity_matrix: np.ndarray,
                             threshold: float) -> List[List[Entity]]:
        """
        Find clusters of similar entities using similarity threshold.
        Uses greedy clustering approach.
        """
        n = len(entities)
        visited = set()
        clusters = []
        
        for i in range(n):
            if i in visited:
                continue
            
            # Start new cluster
            cluster = [entities[i]]
            visited.add(i)
            
            # Find all entities similar to this one
            for j in range(i + 1, n):
                if j in visited:
                    continue
                
                # Check if similar enough to any entity in cluster
                max_sim = max(similarity_matrix[k][j] for k in [i] + 
                            [entities.index(e) for e in cluster[1:]])
                
                if max_sim >= threshold:
                    cluster.append(entities[j])
                    visited.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    def _merge_entity_cluster(self, cluster: List[Entity], entity_type: str) -> Tuple[Entity, Dict[str, Any]]:
        """
        Merge a cluster of entities into a single canonical entity.
        Selects the best representative and combines attributes.
        """
        # Select canonical entity (highest confidence, longest text)
        canonical = max(cluster, key=lambda e: (e.confidence, len(e.entity_text)))
        
        # Merge document IDs
        merged_doc_ids = set()
        for entity in cluster:
            merged_doc_ids.update(entity.document_ids)
        
        # Merge attributes - handle None case
        merged_attributes = canonical.attributes.copy() if canonical.attributes else {}
        for entity in cluster:
            if entity != canonical and entity.attributes:
                for key, value in entity.attributes.items():
                    if key not in merged_attributes:
                        merged_attributes[key] = value
                    elif isinstance(value, list) and isinstance(merged_attributes[key], list):
                        merged_attributes[key].extend(value)
        
        # Calculate average confidence
        avg_confidence = sum(e.confidence for e in cluster) / len(cluster)
        
        # Create merged entity
        merged = Entity(
            entity_id=canonical.entity_id,
            entity_text=self._get_canonical_text(cluster, entity_type),
            entity_type=canonical.entity_type,
            confidence=avg_confidence,
            attributes=merged_attributes,
            document_ids=merged_doc_ids
        )
        
        # Create merge information
        merge_info = {
            "canonical_id": canonical.entity_id,
            "canonical_text": merged.entity_text,
            "merged_entities": [
                {
                    "entity_id": e.entity_id,
                    "entity_text": e.entity_text,
                    "confidence": e.confidence
                }
                for e in cluster if e != canonical
            ],
            "cluster_size": len(cluster),
            "avg_confidence": avg_confidence
        }
        
        return merged, merge_info
    
    def _get_canonical_text(self, cluster: List[Entity], entity_type: str) -> str:
        """
        Determine the canonical text representation for a cluster.
        Uses the most complete/formal version.
        """
        texts = [e.entity_text for e in cluster]
        
        # For legal entities, prefer formal names
        if entity_type in ["COURT", "JUDGE"]:
            # Prefer longer, more formal versions
            return max(texts, key=lambda t: (len(t), t.count(" ")))
        elif entity_type == "PARTY":
            # For parties, prefer the version with most words (likely full name)
            return max(texts, key=lambda t: len(t.split()))
        else:
            # Default: use most common or longest
            return max(texts, key=lambda t: (texts.count(t), len(t)))
    
    async def find_cross_document_entities(self, 
                                          all_entities: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Find entities that appear across multiple documents.
        
        Args:
            all_entities: All entities from multiple documents
            
        Returns:
            Dictionary mapping entity IDs to list of document IDs
        """
        cross_doc_entities = {}
        
        # Group entities by canonical form
        canonical_groups = {}
        for entity in all_entities:
            canonical = self._get_canonical_form(entity.get("entity_text", ""))
            if canonical not in canonical_groups:
                canonical_groups[canonical] = []
            canonical_groups[canonical].append(entity)
        
        # Find entities in multiple documents
        for canonical, entities in canonical_groups.items():
            doc_ids = set()
            entity_ids = []
            
            for entity in entities:
                if "document_ids" in entity:
                    doc_ids.update(entity["document_ids"])
                elif "document_id" in entity:
                    doc_ids.add(entity["document_id"])
                entity_ids.append(entity.get("entity_id"))
            
            if len(doc_ids) > 1:
                for entity_id in entity_ids:
                    cross_doc_entities[entity_id] = list(doc_ids)
        
        return cross_doc_entities
    
    def _get_canonical_form(self, text: str) -> str:
        """Get canonical form of entity text for comparison."""
        if text in self.canonical_forms:
            return self.canonical_forms[text]
        
        # Normalize text
        canonical = text.lower().strip()
        
        # Remove common legal abbreviations and variations
        canonical = re.sub(r'\b(inc|llc|corp|co|ltd)\b\.?', '', canonical)
        canonical = re.sub(r'\s+', ' ', canonical)
        canonical = canonical.strip()
        
        self.canonical_forms[text] = canonical
        return canonical