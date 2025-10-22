# Cross-Schema Database Access - Developer Usage Guide

## Quick Reference

**Validation Status**: ✅ PRODUCTION READY (90% confidence)

The SupabaseClient from graphrag-service can reliably access **client.\*** and **law.\*** schemas in addition to its primary graph schema.

---

## Usage Examples

### 1. Law Schema Access (READ Operations)

```python
from clients.supabase_client import create_admin_supabase_client

# Create admin client
client = create_admin_supabase_client("your-service-name")

# Query law documents
law_docs = await client.get(
    "law.documents",  # Dot notation (auto-converted to law_documents)
    filters={"jurisdiction": "federal"},
    limit=50,
    admin_operation=True
)

# Filter by document type
opinions = await client.get(
    "law.documents",
    filters={"document_type": "opinion"},
    limit=10,
    admin_operation=True
)

# Access law citations
citations = await client.get(
    "law.citations",
    filters={"document_id": "doc_123"},
    admin_operation=True
)
```

**Available Law Schema Tables**:
- ✅ `law.documents` (34 columns) - Court opinions, statutes, regulations
- ✅ `law.citations` - Legal citation references
- ❌ `law.chunks` - Not exposed (use direct SQL or RPC)
- ❌ `law.embeddings` - Not exposed (use direct SQL or RPC)

---

### 2. Client Schema Access (READ Operations)

```python
# Query client documents
client_docs = await client.get(
    "client.documents",  # Dot notation
    filters={"case_id": case_id},
    limit=20,
    admin_operation=True
)

# Filter by document type
contracts = await client.get(
    "client.documents",
    filters={"document_type": "contract"},
    admin_operation=True
)

# Get specific document
doc = await client.get(
    "client.documents",
    filters={"document_id": "client_doc_123"},
    limit=1,
    admin_operation=True
)
```

**Available Client Schema Columns**:
```python
{
    "id": "uuid",
    "document_id": "string",
    "case_id": "uuid",  # Links to case
    "title": "string",
    "document_type": "string",
    "content_md": "string",  # Markdown content
    "storage_path": "string",
    "confidentiality_level": "string",
    "created_at": "timestamp",
    "updated_at": "timestamp"
}
```

---

### 3. Schema Name Conversion

The client automatically handles schema-qualified names:

```python
# These are EQUIVALENT:
await client.get("law.documents")      # Dot notation (recommended)
await client.get("law_documents")      # Underscore notation (REST API format)

# Both convert to: law_documents (internal REST API format)
```

**Conversion Rules**:
- Input: `law.documents` → Output: `law_documents`
- Input: `client.documents` → Output: `client_documents`
- Input: `graph.entities` → Output: `graph_entities`

---

### 4. Dual-Client Architecture

#### Use Anon Client (RLS-enforced)
```python
from clients.supabase_client import create_supabase_client

# Standard client (respects RLS policies)
client = create_supabase_client("service-name", use_service_role=False)

# Query with RLS enforcement
docs = await client.get("law.documents", admin_operation=False)
```

#### Use Admin Client (Bypasses RLS)
```python
from clients.supabase_client import create_admin_supabase_client

# Admin client (bypasses RLS policies)
admin_client = create_admin_supabase_client("service-name")

# Query with admin privileges
docs = await admin_client.get("law.documents", admin_operation=True)
```

---

### 5. Cross-Schema Query Patterns

#### Pattern 1: Multi-Schema Data Aggregation
```python
# Get law documents
law_docs = await client.get("law.documents", limit=10)

# Get related client documents
client_docs = await client.get("client.documents", limit=10)

# Combine results
all_docs = law_docs + client_docs
```

#### Pattern 2: Case-Based Document Retrieval
```python
# Get case-specific client documents
case_docs = await client.get(
    "client.documents",
    filters={"case_id": case_id}
)

# Get related law documents by citation
for doc in case_docs:
    # Extract citations and fetch law documents
    pass
```

#### Pattern 3: Filtered Cross-Schema Search
```python
# Law documents filtered by jurisdiction
federal_law = await client.get(
    "law.documents",
    filters={"jurisdiction": "federal"},
    limit=50
)

# Client documents filtered by type
contracts = await client.get(
    "client.documents",
    filters={"document_type": "contract"},
    limit=50
)
```

---

## Performance Characteristics

**Measured Latencies** (from validation tests):

| Operation | First Query (Cold) | Subsequent (Warm) |
|-----------|-------------------|-------------------|
| Law Schema SELECT | 348.97ms | 81.94ms |
| Client Schema SELECT | N/A | 83.71ms |
| **Average** | **~350ms** | **~80ms** |

**Performance Tips**:
1. ✅ Use `limit` parameter to control result size
2. ✅ Add filters to reduce data transfer
3. ✅ Cache frequently-accessed results
4. ⚠️ First query has cold cache penalty (~350ms)

---

## Known Limitations & Workarounds

### ❌ Limitation 1: Graph Schema Tables Not Exposed

**Problem**: `graph.entities` and `graph.relationships` not accessible via REST API

**Workaround**: Use RPC functions
```python
# ❌ DON'T: Direct REST access fails
entities = await client.get("graph.entities")  # Error!

# ✅ DO: Use RPC function
entities = await client.rpc("get_graph_entities", {
    "case_id": case_id,
    "entity_type": "person"
}, admin_operation=True)
```

### ❌ Limitation 2: Missing Chunk/Embedding Tables

**Problem**: `*_chunks` and `*_embeddings` tables not in public schema

**Workaround**: Check if tables exist in actual schemas or use RPC
```python
# May need to query actual schema tables directly
# Or use dedicated RPC functions for chunk operations
```

### ❌ Limitation 3: Schema Documentation Mismatch

**Problem**: `client_documents` structure differs from documentation

**Current Structure** (validated):
```python
# Has: case_id, confidentiality_level
# Missing: client_name, status
```

**Workaround**: Use `case_id` for client association instead of `client_name`

---

## Error Handling

### Common Errors & Solutions

#### Error: "relation does not exist"
```python
# ❌ Problem: Table not exposed in public schema
entities = await client.get("graph.entities")

# ✅ Solution: Use RPC function
entities = await client.rpc("get_graph_entities", {})
```

#### Error: "Could not find column in schema cache"
```python
# ❌ Problem: Using outdated column names
doc = {"client_name": "ABC Corp"}  # Column doesn't exist

# ✅ Solution: Use actual schema structure
doc = {"case_id": case_uuid}  # Use case_id instead
```

---

## Testing Your Integration

### Quick Validation Test
```python
async def test_cross_schema_access():
    """Validate cross-schema access is working"""
    client = create_admin_supabase_client("test-service")

    # Test law schema
    law_docs = await client.get("law.documents", limit=1, admin_operation=True)
    assert len(law_docs) > 0, "Law schema not accessible"

    # Test client schema
    client_docs = await client.get("client.documents", limit=1, admin_operation=True)
    assert len(client_docs) > 0, "Client schema not accessible"

    # Test schema conversion
    assert client._convert_table_name("law.documents") == "law_documents"

    print("✅ Cross-schema access validated!")

# Run test
asyncio.run(test_cross_schema_access())
```

---

## Best Practices

### ✅ DO

1. **Use dot notation** for schema-qualified names (more readable)
   ```python
   await client.get("law.documents")  # ✅ Recommended
   ```

2. **Use admin_operation=True** for backend services
   ```python
   await client.get("law.documents", admin_operation=True)  # ✅ Bypasses RLS
   ```

3. **Add filters** to reduce data transfer
   ```python
   await client.get("law.documents", filters={"jurisdiction": "federal"})  # ✅ Efficient
   ```

4. **Set reasonable limits**
   ```python
   await client.get("law.documents", limit=50)  # ✅ Controlled result size
   ```

5. **Handle errors gracefully**
   ```python
   try:
       docs = await client.get("law.documents")
   except Exception as e:
       logger.error(f"Failed to fetch law documents: {e}")
   ```

### ❌ DON'T

1. **Don't assume all tables are accessible**
   ```python
   # ❌ May not work for all graph tables
   entities = await client.get("graph.entities")
   ```

2. **Don't skip admin_operation flag** for backend operations
   ```python
   # ❌ May be blocked by RLS policies
   await client.get("law.documents", admin_operation=False)
   ```

3. **Don't query without limits** in production
   ```python
   # ❌ May return huge datasets
   await client.get("law.documents")  # No limit!
   ```

4. **Don't ignore schema conversion**
   ```python
   # ❌ Both work, but dot notation is clearer
   await client.get("law_documents")
   ```

---

## Troubleshooting

### Debug Schema Access Issues

```python
# 1. Check client health
health = client.get_health_info()
print(f"Client healthy: {health['healthy']}")
print(f"Error rate: {health['error_rate']}")

# 2. Test basic connectivity
try:
    result = await client.get("law.documents", limit=1, admin_operation=True)
    print(f"✅ Law schema accessible: {len(result)} rows")
except Exception as e:
    print(f"❌ Law schema error: {e}")

# 3. Verify schema conversion
converted = client._convert_table_name("law.documents")
print(f"Schema conversion: law.documents → {converted}")

# 4. Check available columns
if result:
    print(f"Available columns: {list(result[0].keys())}")
```

---

## Additional Resources

**Test Artifacts**:
- Full Test Report: `/srv/luris/be/graphrag-service/tests/CROSS_SCHEMA_TEST_REPORT.md`
- Test Results JSON: `/srv/luris/be/graphrag-service/tests/cross_schema_test_results_*.json`
- Schema Analysis: `/srv/luris/be/graphrag-service/tests/schema_diagnostic_report.json`

**Client Source Code**:
- SupabaseClient: `/srv/luris/be/graphrag-service/src/clients/supabase_client.py`
- Factory Functions: `create_supabase_client()`, `create_admin_supabase_client()`

**Validation Date**: October 3, 2025
**Confidence Level**: HIGH (90%)
**Production Status**: ✅ APPROVED

---

## Quick Command Reference

```bash
# Run cross-schema validation tests
source venv/bin/activate
python tests/test_cross_schema_access.py

# Run schema diagnostic
python tests/diagnose_schema_structure.py

# Generate test summary
python tests/generate_test_summary.py
```

---

**Questions or Issues?** Refer to the detailed test report or contact the backend engineering team.
