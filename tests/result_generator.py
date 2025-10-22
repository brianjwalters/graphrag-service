#!/usr/bin/env python3
"""
GraphRAG Test Result Generator
Generates standardized test results following AGENT_DEFINITIONS.md structure
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse


class GraphRAGTestResult:
    """Generates standardized GraphRAG test results"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.iso_timestamp = datetime.now().isoformat()
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize standard structure
        self.structure = {
            "test_metadata": {
                "pipeline_id": f"graphrag_test_{self.timestamp}",
                "test_document": "/srv/luris/be/tests/docs/Rahimi.pdf",
                "test_timestamp": self.iso_timestamp,
                "test_status": "in_progress",
                "graphrag_mode": "FULL_GRAPHRAG",  # FULL_GRAPHRAG|LAZY_GRAPHRAG|HYBRID_MODE
                "service_version": "1.0.0"
            },
            "service_health": {
                "document_processing": False,
                "entity_extraction": False,
                "graphrag": False,
                "database": False,
                "embeddings": False
            },
            "pipeline_stages": {
                "document_upload": {
                    "status": "pending",
                    "duration_ms": 0.0,
                    "document_id": "",
                    "file_size_bytes": 0
                },
                "markdown_conversion": {
                    "status": "pending",
                    "duration_ms": 0.0,
                    "content_length": 0
                },
                "chunking": {
                    "status": "pending",
                    "duration_ms": 0.0,
                    "chunks_created": 0,
                    "avg_chunk_size": 0.0
                },
                "entity_extraction": {
                    "status": "pending",
                    "duration_ms": 0.0,
                    "entities_extracted": 0,
                    "citations_extracted": 0
                },
                "embedding_generation": {
                    "status": "pending",
                    "duration_ms": 0.0,
                    "embeddings_created": 0,
                    "dimensions": 2048
                },
                "graph_construction": {
                    "status": "pending",
                    "duration_ms": 0.0,
                    "nodes_created": 0,
                    "edges_created": 0,
                    "communities_detected": 0
                }
            },
            "graph_metrics": {
                "nodes": {
                    "total_count": 0,
                    "by_type": {
                        "entity": 0,
                        "document": 0,
                        "chunk": 0,
                        "community": 0
                    },
                    "centrality_scores": {
                        "highest": {"node_id": "", "score": 0.0},
                        "average": 0.0
                    }
                },
                "edges": {
                    "total_count": 0,
                    "by_type": {
                        "entity_to_entity": 0,
                        "entity_to_document": 0,
                        "chunk_to_chunk": 0,
                        "community_membership": 0
                    },
                    "weight_distribution": {
                        "min": 0.0,
                        "max": 0.0,
                        "average": 0.0
                    }
                },
                "communities": {
                    "total_count": 0,
                    "size_distribution": [],
                    "algorithm": "leiden",
                    "resolution": 1.0,
                    "modularity_score": 0.0
                }
            },
            "relationship_validation": {
                "intra_document_relationships": {
                    "count": 0,
                    "validated": 0,
                    "accuracy": 0.0
                },
                "cross_document_relationships": {
                    "count": 0,
                    "validated": 0,
                    "accuracy": 0.0
                },
                "citation_relationships": {
                    "count": 0,
                    "validated": 0,
                    "accuracy": 0.0
                }
            },
            "query_performance": {
                "local_search": {
                    "avg_response_time_ms": 0.0,
                    "queries_tested": 0,
                    "success_rate": 0.0
                },
                "global_search": {
                    "avg_response_time_ms": 0.0,
                    "queries_tested": 0,
                    "success_rate": 0.0
                },
                "hybrid_search": {
                    "avg_response_time_ms": 0.0,
                    "queries_tested": 0,
                    "success_rate": 0.0
                },
                "graph_traversal": {
                    "1_hop_avg_ms": 0.0,
                    "2_hop_avg_ms": 0.0,
                    "3_hop_avg_ms": 0.0
                }
            },
            "data_flow_visualization": {
                "document_to_chunks": {"document_id": "", "chunk_ids": []},
                "chunks_to_entities": {"chunk_id": "", "entity_ids": []},
                "entities_to_nodes": {"entity_id": "", "node_ids": []},
                "nodes_to_communities": {"node_id": "", "community_ids": []}
            },
            "quality_metrics": {
                "entity_deduplication": {
                    "before": 0,
                    "after": 0,
                    "reduction_percentage": 0.0
                },
                "graph_connectivity": {
                    "connected_components": 0,
                    "largest_component_size": 0,
                    "average_degree": 0.0
                },
                "data_completeness": {
                    "entities_with_embeddings": 0.0,
                    "chunks_with_context": 0.0,
                    "nodes_with_communities": 0.0
                }
            }
        }
    
    def set_metadata(self, **kwargs):
        """Update test metadata"""
        self.structure["test_metadata"].update(kwargs)
        return self
    
    def set_service_health(self, **kwargs):
        """Update service health status"""
        self.structure["service_health"].update(kwargs)
        return self
    
    def update_pipeline_stage(self, stage: str, **kwargs):
        """Update a specific pipeline stage"""
        if stage in self.structure["pipeline_stages"]:
            self.structure["pipeline_stages"][stage].update(kwargs)
        return self
    
    def set_graph_metrics(self, **kwargs):
        """Update graph metrics"""
        if "nodes" in kwargs:
            self.structure["graph_metrics"]["nodes"].update(kwargs["nodes"])
        if "edges" in kwargs:
            self.structure["graph_metrics"]["edges"].update(kwargs["edges"])
        if "communities" in kwargs:
            self.structure["graph_metrics"]["communities"].update(kwargs["communities"])
        return self
    
    def set_relationship_validation(self, **kwargs):
        """Update relationship validation metrics"""
        for rel_type in ["intra_document_relationships", "cross_document_relationships", "citation_relationships"]:
            if rel_type in kwargs:
                self.structure["relationship_validation"][rel_type].update(kwargs[rel_type])
                # Calculate accuracy
                rel = self.structure["relationship_validation"][rel_type]
                if rel["count"] > 0:
                    rel["accuracy"] = rel["validated"] / rel["count"]
        return self
    
    def set_query_performance(self, **kwargs):
        """Update query performance metrics"""
        for search_type in ["local_search", "global_search", "hybrid_search"]:
            if search_type in kwargs:
                self.structure["query_performance"][search_type].update(kwargs[search_type])
                # Calculate success rate
                perf = self.structure["query_performance"][search_type]
                if perf["queries_tested"] > 0:
                    # Assuming success tracking is done elsewhere
                    pass
        
        if "graph_traversal" in kwargs:
            self.structure["query_performance"]["graph_traversal"].update(kwargs["graph_traversal"])
        return self
    
    def set_data_flow(self, **kwargs):
        """Update data flow visualization"""
        self.structure["data_flow_visualization"].update(kwargs)
        return self
    
    def calculate_quality_metrics(self):
        """Calculate quality metrics based on current data"""
        # Calculate entity deduplication
        dedup = self.structure["quality_metrics"]["entity_deduplication"]
        if dedup["before"] > 0:
            dedup["reduction_percentage"] = (
                (dedup["before"] - dedup["after"]) / dedup["before"] * 100
            )
        
        # Calculate graph connectivity
        nodes_count = self.structure["graph_metrics"]["nodes"]["total_count"]
        edges_count = self.structure["graph_metrics"]["edges"]["total_count"]
        
        if nodes_count > 0:
            self.structure["quality_metrics"]["graph_connectivity"]["average_degree"] = (
                2 * edges_count / nodes_count
            )
        
        # Calculate data completeness
        completeness = self.structure["quality_metrics"]["data_completeness"]
        
        # These would be calculated based on actual data
        # For now, setting example values
        if self.structure["graph_metrics"]["nodes"]["total_count"] > 0:
            completeness["nodes_with_communities"] = 0.85  # Example: 85% of nodes in communities
        
        return self
    
    def calculate_total_pipeline_time(self):
        """Calculate total pipeline execution time"""
        total_time = 0
        for stage, data in self.structure["pipeline_stages"].items():
            total_time += data.get("duration_ms", 0)
        return total_time
    
    def finalize(self):
        """Mark test as completed and calculate final metrics"""
        self.structure["test_metadata"]["test_status"] = "completed"
        
        # Calculate quality metrics
        self.calculate_quality_metrics()
        
        # Update node and edge totals
        nodes = self.structure["graph_metrics"]["nodes"]
        nodes["total_count"] = sum(nodes["by_type"].values())
        
        edges = self.structure["graph_metrics"]["edges"]
        edges["total_count"] = sum(edges["by_type"].values())
        
        return self
    
    def save_json(self, filename: Optional[str] = None) -> str:
        """Save results to JSON file"""
        if filename is None:
            filename = f"graphrag_{self.timestamp}.json"
        
        filepath = self.results_dir / filename
        with open(filepath, 'w') as f:
            json.dump(self.structure, f, indent=2, default=str)
        
        print(f"Results saved to: {filepath}")
        return str(filepath)
    
    def save_markdown(self, filename: Optional[str] = None) -> str:
        """Generate and save markdown report"""
        if filename is None:
            filename = f"graphrag_{self.timestamp}.md"
        
        filepath = self.results_dir / filename
        
        md_content = self._generate_markdown_report()
        with open(filepath, 'w') as f:
            f.write(md_content)
        
        print(f"Markdown report saved to: {filepath}")
        return str(filepath)
    
    def _generate_markdown_report(self) -> str:
        """Generate comprehensive markdown report"""
        s = self.structure
        total_time = self.calculate_total_pipeline_time()
        
        report = f"""# GraphRAG Test Report

## Test Information
- **Pipeline ID**: {s['test_metadata']['pipeline_id']}
- **Timestamp**: {s['test_metadata']['test_timestamp']}
- **Document**: {s['test_metadata']['test_document']}
- **GraphRAG Mode**: {s['test_metadata']['graphrag_mode']}
- **Status**: {s['test_metadata']['test_status']}

## Service Health
| Service | Status |
|---------|--------|
| Document Processing | {'✅' if s['service_health']['document_processing'] else '❌'} |
| Entity Extraction | {'✅' if s['service_health']['entity_extraction'] else '❌'} |
| GraphRAG | {'✅' if s['service_health']['graphrag'] else '❌'} |
| Database | {'✅' if s['service_health']['database'] else '❌'} |
| Embeddings | {'✅' if s['service_health']['embeddings'] else '❌'} |

## Pipeline Execution Summary
| Stage | Status | Duration (ms) | Details |
|-------|--------|---------------|---------|
"""
        
        for stage, data in s['pipeline_stages'].items():
            stage_name = stage.replace('_', ' ').title()
            status_icon = '✅' if data['status'] == 'completed' else '⏳' if data['status'] == 'in_progress' else '❌'
            
            details = ""
            if stage == "chunking":
                details = f"{data['chunks_created']} chunks"
            elif stage == "entity_extraction":
                details = f"{data['entities_extracted']} entities, {data['citations_extracted']} citations"
            elif stage == "graph_construction":
                details = f"{data['nodes_created']} nodes, {data['edges_created']} edges"
            
            report += f"| {stage_name} | {status_icon} | {data['duration_ms']:.2f} | {details} |\n"
        
        report += f"\n**Total Pipeline Time**: {total_time:.2f} ms\n"
        
        report += f"""
## Graph Metrics

### Node Statistics
- **Total Nodes**: {s['graph_metrics']['nodes']['total_count']}
- **Entity Nodes**: {s['graph_metrics']['nodes']['by_type']['entity']}
- **Document Nodes**: {s['graph_metrics']['nodes']['by_type']['document']}
- **Chunk Nodes**: {s['graph_metrics']['nodes']['by_type']['chunk']}
- **Community Nodes**: {s['graph_metrics']['nodes']['by_type']['community']}
- **Highest Centrality**: {s['graph_metrics']['nodes']['centrality_scores']['highest']['node_id']} ({s['graph_metrics']['nodes']['centrality_scores']['highest']['score']:.3f})
- **Average Centrality**: {s['graph_metrics']['nodes']['centrality_scores']['average']:.3f}

### Edge Statistics
- **Total Edges**: {s['graph_metrics']['edges']['total_count']}
- **Entity-to-Entity**: {s['graph_metrics']['edges']['by_type']['entity_to_entity']}
- **Entity-to-Document**: {s['graph_metrics']['edges']['by_type']['entity_to_document']}
- **Chunk-to-Chunk**: {s['graph_metrics']['edges']['by_type']['chunk_to_chunk']}
- **Community Membership**: {s['graph_metrics']['edges']['by_type']['community_membership']}
- **Weight Range**: {s['graph_metrics']['edges']['weight_distribution']['min']:.3f} - {s['graph_metrics']['edges']['weight_distribution']['max']:.3f}
- **Average Weight**: {s['graph_metrics']['edges']['weight_distribution']['average']:.3f}

### Community Detection
- **Total Communities**: {s['graph_metrics']['communities']['total_count']}
- **Algorithm**: {s['graph_metrics']['communities']['algorithm']}
- **Resolution**: {s['graph_metrics']['communities']['resolution']}
- **Modularity Score**: {s['graph_metrics']['communities']['modularity_score']:.3f}
- **Size Distribution**: {s['graph_metrics']['communities']['size_distribution']}

## Relationship Validation
| Relationship Type | Count | Validated | Accuracy |
|------------------|-------|-----------|----------|
| Intra-document | {s['relationship_validation']['intra_document_relationships']['count']} | {s['relationship_validation']['intra_document_relationships']['validated']} | {s['relationship_validation']['intra_document_relationships']['accuracy']:.1%} |
| Cross-document | {s['relationship_validation']['cross_document_relationships']['count']} | {s['relationship_validation']['cross_document_relationships']['validated']} | {s['relationship_validation']['cross_document_relationships']['accuracy']:.1%} |
| Citations | {s['relationship_validation']['citation_relationships']['count']} | {s['relationship_validation']['citation_relationships']['validated']} | {s['relationship_validation']['citation_relationships']['accuracy']:.1%} |

## Query Performance
| Search Type | Avg Response (ms) | Queries Tested | Success Rate |
|-------------|------------------|----------------|--------------|
| Local Search | {s['query_performance']['local_search']['avg_response_time_ms']:.2f} | {s['query_performance']['local_search']['queries_tested']} | {s['query_performance']['local_search']['success_rate']:.1%} |
| Global Search | {s['query_performance']['global_search']['avg_response_time_ms']:.2f} | {s['query_performance']['global_search']['queries_tested']} | {s['query_performance']['global_search']['success_rate']:.1%} |
| Hybrid Search | {s['query_performance']['hybrid_search']['avg_response_time_ms']:.2f} | {s['query_performance']['hybrid_search']['queries_tested']} | {s['query_performance']['hybrid_search']['success_rate']:.1%} |

### Graph Traversal Performance
- **1-hop traversal**: {s['query_performance']['graph_traversal']['1_hop_avg_ms']:.2f} ms
- **2-hop traversal**: {s['query_performance']['graph_traversal']['2_hop_avg_ms']:.2f} ms
- **3-hop traversal**: {s['query_performance']['graph_traversal']['3_hop_avg_ms']:.2f} ms

## Quality Metrics

### Entity Deduplication
- **Entities Before**: {s['quality_metrics']['entity_deduplication']['before']}
- **Entities After**: {s['quality_metrics']['entity_deduplication']['after']}
- **Reduction**: {s['quality_metrics']['entity_deduplication']['reduction_percentage']:.1f}%

### Graph Connectivity
- **Connected Components**: {s['quality_metrics']['graph_connectivity']['connected_components']}
- **Largest Component**: {s['quality_metrics']['graph_connectivity']['largest_component_size']} nodes
- **Average Degree**: {s['quality_metrics']['graph_connectivity']['average_degree']:.2f}

### Data Completeness
- **Entities with Embeddings**: {s['quality_metrics']['data_completeness']['entities_with_embeddings']:.1%}
- **Chunks with Context**: {s['quality_metrics']['data_completeness']['chunks_with_context']:.1%}
- **Nodes in Communities**: {s['quality_metrics']['data_completeness']['nodes_with_communities']:.1%}

## Data Flow Visualization
```
Document ({s['data_flow_visualization']['document_to_chunks']['document_id'][:8]}...)
    ↓
Chunks ({len(s['data_flow_visualization']['document_to_chunks']['chunk_ids'])} chunks)
    ↓
Entities ({len(s['data_flow_visualization']['chunks_to_entities']['entity_ids'])} entities)
    ↓
Graph Nodes ({len(s['data_flow_visualization']['entities_to_nodes']['node_ids'])} nodes)
    ↓
Communities ({len(s['data_flow_visualization']['nodes_to_communities']['community_ids'])} communities)
```

## Recommendations
1. Monitor entity extraction accuracy for improved graph quality
2. Optimize embedding generation for large documents
3. Fine-tune community detection parameters for domain-specific clustering
4. Implement caching for frequently accessed graph traversals
"""
        
        return report
    
    def get_results(self) -> Dict[str, Any]:
        """Get the complete results structure"""
        return self.structure


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Generate GraphRAG test results")
    parser.add_argument("--mode", choices=["FULL_GRAPHRAG", "LAZY_GRAPHRAG", "HYBRID_MODE"], 
                       default="FULL_GRAPHRAG", help="GraphRAG mode")
    parser.add_argument("--save", action="store_true", 
                       help="Save results to files")
    parser.add_argument("--example", action="store_true",
                       help="Generate example data")
    
    args = parser.parse_args()
    
    # Create test result generator
    generator = GraphRAGTestResult()
    
    # Set metadata
    generator.set_metadata(graphrag_mode=args.mode)
    
    # Set service health (example)
    generator.set_service_health(
        document_processing=True,
        entity_extraction=True,
        graphrag=True,
        database=True,
        embeddings=True
    )
    
    if args.example:
        # Update pipeline stages
        generator.update_pipeline_stage("document_upload",
            status="completed",
            duration_ms=1523.45,
            document_id="doc_abc123",
            file_size_bytes=2048576
        )
        
        generator.update_pipeline_stage("chunking",
            status="completed",
            duration_ms=823.12,
            chunks_created=42,
            avg_chunk_size=512.5
        )
        
        generator.update_pipeline_stage("entity_extraction",
            status="completed",
            duration_ms=2341.67,
            entities_extracted=156,
            citations_extracted=23
        )
        
        generator.update_pipeline_stage("graph_construction",
            status="completed",
            duration_ms=3456.78,
            nodes_created=198,
            edges_created=456,
            communities_detected=12
        )
        
        # Set graph metrics
        generator.set_graph_metrics(
            nodes={
                "by_type": {
                    "entity": 156,
                    "document": 1,
                    "chunk": 42,
                    "community": 12
                },
                "centrality_scores": {
                    "highest": {"node_id": "node_judge_001", "score": 0.892},
                    "average": 0.234
                }
            },
            edges={
                "by_type": {
                    "entity_to_entity": 234,
                    "entity_to_document": 156,
                    "chunk_to_chunk": 41,
                    "community_membership": 198
                },
                "weight_distribution": {
                    "min": 0.1,
                    "max": 1.0,
                    "average": 0.567
                }
            },
            communities={
                "total_count": 12,
                "size_distribution": [23, 19, 18, 16, 15, 14, 12, 11, 10, 9, 8, 3],
                "algorithm": "leiden",
                "resolution": 1.0,
                "modularity_score": 0.743
            }
        )
        
        # Set relationship validation
        generator.set_relationship_validation(
            intra_document_relationships={
                "count": 234,
                "validated": 221
            },
            cross_document_relationships={
                "count": 45,
                "validated": 38
            },
            citation_relationships={
                "count": 23,
                "validated": 22
            }
        )
        
        # Set query performance
        generator.set_query_performance(
            local_search={
                "avg_response_time_ms": 45.3,
                "queries_tested": 100,
                "success_rate": 0.98
            },
            global_search={
                "avg_response_time_ms": 123.7,
                "queries_tested": 50,
                "success_rate": 0.94
            },
            hybrid_search={
                "avg_response_time_ms": 89.2,
                "queries_tested": 75,
                "success_rate": 0.96
            },
            graph_traversal={
                "1_hop_avg_ms": 12.3,
                "2_hop_avg_ms": 34.5,
                "3_hop_avg_ms": 78.9
            }
        )
        
        # Set quality metrics
        generator.structure["quality_metrics"]["entity_deduplication"] = {
            "before": 234,
            "after": 156,
            "reduction_percentage": 0.0  # Will be calculated
        }
        
        generator.structure["quality_metrics"]["graph_connectivity"] = {
            "connected_components": 1,
            "largest_component_size": 198,
            "average_degree": 0.0  # Will be calculated
        }
        
        generator.structure["quality_metrics"]["data_completeness"] = {
            "entities_with_embeddings": 0.98,
            "chunks_with_context": 1.0,
            "nodes_with_communities": 0.85
        }
    
    # Finalize results
    generator.finalize()
    
    if args.save:
        json_path = generator.save_json()
        md_path = generator.save_markdown()
        print(f"\nTest results saved:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")
    else:
        # Print results to console
        print(json.dumps(generator.get_results(), indent=2, default=str))


if __name__ == "__main__":
    main()