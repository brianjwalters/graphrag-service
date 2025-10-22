# GraphRAG Service Response Field Name Update

## Summary

Updated all GraphRAG service response field names in `storage_info` to match the documented API specification in `api.md` and `README.md`.

## Changes Made

### 1. Source Code Updates (`graph_constructor.py`)

**File**: `/srv/luris/be/graphrag-service/src/core/graph_constructor.py`

#### Change 1: Storage Info Dictionary Initialization (Line 338-343)
```python
# OLD:
storage_info = {
    "entities_stored": 0,
    "relationships_stored": 0,
    "communities_stored": 0,
    "errors": []
}

# NEW:
storage_info = {
    "nodes_created": 0,
    "edges_created": 0,
    "communities_detected": 0,
    "errors": []
}
```

#### Change 2: Entity Storage Increment (Line 392)
```python
# OLD:
storage_info["entities_stored"] = len(result) if result else 0

# NEW:
storage_info["nodes_created"] = len(result) if result else 0
```

#### Change 3: Relationship Storage Increment (Line 428)
```python
# OLD:
storage_info["relationships_stored"] = len(result) if result else 0

# NEW:
storage_info["edges_created"] = len(result) if result else 0
```

#### Change 4: Community Storage Increment (Line 455)
```python
# OLD:
storage_info["communities_stored"] = len(result) if result else 0

# NEW:
storage_info["communities_detected"] = len(result) if result else 0
```

### 2. Documentation Updates

#### API_ENDPOINTS.md (Line 101-106)
```json
// OLD:
"storage_info": {
  "entities_stored": 15,
  "relationships_stored": 23,
  "communities_stored": 3,
  "errors": []
}

// NEW:
"storage_info": {
  "nodes_created": 15,
  "edges_created": 23,
  "communities_detected": 3,
  "errors": []
}
```

#### api.md (Line 572-578)
```json
// OLD:
"storage": {
  "entities_stored": 12500,
  "relationships_stored": 8900,
  "communities_stored": 340,
  "embeddings_stored": 34000,
  "database_size_mb": 450.5
}

// NEW:
"storage": {
  "nodes_created": 12500,
  "edges_created": 8900,
  "communities_detected": 340,
  "embeddings_stored": 34000,
  "database_size_mb": 450.5
}
```

## Rationale

### Why These Field Names?

1. **`nodes_created`** instead of `entities_stored`:
   - More accurate representation: entities are stored as nodes in `graph.nodes` table
   - Aligns with Microsoft GraphRAG terminology (nodes and edges)
   - Clearer semantics: "created" indicates the action performed

2. **`edges_created`** instead of `relationships_stored`:
   - Consistent with graph database terminology
   - Matches the actual database table name (`graph.edges`)
   - Parallel naming with `nodes_created` for consistency

3. **`communities_detected`** instead of `communities_stored`:
   - "Detected" is more accurate for the Leiden algorithm process
   - Emphasizes the algorithmic nature of community detection
   - Matches terminology used in `graph_summary` field

## Verification

### Code Verification
```bash
# No remaining references to old field names in source code
grep -r "entities_stored\|relationships_stored\|communities_stored" src/
# Result: No matches found
```

### Documentation Consistency
All API documentation now uses the new field names:
- ✅ `api.md`
- ✅ `API_ENDPOINTS.md`
- ✅ `README.md` (already using new names)

### Test Files
Note: Test result JSON files (`graphrag_test_report_*.json`) still contain old field names. These are historical test artifacts and will be updated when tests are re-run.

## Impact Assessment

### Breaking Changes
⚠️ **API Breaking Change**: Clients using the old field names will need to update their code.

### Migration Path for Clients
```python
# Before (old field names):
storage_info = response["storage_info"]
entities = storage_info["entities_stored"]
relationships = storage_info["relationships_stored"]
communities = storage_info["communities_stored"]

# After (new field names):
storage_info = response["storage_info"]
nodes = storage_info["nodes_created"]
edges = storage_info["edges_created"]
communities = storage_info["communities_detected"]
```

### Backward Compatibility
To support gradual migration, consider adding both field names temporarily:
```python
storage_info = {
    # New field names (primary)
    "nodes_created": node_count,
    "edges_created": edge_count,
    "communities_detected": community_count,

    # Deprecated field names (for backward compatibility)
    "entities_stored": node_count,  # DEPRECATED: Use nodes_created
    "relationships_stored": edge_count,  # DEPRECATED: Use edges_created
    "communities_stored": community_count,  # DEPRECATED: Use communities_detected

    "errors": []
}
```

## Testing Recommendations

1. **Unit Tests**: Update unit tests to assert new field names
2. **Integration Tests**: Verify GraphRAG service returns correct field names
3. **Client Updates**: Update all service clients that consume GraphRAG responses
4. **Documentation**: Add migration guide for external API consumers

## Files Modified

### Source Code (1 file)
- `/srv/luris/be/graphrag-service/src/core/graph_constructor.py`

### Documentation (2 files)
- `/srv/luris/be/graphrag-service/API_ENDPOINTS.md`
- `/srv/luris/be/graphrag-service/api.md`

## Next Steps

1. ✅ Source code updated
2. ✅ Documentation updated
3. ⏳ Code review by senior-code-reviewer
4. ⏳ Update unit tests to use new field names
5. ⏳ Update integration tests
6. ⏳ Notify downstream service consumers of API change
7. ⏳ Run full test suite and update test result artifacts

## Date

**Updated**: October 8, 2025
**Author**: Backend Engineer Agent
**Reviewer**: TBD (senior-code-reviewer)
