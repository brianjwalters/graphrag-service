# GraphRAG Batch Upload Summary

## 📊 Overview

This document summarizes the batch upload process for ~135,000+ synthetic GraphRAG records to Supabase.

**Date**: October 8, 2025
**Total Records**: 135,078 across 9 tables
**Vector Dimension**: 2048 (Jina Embeddings v4)
**Total Columns**: 122 across all tables

## ✅ Completed Work

### 1. Data Validation ✅
- **All data files verified** in `/srv/luris/be/graphrag-service/data/`
- **Embeddings validated**: All 2048-dimensional vectors normalized
- **Total file size**: ~5.2 GB

**Validation Report** (`/srv/luris/be/graphrag-service/data/validation_report.json`):
- ✅ nodes: 10,000 records with embeddings
- ✅ chunks: 25,000 records with embeddings
- ✅ enhanced_contextual_chunks: 25,000 records with embeddings
- ✅ communities: 500 records with embeddings
- ✅ reports: 200 records with embeddings
- ✅ document_registry: 100 records
- ✅ edges: 20,000 records
- ✅ node_communities: 29,978 records
- ✅ text_units: 25,000 records

### 2. Database Schema Analysis ✅
Using MCP Supabase tools, confirmed:
- All 9 target tables exist in `graph` schema
- Vector columns properly configured for 2048 dimensions
- Foreign key constraints mapped correctly
- RLS policies: Currently disabled (as expected for bulk import)

### 3. Upload Script Created ✅
**Location**: `/srv/luris/be/graphrag-service/scripts/upload_to_database.py`

**Features**:
- Batch processing with configurable batch size
- Foreign key constraint-aware upload order
- Vector embedding handling (2048-dim)
- Progress tracking and logging
- Error recovery and retry logic
- Test mode for validation
- Database verification after upload

**Upload Order** (respects FK constraints):
1. document_registry
2. nodes
3. communities
4. edges
5. node_communities
6. chunks
7. enhanced_contextual_chunks
8. text_units
9. reports

## ⚠️ Issue Encountered

### PostgREST Schema Cache Problem

**Error**: `Could not find the 'case_id' column of 'graph_document_registry' in the schema cache`

**Root Cause**:
- Supabase's PostgREST layer caches schema metadata
- Recently added columns (`case_id`, `client_id`) exist in PostgreSQL but not in PostgREST's cache
- This is a known Supabase limitation (PGRST204 error)

**Evidence**:
- MCP tools show columns exist ✅
- Direct PostgreSQL queries work ✅
- REST API (PostgREST) fails ❌

## 🔧 Recommended Solutions

### Option 1: MCP-Based Upload (RECOMMENDED)

Use Claude Code's MCP Supabase tools directly for batch inserts. These bypass PostgREST entirely.

**Advantages**:
- ✅ No schema cache issues
- ✅ Direct PostgreSQL access
- ✅ Works with ALL columns including new ones
- ✅ Proper vector handling built-in
- ✅ Transaction support

**Implementation**:
```python
# Use MCP apply_migration for bulk inserts
await mcp__supabase__execute_sql(query="""
    INSERT INTO graph.document_registry (document_id, title, document_type, ...)
    VALUES (...), (...), (...)
""")
```

**Next Steps**:
1. Create Python script that uses MCP via subprocess
2. Or manually batch insert via Claude Code MCP interface
3. Process ~500 records per batch to avoid timeout

### Option 2: Direct PostgreSQL Connection

Use `psycopg2` to connect directly to Supabase PostgreSQL database.

**Advantages**:
- ✅ Bypasses PostgREST completely
- ✅ Full PostgreSQL feature support
- ✅ Fast bulk inserts via `COPY` command

**Requirements**:
- Database password (not just API key)
- Connection pooler access
- Install: `pip install psycopg2-binary`

**Script Enhancement** (ALREADY ADDED):
The upload script now supports direct SQL mode:
```bash
USE_DIRECT_SQL=true python scripts/upload_to_database.py
```

**Configuration needed**:
```bash
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.PROJECT_ID.supabase.co:5432/postgres"
# OR
export SUPABASE_DB_PASSWORD="your-database-password"
```

### Option 3: PostgREST Schema Refresh

Refresh Supabase's schema cache via Admin API.

**Advantages**:
- ✅ Fixes root cause
- ✅ Enables REST API usage

**Disadvantages**:
- ❌ Requires Supabase project admin access
- ❌ May take time to propagate

**Implementation**:
```bash
curl -X POST \
  'https://tqfshsnwyhfnkchaiudg.supabase.co/rest/v1/rpc/pgrst_reload_schema' \
  -H "apikey: YOUR_SERVICE_KEY" \
  -H "Authorization: Bearer YOUR_SERVICE_KEY"
```

### Option 4: Migration-Based Approach

Use Supabase migrations to insert data.

**Advantages**:
- ✅ Version controlled
- ✅ Repeatable
- ✅ No cache issues

**Disadvantages**:
- ❌ Migrations should be for schema, not data
- ❌ Large data files in migrations are anti-pattern

## 📈 Performance Estimates

### Upload Time Projections

**Assumptions**:
- Batch size: 500 records
- Average latency: 2s per batch
- Total batches: ~270

**Estimated Total Time**:
- Optimistic: 9-10 minutes
- Realistic: 15-20 minutes
- Conservative: 25-30 minutes

**Breakdown by Table**:
| Table | Records | Batches | Est. Time |
|-------|---------|---------|-----------|
| document_registry | 100 | 1 | 2s |
| nodes | 10,000 | 20 | 40s |
| communities | 500 | 1 | 2s |
| edges | 20,000 | 40 | 80s |
| node_communities | 29,978 | 60 | 120s |
| chunks | 25,000 | 50 | 100s |
| enhanced_contextual_chunks | 25,000 | 50 | 100s |
| text_units | 25,000 | 50 | 100s |
| reports | 200 | 1 | 2s |

## 🎯 Recommended Action Plan

### Phase 1: Test Upload (Option 1 - MCP)
1. Use Claude Code with MCP to insert 10 test records per table
2. Verify foreign key constraints work
3. Validate vector embeddings inserted correctly
4. Confirm data integrity

### Phase 2: Batch Upload Script
1. Enhance Python script to use MCP via subprocess
2. OR get database password for direct psycopg2 connection
3. Run full upload with monitoring
4. Track progress and errors

### Phase 3: Verification
1. Run row count queries on all tables
2. Verify foreign key integrity
3. Test vector similarity search
4. Validate GraphRAG functionality

## 📁 File Locations

**Data Files**: `/srv/luris/be/graphrag-service/data/`
- document_registry.json (61 KB)
- nodes.json (560 MB)
- communities.json (29 MB)
- edges.json (14 MB)
- node_communities.json (6.9 MB)
- chunks.json (1.4 GB)
- enhanced_contextual_chunks.json (1.4 GB)
- text_units.json (41 MB)
- reports.json (12 MB)

**Upload Script**: `/srv/luris/be/graphrag-service/scripts/upload_to_database.py`

**Validation Report**: `/srv/luris/be/graphrag-service/data/validation_report.json`

## 🚀 Quick Start

### Test Mode (10 records per table):
```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate
python scripts/upload_to_database.py --test
```

### Full Upload (with database password):
```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate
export DATABASE_URL="your-connection-string"
USE_DIRECT_SQL=true python scripts/upload_to_database.py
```

### Custom Batch Size:
```bash
python scripts/upload_to_database.py --batch-size 1000
```

### Skip Existing Tables:
```bash
python scripts/upload_to_database.py --skip-if-exists
```

## 📝 Notes

1. **Vector Handling**: All vector embeddings are 2048-dimensional (Jina v4)
2. **UUID Generation**: PostgreSQL auto-generates UUIDs - synthetic `id` fields are removed
3. **Timestamps**: ISO format timestamps are preserved from synthetic data
4. **Foreign Keys**: Upload order strictly follows dependency graph
5. **Error Recovery**: Circuit breaker prevents cascade failures

## ✅ Success Criteria

Upload is successful when:
- [ ] All 135,078 records inserted across 9 tables
- [ ] Row counts match expected values
- [ ] Foreign key constraints validated
- [ ] Vector similarity search returns results
- [ ] GraphRAG queries functional
- [ ] No orphaned records

## 🔍 Troubleshooting

**If upload fails**:
1. Check error log in script output
2. Verify database connection
3. Ensure all foreign key dependencies uploaded first
4. Check for constraint violations
5. Review slow query logs

**Common Issues**:
- Connection timeouts → Reduce batch size
- Vector errors → Validate dimension = 2048
- FK violations → Check upload order
- Out of memory → Process smaller batches

---

**Status**: Ready for execution pending decision on upload method (MCP vs direct PostgreSQL)

**Recommendation**: Use MCP-based approach (Option 1) for guaranteed compatibility
