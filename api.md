# GraphRAG Service API Reference

## Overview

The GraphRAG Service implements Microsoft's GraphRAG (Graph Retrieval-Augmented Generation) methodology for constructing knowledge graphs from legal documents. It provides advanced entity deduplication, community detection, and relationship discovery optimized for legal document processing.

- **Service**: GraphRAG Service
- **Version**: 1.0.0  
- **Port**: 8010
- **Base URL**: `http://localhost:8010/api/v1`
- **Health Check**: `http://localhost:8010/api/v1/health/ping`
- **Interactive Docs**: `http://localhost:8010/docs`

## Features

- **Microsoft GraphRAG Implementation**: Complete GraphRAG pipeline with legal optimizations
- **Entity Deduplication**: 0.85 similarity threshold with legal entity type awareness
- **Community Detection**: Leiden algorithm for optimal community structure (Leiden resolution 1.0, minimum size 3)
- **Cross-Document Linking**: Relationship discovery across document boundaries
- **Legal Specialization**: Court hierarchies, citation relationships, contract parties
- **Quality Assessment**: Graph completeness, coherence, and coverage metrics
- **Multiple Processing Modes**: FULL_GRAPHRAG, LAZY_GRAPHRAG (99.9% cost reduction), HYBRID_MODE
- **Search Types**: LOCAL_SEARCH (entity neighborhoods), GLOBAL_SEARCH (community summaries), HYBRID_SEARCH (combined)
- **Entity Extraction Integration**: Full integration with Entity Extraction Service supporting 31 legal entity types

## Supported Legal Entity Types

The service integrates with the Entity Extraction Service to support 31 comprehensive legal entity types:

### Citation Types (9)
- `CASE_CITATION` - Case law citations
- `STATUTE_CITATION` - Statutory citations
- `REGULATION_CITATION` - Regulatory citations
- `CONSTITUTIONAL_CITATION` - Constitutional provisions
- `LAW_REVIEW_CITATION` - Law review and journal citations
- `BOOK_CITATION` - Legal treatise citations
- `NEWSPAPER_CITATION` - News article citations
- `WEB_CITATION` - Web resource citations
- `PARALLEL_CITATION` - Parallel case citations

### Legal Entities (7)
- `COURT` - Courts and tribunals
- `JUDGE` - Judges and judicial officers
- `ATTORNEY` - Attorneys and legal counsel
- `PARTY` - Parties to legal proceedings
- `LAW_FIRM` - Law firms and legal organizations
- `GOVERNMENT_ENTITY` - Government agencies and bodies
- `JURISDICTION` - Jurisdictional entities

### Legal Concepts (9)
- `LEGAL_DOCTRINE` - Legal doctrines and principles
- `PROCEDURAL_TERM` - Procedural terminology
- `CLAIM_TYPE` - Types of legal claims
- `MOTION_TYPE` - Types of legal motions
- `LEGAL_STANDARD` - Legal standards and tests
- `REMEDY` - Legal remedies and relief
- `LEGAL_ISSUE` - Legal issues and questions
- `HOLDING` - Court holdings and determinations
- `RULING` - Court rulings and decisions

### Document Elements (6)
- `MONETARY_AMOUNT` - Financial amounts and damages
- `DATE` - Legal dates and deadlines
- `DOCKET_NUMBER` - Case docket numbers
- `EXHIBIT` - Exhibit identifiers
- `DEPOSITION` - Deposition references
- `INTERROGATORY` - Interrogatory references

### Additional Legal Elements (3)
- `JURY_VERDICT` - Jury verdicts and findings
- `SETTLEMENT` - Settlement terms and agreements
- `CONTRACT_CLAUSE` - Contract clauses and provisions
- `PATENT_NUMBER` - Patent identifiers
- `TRADEMARK` - Trademark references
- `COPYRIGHT` - Copyright references

## GraphRAG Processing Modes

### FULL_GRAPHRAG
Complete Microsoft GraphRAG implementation with all features enabled including entity extraction, deduplication, community detection, and AI-generated summaries.

### LAZY_GRAPHRAG
Cost-optimized mode with 99.9% cost reduction using NLP-based extraction and on-demand community summary generation. Summaries are only generated when relevance score exceeds 0.7.

### HYBRID_MODE
Intelligently combines FULL_GRAPHRAG and LAZY_GRAPHRAG approaches based on document importance and query relevance, optimizing for both cost and quality.

## Authentication

This service operates without authentication for internal use. Ensure proper network security in production deployments.

## Content Types

All requests and responses use `application/json` content type.

---

## Core Endpoints

### Graph Construction

#### POST /graph/create

Create a comprehensive knowledge graph from document entities, citations, and relationships using Microsoft GraphRAG methodology.

**Request Body:**
```json
{
  "document_id": "doc_001",
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_id": "660e8400-e29b-41d4-a716-446655440001",
  "markdown_content": "Document content for context...",
  "entities": [
    {
      "entity_id": "ent_001", 
      "entity_text": "Supreme Court of the United States",
      "entity_type": "COURT",
      "confidence": 0.95,
      "start_position": 0,
      "end_position": 30,
      "context": "In the Supreme Court case...",
      "metadata": {
        "jurisdiction": "federal",
        "level": "supreme"
      }
    },
    {
      "entity_id": "ent_002",
      "entity_text": "Plaintiff John Doe", 
      "entity_type": "PARTY",
      "confidence": 0.92,
      "start_position": 45,
      "end_position": 62,
      "context": "Plaintiff John Doe filed...",
      "metadata": {
        "party_type": "individual",
        "role": "plaintiff"
      }
    }
  ],
  "citations": [
    {
      "citation_id": "cite_001",
      "citation_text": "Miranda v. Arizona, 384 U.S. 436 (1966)",
      "citation_type": "CASE_LAW", 
      "confidence": 0.98,
      "precedential_value": "binding",
      "jurisdiction": "federal",
      "metadata": {
        "year": 1966,
        "court": "Supreme Court",
        "volume": 384,
        "page": 436
      }
    }
  ],
  "relationships": [
    {
      "relationship_id": "rel_001",
      "source_entity_id": "ent_001",
      "target_entity_id": "ent_002", 
      "relationship_type": "DECIDED_CASE",
      "confidence": 0.89,
      "context": "The Supreme Court decided in favor of...",
      "metadata": {
        "relationship_strength": "strong",
        "temporal_context": "past_decision"
      }
    }
  ],
  "enhanced_chunks": [
    {
      "chunk_id": "chunk_001",
      "content": "Enhanced chunk content with context...",
      "embedding_vector": [0.123, -0.456, 0.789],
      "start_position": 0,
      "end_position": 500,
      "quality_score": 0.92,
      "metadata": {
        "chunk_type": "legal_analysis",
        "contextual_enhancement": true
      }
    }
  ],
  "graph_options": {
    "enable_deduplication": true,
    "enable_community_detection": true, 
    "enable_cross_document_linking": true,
    "enable_analytics": true,
    "use_ai_summaries": true,
    "leiden_resolution": 1.0,
    "min_community_size": 3,
    "similarity_threshold": 0.85
  },
  "metadata": {
    "document_type": "court_opinion",
    "jurisdiction": "federal",
    "legal_domain": "constitutional_law",
    "processing_timestamp": "2025-01-15T10:30:00Z"
  }
}
```

**Success Response (200):**
```json
{
  "success": true,
  "graph_id": "graph_doc_001_1705312200",
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_id": "660e8400-e29b-41d4-a716-446655440001",
  "processing_results": {
    "entities_processed": 45,
    "entities_deduplicated": 8,
    "entities_final": 37,
    "relationships_discovered": 23,
    "relationships_cross_document": 5,
    "communities_detected": 4,
    "chunks_processed": 12,
    "embeddings_generated": 12
  },
  "graph_metrics": {
    "nodes": 37,
    "edges": 23,
    "density": 0.034,
    "connected_components": 1,
    "average_clustering": 0.67,
    "modularity": 0.82
  },
  "quality_metrics": {
    "graph_completeness": 0.94,
    "community_coherence": 0.88,
    "entity_confidence_avg": 0.91,
    "relationship_confidence_avg": 0.87,
    "coverage_score": 0.93,
    "warnings": [],
    "suggestions": [
      "Consider adding more cross-references for improved connectivity"
    ]
  },
  "communities": [
    {
      "community_id": "comm_001",
      "size": 12,
      "entities": ["ent_001", "ent_003", "ent_007"],
      "description": "Supreme Court and Constitutional Law entities",
      "ai_summary": "This community centers around Supreme Court constitutional law decisions...",
      "key_relationships": ["DECIDED_CASE", "CITES", "PRECEDENT"],
      "coherence_score": 0.91
    }
  ],
  "storage_info": {
    "nodes_created": 37,
    "edges_created": 23,
    "communities_detected": 4,
    "chunks_with_embeddings": 12,
    "graph_schema_tables": ["graph.nodes", "graph.edges", "graph.communities", "graph.chunks", "graph.enhanced_contextual_chunks"]
  },
  "processing_time_seconds": 4.25,
  "timestamp": "2025-01-15T10:30:04Z"
}
```

#### POST /graph/update

Update an existing knowledge graph with new entities and relationships.

**Request Body:**
```json
{
  "graph_id": "graph_doc_001_1705312200",
  "document_id": "doc_002",
  "entities": [...],
  "relationships": [...],
  "merge_strategy": "smart",
  "update_communities": true,
  "recalculate_metrics": true
}
```

**Success Response (200):**
```json
{
  "success": true,
  "graph_id": "graph_doc_001_1705312200",
  "nodes_added": 12,
  "edges_added": 8,
  "communities_updated": 2,
  "quality_metrics": {
    "graph_completeness": 0.96,
    "community_coherence": 0.90,
    "entity_confidence_avg": 0.92,
    "relationship_confidence_avg": 0.88,
    "coverage_score": 0.95
  },
  "processing_time_seconds": 2.8
}
```

#### POST /graph/query

Query the knowledge graph for entities, relationships, communities, or analytics.

**Request Body:**
```json
{
  "query_type": "entities",
  "entity_types": ["COURT", "CASE_LAW"],
  "document_ids": ["doc_001", "doc_002"],
  "filters": {
    "confidence_threshold": 0.8,
    "jurisdiction": "federal"
  },
  "max_results": 50,
  "include_relationships": true,
  "include_communities": false,
  "traversal_depth": 2
}
```

**Success Response (200):**
```json
{
  "query_type": "entities",
  "result_count": 15,
  "entities": [
    {
      "entity_id": "ent_001",
      "entity_text": "Supreme Court of the United States", 
      "entity_type": "COURT",
      "confidence": 0.95,
      "document_ids": ["doc_001", "doc_003"],
      "community_id": "comm_001",
      "centrality_scores": {
        "degree": 8,
        "betweenness": 0.23,
        "eigenvector": 0.15
      },
      "relationships": [
        {
          "relationship_id": "rel_001",
          "target_entity_id": "ent_002",
          "relationship_type": "DECIDED_CASE",
          "confidence": 0.89
        }
      ]
    }
  ],
  "relationships": [...],
  "communities": [],
  "analytics": null,
  "query_metadata": {
    "execution_time": 0.12,
    "filters_applied": {
      "entity_types": ["COURT", "CASE_LAW"],
      "document_ids": ["doc_001", "doc_002"]
    },
    "traversal_hops": 2
  }
}
```

### Graph Analytics

#### GET /graph/stats

Get comprehensive graph database statistics and metrics.

**Query Parameters:**
- `include_details` (optional): Include detailed breakdowns
- `date_range` (optional): Filter by date range

**Success Response (200):**
```json
{
  "statistics": {
    "total_entities": 1250,
    "total_relationships": 875,
    "total_communities": 45,
    "total_documents": 150,
    "total_embeddings": 3400
  },
  "entity_breakdown": {
    "COURT": 85,
    "CASE_LAW": 245,
    "STATUTE": 120,
    "PARTY": 180,
    "LEGAL_CONCEPT": 320,
    "CITATION": 300
  },
  "relationship_breakdown": {
    "CITES": 345,
    "DECIDED_CASE": 125,
    "FOLLOWS": 89,
    "OVERRULES": 23,
    "REFERS_TO": 293
  },
  "graph_metrics": {
    "average_degree": 2.8,
    "graph_density": 0.001,
    "connected_components": 12,
    "largest_component_size": 1180,
    "modularity": 0.85,
    "small_world_coefficient": 2.1
  },
  "quality_metrics": {
    "average_entity_confidence": 0.89,
    "average_relationship_confidence": 0.85,
    "community_coherence_avg": 0.82,
    "graph_completeness": 0.91
  },
  "graph_info": {
    "methodology": "Microsoft GraphRAG",
    "entity_deduplication_threshold": 0.85,
    "leiden_resolution": 1.0,
    "min_community_size": 3
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Graph Management

#### DELETE /graph/clear

Clear graph data from the database.

**Query Parameters:**
- `document_id` (optional): Clear data for specific document only
- `confirm` (required): Must be "true" to proceed

**Example Request:**
```bash
curl -X DELETE "http://localhost:8010/api/v1/graph/clear?document_id=doc_001&confirm=true"
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Cleared graph data for document doc_001",
  "entities_removed": 45,
  "relationships_removed": 32,
  "communities_affected": 3,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Health & Monitoring

### Health Check Endpoints

#### GET /health

Basic health check endpoint with service status information.

**Request:**
```bash
curl http://localhost:8010/api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "graphrag-service",
  "version": "1.0.0",
  "uptime_seconds": 3600.45
}
```

**Response (503 Service Unavailable) - If unhealthy:**
```json
{
  "status": "unhealthy",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "graphrag-service",
  "version": "1.0.0",
  "errors": ["database_connection_failed", "graph_algorithm_unavailable"]
}
```

#### GET /health/ping

Simple ping check for load balancers with minimal response data.

**Success Response (200):**
```json
{
  "ping": "pong",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### GET /health/ready

Readiness check with dependency verification to ensure the service can process requests.

**Request:**
```bash
curl http://localhost:8010/api/v1/health/ready
```

**Response (200 OK) - Ready to process requests:**
```json
{
  "status": "ready",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "graphrag-service",
  "version": "1.0.0",
  "ready": true,
  "checks": {
    "database": "healthy",
    "graph_algorithms": "healthy",
    "entity_extraction_service": "healthy",
    "prompt_service": "healthy"
  }
}
```

**Response (503 Service Unavailable) - Not ready:**
```json
{
  "status": "not_ready",
  "timestamp": "2025-07-29T10:30:00Z",
  "service": "graphrag-service",
  "version": "1.0.0",
  "ready": false,
  "checks": {
    "database": "healthy",
    "graph_algorithms": "healthy",
    "entity_extraction_service": "unhealthy",
    "prompt_service": "healthy"
  },
  "blocking_issues": ["entity_extraction_service_unavailable"]
}
```

#### GET /health/detailed

Comprehensive health status and performance metrics (renamed from `/health/metrics` for standardization).

**Success Response (200):**
```json
{
  "status": "healthy",
  "service": "graphrag-service",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 25,
      "connection_pool": "8/20 active"
    },
    "graph_algorithms": {
      "status": "healthy", 
      "leiden_algorithm": "available",
      "embedding_similarity": "available"
    },
    "ai_services": {
      "status": "healthy",
      "community_summarization": "available"
    }
  },
  "performance": {
    "graphs_created": 45,
    "entities_processed": 12500,
    "relationships_discovered": 8900,
    "communities_detected": 340,
    "average_processing_time_seconds": 3.2,
    "cache_hit_rate": 0.78
  },
  "storage": {
    "nodes_created": 12500,
    "edges_created": 8900,
    "communities_detected": 340,
    "chunks_with_embeddings": 34000,
    "database_size_mb": 450.5
  }
}
```

---

## Error Responses

### Validation Error (400)

```json
{
  "error": "ValidationError",
  "message": "Invalid entity type: UNKNOWN_TYPE",
  "details": {
    "field": "entities[0].entity_type",
    "provided_value": "UNKNOWN_TYPE",
    "valid_values": ["COURT", "CASE_LAW", "STATUTE", "PARTY", "LEGAL_CONCEPT", "CITATION"]
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Processing Error (422)

```json
{
  "error": "ProcessingError",
  "message": "Graph construction failed: insufficient entities for community detection",
  "details": {
    "document_id": "doc_001",
    "entities_provided": 2,
    "minimum_required": 3,
    "suggestion": "Provide more entities or disable community detection"
  },
  "processing_time_seconds": 1.2
}
```

### System Error (500)

```json
{
  "error": "Internal server error", 
  "error_id": "error_1705312200",
  "message": "Database connection failed",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## GraphRAG Methodology

### Entity Deduplication Process

1. **Similarity Calculation**: Semantic similarity using embedding vectors
2. **Threshold Filtering**: 0.85 similarity threshold with legal type awareness
3. **Merge Strategy**: Confidence-weighted merging of duplicate entities
4. **Relationship Preservation**: Maintain all relationships during merging

### Community Detection

- **Algorithm**: Leiden algorithm for optimal modularity
- **Resolution**: Configurable resolution parameter (default: 1.0)
- **Minimum Size**: Communities must have ≥3 entities
- **Hierarchical**: Supports multi-level community structure

### Legal Specializations

- **Entity Hierarchies**: PARTY → INDIVIDUAL/CORPORATION
- **Citation Relationships**: CITES, OVERRULES, FOLLOWS, DISTINGUISHES
- **Court Hierarchies**: Supreme Court → Circuit Court → District Court
- **Temporal Reasoning**: Chronological precedent relationships

### Quality Assessment

- **Graph Completeness**: Ratio of discovered vs expected relationships
- **Community Coherence**: Intra-community connection density
- **Entity Confidence**: Average confidence scores
- **Coverage Score**: Percentage of document content represented in graph

---

## Performance Characteristics

### Processing Speed
- **Small Documents** (10-50 entities): ~2-5 seconds
- **Medium Documents** (50-200 entities): ~5-15 seconds
- **Large Documents** (200+ entities): ~15-45 seconds
- **Community Detection**: Additional 1-3 seconds per 100 entities

### Memory Usage
- **Base Service**: 256MB - 512MB
- **Graph Construction**: +50MB per 1000 entities
- **Community Detection**: +100MB during algorithm execution
- **Embedding Storage**: 4KB per embedding vector

### Scalability
- **Maximum Entities**: 10,000 per document
- **Maximum Relationships**: 50,000 per document
- **Graph Database**: Horizontally scalable Supabase backend
- **Concurrent Processing**: 5 parallel graph construction operations

---

## Client Examples

### Python Client

```python
import httpx
import asyncio
import json

async def create_knowledge_graph(document_data):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8010/api/v1/graph/create",
            json=document_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Graph created: {result['graph_id']}")
            print(f"Entities processed: {result['processing_results']['entities_processed']}")
            print(f"Communities detected: {result['processing_results']['communities_detected']}")
            return result
        else:
            print(f"Graph creation failed: {response.text}")
            return None

# Usage with sample data
document_data = {
    "document_id": "case_001",
    "markdown_content": "Supreme Court decision...",
    "entities": [
        {
            "entity_id": "court_1",
            "entity_text": "Supreme Court",
            "entity_type": "COURT",
            "confidence": 0.95
        }
    ],
    "citations": [],
    "relationships": [],
    "enhanced_chunks": [],
    "graph_options": {
        "enable_deduplication": True,
        "enable_community_detection": True
    }
}

result = asyncio.run(create_knowledge_graph(document_data))
```

### JavaScript/Node.js Client

```javascript
async function createKnowledgeGraph(documentData) {
    const response = await fetch('http://localhost:8010/api/v1/graph/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(documentData)
    });
    
    const result = await response.json();
    
    if (response.ok) {
        console.log(`Graph created: ${result.graph_id}`);
        console.log(`Quality score: ${result.quality_metrics.graph_completeness}`);
        return result;
    } else {
        console.error(`Graph creation failed: ${result.message}`);
        return null;
    }
}
```

### Query Graph Example

```python
async def query_entities(entity_types, confidence_threshold=0.8):
    query = {
        "query_type": "entities",
        "entity_types": entity_types,
        "filters": {
            "confidence_threshold": confidence_threshold
        },
        "include_relationships": True,
        "max_results": 100
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8010/api/v1/graph/query",
            json=query
        )
        
        return response.json() if response.status_code == 200 else None

# Find all courts and case law with high confidence
results = await query_entities(["COURT", "CASE_LAW"], 0.9)
```

---

## Database Operations - UPSERT Support (v2.2.0)

### Overview

The GraphRAG service uses **UPSERT semantics** for idempotent batch processing of graph data. This allows safe re-processing of documents without duplicate key errors, enabling resilient pipeline operations.

### UPSERT Implementation

All graph data insertions use UPSERT operations with conflict resolution to ensure idempotency:

#### Database Tables Using UPSERT

| Table | Conflict Column | Purpose | Location |
|-------|----------------|---------|----------|
| `graph.nodes` | `node_id` | Entity deduplication | graph_constructor.py:468-473 |
| `graph.edges` | `edge_id` | Relationship deduplication | graph_constructor.py:549-554 |
| `graph.communities` | `community_id` | Community deduplication | graph_constructor.py:130-135 |

#### SupabaseClient.upsert() Method

**Method Signature:**
```python
async def upsert(
    self,
    table: str,
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    on_conflict: Optional[str] = None,
    admin_operation: bool = False
) -> List[Dict[str, Any]]
```

**Parameters:**
- `table` (str): Table name in dot notation (e.g., `"graph.nodes"`)
- `data` (Union[Dict, List[Dict]]): Single record or batch of records to upsert
- `on_conflict` (Optional[str]): Column name for conflict resolution (e.g., `"node_id"`)
- `admin_operation` (bool): Use service_role client to bypass RLS (default: False)

**Returns:**
- List[Dict]: Upserted records from database

**Conflict Resolution Behavior:**

When `on_conflict` is specified:
- **Existing records** with matching column values are **UPDATED**
- **New records** are **INSERTED**
- **No duplicate key errors** occur

**Example Usage:**

```python
from shared.clients.supabase_client import create_admin_supabase_client

# Initialize admin client for service operations
admin_client = create_admin_supabase_client("graphrag-service")

# Single record upsert
node_record = {
    "node_id": "entity_abc123",
    "node_type": "entity",
    "title": "Supreme Court of the United States",
    "description": "Judicial body",
    "metadata": {
        "entity_type": "COURT",
        "confidence": 0.95,
        "document_id": "doc_001"
    }
}

result = await admin_client.upsert(
    "graph.nodes",
    node_record,
    on_conflict="node_id",
    admin_operation=True
)

# Batch upsert (idempotent batch processing)
node_batch = [
    {
        "node_id": "entity_abc123",
        "node_type": "entity",
        "title": "Supreme Court of the United States",
        # ... more fields
    },
    {
        "node_id": "entity_def456",
        "node_type": "entity",
        "title": "Bruen v. New York",
        # ... more fields
    }
]

result = await admin_client.upsert(
    "graph.nodes",
    node_batch,
    on_conflict="node_id",
    admin_operation=True
)

# Result validation
assert len(result) == len(node_batch), "All records upserted successfully"
```

### Batch Processing Idempotency

With UPSERT support, graph construction batch processing is now **fully idempotent**:

- ✅ **Safe to re-run** the same documents through the pipeline
- ✅ **Deterministic entity IDs** ensure consistent conflict resolution
- ✅ **No duplicate key constraint violations** on re-processing
- ✅ **Automatic updates** when document content changes
- ✅ **Parallel pipeline resilience** - multiple workers can process safely

**Before UPSERT (v2.1.0 and earlier):**
```
1st run: ✅ Insert 45 nodes successful
2nd run: ❌ ERROR: duplicate key value violates unique constraint "nodes_pkey"
         Detail: Key (node_id)=(entity_abc123) already exists.
```

**After UPSERT (v2.2.0+):**
```
1st run: ✅ Insert 45 nodes successful
2nd run: ✅ Update 45 nodes successful (idempotent)
3rd run: ✅ Update 45 nodes successful (idempotent)
```

### Graph Constructor UPSERT Integration

The `GraphConstructor` class uses UPSERT for all batch operations:

**Node Insertion (graph_constructor.py:468-473):**
```python
# Batch upsert nodes with validation (idempotent for re-runs)
await self._log_step("upserting_nodes", {"count": len(node_records)})
result = await self.supabase_client.upsert(
    "graph.nodes",
    node_records,
    on_conflict="node_id",
    admin_operation=True
)

# CRITICAL FIX: Validate result and fail fast if insert failed
if result is None:
    raise Exception(f"Failed to insert {len(node_records)} nodes: Supabase returned None")
elif len(result) == 0:
    raise Exception(f"Failed to insert {len(node_records)} nodes: Supabase returned empty result")
elif len(result) != len(node_records):
    raise Exception(f"Partial insert failure: Expected {len(node_records)} nodes, got {len(result)}")
```

**Edge Insertion (graph_constructor.py:549-554):**
```python
# Batch upsert edges with validation (idempotent for re-runs)
await self._log_step("upserting_edges", {"count": len(edge_records)})
result = await self.supabase_client.upsert(
    "graph.edges",
    edge_records,
    on_conflict="edge_id",
    admin_operation=True
)
```

**Community Insertion (graph_constructor.py:130-135):**
```python
# Batch upsert communities with validation (idempotent for re-runs)
await self._log_step("upserting_communities", {"count": len(community_records)})
result = await self.supabase_client.upsert(
    "graph.communities",
    community_records,
    on_conflict="community_id",
    admin_operation=True
)
```

### Migration Notes (v2.2.0)

**Package Upgrade:**
- **Before**: `supabase-py==2.18.1`
- **After**: `supabase-py>=2.22.0`
- **Reason**: Full `on_conflict` parameter support added in 2.22.0

**Breaking Changes:** None
- Existing `insert()` operations continue to work
- UPSERT is opt-in via explicit `on_conflict` parameter
- No schema changes required

**New Features:**
- ✅ Idempotent batch processing with UPSERT
- ✅ `on_conflict` parameter for conflict resolution
- ✅ Automatic update-or-insert semantics
- ✅ Fail-fast validation for batch operations
- ✅ Enhanced error messages for debugging

**Developer Impact:**

1. **Re-processing Documents**: Safe to re-run document processing without errors
2. **Pipeline Resilience**: Failed pipeline runs can be retried without cleanup
3. **Parallel Workers**: Multiple workers can process the same documents safely
4. **Testing**: Easier to write idempotent integration tests

**Example Migration:**

```python
# Before (v2.1.0 - INSERT only)
try:
    result = await client.insert("graph.nodes", node_records, admin_operation=True)
except Exception as e:
    if "duplicate key" in str(e):
        # Manual cleanup required
        await cleanup_existing_nodes(node_records)
        result = await client.insert("graph.nodes", node_records, admin_operation=True)

# After (v2.2.0 - UPSERT)
result = await client.upsert(
    "graph.nodes",
    node_records,
    on_conflict="node_id",
    admin_operation=True
)
# No error handling needed - idempotent!
```

### Best Practices

1. **Always specify `on_conflict`** for batch operations to enable idempotency
2. **Use deterministic IDs** (hash-based) to ensure consistent conflict resolution
3. **Validate batch results** to detect partial failures early
4. **Log UPSERT operations** with clear metrics (inserted vs updated counts)
5. **Test idempotency** by running the same operation multiple times

### Troubleshooting

**Issue**: UPSERT returns empty result
```python
result = await client.upsert("graph.nodes", data, on_conflict="node_id")
# result = []  ❌
```

**Possible Causes:**
- Table does not exist or is not exposed via REST API
- RLS policies blocking access (use `admin_operation=True`)
- Invalid data format or schema mismatch
- Network connectivity issues

**Solution:**
```python
# 1. Verify table exists
tables = await client.get("information_schema.tables",
    filters={"table_name": "nodes", "table_schema": "graph"})

# 2. Use admin client to bypass RLS
result = await client.upsert(
    "graph.nodes",
    data,
    on_conflict="node_id",
    admin_operation=True  # ✅ Bypass RLS
)

# 3. Validate result
if not result or len(result) == 0:
    raise Exception("UPSERT failed - check logs for details")
```

---

## Additional GraphRAG Endpoints

### Build GraphRAG

#### POST /api/v1/graphrag/build

Build GraphRAG for specified documents with chosen processing mode.

**Request Body:**
```json
{
  "document_ids": ["doc_001", "doc_002"],
  "client_id": "client_123",
  "mode": "HYBRID_MODE"
}
```

**Success Response (200):**
```json
{
  "build_id": "build_client_123_20250115_103000",
  "status": "started",
  "mode": "HYBRID_MODE",
  "documents": 2,
  "estimated_time_minutes": 4
}
```

### Query GraphRAG

#### POST /api/v1/graphrag/query

Execute GraphRAG query with specified search type and mode.

**Request Body:**
```json
{
  "query": "Find all Supreme Court cases related to Miranda rights",
  "client_id": "client_123",
  "search_type": "HYBRID_SEARCH",
  "mode": "LAZY_GRAPHRAG",
  "relevance_budget": 500,
  "community_level": 2,
  "vector_weight": 0.7
}
```

**Success Response (200):**
```json
{
  "query": "Find all Supreme Court cases related to Miranda rights",
  "search_type": "HYBRID_SEARCH",
  "mode": "LAZY_GRAPHRAG",
  "response": "Found 5 Supreme Court cases related to Miranda rights...",
  "results": [
    {
      "entity_id": "ent_001",
      "entity_text": "Miranda v. Arizona",
      "entity_type": "CASE_CITATION",
      "relevance_score": 0.95,
      "context": "The landmark case establishing Miranda rights..."
    }
  ],
  "metadata": {
    "contextual_results_count": 12,
    "graph_results_count": 8,
    "processing_time_seconds": 2.3
  }
}
```

### Get Build Status

#### GET /api/v1/graphrag/status/{build_id}

Get the status of a GraphRAG build operation.

**Path Parameters:**
- `build_id` (required): The build identifier

**Query Parameters:**
- `client_id` (required): Client identifier

**Success Response (200):**
```json
{
  "build_id": "build_client_123_20250115_103000",
  "client_id": "client_123",
  "mode": "HYBRID_MODE",
  "document_ids": ["doc_001", "doc_002"],
  "status": "completed",
  "start_time": "2025-01-15T10:30:00Z",
  "end_time": "2025-01-15T10:34:00Z",
  "processing_results": {
    "documents_processed": 2,
    "entities_extracted": 234,
    "relationships_discovered": 156,
    "communities_detected": 12
  }
}
```

### Graph Visualization Data

#### GET /api/v1/graphrag/graph/visualization/{client_id}

Get graph data formatted for visualization.

**Path Parameters:**
- `client_id` (required): Client identifier

**Query Parameters:**
- `max_nodes` (optional): Maximum number of nodes to return (default: 100)
- `node_types` (optional): Array of node types to filter

**Example Request:**
```bash
curl "http://localhost:8010/api/v1/graphrag/graph/visualization/client_123?max_nodes=50&node_types=entity&node_types=citation"
```

**Success Response (200):**
```json
{
  "nodes": [
    {
      "node_id": "node_entity_001",
      "label": "Supreme Court",
      "node_type": "entity",
      "importance_score": 0.95,
      "x_position": 100.5,
      "y_position": 200.3,
      "color": "#FF6B6B",
      "size": 15
    }
  ],
  "edges": [
    {
      "edge_id": "edge_rel_001",
      "source_node_id": "node_entity_001",
      "target_node_id": "node_entity_002",
      "edge_type": "DECIDED_CASE",
      "weight": 0.89
    }
  ],
  "metadata": {
    "total_nodes": 50,
    "total_edges": 45,
    "node_types": ["entity", "citation"]
  }
}
```

### Get Extracted Entities

#### GET /api/v1/graphrag/entities/{client_id}

Get extracted legal entities with filtering options.

**Path Parameters:**
- `client_id` (required): Client identifier

**Query Parameters:**
- `entity_type` (optional): Filter by entity type
- `min_confidence` (optional): Minimum confidence threshold (default: 0.7)
- `limit` (optional): Maximum results to return (default: 100)

**Example Request:**
```bash
curl "http://localhost:8010/api/v1/graphrag/entities/client_123?entity_type=COURT&min_confidence=0.8&limit=50"
```

**Success Response (200):**
```json
{
  "entities": [
    {
      "entity_id": "ent_001",
      "entity_text": "Supreme Court of the United States",
      "entity_type": "COURT",
      "confidence_score": 0.95,
      "document_ids": ["doc_001", "doc_003"],
      "extraction_method": "ai_enhanced",
      "metadata": {
        "jurisdiction": "federal",
        "level": "supreme"
      }
    }
  ],
  "count": 15,
  "filters_applied": {
    "entity_type": "COURT",
    "min_confidence": 0.8
  }
}
```

---

## Integration with Other Services

### Document Processing Pipeline

1. **Entity Extraction Service** (Port 8007) → Extract entities and relationships
2. **Chunking Service** (Port 8009) → Generate enhanced chunks with embeddings
3. **GraphRAG Service** (Port 8010) → Construct knowledge graph
4. **Storage** → Persist in Supabase graph schema tables

### Database Schema Integration

The service uses comprehensive graph schema tables with multi-tenant isolation:

#### Core Graph Tables

##### graph.chunks

**Columns**:
- `chunk_id` (text, PK)
- `document_id` (text, FK → document_registry)
- **`client_id` (uuid, FK → client.cases)** ← Multi-tenant isolation
- **`case_id` (uuid, FK → client.cases)** ← Multi-tenant isolation
- `content` (text)
- `chunk_index` (integer)
- `token_count` (integer)
- `content_embedding` (vector(2048))
- `metadata` (jsonb)
- `created_at` (timestamp)

**Foreign Keys**:
- `document_id` → `graph.document_registry.document_id`
- `case_id` → `client.cases.case_id` (ON DELETE SET NULL)

**Indexes**:
- PRIMARY KEY: chunk_id
- INDEX: case_id (partial, WHERE case_id IS NOT NULL)
- INDEX: client_id (partial, WHERE client_id IS NOT NULL)
- INDEX: (case_id, client_id) (compound)
- INDEX: (case_id, document_id) (compound)

##### graph.text_units

**Columns**:
- `text_unit_id` (text, PK)
- `chunk_id` (text, FK → chunks)
- **`client_id` (uuid, FK → client.cases)** ← Multi-tenant isolation
- **`case_id` (uuid, FK → client.cases)** ← Multi-tenant isolation
- `content` (text)
- `token_count` (integer)
- `metadata` (jsonb)
- `created_at` (timestamp)

**Foreign Keys**:
- `chunk_id` → `graph.chunks.chunk_id`
- `case_id` → `client.cases.case_id` (ON DELETE SET NULL)

**Indexes**:
- PRIMARY KEY: text_unit_id
- INDEX: case_id (partial, WHERE case_id IS NOT NULL)
- INDEX: client_id (partial, WHERE client_id IS NOT NULL)
- INDEX: (case_id, client_id) (compound)
- INDEX: (case_id, chunk_id) (compound)

##### graph.enhanced_contextual_chunks

**Columns**:
- `chunk_id` (text, PK)
- `document_id` (text, FK → document_registry)
- **`client_id` (uuid, FK → client.cases)** ← Multi-tenant isolation
- **`case_id` (uuid, FK → client.cases)** ← Multi-tenant isolation
- `original_content` (text)
- `enriched_content` (text)
- `vector` (vector(2048))
- `metadata` (jsonb)
- `created_at` (timestamp)

**Foreign Keys**:
- `document_id` → `graph.document_registry.document_id`
- `case_id` → `client.cases.case_id` (ON DELETE SET NULL)

**Indexes**:
- PRIMARY KEY: chunk_id
- INDEX: case_id (partial, WHERE case_id IS NOT NULL)
- INDEX: client_id (partial, WHERE client_id IS NOT NULL)
- INDEX: (case_id, client_id) (compound)
- INDEX: (case_id, document_id) (compound)

#### Other Core Tables
- `graph.nodes`: **Canonical deduplicated entities** - Single source of truth for all entities across documents
- `graph.edges`: Cross-document relationships with deduplication
- `graph.communities`: Leiden algorithm community detection results
- `graph.node_communities`: **Many-to-many junction table** - Links nodes to communities with membership strength scores (0.0-1.0)
- `graph.document_registry`: Central document catalog across all schemas
- `graph.reports`: AI-generated summaries (optional, expensive in FULL_GRAPHRAG mode)

#### Domain Storage Tables
- `law.documents`: Legal reference documents (statutes, case law, regulations)
- `law.entities`: Raw entity extraction from legal documents (pre-deduplication audit trail)
- `law.entity_relationships`: Document-scoped relationships before graph deduplication
- `client.documents`: Client-specific case documents
- `client.entities`: Raw entity extraction from client documents

**Key Design Philosophy:**
- **law.entities / client.entities**: Raw extraction results (document-scoped, pre-deduplication)
- **graph.nodes**: Deduplicated canonical entities (cross-document, post-deduplication)
- Embeddings stored in source tables (distributed strategy) for better query performance

#### Advanced Cross-Reference Tables

- `graph.chunk_entity_connections` - Bidirectional links between chunks and entities for enhanced retrieval
- `graph.chunk_cross_references` - Semantic relationships between chunks (citation, follows, contradicts, supports, etc.)

See [Chunk Cross-Reference Tables](#chunk-cross-reference-tables) for detailed usage examples.

### Removed Tables (Schema Consolidation)

The following tables have been removed to eliminate redundancy and improve performance:

#### graph.entities (Removed)
**Reason**: Redundant with `graph.nodes`
- Original intent: Store Microsoft GraphRAG entities
- **Reality**: Code actually uses `graph.nodes` directly
- **Migration**: No data to migrate (table was never used)

#### law.citations (Removed)
**Reason**: Citations are entity types, not separate entities
- Citations now stored in `graph.nodes` with types:
  - CASE_CITATION
  - STATUTE_CITATION
  - REGULATION_CITATION
  - CONSTITUTIONAL_CITATION
  - etc. (9 citation types total)
- **Migration**: Citation data preserved in graph.nodes

#### graph.covariates (Removed)
**Reason**: Unused legacy from Microsoft GraphRAG
- Metadata now stored in JSONB columns on respective tables
- **Migration**: No data to migrate (table was unused)

#### graph.embeddings (Removed)
**Reason**: Centralized storage created performance bottleneck
- **New approach**: Distributed embeddings in source tables
- **Migration**: Embeddings moved to content_embedding/vector fields in source tables

---

## Multi-Tenant Query Patterns

### Tenant Isolation

Always filter by `case_id` for tenant isolation:

```python
# ✅ CORRECT - Tenant-isolated query
chunks = await client.get(
    'graph.chunks',
    filters={'case_id': current_case_id}
)

# ❌ WRONG - Cross-tenant data leak
chunks = await client.get('graph.chunks')  # Returns all tenants!
```

### Performance Best Practices

1. **Always include case_id** in WHERE clauses to use indexes
2. **Use compound indexes** for multi-column filters
3. **Limit results** for large tables (chunks, enhanced_chunks)
4. **Filter early** - apply case_id filter before other conditions

**Example**:
```python
# Efficient query using indexes
chunks = await client.get(
    'graph.chunks',
    filters={
        'case_id': case_id,  # Uses index
        'document_id': doc_id  # Uses compound index
    },
    order_by='chunk_index',
    limit=100
)
```

### Multi-Tenant Query Examples

**Example 1: Get all chunks for a case**:
```python
from shared.clients.supabase_client import create_supabase_client

client = create_supabase_client("graphrag-service")

chunks = await client.get(
    "graph.chunks",
    filters={"case_id": "550e8400-e29b-41d4-a716-446655440000"},
    limit=1000
)
```

**Example 2: Get chunks for specific document in a case**:
```python
chunks = await client.get(
    "graph.chunks",
    filters={
        "case_id": "550e8400-e29b-41d4-a716-446655440000",
        "document_id": "doc_123"
    },
    order_by="chunk_index"
)
```

**Example 3: Get all communities for a client**:
```python
communities = await client.get(
    "graph.communities",
    filters={"client_id": "660e8400-e29b-41d4-a716-446655440001"}
)
```

**Example 4: Cross-document entity search within a case**:
```python
# Find all nodes (entities) across all documents in a case
nodes = await client.get(
    "graph.nodes",
    filters={
        "case_id": "550e8400-e29b-41d4-a716-446655440000",
        "node_type": "entity"
    },
    limit=500
)
```

### SQL Query Patterns

**Tenant-Isolated Chunk Retrieval**:
```sql
-- Uses idx_chunks_case_id index
SELECT chunk_id, content, token_count
FROM graph.chunks
WHERE case_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY chunk_index
LIMIT 100;
```

**Compound Index Optimization**:
```sql
-- Uses idx_chunks_case_document compound index
SELECT chunk_id, content
FROM graph.chunks
WHERE case_id = '550e8400-e29b-41d4-a716-446655440000'
  AND document_id = 'doc_123'
ORDER BY chunk_index;
```

**Client-Wide Query**:
```sql
-- Uses idx_communities_client_id index
SELECT community_id, title, summary
FROM graph.communities
WHERE client_id = '660e8400-e29b-41d4-a716-446655440001';
```

---

## Vector/Embedding Strategy

The GraphRAG service implements a sophisticated multi-layer embedding architecture using **Jina Embeddings v4** (2048 dimensions) running on dedicated GPU hardware for optimal performance.

### Architecture Overview

```
Document → Chunking Service → vLLM Embeddings (GPU 1) → PostgreSQL pgvector
                              Jina v4 (2048-dim)          Distributed Storage:
                                                          - graph.chunks.content_embedding
                                                          - graph.enhanced_contextual_chunks.vector
                                                          - graph.nodes.embedding
                                                          - graph.communities.summary_embedding
```

### Why Distributed Embedding Storage?

The GraphRAG service uses a **distributed embedding strategy** where vectors are stored directly in the tables they represent, rather than in a centralized `graph.embeddings` table.

**Benefits:**
- **No JOINs required**: Querying `graph.chunks` includes embeddings automatically
- **Better index optimization**: Each table can have vector indexes tuned for its row count
- **Localized queries**: Searching chunks doesn't scan node embeddings
- **Simpler query patterns**: One table = one query

**Storage locations:**
```sql
-- Chunk embeddings stored in chunk table
SELECT chunk_id, content, content_embedding
FROM graph.chunks
WHERE (content_embedding <=> :query_vector) < 0.3;

-- Enhanced chunk embeddings in enhanced chunk table
SELECT chunk_id, enriched_content, vector
FROM graph.enhanced_contextual_chunks
WHERE (vector <=> :query_vector) < 0.3;

-- Entity embeddings in nodes table
SELECT node_id, label, embedding
FROM graph.nodes
WHERE node_type = 'entity'
  AND (embedding <=> :query_vector) < 0.3;

-- Community embeddings in communities table
SELECT community_id, summary, summary_embedding
FROM graph.communities
WHERE (summary_embedding <=> :query_vector) < 0.3;
```

### Three Embedding Types

The system generates **three distinct embedding types** for different retrieval purposes:

#### 1. Contextual Chunk Embeddings (Primary)

**Purpose**: Semantic search for document retrieval using Anthropic-style contextual enhancement

**Storage**:
```json
{
  "chunk_id": "chunk_doc123_001",
  "enriched_content": "Document: Rahimi v. US (2024)...",
  "vector": [2048 dimensions],
  "model_name": "jinaai/jina-embeddings-v4-base-en"
}
```
Stored directly in `graph.enhanced_contextual_chunks.vector` field.

**Process**:
1. Original chunk: `"The court in Rahimi v. United States held..."`
2. Contextual enhancement: `"Document: Rahimi v. US (2024), Topic: Second Amendment, Section: Constitutional Analysis, Context: This chunk discusses the court's holding regarding..."`
3. Embedding generated from enhanced text (2048-dim vector)
4. Stored directly in chunk table's vector field

**Use Case**: High-precision semantic search with improved context awareness (15-20% better retrieval vs. plain text)

#### 2. Entity Embeddings

**Purpose**: Entity deduplication and entity-centric search

**Storage**:
```json
{
  "node_id": "entity_case_bruen_001",
  "label": "New York State Rifle & Pistol Association, Inc. v. Bruen",
  "node_type": "entity",
  "embedding": [2048 dimensions],
  "metadata": {"entity_type": "CASE_CITATION"}
}
```
Stored directly in `graph.nodes.embedding` field.

**Process**:
1. Entity text: `"New York State Rifle & Pistol Association, Inc. v. Bruen"`
2. Entity context: `"Case citation from Supreme Court decision (2022), legal doctrine: Second Amendment"`
3. Combined embedding from text + context
4. Used for similarity matching (0.85 threshold)

**Use Case**: Deduplicating entities across documents, finding similar legal concepts

#### 3. Community Summary Embeddings

**Purpose**: Global search across knowledge graph communities

**Storage**:
```json
{
  "community_id": "community_2A_doctrine_001",
  "summary": "This community contains Second Amendment cases...",
  "summary_embedding": [2048 dimensions],
  "model_name": "jinaai/jina-embeddings-v4-base-en"
}
```
Stored directly in `graph.communities.summary_embedding` field.

**Process**:
1. AI-generated community summary: `"This community contains Second Amendment cases focusing on the right to bear arms, including landmark decisions like Heller, McDonald, Bruen, and Rahimi. Common themes include individual gun rights, historical tradition test, and sensitive places restrictions."`
2. Summary embedded using Jina v4
3. Used for high-level topic matching

**Use Case**: Finding relevant communities for broad legal queries, topic clustering

### Search Types

#### Semantic Search (Pure Vector)

Uses cosine similarity with pgvector for high-precision retrieval:

```sql
SELECT
    chunk_id,
    enriched_content,
    1 - (vector <=> query_embedding) as similarity
FROM graph.enhanced_contextual_chunks
WHERE (vector <=> query_embedding) < 0.3  -- Distance threshold
ORDER BY vector <=> query_embedding
LIMIT 10;
```

**Example Query**: `"Second Amendment disarmament cases"`

**Results**:
- Rahimi v. United States (similarity: 0.92)
- Bruen v. New York (similarity: 0.88)
- Heller v. DC (similarity: 0.85)

**Parameters**:
- `similarity_threshold`: Default 0.7 (adjust based on precision/recall needs)
- `limit`: Maximum results (default 10)
- `client_id`: Multi-tenant filtering

#### Hybrid Search (Vector + BM25)

Combines semantic understanding with keyword matching using Reciprocal Rank Fusion (RRF):

```python
# Step 1: Vector search (semantic understanding)
vector_results = semantic_search(query_embedding)  # Scores: [0.92, 0.88, 0.85]

# Step 2: BM25 search (keyword matching)
keyword_results = bm25_search(query_text, bm25_content)  # Scores: [15.2, 12.8, 10.5]

# Step 3: Reciprocal Rank Fusion
rrf_score = 1/(k + rank_vector) + 1/(k + rank_keyword)  # k=60 (default)

# Step 4: Weighted combination
final_score = (alpha * vector_score) + ((1-alpha) * normalized_bm25)
```

**Example Query**: `"Rahimi domestic violence restraining order"`

**Hybrid Results** (alpha=0.5):
- Rahimi v. US (RRF: 0.0328, final: 0.935) - #1 in both semantic and keyword
- Bruen v. NY (RRF: 0.0313, final: 0.887) - #2 semantic, #5 keyword
- Heller v. DC (RRF: 0.0298, final: 0.862) - #3 semantic, #8 keyword

**Parameters**:
- `alpha`: Weight between semantic (1.0) and keyword (0.0) search, default 0.5
- `k`: RRF constant (default 60)
- `match_count`: Results to return

**Benefits**:
- Better handling of exact phrase matches (e.g., legal terms, case names)
- Improved recall for domain-specific terminology
- Resilient to out-of-vocabulary terms

#### Local Community Search

Searches within specific knowledge graph communities for focused retrieval:

```python
# Step 1: Identify relevant community
community_id = "community_2A_doctrine_001"

# Step 2: Get community members (entities/chunks)
members = graph.node_communities.filter(community_id=community_id)

# Step 3: Scoped semantic search
results = vector_search(
    query_embedding,
    filters={"node_id": IN members}
)
```

**Example**: Finding Second Amendment precedents only within the "2A Doctrine" community

**Benefits**:
- Faster search (smaller search space)
- More relevant results (thematically focused)
- Better for specialized legal research

#### Global Knowledge Search

Searches across all communities using community summaries + entity matching:

```python
# Step 1: Match query to relevant communities (via community embeddings)
relevant_communities = community_search(query_embedding)

# Step 2: Aggregate results from top communities
results = []
for community in relevant_communities[:5]:
    community_results = local_search(query, community.id)
    results.extend(community_results)

# Step 3: Re-rank and deduplicate
final_results = rerank(results, query_embedding)
```

**Example Query**: `"Constitutional challenges to firearms regulations"`

**Global Search Process**:
1. Matches to communities: "2A Doctrine" (0.94), "Constitutional Law" (0.89), "Due Process" (0.82)
2. Searches within top 3 communities
3. Aggregates and re-ranks results
4. Returns comprehensive cross-community results

**Benefits**:
- Comprehensive coverage across knowledge graph
- Discovers connections between related topics
- Scales to large document collections (10,000+ documents)

### Vector Search Performance

**Hardware Configuration**:
- **GPU 0**: vLLM LLM Service (IBM Granite 3.3 2B, port 8080)
- **GPU 1**: vLLM Embeddings Service (Jina v4, port 8081) - **DEDICATED**

**Important**: Never run both services on the same GPU to avoid memory conflicts

**Embedding Generation Speed**:
- Single chunk: ~15-25ms
- Batch (10 chunks): ~80-120ms
- Batch (100 chunks): ~600-900ms

**Search Performance**:
- Semantic search (1,000 chunks): ~5-15ms
- Hybrid search (1,000 chunks): ~20-40ms
- Local search (community of 50 nodes): ~3-8ms
- Global search (5 communities): ~30-60ms

**Scaling**:
- **10,000 chunks**: Search latency ~20-50ms (with proper indexing)
- **100,000 chunks**: Search latency ~50-150ms (requires index optimization)
- **1,000,000 chunks**: Requires partitioning strategy (by client_id, case_id)

### pgvector Integration

The service uses PostgreSQL's `pgvector` extension for efficient similarity search:

**Index Type**: `vector_cosine_ops` (optimized for cosine similarity)

```sql
-- Create HNSW indexes for fast approximate nearest neighbor search
CREATE INDEX ON graph.enhanced_contextual_chunks
USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX ON graph.chunks
USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX ON graph.nodes
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX ON graph.communities
USING hnsw (summary_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Index Parameters**:
- `m`: Maximum connections per layer (16 = balanced speed/recall)
- `ef_construction`: Size of dynamic candidate list (64 = good quality)

**Query Operators**:
- `<=>`: Cosine distance (used for similarity: `1 - (vec1 <=> vec2)`)
- `<->`: L2 distance (Euclidean)
- `<#>`: Inner product

**Multi-Tenant Isolation**:
```sql
-- All queries filtered by client_id for data isolation
SELECT chunk_id, enriched_content, vector
FROM graph.enhanced_contextual_chunks
WHERE metadata->>'client_id' = :client_id
  AND (vector <=> :query_embedding) < 0.3;
```

### Caching Strategy

**Vector Cache**:
- Frequently queried vectors cached in memory
- LRU eviction policy (max 1,000 vectors per table)
- Reduces database round-trips by ~40-60%

**Query Result Cache**:
- Search results cached for 15 minutes
- Cache key: `client_id:search_type:query_text:filters`
- Improves response time from ~50ms → ~2ms for cached queries

**Cache Hit Rates** (typical):
- Query cache: 30-50% (depends on query diversity)
- Vector cache: 60-75% (common entities reused)

### Best Practices

1. **Use Contextual Embeddings**: Always prefer enhanced chunks over raw text for 15-20% better retrieval
2. **Tune Alpha Parameter**: Start with 0.5 for hybrid search, adjust based on your use case:
   - Legal research (precise terms): alpha=0.3 (favor keywords)
   - Concept discovery: alpha=0.7 (favor semantic)
3. **Leverage Communities**: Use local search when topic is known for 3-5x faster queries
4. **Batch Embeddings**: Generate embeddings in batches of 10-50 for optimal throughput
5. **Monitor GPU Memory**: Keep GPU 1 dedicated to embeddings to prevent OOM errors

---

## Chunk Cross-Reference Tables

The GraphRAG service provides two advanced tables for enhanced document cross-referencing and entity linking.

### graph.chunk_entity_connections

Creates bidirectional links between chunks and entities for entity-centric retrieval and co-occurrence analysis.

**Schema**:
```sql
CREATE TABLE graph.chunk_entity_connections (
    id UUID PRIMARY KEY,
    chunk_id TEXT,              -- References graph.contextual_chunks
    entity_id TEXT,             -- References graph.nodes (entity nodes)
    relevance_score REAL,       -- 0.0-1.0 (how relevant entity is to chunk)
    position_in_chunk INTEGER,  -- Character position of entity mention
    created_at TIMESTAMP,

    UNIQUE(chunk_id, entity_id)
);

-- Optimized indexes
CREATE INDEX idx_chunk_entity_chunk ON graph.chunk_entity_connections(chunk_id);
CREATE INDEX idx_chunk_entity_entity ON graph.chunk_entity_connections(entity_id);
CREATE INDEX idx_chunk_entity_relevance ON graph.chunk_entity_connections(relevance_score)
    WHERE relevance_score >= 0.7;  -- Partial index for high-relevance only
```

**Example Data**:
```json
{
  "chunk_id": "chunk_rahimi_p12_001",
  "entity_id": "entity_case_bruen_001",
  "relevance_score": 0.95,
  "position_in_chunk": 14,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Use Case 1: Entity-Centric Retrieval**

Find all chunks that mention a specific case:

```sql
SELECT
    cc.chunk_id,
    cc.original_content,
    cec.relevance_score,
    cec.position_in_chunk
FROM graph.chunk_entity_connections cec
INNER JOIN graph.contextual_chunks cc ON cc.chunk_id = cec.chunk_id
WHERE cec.entity_id = 'entity_case_bruen_001'
    AND cec.relevance_score >= 0.7
ORDER BY cec.relevance_score DESC
LIMIT 10;
```

**Results**:
- Rahimi opinion, page 12 (relevance: 0.95) - "Bruen emphasized..."
- McDonald opinion, page 8 (relevance: 0.88) - "Following Bruen..."
- Miller brief, page 3 (relevance: 0.82) - "Unlike Bruen..."

**Use Case 2: Co-Occurrence Analysis**

Find entities that commonly appear together:

```sql
SELECT
    e2.entity_text,
    COUNT(*) as co_occurrence_count,
    AVG(cec1.relevance_score + cec2.relevance_score) / 2 as avg_relevance
FROM graph.chunk_entity_connections cec1
INNER JOIN graph.chunk_entity_connections cec2
    ON cec1.chunk_id = cec2.chunk_id
INNER JOIN graph.nodes e2 ON e2.node_id = cec2.entity_id
WHERE cec1.entity_id = 'entity_legal_doctrine_2A'
    AND cec2.entity_id != 'entity_legal_doctrine_2A'
GROUP BY e2.entity_text
ORDER BY co_occurrence_count DESC
LIMIT 10;
```

**Results**:
- "Bruen v. NYC" - 45 co-occurrences (avg relevance: 0.89)
- "Heller v. DC" - 38 co-occurrences (avg relevance: 0.87)
- "Restraining Order" - 22 co-occurrences (avg relevance: 0.76)

**Use Case 3: Chunk Quality Scoring**

Identify information-rich chunks based on entity density:

```sql
SELECT
    chunk_id,
    COUNT(*) as entity_count,
    AVG(relevance_score) as avg_entity_relevance,
    SUM(CASE WHEN relevance_score >= 0.9 THEN 1 ELSE 0 END) as primary_entities
FROM graph.chunk_entity_connections
GROUP BY chunk_id
HAVING COUNT(*) >= 3
ORDER BY avg_entity_relevance DESC;
```

Use this to prioritize high-quality chunks for retrieval.

### graph.chunk_cross_references

Captures semantic relationships between chunks for citation analysis and reasoning chains.

**Schema**:
```sql
CREATE TABLE graph.chunk_cross_references (
    id UUID PRIMARY KEY,
    source_chunk_id TEXT,              -- References graph.contextual_chunks
    target_chunk_id TEXT,              -- References graph.contextual_chunks
    reference_type TEXT,               -- Type of relationship
    confidence_score REAL,             -- 0.0-1.0 confidence
    created_at TIMESTAMP,

    CONSTRAINT no_self_references CHECK (source_chunk_id != target_chunk_id),
    UNIQUE(source_chunk_id, target_chunk_id, reference_type)
);

-- Optimized indexes
CREATE INDEX idx_chunk_xref_source ON graph.chunk_cross_references(source_chunk_id);
CREATE INDEX idx_chunk_xref_target ON graph.chunk_cross_references(target_chunk_id);
CREATE INDEX idx_chunk_xref_type ON graph.chunk_cross_references(reference_type);
CREATE INDEX idx_chunk_xref_bidirectional ON graph.chunk_cross_references(target_chunk_id, source_chunk_id);
```

**Reference Types**:
- `citation` - Chunk A explicitly cites case/statute in Chunk B
- `follows` - Chunk A follows precedent established in Chunk B
- `contradicts` - Chunk A contradicts reasoning in Chunk B
- `supports` - Chunk A supports argument made in Chunk B
- `elaborates` - Chunk A elaborates on concept from Chunk B
- `summarizes` - Chunk A summarizes content of Chunk B
- `questions` - Chunk A questions reasoning in Chunk B
- `references` - Chunk A references Chunk B generally
- `similar_topic` - Chunks share similar topics (vector similarity ≥ 0.85)

**Example Data**:
```json
{
  "source_chunk_id": "chunk_rahimi_p5_002",
  "target_chunk_id": "chunk_bruen_p34_001",
  "reference_type": "citation",
  "confidence_score": 0.98,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Use Case 1: Citation Network Traversal**

Find all cases cited by Rahimi:

```sql
SELECT DISTINCT
    target.document_id,
    target.original_content as cited_text,
    ccr.confidence_score
FROM graph.chunk_cross_references ccr
INNER JOIN graph.contextual_chunks source
    ON source.chunk_id = ccr.source_chunk_id
INNER JOIN graph.contextual_chunks target
    ON target.chunk_id = ccr.target_chunk_id
WHERE source.document_id = 'rahimi_v_us_2024'
    AND ccr.reference_type = 'citation'
    AND ccr.confidence_score >= 0.8
ORDER BY ccr.confidence_score DESC;
```

**Results**:
- Bruen v. NYC (confidence: 0.98)
- Heller v. DC (confidence: 0.97)
- McDonald v. Chicago (confidence: 0.95)

**Use Case 2: Precedent Analysis**

Find later cases that follow Bruen's reasoning:

```sql
SELECT
    source.document_id,
    source.original_content,
    ccr.confidence_score,
    ccr.reference_type
FROM graph.chunk_cross_references ccr
INNER JOIN graph.contextual_chunks source
    ON source.chunk_id = ccr.source_chunk_id
INNER JOIN graph.contextual_chunks target
    ON target.chunk_id = ccr.target_chunk_id
WHERE target.document_id = 'bruen_v_nyc_2022'
    AND ccr.reference_type IN ('follows', 'supports')
    AND ccr.confidence_score >= 0.75
ORDER BY source.created_at DESC;
```

**Results**:
- Rahimi v. US (2024) - follows Bruen framework (0.85)
- Range v. Garland (2023) - supports Bruen analysis (0.78)

**Use Case 3: Contradiction Detection**

Identify conflicting legal reasoning across documents:

```sql
SELECT
    s.document_id as doc1,
    t.document_id as doc2,
    s.original_content as chunk1,
    t.original_content as chunk2,
    ccr.confidence_score
FROM graph.chunk_cross_references ccr
INNER JOIN graph.contextual_chunks s ON s.chunk_id = ccr.source_chunk_id
INNER JOIN graph.contextual_chunks t ON t.chunk_id = ccr.target_chunk_id
WHERE ccr.reference_type = 'contradicts'
    AND ccr.confidence_score >= 0.7
ORDER BY ccr.confidence_score DESC;
```

**Applications**:
- Identifying split circuit decisions
- Finding overruled precedents
- Detecting legal evolution over time

**Use Case 4: Semantic Similarity Clustering**

Find thematically related chunks using vector similarity:

```sql
SELECT
    target.chunk_id,
    target.original_content,
    ccr.confidence_score as similarity
FROM graph.chunk_cross_references ccr
INNER JOIN graph.contextual_chunks target
    ON target.chunk_id = ccr.target_chunk_id
WHERE ccr.source_chunk_id = 'chunk_rahimi_p12_001'
    AND ccr.reference_type = 'similar_topic'
    AND ccr.confidence_score >= 0.85
ORDER BY ccr.confidence_score DESC;
```

Creates a "neighborhood" of semantically similar chunks for enhanced contextual retrieval.

**Performance Considerations**:

- Both tables use partial indexes for high-relevance records only (score ≥ 0.7)
- Bidirectional index on cross-references enables efficient reverse lookups
- Unique constraints prevent duplicate connections
- Typical table sizes: 5-10x number of chunks for connections, 2-3x for cross-references

---

## Many-to-Many Node-Community Relationships

The `graph.node_communities` junction table enables many-to-many relationships between nodes and communities, allowing sophisticated community membership analysis. This architecture supports nodes belonging to multiple communities with varying membership strengths, reflecting the reality that legal entities often participate in multiple thematic clusters.

### Schema: graph.node_communities

```sql
CREATE TABLE graph.node_communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id TEXT NOT NULL,              -- References graph.nodes.node_id
    community_id TEXT NOT NULL,         -- References graph.communities.community_id
    membership_strength REAL,           -- 0.0-1.0 (strength of community membership)
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_node_community UNIQUE(node_id, community_id),
    CONSTRAINT valid_membership_strength CHECK (membership_strength BETWEEN 0.0 AND 1.0),
    FOREIGN KEY (node_id) REFERENCES graph.nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (community_id) REFERENCES graph.communities(community_id) ON DELETE CASCADE
);

-- Optimized indexes for bidirectional queries
CREATE INDEX idx_node_communities_node ON graph.node_communities(node_id);
CREATE INDEX idx_node_communities_community ON graph.node_communities(community_id);
CREATE INDEX idx_node_communities_strength ON graph.node_communities(membership_strength DESC);
```

**Field Descriptions:**
- `node_id`: The entity/node identifier from graph.nodes
- `community_id`: The community identifier from graph.communities
- `membership_strength`: Score from 0.0 to 1.0 indicating how strongly the node belongs to the community
  - **0.9-1.0**: Core member (central to community theme)
  - **0.7-0.89**: Strong member (highly relevant)
  - **0.5-0.69**: Moderate member (relevant but peripheral)
  - **0.0-0.49**: Weak member (tangentially related)

### Use Case 1: Find All Communities for a Specific Node

Find all communities that contain the "Bruen v. NYC" case entity:

```sql
SELECT
    c.community_id,
    c.title,
    c.summary,
    nc.membership_strength,
    c.size as community_size,
    c.level
FROM graph.node_communities nc
INNER JOIN graph.communities c ON c.community_id = nc.community_id
WHERE nc.node_id = 'entity_case_bruen_001'
ORDER BY nc.membership_strength DESC;
```

**Example Results:**
```
community_id               | title                      | membership_strength | size
---------------------------|----------------------------|--------------------|-----
community_2A_doctrine_001  | Second Amendment Cases     | 0.95               | 45
community_scotus_2022_003  | 2022 Supreme Court Term    | 0.82               | 38
community_gun_rights_007   | Firearms Regulations       | 0.78               | 52
```

**Interpretation**: Bruen is a core member (0.95) of the Second Amendment community but also belongs to broader SCOTUS and firearms regulation communities.

### Use Case 2: Find All Nodes in a Community

Get all entities in the "Second Amendment Cases" community with strong membership:

```sql
SELECT
    n.node_id,
    n.label,
    n.node_type,
    nc.membership_strength,
    COALESCE(n.metadata->>'entity_type', 'unknown') as entity_type
FROM graph.node_communities nc
INNER JOIN graph.nodes n ON n.node_id = nc.node_id
WHERE nc.community_id = 'community_2A_doctrine_001'
    AND nc.membership_strength >= 0.7  -- Only strong members
ORDER BY nc.membership_strength DESC, n.label
LIMIT 20;
```

**Example Results:**
```
label                                      | node_type | membership_strength | entity_type
-------------------------------------------|-----------|---------------------|-------------
Bruen v. New York (2022)                  | entity    | 0.95                | CASE_CITATION
Heller v. DC (2008)                       | entity    | 0.93                | CASE_CITATION
McDonald v. Chicago (2010)                | entity    | 0.91                | CASE_CITATION
Rahimi v. United States (2024)            | entity    | 0.88                | CASE_CITATION
Second Amendment                          | entity    | 0.87                | LEGAL_DOCTRINE
Right to Bear Arms                        | entity    | 0.85                | LEGAL_DOCTRINE
```

### Use Case 3: Multi-Community Node Analysis

Find nodes that belong to multiple high-relevance communities (potential bridge entities):

```sql
SELECT
    n.node_id,
    n.label,
    n.node_type,
    COUNT(DISTINCT nc.community_id) as community_count,
    AVG(nc.membership_strength) as avg_membership_strength,
    ARRAY_AGG(c.title ORDER BY nc.membership_strength DESC) as communities
FROM graph.node_communities nc
INNER JOIN graph.nodes n ON n.node_id = nc.node_id
INNER JOIN graph.communities c ON c.community_id = nc.community_id
WHERE nc.membership_strength >= 0.7
GROUP BY n.node_id, n.label, n.node_type
HAVING COUNT(DISTINCT nc.community_id) >= 3  -- Belongs to 3+ communities
ORDER BY community_count DESC, avg_membership_strength DESC
LIMIT 10;
```

**Example Results:**
```
label                          | community_count | avg_strength | communities
-------------------------------|-----------------|--------------|----------------------------------
Supreme Court of United States | 5               | 0.89         | {Constitutional Law, 2A Cases, Due Process, SCOTUS 2022, Precedent}
Substantive Due Process        | 4               | 0.84         | {Constitutional Law, 14th Amendment, Liberty Rights, Criminal Law}
```

**Interpretation**: These are "bridge entities" that connect multiple thematic areas in the knowledge graph.

### Use Case 4: Community Membership Strength Distribution

Analyze the distribution of membership strengths within a community:

```sql
SELECT
    CASE
        WHEN membership_strength >= 0.9 THEN 'Core (0.9-1.0)'
        WHEN membership_strength >= 0.7 THEN 'Strong (0.7-0.89)'
        WHEN membership_strength >= 0.5 THEN 'Moderate (0.5-0.69)'
        ELSE 'Weak (0.0-0.49)'
    END as membership_tier,
    COUNT(*) as node_count,
    ROUND(AVG(membership_strength)::numeric, 3) as avg_strength
FROM graph.node_communities
WHERE community_id = 'community_2A_doctrine_001'
GROUP BY membership_tier
ORDER BY MIN(membership_strength) DESC;
```

**Example Results:**
```
membership_tier      | node_count | avg_strength
---------------------|------------|-------------
Core (0.9-1.0)      | 8          | 0.943
Strong (0.7-0.89)   | 15         | 0.802
Moderate (0.5-0.69) | 12         | 0.614
Weak (0.0-0.49)     | 10         | 0.387
```

**Use Case**: Helps assess community cohesion - tight communities have more core/strong members.

### Use Case 5: Find Related Nodes via Shared Communities

Find nodes related to a given node by shared community membership:

```sql
WITH target_communities AS (
    SELECT community_id, membership_strength
    FROM graph.node_communities
    WHERE node_id = 'entity_case_rahimi_001'
)
SELECT
    n.node_id,
    n.label,
    COUNT(DISTINCT tc.community_id) as shared_communities,
    AVG(nc.membership_strength) as avg_related_strength,
    ARRAY_AGG(DISTINCT c.title) as shared_community_names
FROM target_communities tc
INNER JOIN graph.node_communities nc
    ON nc.community_id = tc.community_id
INNER JOIN graph.nodes n
    ON n.node_id = nc.node_id
INNER JOIN graph.communities c
    ON c.community_id = tc.community_id
WHERE nc.node_id != 'entity_case_rahimi_001'  -- Exclude the target node
    AND nc.membership_strength >= 0.6
GROUP BY n.node_id, n.label
HAVING COUNT(DISTINCT tc.community_id) >= 2  -- Share at least 2 communities
ORDER BY shared_communities DESC, avg_related_strength DESC
LIMIT 10;
```

**Example Results:**
```
label                     | shared_communities | avg_strength | shared_community_names
--------------------------|-------------------|--------------|-----------------------
Bruen v. NYC (2022)      | 3                 | 0.91         | {2A Cases, SCOTUS Precedent, Firearm Restrictions}
Heller v. DC (2008)      | 2                 | 0.88         | {2A Cases, Constitutional Rights}
```

**Use Case**: Discover semantically related entities through community co-membership.

### Performance Optimization Tips

1. **Always filter by membership_strength** when you only need strong relationships:
   ```sql
   WHERE membership_strength >= 0.7  -- Uses partial index
   ```

2. **Use EXISTS for membership checks** instead of JOIN when you only need true/false:
   ```sql
   WHERE EXISTS (
       SELECT 1 FROM graph.node_communities
       WHERE node_id = n.node_id
       AND community_id = 'community_2A_doctrine_001'
   )
   ```

3. **Leverage bidirectional indexes** for efficient lookups in both directions

4. **Batch queries** when checking membership for multiple nodes/communities

**Typical Performance**:
- Node→Communities lookup: 2-5ms
- Community→Nodes lookup: 3-8ms (depends on community size)
- Multi-community analysis: 10-30ms
- Bridge entity detection: 20-50ms

---

For comprehensive integration examples and troubleshooting guides, refer to the main service documentation and health monitoring endpoints.