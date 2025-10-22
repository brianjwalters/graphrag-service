# Test Data Inventory - API Parity Testing

**Discovery Date**: 2025-10-20
**Purpose**: Identify production data suitable for testing GraphRAG Service fluent API
**Analyst**: backend-engineer

---

## Executive Summary

The database contains substantial test data across three schemas:
- **Law Schema**: 15,001 legal documents with 59,919 extracted entities
- **Client Schema**: 50 cases defined (but no documents or entities yet)
- **Graph Schema**: 141,000 nodes, 81,974 edges, 1,000 communities, 30,000 chunks

**Key Finding**: Graph schema data appears to be synthetic test data without case_id/client_id filtering. Law schema has real legal reference data.

---

## Law Schema

### Documents
- **Total Documents**: 15,001
- **Document Types**: Mixed (opinions, statutes, regulations, case law, etc.)
- **Processing Status**: Various (pending, processing, completed, failed, archived)
- **Storage**: Supabase Storage with metadata tracking
- **Use Case**: Legal reference materials, precedent analysis

### Entities
- **Total Entities**: 59,919 legal entities extracted
- **Entity Types**: 31 legal entity types (agreement, appeal, citation, statute, etc.)

#### Top Entity Types:
| Entity Type | Count |
|-------------|-------|
| agreement | 514 |
| appeal | 486 |
| *(others distributed across 31 types)* | 58,919 |

### Recommended Use Cases:
- ✅ Test entity extraction on real legal documents
- ✅ Test relationship extraction between legal entities
- ✅ Test legal document classification
- ✅ Test citation parsing and validation
- ✅ Test semantic search across law documents

---

## Client Schema

### Cases
- **Total Cases**: 50 case records defined
- **Case IDs**: 50 unique UUID-based case identifiers
- **Case Numbers**: Various (formatted case numbers)
- **Status**: Mixed (active, pending, archived)
- **Courts**: Multiple jurisdictions

### Documents & Entities
- **Total Documents**: 0 (empty table)
- **Total Entities**: 0 (empty table)
- **Financial Data**: 0 records

**Status**: Client schema structure is defined but contains minimal data. Case records exist but no associated documents or entities have been ingested.

### Recommended Use Cases:
- ⚠️ **Limited**: Client schema not suitable for data-dependent tests yet
- ✅ Can test case creation and metadata management
- ✅ Can test case filtering and search
- ❌ Cannot test document processing or entity extraction

---

## Graph Schema

### Overview
- **Total Nodes**: 141,000 (mostly entity and chunk types)
- **Total Edges**: 81,974 relationships
- **Total Communities**: 1,000 detected communities
- **Total Chunks**: 30,000 document chunks
- **Document Registry**: 1,030 documents tracked

### Node Distribution (Sampled)
- **Node Types**: Predominantly "chunk" type (100% of 5,000 sample)
- **Synthetic Data**: Nodes appear to be synthetically generated test data
- **Metadata Structure**: `{"node_type": "entity", "synthetic": true}`

### Data Characteristics
- ❌ **No case_id/client_id columns** in public schema views (graph_nodes)
- ⚠️ **Synthetic test data** - nodes labeled as "Entity 0", "Entity 1", etc.
- ✅ **Large volume** - sufficient for performance and pagination testing
- ✅ **Graph structure** - nodes, edges, communities all populated

### Recommended Use Cases:
- ✅ Test pagination on large datasets (141K nodes)
- ✅ Test graph traversal algorithms
- ✅ Test community detection results
- ✅ Test edge relationship queries
- ✅ Test performance with large result sets
- ⚠️ NOT suitable for case_id/client_id filtering tests (columns not exposed)
- ⚠️ NOT suitable for real-world data validation

---

## Cross-Schema Coverage

### Findings
- **Law → Graph**: Law documents appear in document_registry (1,030 documents)
- **Client → Graph**: Case references exist in schema but not accessible via public REST API
- **Common Identifiers**: No case_id/client_id overlap detected in accessible data

### Schema Relationships
```
law.documents (15,001)
    ↓ (document_id)
graph.document_registry (1,030)
    ↓ (document_id)
graph.chunks (30,000)
    ↓ (references)
graph.nodes (141,000)
    ↓ (relationships)
graph.edges (81,974)
```

**Note**: Client schema (50 cases) exists independently with no current document/entity data.

---

## Recommended Test Parameters

### For Law Schema Testing

#### Large Dataset Test
```python
# Query law documents
table = "law_documents"
limit = 1000
filters = {"processing_status": "completed"}

# Expected: ~15,000 total documents
# Use LIMIT: 100-1000 for reasonable response times
```

#### Entity Extraction Test
```python
# Query law entities
table = "law_entities"
limit = 500
filters = {"entity_type": "agreement"}  # or "appeal", "citation", etc.

# Expected: 59,919 total entities
# Use LIMIT: 50-500 for standard testing
```

### For Graph Schema Testing

#### Node Pagination Test
```python
# Test large dataset pagination
table = "graph_nodes"
limit = 1000
offset = 0  # Increment by limit for pagination

# Expected: 141,000 total nodes
# Safe LIMIT: 100-5000 depending on performance requirements
```

#### Community Analysis Test
```python
# Query communities
table = "graph_communities"
limit = 100

# Expected: 1,000 communities
# Can query all communities or filter by size/coherence
```

#### Edge Traversal Test
```python
# Query relationships
table = "graph_edges"
limit = 500
filters = {"relationship_type": "RELATED_TO"}

# Expected: 81,974 total edges
# Use LIMIT: 100-1000 for relationship queries
```

### Safe Query Limits

| Query Type | Recommended LIMIT | Use Case |
|------------|-------------------|----------|
| Quick Tests | 10-50 | Development, debugging |
| Standard Tests | 100-500 | Integration testing |
| Performance Tests | 1,000-5,000 | Load testing, benchmarking |
| Full Scans | Use pagination | Data migrations, reports |

### Pagination Pattern
```python
# For large datasets
page_size = 500
page = 0

while True:
    result = client.table("graph_nodes") \
        .select("*") \
        .limit(page_size) \
        .offset(page * page_size) \
        .execute()

    if not result.data:
        break

    # Process result.data
    page += 1
```

---

## Data Quality Assessment

### ✅ Strengths
1. **Law Schema**: Real legal documents with authentic entity extraction
2. **Graph Volume**: Large dataset (141K nodes) suitable for performance testing
3. **Graph Structure**: Complete graph structure (nodes, edges, communities, chunks)
4. **Document Registry**: Cross-schema document tracking operational (1,030 docs)
5. **Entity Types**: Comprehensive legal entity taxonomy (31 types, 59K entities)

### ⚠️ Limitations
1. **Client Schema**: Minimal data (cases defined but no documents/entities)
2. **Synthetic Graph Data**: Graph nodes appear to be test/synthetic data
3. **Case/Client Filtering**: case_id/client_id columns not accessible via public API
4. **Cross-Schema Gaps**: Limited data flow between client and graph schemas

### ❌ Gaps
1. **Client Documents**: 0 client documents for testing document upload flow
2. **Client Entities**: 0 client entities for testing entity extraction on client data
3. **Multi-Tenant Testing**: Cannot test case_id/client_id isolation with current data access
4. **Real-World Validation**: Graph data is synthetic, not suitable for production validation

---

## Implementation Recommendations

### For API Parity Testing

#### ✅ **RECOMMENDED**: Use Law Schema + Graph Schema
```python
# Test Pattern 1: Law Documents + Entity Extraction
# - Use law.documents for document queries
# - Use law.entities for entity queries
# - Rich real-world legal data

# Test Pattern 2: Graph Operations
# - Use graph.nodes for large dataset pagination
# - Use graph.edges for relationship traversal
# - Use graph.communities for clustering analysis
# - Synthetic data but suitable for API/performance testing
```

#### ⚠️ **LIMITED**: Client Schema Testing
```python
# Only test case management operations
# - Case creation, update, filtering
# - Case metadata queries
# - Cannot test document/entity operations (no data)
```

### Test Data Creation Strategy

**If real client data is needed**:
1. Upload sample client documents via Document Upload Service (port 8008)
2. Process through Entity Extraction Service (port 8007)
3. Store results in client.documents and client.entities
4. Link to existing cases using case_id

**For graph testing**:
1. Current synthetic data sufficient for API testing
2. For production validation, rebuild graph from law.documents
3. Run GraphRAG service graph construction on real documents

---

## Test Scenarios by Priority

### Priority 1: Core API Functionality (Use Law Schema)
```python
# Scenario 1: Query law documents with filters
client.table("law_documents") \
    .select("*") \
    .eq("document_type", "opinion") \
    .gte("entity_count", 10) \
    .limit(100) \
    .execute()

# Scenario 2: Query law entities by type
client.table("law_entities") \
    .select("*") \
    .eq("entity_type", "agreement") \
    .gte("confidence_score", 0.8) \
    .limit(500) \
    .execute()

# Scenario 3: Count operations
client.table("law_documents") \
    .select("*", count="exact", head=True) \
    .eq("processing_status", "completed") \
    .execute()
```

### Priority 2: Graph Operations (Use Graph Schema)
```python
# Scenario 1: Large dataset pagination
client.table("graph_nodes") \
    .select("*") \
    .eq("node_type", "entity") \
    .limit(1000) \
    .offset(0) \
    .execute()

# Scenario 2: Community queries
client.table("graph_communities") \
    .select("*") \
    .gte("node_count", 10) \
    .order("coherence_score", desc=True) \
    .limit(50) \
    .execute()

# Scenario 3: Edge traversal
client.table("graph_edges") \
    .select("*") \
    .eq("relationship_type", "RELATED_TO") \
    .gte("confidence_score", 0.7) \
    .limit(500) \
    .execute()
```

### Priority 3: Performance Testing (Use Graph Schema)
```python
# Scenario 1: Large result sets
client.table("graph_nodes") \
    .select("*") \
    .limit(5000) \
    .execute()

# Scenario 2: Complex joins (if supported)
client.table("graph_edges") \
    .select("*, source:graph_nodes!source_node_id(*), target:graph_nodes!target_node_id(*)") \
    .limit(100) \
    .execute()

# Scenario 3: Aggregations
client.table("graph_communities") \
    .select("*, graph_nodes(count)") \
    .execute()
```

---

## Conclusion

### Summary
The database provides **substantial test data** for API parity testing with the following characteristics:

- **Best for Testing**: Law schema operations, graph structure queries, pagination, performance
- **Limited Testing**: Client schema operations (minimal data)
- **Not Suitable**: Multi-tenant isolation testing (case_id/client_id not accessible), real-world data validation with graph data

### Recommended Approach
1. **Phase 1**: Test core fluent API functionality using law schema (real data)
2. **Phase 2**: Test graph operations and pagination using graph schema (synthetic data)
3. **Phase 3**: Ingest client documents if multi-tenant testing is required

### Key Metrics
- ✅ **15,001** law documents available for testing
- ✅ **59,919** law entities for entity operations
- ✅ **141,000** graph nodes for performance testing
- ✅ **81,974** graph edges for relationship queries
- ✅ **1,000** communities for clustering analysis

**Assessment**: Database contains sufficient data for comprehensive fluent API testing.

---

**Report Generated**: 2025-10-20
**Status**: ✅ Complete - Ready for test implementation
