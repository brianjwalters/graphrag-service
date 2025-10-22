# GraphRAG Upload Optimization - Quick Start Guide

**CRITICAL**: Apply these optimizations BEFORE running the next upload

---

## 1. Environment Variable Configuration (IMMEDIATE ACTION)

Copy and paste these into your `.env` file or export before running upload:

```bash
# Critical Timeout Fixes (REQUIRED)
export SUPABASE_BATCH_OP_TIMEOUT=120        # Increased from 30s
export SUPABASE_VECTOR_OP_TIMEOUT=180       # Increased from 25s
export SUPABASE_GRAPH_TIMEOUT_MULT=2.5      # Increased from 1.5

# Connection Pool Expansion (REQUIRED)
export SUPABASE_MAX_CONNECTIONS=50          # Increased from 30

# Circuit Breaker Tuning (REQUIRED)
export SUPABASE_CB_FAILURE_THRESHOLD=20     # Increased from 5
export SUPABASE_CB_RECOVERY_TIMEOUT=180     # Increased from 60

# Retry Optimization (RECOMMENDED)
export SUPABASE_MAX_RETRIES=5               # Increased from 3
export SUPABASE_BACKOFF_MAX=60              # Increased from 30
```

---

## 2. Upload Script Command (IMMEDIATE ACTION)

Run upload with optimized batch sizes:

```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate

# For full upload (recommended configuration)
python scripts/upload_to_database.py --batch-size 2000

# For test mode (verify configuration)
python scripts/upload_to_database.py --batch-size 2000 --test
```

---

## 3. Expected Performance Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Upload Time | 45-60 min | 20-27 min | **55% faster** |
| Timeout Failures | 10-20% | <1% | **95% reduction** |
| Batch Count | 235 batches | 44 batches | **81% reduction** |
| Memory Usage | 6-8 GB | 4-6 GB | **25% reduction** |

---

## 4. Monitoring During Upload

Watch for these indicators of successful optimization:

```bash
# Monitor upload progress
tail -f /srv/luris/be/graphrag-service/upload.log

# Check for timeout errors (should be 0)
grep "timeout" /srv/luris/be/graphrag-service/upload.log

# Check circuit breaker status (should be closed)
grep "Circuit breaker" /srv/luris/be/graphrag-service/upload.log

# Monitor memory usage
watch -n 5 free -h
```

---

## 5. Troubleshooting

### Problem: Still Getting Timeouts

**Solution**: Increase timeout further
```bash
export SUPABASE_BATCH_OP_TIMEOUT=180
export SUPABASE_VECTOR_OP_TIMEOUT=240
```

### Problem: High Memory Usage (>12GB)

**Solution**: Reduce batch size
```bash
python scripts/upload_to_database.py --batch-size 1000
```

### Problem: Connection Pool Exhausted

**Solution**: Increase max connections
```bash
export SUPABASE_MAX_CONNECTIONS=75
```

### Problem: Circuit Breaker Opens

**Solution**: Check logs for actual error, increase threshold
```bash
export SUPABASE_CB_FAILURE_THRESHOLD=30
```

---

## 6. Table-Specific Batch Sizes (FUTURE OPTIMIZATION)

Modify `upload_to_database.py` to use optimal batch sizes per table:

```python
# Add to DatabaseUploader class
TABLE_BATCH_SIZES = {
    'chunks': 2000,                      # 2048-dim vectors
    'enhanced_contextual_chunks': 2000,  # 2048-dim vectors
    'nodes': 2500,                       # 2048-dim vectors
    'communities': 2500,                 # 2048-dim vectors
    'reports': 2000,                     # 2048-dim vectors
    'text_units': 5000,                  # No vectors
    'edges': 5000,                       # No vectors
    'node_communities': 5000,            # No vectors
    'document_registry': 100             # Tiny table
}

def __init__(self, data_dir: str, batch_size: int = 2000, test_mode: bool = False):
    # Use table-specific batch sizes
    self.default_batch_size = batch_size
    self.table_batch_sizes = self.TABLE_BATCH_SIZES
```

Then update `upload_table()` to use table-specific sizes:

```python
async def upload_table(self, table: str, skip_if_exists: bool = False):
    # Get optimal batch size for this table
    batch_size = self.table_batch_sizes.get(table, self.default_batch_size)

    # ... rest of upload logic
```

---

## 7. Full Optimization Checklist

**Before Upload**:
- [ ] Set environment variables (timeout, connections, circuit breaker)
- [ ] Verify system has 8+ GB RAM available
- [ ] Check Supabase connection (`curl $SUPABASE_URL/rest/v1/`)
- [ ] Run test upload (`--test` flag) to validate configuration

**During Upload**:
- [ ] Monitor timeout errors (should be 0%)
- [ ] Monitor memory usage (should be <80%)
- [ ] Monitor batch completion rate
- [ ] Watch for circuit breaker warnings

**After Upload**:
- [ ] Verify record counts match expected
- [ ] Check upload success rate (should be >99%)
- [ ] Review error logs for any issues
- [ ] Document actual upload time for future reference

---

## 8. Quick Reference: Upload Performance Targets

| Table | Records | Optimal Batch | Expected Time | Timeout Threshold |
|-------|---------|---------------|---------------|------------------|
| chunks | 25,000 | 2,000 | 10-11 min | 120s |
| enhanced_contextual_chunks | 25,000 | 2,000 | 10-11 min | 120s |
| nodes | 10,000 | 2,500 | 3 min | 120s |
| text_units | 25,000 | 5,000 | <1 min | 30s |
| edges | 15,000 | 5,000 | <1 min | 30s |
| communities | 5,000 | 2,500 | 1-2 min | 120s |
| reports | 2,000 | 2,000 | <1 min | 120s |
| node_communities | 10,000 | 5,000 | <1 min | 30s |
| document_registry | 100 | 100 | <1 min | 10s |

**Total Expected Time**: 25-30 minutes (with optimized configuration)

---

## 9. Emergency Rollback

If upload fails catastrophically:

```bash
# Stop upload immediately
Ctrl+C

# Connect to Supabase
psql $DATABASE_URL

# Delete records from failed upload (adjust timestamp)
DELETE FROM graph.chunks WHERE created_at > '2025-10-08T20:00:00Z';
DELETE FROM graph.enhanced_contextual_chunks WHERE created_at > '2025-10-08T20:00:00Z';
DELETE FROM graph.nodes WHERE created_at > '2025-10-08T20:00:00Z';
-- ... repeat for all tables

# Verify cleanup
SELECT COUNT(*) FROM graph.chunks;
```

---

## 10. Next Steps After Successful Upload

1. **Document actual performance**:
   - Upload time per table
   - Success rate
   - Any errors encountered

2. **Review optimization opportunities**:
   - Consider binary vector encoding (70% network reduction)
   - Evaluate PostgreSQL COPY command (3-5× faster)
   - Assess parallel table upload feasibility

3. **Plan for production scale**:
   - California Supreme Court: 500K records
   - All state courts: 25M records
   - Federal + state courts: 75M records

---

**For detailed analysis, see**: `SUPABASE_CLIENT_PERFORMANCE_ANALYSIS.md`

**Report Date**: 2025-10-08
**Contact**: Performance Engineering Team
