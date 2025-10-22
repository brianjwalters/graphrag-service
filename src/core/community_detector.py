"""
Community Detection Module
Implements Leiden algorithm for optimal community detection following Microsoft GraphRAG
"""

import asyncio
from typing import List, Dict, Any, Tuple, Optional, Set
import networkx as nx
import igraph as ig
import leidenalg
import numpy as np
from collections import defaultdict


class CommunityDetector:
    """
    Community detection using Leiden algorithm with legal context awareness.
    Follows Microsoft GraphRAG methodology for hierarchical community detection.
    """
    
    def __init__(self,
                 resolution: float = 1.0,
                 min_community_size: int = 3,
                 max_community_size: int = 50,
                 coherence_threshold: float = 0.7):
        """
        Initialize community detector.
        
        Args:
            resolution: Leiden algorithm resolution parameter (higher = more communities)
            min_community_size: Minimum entities for valid community
            max_community_size: Maximum entities per community
            coherence_threshold: Minimum coherence score for community
        """
        self.resolution = resolution
        self.min_community_size = min_community_size
        self.max_community_size = max_community_size
        self.coherence_threshold = coherence_threshold
        
    async def detect_communities(self,
                                entities: List[Dict[str, Any]],
                                relationships: List[Dict[str, Any]],
                                citations: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Detect communities in the entity-relationship graph.
        
        Args:
            entities: List of deduplicated entities
            relationships: List of entity relationships
            citations: Optional list of citations for enhanced detection
            
        Returns:
            Tuple of (communities, detection metadata)
        """
        if len(entities) < self.min_community_size:
            return [], {"message": "Too few entities for community detection"}
        
        # Build NetworkX graph
        nx_graph = self._build_networkx_graph(entities, relationships, citations)
        
        if nx_graph.number_of_edges() == 0:
            return [], {"message": "No relationships for community detection"}
        
        # Convert to igraph for Leiden algorithm
        ig_graph = self._convert_to_igraph(nx_graph)
        
        # Run Leiden algorithm
        partition = self._run_leiden(ig_graph)
        
        # Extract communities from partition
        raw_communities = self._extract_communities(partition, ig_graph, nx_graph)
        
        # Filter and validate communities
        valid_communities = self._filter_communities(raw_communities, nx_graph)
        
        # Calculate community metadata and quality metrics
        communities_with_metadata = []
        for comm_id, community in enumerate(valid_communities):
            community_info = await self._analyze_community(
                comm_id, community, nx_graph, entities
            )
            communities_with_metadata.append(community_info)
        
        # Build detection metadata
        metadata = {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "raw_communities_found": len(raw_communities),
            "valid_communities": len(communities_with_metadata),
            "resolution_used": self.resolution,
            "graph_metrics": {
                "nodes": nx_graph.number_of_nodes(),
                "edges": nx_graph.number_of_edges(),
                "density": nx.density(nx_graph) if nx_graph.number_of_nodes() > 0 else 0,
                "components": nx.number_connected_components(nx_graph)
            }
        }
        
        return communities_with_metadata, metadata
    
    def _build_networkx_graph(self,
                             entities: List[Dict[str, Any]],
                             relationships: List[Dict[str, Any]],
                             citations: Optional[List[Dict[str, Any]]]) -> nx.Graph:
        """Build NetworkX graph from entities and relationships."""
        G = nx.Graph()
        
        # Add nodes (entities)
        for entity in entities:
            G.add_node(
                entity["entity_id"],
                entity_text=entity.get("entity_text", ""),
                entity_type=entity.get("entity_type", ""),
                confidence=entity.get("confidence", 0.95),
                attributes=entity.get("attributes", {})
            )
        
        # Add edges (relationships)
        for rel in relationships:
            source = rel.get("source_entity")
            target = rel.get("target_entity")
            
            # Only add edge if both entities exist in graph
            if source in G.nodes and target in G.nodes:
                weight = rel.get("confidence", 0.8)
                
                # Boost weight for certain relationship types
                rel_type = rel.get("relationship_type", "")
                if rel_type in ["REPRESENTS", "EMPLOYS", "OWNS"]:
                    weight *= 1.5
                elif rel_type in ["CITES", "REFERENCES"]:
                    weight *= 1.2
                
                G.add_edge(
                    source, target,
                    weight=min(weight, 1.0),
                    relationship_type=rel_type,
                    attributes=rel.get("attributes", {})
                )
        
        # Add citation-based edges if available
        if citations:
            self._add_citation_edges(G, citations, entities)
        
        return G
    
    def _add_citation_edges(self, 
                           G: nx.Graph,
                           citations: List[Dict[str, Any]],
                           entities: List[Dict[str, Any]]):
        """Add edges based on shared citations."""
        # Group entities by document
        entities_by_doc = defaultdict(list)
        for entity in entities:
            for doc_id in entity.get("document_ids", []):
                entities_by_doc[doc_id].append(entity["entity_id"])
        
        # Group citations by document
        citations_by_doc = defaultdict(list)
        for citation in citations:
            doc_id = citation.get("document_id")
            if doc_id:
                citations_by_doc[doc_id].append(citation)
        
        # Connect entities that share citations
        for doc_id, doc_citations in citations_by_doc.items():
            doc_entities = entities_by_doc.get(doc_id, [])
            
            # If document has both entities and citations
            if doc_entities and len(doc_entities) > 1:
                # Connect entities in same document with citation relationship
                for i, entity1 in enumerate(doc_entities):
                    for entity2 in doc_entities[i+1:]:
                        if entity1 in G.nodes and entity2 in G.nodes:
                            # Check if edge already exists
                            if not G.has_edge(entity1, entity2):
                                G.add_edge(
                                    entity1, entity2,
                                    weight=0.6,
                                    relationship_type="SHARED_CITATION",
                                    citation_count=len(doc_citations)
                                )
    
    def _convert_to_igraph(self, nx_graph: nx.Graph) -> ig.Graph:
        """Convert NetworkX graph to igraph for Leiden algorithm."""
        # Get node list to maintain consistent ordering
        node_list = list(nx_graph.nodes())
        node_to_idx = {node: idx for idx, node in enumerate(node_list)}
        
        # Extract edges with weights
        edges = []
        weights = []
        for source, target, data in nx_graph.edges(data=True):
            edges.append((node_to_idx[source], node_to_idx[target]))
            weights.append(data.get('weight', 1.0))
        
        # Create igraph
        ig_graph = ig.Graph(len(node_list))
        ig_graph.add_edges(edges)
        ig_graph.es['weight'] = weights
        
        # Add node attributes
        for attr_name in ['entity_text', 'entity_type', 'confidence']:
            ig_graph.vs[attr_name] = [
                nx_graph.nodes[node].get(attr_name, '') 
                for node in node_list
            ]
        
        # Store original node IDs
        ig_graph.vs['original_id'] = node_list
        
        return ig_graph
    
    def _run_leiden(self, ig_graph: ig.Graph) -> leidenalg.VertexPartition:
        """Run Leiden algorithm for community detection."""
        # Use RBConfigurationVertexPartition for weighted graphs
        partition = leidenalg.find_partition(
            ig_graph,
            leidenalg.RBConfigurationVertexPartition,
            weights='weight',
            resolution_parameter=self.resolution,
            seed=42  # For reproducibility
        )
        
        return partition
    
    def _extract_communities(self,
                           partition: leidenalg.VertexPartition,
                           ig_graph: ig.Graph,
                           nx_graph: nx.Graph) -> List[Set[str]]:
        """Extract communities from Leiden partition."""
        communities = []
        
        for community_idx in range(len(partition)):
            community_vertices = partition[community_idx]
            
            # Get original entity IDs for community members
            community_entities = set()
            for vertex_idx in community_vertices:
                original_id = ig_graph.vs[vertex_idx]['original_id']
                community_entities.add(original_id)
            
            if community_entities:
                communities.append(community_entities)
        
        return communities
    
    def _filter_communities(self,
                          raw_communities: List[Set[str]],
                          nx_graph: nx.Graph) -> List[Set[str]]:
        """Filter communities based on size and coherence."""
        valid_communities = []
        
        for community in raw_communities:
            # Check size constraints
            if len(community) < self.min_community_size:
                continue
            
            # Split if too large
            if len(community) > self.max_community_size:
                # Use hierarchical splitting
                sub_communities = self._split_large_community(community, nx_graph)
                valid_communities.extend(sub_communities)
            else:
                # Check coherence
                coherence = self._calculate_coherence(community, nx_graph)
                if coherence >= self.coherence_threshold:
                    valid_communities.append(community)
        
        return valid_communities
    
    def _split_large_community(self,
                              community: Set[str],
                              nx_graph: nx.Graph) -> List[Set[str]]:
        """Split large community into smaller sub-communities."""
        # Create subgraph for this community
        subgraph = nx_graph.subgraph(community)
        
        # Find connected components in subgraph
        components = list(nx.connected_components(subgraph))
        
        valid_splits = []
        for component in components:
            if len(component) >= self.min_community_size:
                if len(component) <= self.max_community_size:
                    valid_splits.append(component)
                else:
                    # Recursively split if still too large
                    # (In practice, we'd use a more sophisticated method)
                    valid_splits.append(set(list(component)[:self.max_community_size]))
        
        return valid_splits if valid_splits else [community]
    
    def _calculate_coherence(self, community: Set[str], nx_graph: nx.Graph) -> float:
        """
        Calculate community coherence score.
        Coherence = internal edges / possible internal edges
        """
        if len(community) <= 1:
            return 1.0
        
        subgraph = nx_graph.subgraph(community)
        internal_edges = subgraph.number_of_edges()
        possible_edges = len(community) * (len(community) - 1) / 2
        
        if possible_edges == 0:
            return 0.0
        
        # Basic coherence
        basic_coherence = internal_edges / possible_edges
        
        # Weight by edge strengths
        if internal_edges > 0:
            avg_weight = sum(data.get('weight', 1.0) 
                           for _, _, data in subgraph.edges(data=True)) / internal_edges
            weighted_coherence = basic_coherence * avg_weight
        else:
            weighted_coherence = 0.0
        
        return weighted_coherence
    
    async def _analyze_community(self,
                                comm_id: int,
                                community: Set[str],
                                nx_graph: nx.Graph,
                                all_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a community and generate metadata."""
        # Get entity details for community members
        entity_map = {e["entity_id"]: e for e in all_entities}
        community_entities = [entity_map[eid] for eid in community if eid in entity_map]
        
        # Determine community type based on entity types
        entity_types = [e.get("entity_type", "") for e in community_entities]
        community_type = self._determine_community_type(entity_types)
        
        # Find central entities using degree centrality
        subgraph = nx_graph.subgraph(community)
        centrality = nx.degree_centrality(subgraph)
        central_entities = sorted(centrality.keys(), 
                                key=lambda x: centrality[x], 
                                reverse=True)[:3]
        
        # Calculate coherence score
        coherence = self._calculate_coherence(community, nx_graph)
        
        # Generate description
        description = self._generate_community_description(
            community_entities, community_type, central_entities, entity_map
        )
        
        return {
            "community_id": f"comm_{comm_id:03d}",
            "description": description,
            "entity_count": len(community),
            "coherence_score": round(coherence, 3),
            "entity_ids": list(community),
            "central_entities": central_entities,
            "community_type": community_type,
            "metadata": {
                "entity_types": dict(zip(*np.unique(entity_types, return_counts=True))),
                "avg_confidence": np.mean([e.get("confidence", 0.95) for e in community_entities])
            }
        }
    
    def _determine_community_type(self, entity_types: List[str]) -> str:
        """Determine community type based on entity composition."""
        if not entity_types:
            return "UNKNOWN"
        
        type_counts = defaultdict(int)
        for etype in entity_types:
            type_counts[etype] += 1
        
        # Get dominant type
        dominant_type = max(type_counts, key=type_counts.get)
        dominant_ratio = type_counts[dominant_type] / len(entity_types)
        
        # Legal-specific community types
        if dominant_type == "PARTY" and dominant_ratio > 0.6:
            return "LEGAL_PARTIES"
        elif dominant_type == "COURT" and dominant_ratio > 0.5:
            return "JUDICIAL_ENTITIES"
        elif dominant_type in ["JUDGE", "ATTORNEY"] and dominant_ratio > 0.5:
            return "LEGAL_PROFESSIONALS"
        elif "CITATION" in type_counts and type_counts["CITATION"] > 2:
            return "CITATION_NETWORK"
        elif "CONTRACT" in dominant_type:
            return "CONTRACT_ENTITIES"
        else:
            return "MIXED_ENTITIES"
    
    def _generate_community_description(self,
                                       community_entities: List[Dict[str, Any]],
                                       community_type: str,
                                       central_entities: List[str],
                                       entity_map: Dict[str, Dict[str, Any]]) -> str:
        """Generate human-readable community description."""
        if not central_entities:
            return f"{community_type} community with {len(community_entities)} entities"
        
        # Get names of central entities
        central_names = []
        for eid in central_entities[:2]:
            if eid in entity_map:
                central_names.append(entity_map[eid].get("entity_text", eid))
        
        if community_type == "LEGAL_PARTIES":
            return f"Legal parties centered around {', '.join(central_names)}"
        elif community_type == "JUDICIAL_ENTITIES":
            return f"Judicial entities including {', '.join(central_names)}"
        elif community_type == "LEGAL_PROFESSIONALS":
            return f"Legal professionals network with {', '.join(central_names)}"
        elif community_type == "CITATION_NETWORK":
            return f"Citation network involving {', '.join(central_names)}"
        else:
            return f"{community_type} community featuring {', '.join(central_names)}"
    
    async def calculate_hierarchical_communities(self,
                                                entities: List[Dict[str, Any]],
                                                relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate hierarchical community structure (Microsoft GraphRAG approach).
        Detects communities at multiple resolution levels.
        """
        hierarchical_communities = []
        
        # Try different resolution parameters
        resolutions = [0.5, 1.0, 1.5, 2.0]
        
        for resolution in resolutions:
            self.resolution = resolution
            communities, metadata = await self.detect_communities(
                entities, relationships
            )
            
            if communities:
                hierarchical_communities.append({
                    "level": f"resolution_{resolution}",
                    "resolution": resolution,
                    "communities": communities,
                    "metadata": metadata
                })
        
        return hierarchical_communities