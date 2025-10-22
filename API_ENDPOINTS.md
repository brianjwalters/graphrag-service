# GraphRAG Service API Endpoints

**Base URL**: `http://localhost:8010`  
**API Prefix**: `/api/v1`

## 📊 Graph Operations

### 1. Create Knowledge Graph
**POST** `/api/v1/graph/create`

Creates a new knowledge graph from document entities and relationships.

**Request Body**:
```json
{
  "document_id": "doc-123",
  "client_id": "client-uuid",     // Optional: for tenant isolation
  "case_id": "case-uuid",         // Optional: for case isolation
  "markdown_content": "Document content...",
  "entities": [
    {
      "entity_id": "entity-1",
      "entity_text": "Acme Corporation",
      "entity_type": "ORGANIZATION",
      "confidence": 0.95,
      "attributes": {}
    }
  ],
  "citations": [
    {
      "citation_id": "cite-1",
      "citation_text": "Smith v. Jones, 123 F.3d 456",
      "citation_type": "case",
      "is_valid": true,
      "bluebook_format": "Smith v. Jones, 123 F.3d 456 (2d Cir. 2020)"
    }
  ],
  "relationships": [
    {
      "relationship_id": "rel-1",
      "source_entity": "entity-1",
      "target_entity": "entity-2",
      "relationship_type": "CONTRACTS_WITH",
      "confidence": 0.8
    }
  ],
  "enhanced_chunks": [
    {
      "chunk_id": "chunk-1",
      "content": "Chunk content...",
      "contextualized_content": "Enhanced content with context...",
      "chunk_index": 0,
      "metadata": {}
    }
  ],
  "graph_options": {
    "enable_deduplication": true,
    "enable_community_detection": true,
    "enable_cross_document_linking": true,
    "enable_analytics": true,
    "use_ai_summaries": true,
    "similarity_threshold": 0.85,
    "leiden_resolution": 1.0,
    "min_community_size": 3
  },
  "metadata": {
    "document_type": "contract",
    "jurisdiction": "federal"
  }
}
```

**Response**:
```json
{
  "success": true,
  "graph_id": "graph_doc-123_1234567890",
  "document_id": "doc-123",
  "client_id": "client-uuid",
  "case_id": "case-uuid",
  "graph_summary": {
    "nodes_created": 15,
    "edges_created": 23,
    "communities_detected": 3,
    "deduplication_rate": 0.12,
    "graph_density": 0.34,
    "processing_time_seconds": 2.5
  },
  "quality_metrics": {
    "graph_completeness": 0.92,
    "community_coherence": 0.87,
    "entity_confidence_avg": 0.93,
    "relationship_confidence_avg": 0.85,
    "coverage_score": 0.95,
    "warnings": [],
    "suggestions": []
  },
  "communities": [...],
  "analytics": {...},
  "deduplication": {...},
  "storage_info": {
    "nodes_created": 15,
    "edges_created": 23,
    "communities_detected": 3,
    "errors": []
  },
  "cross_document_links": 5,
  "processing_metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "processing_time": 2.5,
    "options_used": {...}
  }
}
```

---

### 2. Update Knowledge Graph
**POST** `/api/v1/graph/update`

Updates an existing knowledge graph with new entities and relationships.

**Request Body**:
```json
{
  "graph_id": "graph_doc-123_1234567890",
  "document_id": "doc-456",
  "entities": [...],
  "relationships": [...],
  "merge_strategy": "smart",  // Options: "smart", "replace", "append"
  "graph_options": {...}
}
```

**Response**:
```json
{
  "success": true,
  "graph_id": "graph_doc-123_1234567890",
  "nodes_added": 5,
  "edges_added": 8,
  "communities_updated": 2,
  "quality_metrics": {...},
  "processing_time_seconds": 1.5
}
```

---

### 3. Query Knowledge Graph
**POST** `/api/v1/graph/query`

Query the knowledge graph for entities, relationships, or communities.

**Request Body**:
```json
{
  "query_type": "entities",  // Options: "entities", "relationships", "communities", "analytics"
  "client_id": "client-uuid",    // Optional: tenant filtering
  "case_id": "case-uuid",        // Optional: case filtering
  "entity_ids": ["entity-1", "entity-2"],
  "document_ids": ["doc-123"],
  "entity_types": ["ORGANIZATION", "PERSON"],
  "max_hops": 2,
  "limit": 100,
  "include_analytics": false,
  "include_communities": false,
  "include_public": false  // Include public entities in results
}
```

**Response**:
```json
{
  "query_type": "entities",
  "result_count": 25,
  "entities": [...],
  "relationships": [...],
  "communities": [...],
  "analytics": null,
  "query_metadata": {
    "execution_time": 0.1,
    "filters_applied": {...}
  }
}
```

---

### 4. Get Graph Statistics
**GET** `/api/v1/graph/stats`

Get overall graph database statistics.

**Response**:
```json
{
  "statistics": {
    "total_entities": 1500,
    "total_relationships": 3200,
    "total_communities": 45,
    "total_documents": 120
  },
  "graph_info": {
    "methodology": "Microsoft GraphRAG",
    "entity_deduplication_threshold": 0.85,
    "leiden_resolution": 1.0,
    "min_community_size": 3
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### 5. Clear Graph Data
**DELETE** `/api/v1/graph/clear?document_id={document_id}`

Clear graph data from database.

**Query Parameters**:
- `document_id` (optional): Clear data for specific document only

**Response**:
```json
{
  "success": true,
  "message": "Cleared graph data for document doc-123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🏥 Health & Monitoring

### 6. Health Check
**GET** `/api/v1/health/ping`

Basic health check endpoint for load balancers and monitoring.

**Response**:
```json
{
  "status": "healthy",  // or "degraded", "unhealthy"
  "service": "graphrag-service",
  "version": "1.0.0",
  "dependencies": {
    "supabase": "healthy",
    "prompt_service": "healthy"
  },
  "metrics": {
    "uptime_seconds": 3600,
    "environment": "development"
  }
}
```

---

### 7. Service Metrics
**GET** `/api/v1/health/metrics`

Get detailed service metrics and performance data.

**Response**:
```json
{
  "service": "graphrag-service",
  "timestamp": "2024-01-15T10:30:00Z",
  "system_metrics": {
    "cpu_percent": 12.5,
    "memory_mb": 256.4,
    "memory_percent": 8.2,
    "num_threads": 4,
    "num_connections": 10
  },
  "processing_metrics": {
    "graphs_created": 150,
    "total_entities_processed": 5000,
    "total_relationships_discovered": 8500,
    "total_communities_detected": 120,
    "average_processing_time": 2.1,
    "error_rate": 0.02
  },
  "config_metrics": {
    "entity_similarity_threshold": 0.85,
    "leiden_resolution": 1.0,
    "min_community_size": 3,
    "max_community_size": 100,
    "batch_size": 100
  },
  "status": "operational"
}
```

---

### 8. Readiness Check
**GET** `/api/v1/health/ready`

Kubernetes readiness probe - checks if service is fully initialized.

**Response**:
```json
{
  "ready": true,
  "checks": {
    "graph_constructor": true,
    "supabase_client": true,
    "deduplicator": true,
    "community_detector": true,
    "relationship_discoverer": true,
    "analytics_engine": true
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### 9. Liveness Check
**GET** `/api/v1/health/live`

Kubernetes liveness probe - simple check if service is running.

**Response**:
```json
{
  "alive": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🏠 Service Information

### 10. Root Endpoint
**GET** `/`

Get service information and available endpoints.

**Response**:
```json
{
  "service": "GraphRAG Service",
  "version": "1.0.0",
  "status": "operational",
  "port": 8010,
  "environment": "development",
  "description": "Knowledge Graph Construction using Microsoft GraphRAG",
  "endpoints": {
    "create_graph": "/api/v1/graph/create",
    "update_graph": "/api/v1/graph/update",
    "query_graph": "/api/v1/graph/query",
    "health": "/api/v1/health/ping",
    "metrics": "/api/v1/health/metrics"
  },
  "features": [
    "Entity deduplication with 0.85 threshold",
    "Leiden algorithm community detection",
    "Cross-document relationship discovery",
    "Legal entity specialization",
    "Graph analytics and quality scoring",
    "AI-powered community summaries"
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🔐 Multi-Tenant Features

All graph operations now support multi-tenant isolation through:

- **`client_id`**: Isolates data by client/organization
- **`case_id`**: Further isolates data by legal case
- **Nullable columns**: NULL values indicate public/shared legal references

### Tenant Isolation Rules:
1. **Client-specific data**: Only accessible within same client context
2. **Case-specific data**: Only accessible within same case context
3. **Public data**: Accessible to all (NULL client_id and case_id)
4. **Cross-document linking**: Only within same tenant scope

### Query Filtering:
- Queries with `client_id` return only that client's data
- Queries with `case_id` return only that case's data
- `include_public: true` flag allows including public entities in results

---

## 🚀 Example Usage

### Creating a Client-Specific Graph:
```bash
curl -X POST http://localhost:8010/api/v1/graph/create \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "contract-001",
    "client_id": "law-firm-123",
    "case_id": "case-456",
    "markdown_content": "...",
    "entities": [...],
    "graph_options": {
      "enable_deduplication": true,
      "enable_community_detection": true
    }
  }'
```

### Querying Tenant-Isolated Data:
```bash
curl -X POST http://localhost:8010/api/v1/graph/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "entities",
    "client_id": "law-firm-123",
    "entity_types": ["ORGANIZATION"],
    "include_public": true
  }'
```

---

## 📝 Notes

- All endpoints return JSON responses
- Errors follow standard HTTP status codes
- Request IDs are propagated for distributed tracing
- API supports CORS for configured origins
- Service runs on port 8010 by default
- Requires Supabase connection for data persistence
- Optional integration with Prompt Service for AI features