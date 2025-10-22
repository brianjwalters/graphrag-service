"""
Relationship Discovery Module
Discovers cross-document relationships and inferred connections
"""

import asyncio
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict
import networkx as nx
import numpy as np
from dataclasses import dataclass


@dataclass
class RelationshipCandidate:
    """Candidate relationship for validation."""
    source_entity: str
    target_entity: str
    relationship_type: str
    confidence: float
    evidence: List[str]
    source_documents: Set[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "source_documents": list(self.source_documents)
        }


class RelationshipDiscoverer:
    """
    Discovers relationships between entities, including cross-document connections.
    Implements relationship inference and validation for legal documents.
    """
    
    # Legal relationship patterns
    LEGAL_RELATIONSHIP_PATTERNS = {
        "REPRESENTS": ["attorney", "counsel", "lawyer", "represents", "on behalf of"],
        "EMPLOYS": ["employee", "works for", "employed by", "staff"],
        "OWNS": ["owner", "owns", "proprietor", "subsidiary"],
        "CITES": ["cites", "references", "pursuant to", "under", "according to"],
        "OVERRULES": ["overrules", "overturns", "reverses", "vacates"],
        "FOLLOWS": ["follows", "adheres to", "consistent with", "in accordance with"],
        "OPPOSES": ["versus", "v.", "against", "plaintiff", "defendant", "appellant", "appellee"],
        "GOVERNS": ["governs", "regulates", "oversees", "jurisdiction over"],
        "AFFILIATES": ["affiliated with", "associated with", "member of", "part of"]
    }
    
    # Relationship inference rules for legal entities
    INFERENCE_RULES = {
        ("ATTORNEY", "PARTY"): "REPRESENTS",
        ("PARTY", "PARTY"): "OPPOSES",  # In litigation context
        ("COURT", "CASE"): "PRESIDES",
        ("JUDGE", "COURT"): "SERVES_ON",
        ("STATUTE", "REGULATION"): "AUTHORIZES",
        ("CASE", "CASE"): "CITES",  # Default for case relationships
        ("CORPORATION", "INDIVIDUAL"): "EMPLOYS",  # Potential employment
    }
    
    def __init__(self,
                 min_confidence: float = 0.5,
                 citation_weight: float = 2.0,
                 cross_doc_boost: float = 1.5):
        """
        Initialize relationship discoverer.
        
        Args:
            min_confidence: Minimum confidence for relationship acceptance
            citation_weight: Weight multiplier for citation relationships
            cross_doc_boost: Boost for cross-document relationships
        """
        self.min_confidence = min_confidence
        self.citation_weight = citation_weight
        self.cross_doc_boost = cross_doc_boost
        
    async def discover_relationships(self,
                                    entities: List[Dict[str, Any]],
                                    existing_relationships: List[Dict[str, Any]],
                                    citations: Optional[List[Dict[str, Any]]] = None,
                                    chunks: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Discover new relationships and enhance existing ones.
        
        Args:
            entities: Deduplicated entities
            existing_relationships: Already extracted relationships
            citations: Document citations
            chunks: Document chunks with context
            
        Returns:
            Tuple of (enhanced relationships, discovery metadata)
        """
        # Index existing relationships to avoid duplicates
        existing_rel_index = self._index_relationships(existing_relationships)
        
        # Discover different types of relationships
        discovered_relationships = []
        
        # 1. Discover citation-based relationships
        if citations:
            citation_rels = await self._discover_citation_relationships(
                entities, citations, existing_rel_index
            )
            discovered_relationships.extend(citation_rels)
        
        # 2. Discover cross-document relationships
        cross_doc_rels = await self._discover_cross_document_relationships(
            entities, existing_rel_index
        )
        discovered_relationships.extend(cross_doc_rels)
        
        # 3. Infer relationships from entity types and context
        if chunks:
            inferred_rels = await self._infer_relationships_from_context(
                entities, chunks, existing_rel_index
            )
            discovered_relationships.extend(inferred_rels)
        
        # 4. Discover co-occurrence based relationships
        cooccurrence_rels = await self._discover_cooccurrence_relationships(
            entities, chunks, existing_rel_index
        )
        discovered_relationships.extend(cooccurrence_rels)
        
        # Combine with existing relationships
        all_relationships = existing_relationships + discovered_relationships
        
        # Enhance relationships with additional metadata
        enhanced_relationships = await self._enhance_relationships(
            all_relationships, entities
        )
        
        # Build discovery metadata
        metadata = {
            "existing_relationships": len(existing_relationships),
            "discovered_relationships": len(discovered_relationships),
            "total_relationships": len(enhanced_relationships),
            "discovery_breakdown": {
                "citation_based": len([r for r in discovered_relationships 
                                     if r.get("discovery_method") == "citation"]),
                "cross_document": len([r for r in discovered_relationships 
                                     if r.get("discovery_method") == "cross_document"]),
                "inferred": len([r for r in discovered_relationships 
                              if r.get("discovery_method") == "inference"]),
                "cooccurrence": len([r for r in discovered_relationships 
                                  if r.get("discovery_method") == "cooccurrence"])
            }
        }
        
        return enhanced_relationships, metadata
    
    def _index_relationships(self, relationships: List[Dict[str, Any]]) -> Set[Tuple[str, str, str]]:
        """Create index of existing relationships for duplicate detection."""
        index = set()
        for rel in relationships:
            key = (
                rel.get("source_entity", ""),
                rel.get("target_entity", ""),
                rel.get("relationship_type", "")
            )
            index.add(key)
            # Also add reverse for undirected relationships
            if rel.get("relationship_type") in ["AFFILIATES", "ASSOCIATES"]:
                reverse_key = (
                    rel.get("target_entity", ""),
                    rel.get("source_entity", ""),
                    rel.get("relationship_type", "")
                )
                index.add(reverse_key)
        return index
    
    async def _discover_citation_relationships(self,
                                              entities: List[Dict[str, Any]],
                                              citations: List[Dict[str, Any]],
                                              existing_index: Set) -> List[Dict[str, Any]]:
        """Discover relationships based on citations."""
        relationships = []
        entity_map = {e["entity_id"]: e for e in entities}
        
        # Group citations by document
        citations_by_doc = defaultdict(list)
        for citation in citations:
            doc_id = citation.get("document_id")
            if doc_id:
                citations_by_doc[doc_id].append(citation)
        
        # Find entities that appear in documents with citations
        for doc_id, doc_citations in citations_by_doc.items():
            # Get entities in this document
            doc_entities = [e for e in entities 
                          if doc_id in e.get("document_ids", [])]
            
            # Create citation relationships
            for citation in doc_citations:
                citation_text = citation.get("citation_text", "")
                citation_type = citation.get("citation_type", "")
                
                # Find entities that might be related to this citation
                for entity in doc_entities:
                    entity_text = entity.get("entity_text", "").lower()
                    
                    # Check if entity is mentioned in citation
                    if entity_text in citation_text.lower():
                        # Create citation relationship
                        for other_entity in doc_entities:
                            if other_entity["entity_id"] != entity["entity_id"]:
                                rel_key = (
                                    entity["entity_id"],
                                    other_entity["entity_id"],
                                    "CITED_TOGETHER"
                                )
                                
                                if rel_key not in existing_index:
                                    relationships.append({
                                        "relationship_id": f"rel_cite_{len(relationships)}",
                                        "source_entity": entity["entity_id"],
                                        "target_entity": other_entity["entity_id"],
                                        "relationship_type": "CITED_TOGETHER",
                                        "confidence": 0.7 * self.citation_weight,
                                        "discovery_method": "citation",
                                        "evidence": [f"Both appear in {citation_type}: {citation_text[:50]}..."],
                                        "document_id": doc_id
                                    })
                                    existing_index.add(rel_key)
        
        return relationships
    
    async def _discover_cross_document_relationships(self,
                                                    entities: List[Dict[str, Any]],
                                                    existing_index: Set) -> List[Dict[str, Any]]:
        """Discover relationships between entities across documents."""
        relationships = []
        
        # Find entities that appear in multiple documents
        multi_doc_entities = [e for e in entities 
                             if len(e.get("document_ids", [])) > 1]
        
        if not multi_doc_entities:
            return relationships
        
        # Group entities by shared documents
        doc_entity_map = defaultdict(list)
        for entity in entities:
            for doc_id in entity.get("document_ids", []):
                doc_entity_map[doc_id].append(entity)
        
        # Find entities that co-occur across multiple documents
        entity_cooccurrence = defaultdict(set)
        for doc_id, doc_entities in doc_entity_map.items():
            for i, entity1 in enumerate(doc_entities):
                for entity2 in doc_entities[i+1:]:
                    pair = tuple(sorted([entity1["entity_id"], entity2["entity_id"]]))
                    entity_cooccurrence[pair].add(doc_id)
        
        # Create relationships for entities that co-occur in multiple documents
        for (entity1_id, entity2_id), shared_docs in entity_cooccurrence.items():
            if len(shared_docs) >= 2:  # Appear together in at least 2 documents
                rel_key = (entity1_id, entity2_id, "CROSS_DOCUMENT_ASSOCIATION")
                
                if rel_key not in existing_index:
                    confidence = min(0.6 + (len(shared_docs) * 0.1), 0.95) * self.cross_doc_boost
                    
                    relationships.append({
                        "relationship_id": f"rel_cross_{len(relationships)}",
                        "source_entity": entity1_id,
                        "target_entity": entity2_id,
                        "relationship_type": "CROSS_DOCUMENT_ASSOCIATION",
                        "confidence": confidence,
                        "discovery_method": "cross_document",
                        "evidence": [f"Co-occur in {len(shared_docs)} documents"],
                        "shared_documents": list(shared_docs)
                    })
                    existing_index.add(rel_key)
        
        return relationships
    
    async def _infer_relationships_from_context(self,
                                               entities: List[Dict[str, Any]],
                                               chunks: Optional[List[Dict[str, Any]]],
                                               existing_index: Set) -> List[Dict[str, Any]]:
        """Infer relationships based on entity types and context."""
        if not chunks:
            return []
        
        relationships = []
        entity_map = {e["entity_id"]: e for e in entities}
        
        # Group entities by chunk
        entities_by_chunk = defaultdict(list)
        for entity in entities:
            chunk_id = entity.get("source_chunk_id")
            if chunk_id:
                entities_by_chunk[chunk_id].append(entity)
        
        # Analyze each chunk for relationship patterns
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            chunk_content = chunk.get("content", "").lower()
            chunk_entities = entities_by_chunk.get(chunk_id, [])
            
            if len(chunk_entities) < 2:
                continue
            
            # Check for relationship patterns in chunk text
            for i, entity1 in enumerate(chunk_entities):
                for entity2 in chunk_entities[i+1:]:
                    # Try to infer relationship based on entity types
                    rel_type = self._infer_relationship_type(
                        entity1, entity2, chunk_content
                    )
                    
                    if rel_type:
                        rel_key = (entity1["entity_id"], entity2["entity_id"], rel_type)
                        
                        if rel_key not in existing_index:
                            relationships.append({
                                "relationship_id": f"rel_infer_{len(relationships)}",
                                "source_entity": entity1["entity_id"],
                                "target_entity": entity2["entity_id"],
                                "relationship_type": rel_type,
                                "confidence": 0.7,
                                "discovery_method": "inference",
                                "evidence": [f"Inferred from context in chunk {chunk_id}"],
                                "chunk_id": chunk_id
                            })
                            existing_index.add(rel_key)
        
        return relationships
    
    def _infer_relationship_type(self,
                                entity1: Dict[str, Any],
                                entity2: Dict[str, Any],
                                context: str) -> Optional[str]:
        """Infer relationship type based on entity types and context."""
        type1 = entity1.get("entity_type", "")
        type2 = entity2.get("entity_type", "")
        
        # Check inference rules
        type_pair = (type1, type2)
        if type_pair in self.INFERENCE_RULES:
            return self.INFERENCE_RULES[type_pair]
        
        # Check reverse pair
        reverse_pair = (type2, type1)
        if reverse_pair in self.INFERENCE_RULES:
            return self.INFERENCE_RULES[reverse_pair]
        
        # Check for relationship patterns in context
        entity1_text = entity1.get("entity_text", "").lower()
        entity2_text = entity2.get("entity_text", "").lower()
        
        for rel_type, patterns in self.LEGAL_RELATIONSHIP_PATTERNS.items():
            for pattern in patterns:
                # Check if pattern appears between entities in context
                if pattern in context:
                    # Simple proximity check
                    if entity1_text in context and entity2_text in context:
                        pos1 = context.find(entity1_text)
                        pos2 = context.find(entity2_text)
                        pattern_pos = context.find(pattern)
                        
                        # Pattern should be between entities (roughly)
                        if min(pos1, pos2) < pattern_pos < max(pos1, pos2):
                            return rel_type
        
        return None
    
    async def _discover_cooccurrence_relationships(self,
                                                  entities: List[Dict[str, Any]],
                                                  chunks: Optional[List[Dict[str, Any]]],
                                                  existing_index: Set) -> List[Dict[str, Any]]:
        """Discover relationships based on entity co-occurrence patterns."""
        if not chunks:
            return []
        
        relationships = []
        
        # Calculate co-occurrence matrix
        entity_ids = [e["entity_id"] for e in entities]
        cooccurrence_matrix = np.zeros((len(entity_ids), len(entity_ids)))
        
        # Count co-occurrences in chunks
        for chunk in chunks:
            chunk_content = chunk.get("content", "").lower()
            
            # Find which entities appear in this chunk
            appearing_entities = []
            for i, entity in enumerate(entities):
                entity_text = entity.get("entity_text", "").lower()
                if entity_text in chunk_content:
                    appearing_entities.append(i)
            
            # Update co-occurrence matrix
            for i in appearing_entities:
                for j in appearing_entities:
                    if i != j:
                        cooccurrence_matrix[i][j] += 1
        
        # Create relationships for strong co-occurrences
        threshold = 3  # Minimum co-occurrences
        for i in range(len(entity_ids)):
            for j in range(i+1, len(entity_ids)):
                cooccurrence_count = cooccurrence_matrix[i][j]
                
                if cooccurrence_count >= threshold:
                    rel_key = (entity_ids[i], entity_ids[j], "FREQUENTLY_COOCCURS")
                    
                    if rel_key not in existing_index:
                        confidence = min(0.5 + (cooccurrence_count * 0.05), 0.9)
                        
                        relationships.append({
                            "relationship_id": f"rel_cooc_{len(relationships)}",
                            "source_entity": entity_ids[i],
                            "target_entity": entity_ids[j],
                            "relationship_type": "FREQUENTLY_COOCCURS",
                            "confidence": confidence,
                            "discovery_method": "cooccurrence",
                            "evidence": [f"Co-occur in {int(cooccurrence_count)} chunks"],
                            "cooccurrence_count": int(cooccurrence_count)
                        })
                        existing_index.add(rel_key)
        
        return relationships
    
    async def _enhance_relationships(self,
                                    relationships: List[Dict[str, Any]],
                                    entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance relationships with additional metadata."""
        entity_map = {e["entity_id"]: e for e in entities}
        enhanced = []
        
        for rel in relationships:
            enhanced_rel = rel.copy()
            
            # Add entity details
            source_entity = entity_map.get(rel.get("source_entity"))
            target_entity = entity_map.get(rel.get("target_entity"))
            
            if source_entity and target_entity:
                enhanced_rel["source_entity_text"] = source_entity.get("entity_text", "")
                enhanced_rel["source_entity_type"] = source_entity.get("entity_type", "")
                enhanced_rel["target_entity_text"] = target_entity.get("entity_text", "")
                enhanced_rel["target_entity_type"] = target_entity.get("entity_type", "")
                
                # Validate confidence meets threshold
                if enhanced_rel.get("confidence", 0) >= self.min_confidence:
                    enhanced.append(enhanced_rel)
        
        return enhanced
    
    async def identify_cross_document_links(self,
                                           documents: List[Dict[str, Any]],
                                           all_entities: List[Dict[str, Any]],
                                           all_relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify cross-document links based on shared entities and relationships.
        
        Returns:
            List of cross-document link objects
        """
        cross_doc_links = []
        
        # Build document-entity index
        doc_entity_map = defaultdict(set)
        for entity in all_entities:
            for doc_id in entity.get("document_ids", []):
                doc_entity_map[doc_id].add(entity["entity_id"])
        
        # Find document pairs with shared entities
        doc_ids = list(doc_entity_map.keys())
        for i, doc1 in enumerate(doc_ids):
            for doc2 in doc_ids[i+1:]:
                shared_entities = doc_entity_map[doc1] & doc_entity_map[doc2]
                
                if shared_entities:
                    # Determine link type based on shared entities
                    link_type = self._determine_link_type(
                        shared_entities, all_entities, all_relationships
                    )
                    
                    cross_doc_links.append({
                        "source_document_id": doc1,
                        "target_document_id": doc2,
                        "link_type": link_type,
                        "shared_entities": list(shared_entities),
                        "strength": len(shared_entities) / min(
                            len(doc_entity_map[doc1]),
                            len(doc_entity_map[doc2])
                        )
                    })
        
        return cross_doc_links
    
    def _determine_link_type(self,
                            shared_entities: Set[str],
                            all_entities: List[Dict[str, Any]],
                            all_relationships: List[Dict[str, Any]]) -> str:
        """Determine the type of cross-document link."""
        # Get entity types for shared entities
        entity_types = []
        for entity in all_entities:
            if entity["entity_id"] in shared_entities:
                entity_types.append(entity.get("entity_type", ""))
        
        # Determine link type based on entity types
        if "CASE" in entity_types or "CITATION" in entity_types:
            return "CITATION_LINK"
        elif "PARTY" in entity_types:
            return "SHARED_PARTY"
        elif "COURT" in entity_types or "JUDGE" in entity_types:
            return "SAME_JURISDICTION"
        elif "CONTRACT" in entity_types:
            return "RELATED_CONTRACT"
        else:
            return "GENERAL_REFERENCE"