# Test Data Quick Reference - API Parity Testing

**Last Updated**: 2025-10-20
**Status**: ✅ Ready for test implementation

---

## TL;DR - What Data Can I Use?

### ✅ **USE THIS**: Law Schema (Real Production Data)
```python
# 15,001 legal documents with 59,919 entities
table = "law_documents"  # or "law_entities"
limit = 100-1000
```

### ✅ **USE THIS**: Graph Schema (Synthetic but Large)
```python
# 141,000 nodes, 81,974 edges, 1,000 communities
table = "graph_nodes"  # or "graph_edges", "graph_communities"
limit = 100-5000
```

### ⚠️ **LIMITED**: Client Schema (Empty Tables)
```python
# 50 cases but 0 documents/entities
# Only test case management, not document operations
```

---

## Quick Test Examples

### Test 1: Query Law Documents
```python
from src.clients.supabase_fluent import SupabaseFluentClient

client = SupabaseFluentClient()

# Get law documents
result = client.table("law_documents") \
    .select("*") \
    .eq("document_type", "opinion") \
    .limit(100) \
    .execute()

print(f"Found {len(result.data)} documents")
```

### Test 2: Query Law Entities
```python
# Get entities by type
result = client.table("law_entities") \
    .select("*") \
    .eq("entity_type", "agreement") \
    .gte("confidence_score", 0.8) \
    .limit(500) \
    .execute()

print(f"Found {len(result.data)} entities")
```

### Test 3: Pagination on Large Dataset
```python
# Test pagination with graph nodes (141K total)
page_size = 1000
page = 0

result = client.table("graph_nodes") \
    .select("*") \
    .limit(page_size) \
    .offset(page * page_size) \
    .execute()

print(f"Page {page}: {len(result.data)} nodes")
```

### Test 4: Count Operations
```python
# Test count functionality
result = client.table("law_documents") \
    .select("*", count="exact", head=True) \
    .eq("processing_status", "completed") \
    .execute()

print(f"Total completed documents: {result.count}")
```

### Test 5: Graph Operations
```python
# Query graph communities
result = client.table("graph_communities") \
    .select("*") \
    .gte("node_count", 10) \
    .order("coherence_score", desc=True) \
    .limit(50) \
    .execute()

print(f"Found {len(result.data)} communities")

# Query edges/relationships
result = client.table("graph_edges") \
    .select("*") \
    .eq("relationship_type", "RELATED_TO") \
    .limit(500) \
    .execute()

print(f"Found {len(result.data)} edges")
```

---

## Safe LIMIT Values

| Dataset | Records | Safe LIMIT | Purpose |
|---------|---------|------------|---------|
| law_documents | 15,001 | 100-1000 | Standard queries |
| law_entities | 59,919 | 100-500 | Entity queries |
| graph_nodes | 141,000 | 1000-5000 | Performance tests |
| graph_edges | 81,974 | 500-1000 | Relationship queries |
| graph_communities | 1,000 | 50-100 | Community analysis |
| graph_chunks | 30,000 | 500-2000 | Chunk operations |

---

## Data Availability Matrix

| Feature | Law Schema | Client Schema | Graph Schema |
|---------|-----------|--------------|--------------|
| **Documents** | ✅ 15,001 | ❌ 0 | ✅ 1,030 (registry) |
| **Entities** | ✅ 59,919 | ❌ 0 | ✅ 141,000 (nodes) |
| **Relationships** | ✅ 29,835 | ❌ 0 | ✅ 81,974 (edges) |
| **Real Data** | ✅ Yes | ⚠️ Partial | ⚠️ Synthetic |
| **case_id filtering** | ❌ N/A | ✅ Yes | ❌ Not exposed |
| **Large datasets** | ⚠️ Medium | ❌ Empty | ✅ Large |

---

## Common Queries

### Get Document by ID
```python
result = client.table("law_documents") \
    .select("*") \
    .eq("document_id", "doc_123") \
    .single() \
    .execute()
```

### Filter by Document Type
```python
result = client.table("law_documents") \
    .select("*") \
    .eq("document_type", "opinion") \
    .limit(100) \
    .execute()
```

### Range Queries
```python
result = client.table("law_entities") \
    .select("*") \
    .gte("confidence_score", 0.8) \
    .lte("confidence_score", 1.0) \
    .limit(500) \
    .execute()
```

### Ordering
```python
result = client.table("graph_communities") \
    .select("*") \
    .order("node_count", desc=True) \
    .limit(50) \
    .execute()
```

### Text Search
```python
result = client.table("law_documents") \
    .select("*") \
    .text_search("title", "jurisdiction") \
    .limit(100) \
    .execute()
```

---

## Performance Tips

1. **Use Appropriate LIMITS**: Don't query all 141K nodes at once
2. **Paginate Large Results**: Use `offset` for large datasets
3. **Filter Early**: Use `.eq()`, `.gt()`, `.lt()` before `.select()`
4. **Count Without Data**: Use `count="exact", head=True` for counts only
5. **Select Specific Columns**: Use `.select("id,title,status")` not `.select("*")`

---

## When to Use Each Schema

### Law Schema ✅
- ✅ Testing core query operations
- ✅ Testing filters, ordering, pagination
- ✅ Real legal document data
- ✅ Entity extraction validation
- ⚠️ No case_id filtering (law docs are universal)

### Client Schema ⚠️
- ✅ Testing case management
- ⚠️ Very limited data (50 cases only)
- ❌ Cannot test document/entity operations (empty)
- ⚠️ Need to upload test documents first

### Graph Schema ✅
- ✅ Performance testing (141K nodes)
- ✅ Pagination testing
- ✅ Large result set handling
- ✅ Graph traversal operations
- ⚠️ Synthetic data (not production-representative)
- ❌ No case_id/client_id filtering (columns not exposed)

---

## Next Steps

1. **Implement Tests**: Use law schema for core functionality tests
2. **Performance Tests**: Use graph schema for large dataset tests
3. **Edge Cases**: Test with various filters, orders, limits
4. **Error Handling**: Test invalid queries, non-existent IDs
5. **Pagination**: Test offset-based pagination with graph_nodes

---

**Full Report**: See `test_data_inventory.md` for complete details
**Discovery Script**: `discover_test_data.py` for re-running discovery
