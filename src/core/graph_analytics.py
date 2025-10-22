"""
Graph Analytics Module
Computes graph metrics, centrality scores, and quality assessments
"""

import asyncio
from typing import List, Dict, Any, Tuple, Optional
import networkx as nx
import numpy as np
from collections import defaultdict, Counter


class GraphAnalytics:
    """
    Computes comprehensive graph analytics and quality metrics.
    Implements legal-specific metrics and Microsoft GraphRAG quality scoring.
    """
    
    def __init__(self):
        """Initialize graph analytics engine."""
        self.graph = None
        self.metrics_cache = {}
        
    async def analyze_graph(self,
                           entities: List[Dict[str, Any]],
                           relationships: List[Dict[str, Any]],
                           communities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform comprehensive graph analysis.
        
        Args:
            entities: List of graph entities
            relationships: List of relationships
            communities: List of detected communities
            
        Returns:
            Dictionary of analytics results
        """
        # Build NetworkX graph
        self.graph = self._build_graph(entities, relationships)
        
        # Compute various analytics
        analytics = {
            "basic_metrics": await self._compute_basic_metrics(),
            "centrality_analysis": await self._compute_centrality_metrics(),
            "connectivity_analysis": await self._compute_connectivity_metrics(),
            "community_analysis": await self._analyze_communities(communities),
            "legal_metrics": await self._compute_legal_metrics(entities, relationships),
            "quality_assessment": await self._assess_graph_quality(entities, relationships, communities),
            "temporal_analysis": await self._compute_temporal_metrics(entities, relationships)
        }
        
        # Compute top entities and relationships
        analytics["top_entities"] = self._get_top_entities(analytics["centrality_analysis"])
        analytics["relationship_distribution"] = self._analyze_relationship_distribution(relationships)
        
        return analytics
    
    def _build_graph(self, 
                    entities: List[Dict[str, Any]], 
                    relationships: List[Dict[str, Any]]) -> nx.Graph:
        """Build NetworkX graph from entities and relationships."""
        G = nx.Graph()
        
        # Add nodes
        for entity in entities:
            G.add_node(
                entity["entity_id"],
                **{k: v for k, v in entity.items() if k != "entity_id"}
            )
        
        # Add edges
        for rel in relationships:
            if (rel.get("source_entity") in G.nodes and 
                rel.get("target_entity") in G.nodes):
                G.add_edge(
                    rel["source_entity"],
                    rel["target_entity"],
                    weight=rel.get("confidence", 0.8),
                    relationship_type=rel.get("relationship_type", ""),
                    **{k: v for k, v in rel.items() 
                       if k not in ["source_entity", "target_entity", "confidence", "relationship_type"]}
                )
        
        return G
    
    async def _compute_basic_metrics(self) -> Dict[str, Any]:
        """Compute basic graph metrics."""
        if not self.graph:
            return {}
        
        metrics = {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph) if self.graph.number_of_nodes() > 0 else 0,
            "average_degree": sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() 
                            if self.graph.number_of_nodes() > 0 else 0,
            "components": nx.number_connected_components(self.graph),
            "is_connected": nx.is_connected(self.graph),
            "diameter": nx.diameter(self.graph) if nx.is_connected(self.graph) else -1,
            "radius": nx.radius(self.graph) if nx.is_connected(self.graph) else -1
        }
        
        # Clustering coefficient
        try:
            metrics["clustering_coefficient"] = nx.average_clustering(self.graph)
        except:
            metrics["clustering_coefficient"] = 0.0
        
        # Transitivity
        try:
            metrics["transitivity"] = nx.transitivity(self.graph)
        except:
            metrics["transitivity"] = 0.0
        
        return metrics
    
    async def _compute_centrality_metrics(self) -> Dict[str, Any]:
        """Compute various centrality metrics."""
        if not self.graph or self.graph.number_of_nodes() == 0:
            return {}
        
        centrality_metrics = {}
        
        # Degree centrality
        degree_centrality = nx.degree_centrality(self.graph)
        centrality_metrics["degree_centrality"] = {
            "values": degree_centrality,
            "mean": np.mean(list(degree_centrality.values())),
            "std": np.std(list(degree_centrality.values())),
            "max": max(degree_centrality.values()) if degree_centrality else 0
        }
        
        # Betweenness centrality (computationally expensive for large graphs)
        if self.graph.number_of_nodes() < 1000:
            betweenness = nx.betweenness_centrality(self.graph)
            centrality_metrics["betweenness_centrality"] = {
                "values": betweenness,
                "mean": np.mean(list(betweenness.values())),
                "std": np.std(list(betweenness.values())),
                "max": max(betweenness.values()) if betweenness else 0
            }
        
        # Closeness centrality (only for connected components)
        if nx.is_connected(self.graph):
            closeness = nx.closeness_centrality(self.graph)
            centrality_metrics["closeness_centrality"] = {
                "values": closeness,
                "mean": np.mean(list(closeness.values())),
                "std": np.std(list(closeness.values())),
                "max": max(closeness.values()) if closeness else 0
            }
        
        # Eigenvector centrality
        try:
            eigenvector = nx.eigenvector_centrality(self.graph, max_iter=100)
            centrality_metrics["eigenvector_centrality"] = {
                "values": eigenvector,
                "mean": np.mean(list(eigenvector.values())),
                "std": np.std(list(eigenvector.values())),
                "max": max(eigenvector.values()) if eigenvector else 0
            }
        except:
            centrality_metrics["eigenvector_centrality"] = {"error": "Could not compute"}
        
        # PageRank
        try:
            pagerank = nx.pagerank(self.graph)
            centrality_metrics["pagerank"] = {
                "values": pagerank,
                "mean": np.mean(list(pagerank.values())),
                "std": np.std(list(pagerank.values())),
                "max": max(pagerank.values()) if pagerank else 0
            }
        except:
            centrality_metrics["pagerank"] = {"error": "Could not compute"}
        
        return centrality_metrics
    
    async def _compute_connectivity_metrics(self) -> Dict[str, Any]:
        """Compute connectivity-related metrics."""
        if not self.graph:
            return {}
        
        metrics = {}
        
        # Connected components
        components = list(nx.connected_components(self.graph))
        metrics["num_components"] = len(components)
        metrics["largest_component_size"] = max(len(c) for c in components) if components else 0
        metrics["component_sizes"] = sorted([len(c) for c in components], reverse=True)
        
        # Node connectivity (for connected graphs)
        if nx.is_connected(self.graph):
            metrics["node_connectivity"] = nx.node_connectivity(self.graph)
            metrics["edge_connectivity"] = nx.edge_connectivity(self.graph)
        
        # Bridges and articulation points
        bridges = list(nx.bridges(self.graph))
        metrics["num_bridges"] = len(bridges)
        metrics["bridges"] = bridges[:10]  # Limit to first 10
        
        articulation_points = list(nx.articulation_points(self.graph))
        metrics["num_articulation_points"] = len(articulation_points)
        metrics["articulation_points"] = articulation_points[:10]  # Limit to first 10
        
        # Assortativity (tendency of nodes to connect to similar nodes)
        # Only compute for graphs with sufficient edges to avoid division by zero warnings
        if self.graph.number_of_edges() > 2:
            try:
                metrics["degree_assortativity"] = nx.degree_assortativity_coefficient(self.graph)
            except:
                metrics["degree_assortativity"] = None
        else:
            metrics["degree_assortativity"] = None
        
        return metrics
    
    async def _analyze_communities(self, communities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze community structure."""
        if not communities:
            return {"num_communities": 0}
        
        analysis = {
            "num_communities": len(communities),
            "community_sizes": [c.get("entity_count", 0) for c in communities],
            "avg_community_size": np.mean([c.get("entity_count", 0) for c in communities]),
            "avg_coherence": np.mean([c.get("coherence_score", 0) for c in communities]),
            "community_types": Counter([c.get("community_type", "UNKNOWN") for c in communities])
        }
        
        # Modularity calculation (if we have node-to-community mapping)
        if self.graph and communities:
            # Create partition dictionary
            partition = {}
            for idx, community in enumerate(communities):
                for entity_id in community.get("entity_ids", []):
                    if entity_id in self.graph.nodes:
                        partition[entity_id] = idx
            
            # Calculate modularity if partition is valid
            if partition:
                try:
                    from networkx.algorithms.community import modularity
                    communities_for_modularity = defaultdict(set)
                    for node, comm_id in partition.items():
                        communities_for_modularity[comm_id].add(node)
                    
                    mod_value = modularity(self.graph, communities_for_modularity.values())
                    analysis["modularity"] = mod_value
                except:
                    analysis["modularity"] = None
        
        return analysis
    
    async def _compute_legal_metrics(self, 
                                    entities: List[Dict[str, Any]], 
                                    relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute legal domain-specific metrics."""
        metrics = {}
        
        # Entity type distribution
        entity_types = [e.get("entity_type", "UNKNOWN") for e in entities]
        metrics["entity_type_distribution"] = dict(Counter(entity_types))
        
        # Relationship type distribution
        rel_types = [r.get("relationship_type", "UNKNOWN") for r in relationships]
        metrics["relationship_type_distribution"] = dict(Counter(rel_types))
        
        # Legal entity statistics
        legal_entities = ["PARTY", "COURT", "JUDGE", "ATTORNEY", "CASE", "STATUTE"]
        legal_entity_count = sum(1 for t in entity_types if t in legal_entities)
        metrics["legal_entity_ratio"] = legal_entity_count / len(entities) if entities else 0
        
        # Citation relationship analysis
        citation_rels = [r for r in relationships 
                        if "CITE" in r.get("relationship_type", "").upper()]
        metrics["citation_relationships"] = len(citation_rels)
        metrics["citation_ratio"] = len(citation_rels) / len(relationships) if relationships else 0
        
        # Cross-document relationship analysis
        cross_doc_rels = [r for r in relationships 
                         if r.get("discovery_method") == "cross_document"]
        metrics["cross_document_relationships"] = len(cross_doc_rels)
        metrics["cross_document_ratio"] = len(cross_doc_rels) / len(relationships) if relationships else 0
        
        # Court hierarchy analysis
        courts = [e for e in entities if e.get("entity_type") == "COURT"]
        if courts and self.graph:
            court_ids = [c["entity_id"] for c in courts]
            court_subgraph = self.graph.subgraph(court_ids)
            metrics["court_network_density"] = nx.density(court_subgraph) if court_subgraph.number_of_nodes() > 1 else 0
        
        # Party network analysis
        parties = [e for e in entities if e.get("entity_type") == "PARTY"]
        if parties and self.graph:
            party_ids = [p["entity_id"] for p in parties]
            party_subgraph = self.graph.subgraph(party_ids)
            metrics["party_network_density"] = nx.density(party_subgraph) if party_subgraph.number_of_nodes() > 1 else 0
        
        return metrics
    
    async def _assess_graph_quality(self,
                                   entities: List[Dict[str, Any]],
                                   relationships: List[Dict[str, Any]],
                                   communities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess overall graph quality using Microsoft GraphRAG metrics."""
        quality = {}
        
        # Graph completeness (ratio of actual to expected relationships)
        if entities and len(entities) > 1:
            max_possible_edges = len(entities) * (len(entities) - 1) / 2
            actual_edges = len(relationships)
            # Avoid division by zero and handle small graphs
            if max_possible_edges > 0:
                quality["completeness"] = min(actual_edges / (max_possible_edges * 0.1), 1.0)  # Assume 10% connectivity is complete
            else:
                quality["completeness"] = 1.0 if actual_edges == 0 else 0.0
        elif entities and len(entities) == 1:
            # Single entity graph is complete by definition
            quality["completeness"] = 1.0
        else:
            quality["completeness"] = 0.0
        
        # Entity confidence
        entity_confidences = [e.get("confidence", 0.95) for e in entities]
        quality["avg_entity_confidence"] = np.mean(entity_confidences) if entity_confidences else 0
        quality["min_entity_confidence"] = min(entity_confidences) if entity_confidences else 0
        
        # Relationship confidence
        rel_confidences = [r.get("confidence", 0.8) for r in relationships]
        quality["avg_relationship_confidence"] = np.mean(rel_confidences) if rel_confidences else 0
        quality["min_relationship_confidence"] = min(rel_confidences) if rel_confidences else 0
        
        # Community coherence
        if communities:
            coherences = [c.get("coherence_score", 0) for c in communities]
            quality["avg_community_coherence"] = np.mean(coherences)
            quality["min_community_coherence"] = min(coherences) if coherences else 0
        else:
            quality["avg_community_coherence"] = 0
            quality["min_community_coherence"] = 0
        
        # Coverage score (percentage of entities in communities)
        if communities and entities:
            entities_in_communities = set()
            for community in communities:
                entities_in_communities.update(community.get("entity_ids", []))
            quality["coverage_score"] = len(entities_in_communities) / len(entities)
        else:
            quality["coverage_score"] = 0
        
        # Overall quality score (weighted average)
        quality["overall_score"] = (
            quality["completeness"] * 0.2 +
            quality["avg_entity_confidence"] * 0.2 +
            quality["avg_relationship_confidence"] * 0.2 +
            quality["avg_community_coherence"] * 0.2 +
            quality["coverage_score"] * 0.2
        )
        
        # Quality warnings
        warnings = []
        if quality["completeness"] < 0.3:
            warnings.append("Low graph completeness - consider additional relationship discovery")
        if quality["avg_entity_confidence"] < 0.7:
            warnings.append("Low average entity confidence - review entity extraction")
        if quality["coverage_score"] < 0.5:
            warnings.append("Low community coverage - many isolated entities")
        
        quality["warnings"] = warnings
        
        # Improvement suggestions
        suggestions = []
        if len(relationships) < len(entities):
            suggestions.append("Graph has fewer relationships than entities - consider relationship inference")
        if communities and quality["avg_community_coherence"] < 0.7:
            suggestions.append("Low community coherence - adjust community detection parameters")
        
        quality["suggestions"] = suggestions
        
        return quality
    
    async def _compute_temporal_metrics(self,
                                       entities: List[Dict[str, Any]],
                                       relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute temporal analysis metrics if temporal data is available."""
        metrics = {}
        
        # Check for temporal data in entities
        temporal_entities = [e for e in entities 
                           if "created_at" in e or (e.get("attributes") and "date" in e.get("attributes", {}))]
        
        if temporal_entities:
            metrics["temporal_entities"] = len(temporal_entities)
            metrics["temporal_coverage"] = len(temporal_entities) / len(entities)
            
            # Extract dates and analyze temporal distribution
            dates = []
            for entity in temporal_entities:
                if "created_at" in entity:
                    dates.append(entity["created_at"])
                elif "date" in entity.get("attributes", {}):
                    dates.append(entity["attributes"]["date"])
            
            if dates:
                # Could perform more sophisticated temporal analysis here
                metrics["date_range"] = {
                    "earliest": min(dates) if dates else None,
                    "latest": max(dates) if dates else None
                }
        
        return metrics
    
    def _get_top_entities(self, centrality_analysis: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top entities by various centrality measures."""
        top_entities = []
        
        # Get top by degree centrality
        if "degree_centrality" in centrality_analysis and "values" in centrality_analysis["degree_centrality"]:
            degree_values = centrality_analysis["degree_centrality"]["values"]
            top_by_degree = sorted(degree_values.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            for entity_id, score in top_by_degree:
                entity_info = {
                    "entity_id": entity_id,
                    "degree_centrality": score
                }
                
                # Add other centrality scores if available
                if "pagerank" in centrality_analysis and "values" in centrality_analysis["pagerank"]:
                    entity_info["pagerank"] = centrality_analysis["pagerank"]["values"].get(entity_id, 0)
                
                if "betweenness_centrality" in centrality_analysis and "values" in centrality_analysis["betweenness_centrality"]:
                    entity_info["betweenness"] = centrality_analysis["betweenness_centrality"]["values"].get(entity_id, 0)
                
                # Add entity attributes from graph
                if self.graph and entity_id in self.graph.nodes:
                    node_data = self.graph.nodes[entity_id]
                    entity_info["entity_text"] = node_data.get("entity_text", "")
                    entity_info["entity_type"] = node_data.get("entity_type", "")
                
                top_entities.append(entity_info)
        
        return top_entities
    
    def _analyze_relationship_distribution(self, relationships: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze distribution of relationship types."""
        rel_types = [r.get("relationship_type", "UNKNOWN") for r in relationships]
        return dict(Counter(rel_types))
    
    async def calculate_importance_scores(self, entities: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate importance scores for entities using multiple factors.
        Used for ranking and filtering in GraphRAG queries.
        """
        if not self.graph:
            return {}
        
        importance_scores = {}
        
        # Get centrality metrics
        centrality = await self._compute_centrality_metrics()
        
        for entity in entities:
            entity_id = entity["entity_id"]
            if entity_id not in self.graph.nodes:
                continue
            
            score = 0.0
            weight_sum = 0.0
            
            # Degree centrality (weight: 0.3)
            if "degree_centrality" in centrality and "values" in centrality["degree_centrality"]:
                score += centrality["degree_centrality"]["values"].get(entity_id, 0) * 0.3
                weight_sum += 0.3
            
            # PageRank (weight: 0.3)
            if "pagerank" in centrality and "values" in centrality["pagerank"]:
                score += centrality["pagerank"]["values"].get(entity_id, 0) * 0.3
                weight_sum += 0.3
            
            # Entity confidence (weight: 0.2)
            confidence = entity.get("confidence", 0.95)
            score += confidence * 0.2
            weight_sum += 0.2
            
            # Entity type importance (weight: 0.2)
            entity_type = entity.get("entity_type", "")
            type_importance = {
                "COURT": 1.0,
                "JUDGE": 0.9,
                "PARTY": 0.8,
                "ATTORNEY": 0.7,
                "CASE": 0.9,
                "STATUTE": 0.85
            }.get(entity_type, 0.5)
            score += type_importance * 0.2
            weight_sum += 0.2
            
            # Normalize score
            if weight_sum > 0:
                importance_scores[entity_id] = score / weight_sum
            else:
                importance_scores[entity_id] = 0.0
        
        return importance_scores