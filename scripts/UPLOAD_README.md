# GraphRAG Data Upload Script - Production Guide

## Overview

Production-grade script for uploading 135,078 GraphRAG records (including 60,700 2048-dimensional embeddings) to Supabase database using the enhanced SupabaseClient.

### Key Features

✅ **Batch Processing** - Configurable batch sizes (500-2000 records)
✅ **Checkpoint/Resume** - Resume from last successful checkpoint
✅ **Progress Tracking** - Real-time progress bar with ETA
✅ **Error Handling** - Comprehensive retry logic and error reporting
✅ **Data Validation** - Pre-upload validation of vectors and required fields
✅ **Memory Efficient** - Streaming processing for multi-GB files
✅ **Dry Run Mode** - Validate data without uploading
✅ **Test Mode** - Test with limited records before full upload

## Prerequisites

### Environment Variables

**Required:**
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_API_KEY="your-anon-key"
export SUPABASE_SERVICE_KEY="your-service-role-key"  # Required for admin operations
```

**Optional (Performance Tuning):**
```bash
export SUPABASE_OP_TIMEOUT=30
export SUPABASE_MAX_RETRIES=3
export SUPABASE_MAX_CONNECTIONS=30
export SUPABASE_BATCH_SIZE=500
export SUPABASE_BATCH_OP_TIMEOUT=30
export SUPABASE_VECTOR_OP_TIMEOUT=25
```

### Data Files

All JSON files must be in `/srv/luris/be/graphrag-service/data/`:

```
data/
├── document_registry.json (100 records)
├── nodes.json (10,000 records with embeddings)
├── communities.json (500 records with embeddings)
├── edges.json (20,000 records)
├── node_communities.json (29,978 records)
├── chunks.json (25,000 records with embeddings)
├── enhanced_contextual_chunks.json (25,000 records with embeddings)
├── text_units.json (25,000 records)
└── reports.json (200 records with embeddings)
```

**Total:** 135,078 records, 60,700 embeddings (2048 dimensions each)

## Usage

### 1. Basic Upload (Full Production Run)

```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate
python scripts/upload_via_supabase_client.py
```

**Expected Output:**
```
🚀 GraphRAG Data Upload Script
================================================================================
📁 Data directory: /srv/luris/be/graphrag-service/data
📦 Batch size: 500
🔄 Checkpoint interval: 5000
📊 Vector dimension: 2048

🔌 Connecting to Supabase...
✓ Connected to Supabase
  Primary client: service_role
  Max connections: 30

🚀 Starting upload process...
================================================================================

📊 Table: graph.document_registry
--------------------------------------------------------------------------------
📄 Loading document_registry.json... ✓ Loaded 100 records
🔍 Validating 100 records... ✓ All records valid
  [████████████████████████████████████████] 100.0% | 100/100 | 50 rec/s | ETA: 0:00:00 | Failed: 0 | Mem: 256MB
  ✓ Completed in 0:00:02
  ✓ Uploaded: 100 | Failed: 0 | Speed: 50 rec/s
```

### 2. Dry Run (Validation Only)

Test data validation without uploading:

```bash
python scripts/upload_via_supabase_client.py --dry-run
```

**Use Case:** Verify all JSON files are valid before production upload

### 3. Test Mode (Limited Records)

Upload a small subset for testing:

```bash
# Test with 100 records per table
python scripts/upload_via_supabase_client.py --test --limit 100

# Test with 500 records per table
python scripts/upload_via_supabase_client.py --test --limit 500
```

**Use Case:** Test upload pipeline before committing to full upload

### 4. Resume from Checkpoint

If upload is interrupted, resume from last checkpoint:

```bash
python scripts/upload_via_supabase_client.py --resume-from upload_checkpoint.json
```

**Use Case:** Network interruption, timeout, or manual stop (Ctrl+C)

### 5. Custom Batch Size

Optimize for your database performance:

```bash
# Small batches (safer, slower)
python scripts/upload_via_supabase_client.py --batch-size 250

# Large batches (faster, more memory)
python scripts/upload_via_supabase_client.py --batch-size 1000
```

**Recommendations:**
- **Small batches (250-500):** Better for unstable connections, limited memory
- **Large batches (1000-2000):** Faster upload with stable connection, more memory

### 6. Custom Data Directory

Specify alternate data location:

```bash
python scripts/upload_via_supabase_client.py --data-dir /path/to/data
```

## Upload Order (Foreign Key Dependencies)

The script uploads tables in this **required order** to respect foreign key constraints:

1. **graph.document_registry** (100 records) - Parent for chunks
2. **graph.nodes** (10,000 records + embeddings) - Parent for edges, communities
3. **graph.communities** (500 records + embeddings) - Parent for node_communities
4. **graph.edges** (20,000 records) - References nodes
5. **graph.node_communities** (29,978 records) - References nodes & communities
6. **graph.chunks** (25,000 records + embeddings) - References document_registry
7. **graph.enhanced_contextual_chunks** (25,000 records + embeddings) - Independent
8. **graph.text_units** (25,000 records) - References chunks
9. **graph.reports** (200 records + embeddings) - References communities & nodes

**⚠️ CRITICAL:** Do not change this order without reviewing foreign key constraints!

## Progress Tracking

### Real-Time Progress Bar

```
[████████████████████░░░░░░░░] 75.0% | 7,500/10,000 | 250 rec/s | ETA: 0:00:10 | Failed: 3 | Mem: 512MB
```

**Displays:**
- Visual progress bar
- Percentage complete
- Records uploaded / total
- Upload speed (records/second)
- Estimated time to completion
- Failed record count
- Memory usage

### Checkpoint System

Automatic checkpoints saved every **5,000 records**:

```json
{
  "graph.nodes": {
    "uploaded_count": 5000,
    "timestamp": "2025-10-08T22:30:15.123456",
    "stats": {
      "total_records": 10000,
      "uploaded_records": 5000,
      "failed_records": 0,
      "batches_processed": 10,
      "records_per_second": 125.5
    }
  }
}
```

**Resume Behavior:**
- Skips already-uploaded tables completely
- Resumes incomplete tables from last checkpoint
- Validates remaining records before upload

## Error Handling

### Retry Logic

**Automatic retries** for transient errors:
- **Network timeouts:** 3 retries with exponential backoff
- **Connection errors:** 3 retries with 2-4-8 second delays
- **Database locks:** 3 retries with jitter

**Non-retryable errors** (immediate failure):
- Data validation errors
- Foreign key constraint violations
- Schema errors
- Permission errors

### Error Report

Failed records are saved to `upload_errors.json`:

```json
{
  "timestamp": "2025-10-08T22:45:30.123456",
  "total_failed_records": 15,
  "tables_with_errors": ["graph.nodes", "graph.edges"],
  "failed_records": {
    "graph.nodes": [
      {"node_id": "node_123", "error": "Invalid vector dimension"}
    ],
    "graph.edges": [
      {"edge_id": "edge_456", "error": "Foreign key violation"}
    ]
  }
}
```

**Review failed records** and fix issues before re-uploading.

## Data Validation

### Pre-Upload Checks

✅ **Required Fields:** Validates all required columns exist
✅ **Vector Dimensions:** Ensures all embeddings are exactly 2048-dim
✅ **Foreign Keys:** Checks references to parent tables
✅ **Data Types:** Validates JSON structure and types
✅ **NULL Values:** Flags invalid NULL values in required fields

### Vector Validation

All embedding fields are validated for correct dimension:

| Table | Vector Field | Dimension | Count |
|-------|-------------|-----------|-------|
| graph.nodes | embedding | 2048 | 10,000 |
| graph.communities | summary_embedding | 2048 | 500 |
| graph.chunks | content_embedding | 2048 | 25,000 |
| graph.enhanced_contextual_chunks | vector | 2048 | 25,000 |
| graph.reports | report_embedding | 2048 | 200 |

**Total Embeddings:** 60,700 vectors × 2048 dimensions

## Performance Optimization

### Recommended Settings

**For Fast, Stable Networks:**
```bash
python scripts/upload_via_supabase_client.py \
  --batch-size 1000 \
  SUPABASE_MAX_CONNECTIONS=50 \
  SUPABASE_BATCH_OP_TIMEOUT=60
```

**For Slow or Unstable Networks:**
```bash
python scripts/upload_via_supabase_client.py \
  --batch-size 250 \
  SUPABASE_MAX_CONNECTIONS=20 \
  SUPABASE_BATCH_OP_TIMEOUT=120
```

### Memory Management

**Memory-Efficient Processing:**
- Loads one table at a time
- Streams large files (chunks.json = 1.4GB)
- Releases memory after each table
- Peak memory usage: ~500-800 MB

**Monitor Memory:**
```bash
# Watch memory during upload
watch -n 1 'ps aux | grep upload_via_supabase'
```

### Upload Speed Estimates

Based on batch size and network:

| Batch Size | Network | Speed | Total Time |
|-----------|---------|-------|-----------|
| 250 | Slow | 50 rec/s | ~45 min |
| 500 | Medium | 125 rec/s | ~18 min |
| 1000 | Fast | 250 rec/s | ~9 min |
| 2000 | Very Fast | 400 rec/s | ~6 min |

**Your actual speed will vary** based on:
- Network latency to Supabase
- Database load
- Vector indexing overhead
- Connection pool availability

## Summary Report

After upload completion, detailed report is displayed:

```
================================================================================
📊 UPLOAD SUMMARY REPORT
================================================================================

🎯 Overall Statistics:
  Total records processed: 135,078
  Successfully uploaded: 135,063
  Failed: 15
  Success rate: 99.99%
  Total duration: 0:15:23
  Average speed: 146 records/second

📋 Per-Table Statistics:
  Table                                    Records    Uploaded   Failed   Speed
  ---------------------------------------- ---------- ---------- -------- ------------
  graph.document_registry                  100        100        0        50 rec/s
  graph.nodes                              10,000     10,000     0        125 rec/s
  graph.communities                        500        500        0        100 rec/s
  graph.edges                              20,000     19,995     5        150 rec/s
  graph.node_communities                   29,978     29,978     0        200 rec/s
  graph.chunks                             25,000     25,000     0        120 rec/s
  graph.enhanced_contextual_chunks         25,000     25,000     0        130 rec/s
  graph.text_units                         25,000     24,990     10       140 rec/s
  graph.reports                            200        200        0        80 rec/s

💾 Memory Usage:
  Peak memory: 623 MB

🏥 Database Health:
  Operation count: 270
  Error rate: 0.04%
  Average latency: 0.123s
  Connection pool utilization: 42.3%

================================================================================
```

## Troubleshooting

### Common Issues

#### 1. Connection Timeout

**Error:** `asyncio.TimeoutError: Operation timed out after 30s`

**Solution:**
```bash
# Increase timeout
export SUPABASE_BATCH_OP_TIMEOUT=60
export SUPABASE_VECTOR_OP_TIMEOUT=45

# Reduce batch size
python scripts/upload_via_supabase_client.py --batch-size 250
```

#### 2. Foreign Key Violation

**Error:** `foreign key constraint "fk_edges_source_node_id" violated`

**Solution:**
- Ensure upload order is correct (script handles this automatically)
- Check that parent records exist in database
- Validate JSON data has correct foreign key values

#### 3. Vector Dimension Mismatch

**Error:** `Invalid vector dimension for embedding`

**Solution:**
```bash
# Run dry-run to validate all vectors
python scripts/upload_via_supabase_client.py --dry-run

# Check embeddings_metadata.json for model info
cat data/embeddings_metadata.json
```

#### 4. Memory Issues

**Error:** `MemoryError` or system slowdown

**Solution:**
```bash
# Reduce batch size
python scripts/upload_via_supabase_client.py --batch-size 100

# Close other applications
# Monitor memory: htop or top
```

#### 5. Permission Denied

**Error:** `permission denied for table graph.nodes`

**Solution:**
- Verify `SUPABASE_SERVICE_KEY` is set (not just API key)
- Ensure service role key has admin privileges
- Check RLS policies are disabled for graph schema

### Debug Mode

Enable verbose logging:

```bash
# Add debug prints to script
export PYTHONUNBUFFERED=1
python scripts/upload_via_supabase_client.py 2>&1 | tee upload.log
```

### Database Verification

After upload, verify data:

```bash
# Connect to Supabase and check counts
python -c "
from src.clients.supabase_client import create_admin_supabase_client
import asyncio

async def check():
    client = create_admin_supabase_client('verify')

    tables = [
        'graph.document_registry',
        'graph.nodes',
        'graph.communities',
        'graph.edges',
        'graph.node_communities',
        'graph.chunks',
        'graph.enhanced_contextual_chunks',
        'graph.text_units',
        'graph.reports'
    ]

    for table in tables:
        result = await client.get(table, limit=1, admin_operation=True)
        print(f'{table}: {len(result)} records (sample)')

    await client.close()

asyncio.run(check())
"
```

## Production Checklist

Before running full production upload:

- [ ] **Environment variables set** (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`)
- [ ] **All JSON files present** in `data/` directory
- [ ] **Dry run successful** (`--dry-run` shows no errors)
- [ ] **Test mode successful** (`--test --limit 100` completes)
- [ ] **Database connection verified** (can connect with SupabaseClient)
- [ ] **Sufficient disk space** for checkpoint files (~100 MB)
- [ ] **Sufficient memory** (at least 1 GB free)
- [ ] **Stable network connection** (upload takes 10-20 minutes)
- [ ] **Backup plan** (checkpoint files enable resume)

## Best Practices

### 1. Always Start with Dry Run

```bash
python scripts/upload_via_supabase_client.py --dry-run
```

Validates all data before committing to upload.

### 2. Test with Small Dataset First

```bash
python scripts/upload_via_supabase_client.py --test --limit 100
```

Ensures script works end-to-end before full run.

### 3. Monitor Progress

Keep terminal window visible to monitor:
- Upload speed
- Memory usage
- Failed record count
- ETA

### 4. Save Checkpoint Files

Don't delete `upload_checkpoint.json` until upload is fully complete.

### 5. Review Error Report

Check `upload_errors.json` for any failed records and fix issues.

### 6. Verify Database After Upload

Run verification queries to ensure data integrity:

```sql
-- Check record counts
SELECT 'nodes' AS table, COUNT(*) FROM graph.nodes
UNION ALL
SELECT 'edges', COUNT(*) FROM graph.edges
UNION ALL
SELECT 'communities', COUNT(*) FROM graph.communities;

-- Check embeddings
SELECT COUNT(*) FROM graph.nodes WHERE embedding IS NOT NULL;
SELECT COUNT(*) FROM graph.chunks WHERE content_embedding IS NOT NULL;

-- Check foreign key integrity
SELECT COUNT(*) FROM graph.edges e
WHERE NOT EXISTS (SELECT 1 FROM graph.nodes n WHERE n.node_id = e.source_node_id);
```

## Support

### Log Files

All output is displayed in terminal. Redirect to file for logging:

```bash
python scripts/upload_via_supabase_client.py 2>&1 | tee upload_$(date +%Y%m%d_%H%M%S).log
```

### Health Monitoring

Monitor Supabase health during upload:

```bash
# In separate terminal
watch -n 5 'curl -s http://localhost:8002/health | jq .'
```

### Circuit Breaker

The SupabaseClient includes circuit breaker protection:
- **Opens** after 5 consecutive failures
- **Recovers** after 60 seconds
- **Prevents** cascading failures

If circuit breaker opens, the script will pause and retry automatically.

## Next Steps

After successful upload:

1. **Verify Data Integrity:** Run database queries to check counts and relationships
2. **Test GraphRAG Queries:** Ensure embeddings work for similarity search
3. **Monitor Performance:** Check database performance with real queries
4. **Optimize Indexes:** Add indexes for frequently queried columns
5. **Enable RLS:** Set up Row Level Security policies if needed
6. **Backup Database:** Create backup after successful upload

## Reference

- **Script:** `/srv/luris/be/graphrag-service/scripts/upload_via_supabase_client.py`
- **Config:** `/srv/luris/be/graphrag-service/upload_config.json`
- **Data:** `/srv/luris/be/graphrag-service/data/`
- **SupabaseClient:** `/srv/luris/be/graphrag-service/src/clients/supabase_client.py`
- **Checkpoints:** `upload_checkpoint.json` (auto-generated)
- **Errors:** `upload_errors.json` (auto-generated if failures occur)

---

**Version:** 1.0.0
**Last Updated:** October 8, 2025
**Maintainer:** Luris Backend Engineering Team
