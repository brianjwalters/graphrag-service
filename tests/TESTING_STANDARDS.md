# GraphRAG Service Testing Standards

## Overview
This document defines the testing standards for the GraphRAG Service. All tests MUST follow these standards to ensure consistency and comprehensive coverage of the graph construction pipeline.

## Standard Test Document
- **Primary**: `/srv/luris/be/tests/docs/Rahimi.pdf`
- **Secondary**: Legal documents in `/srv/luris/be/tests/docs/`

## Required Test Result Structure

All GraphRAG tests MUST generate results in the exact JSON structure defined in:
`/srv/luris/be/AGENT_DEFINITIONS.md` - "Standardized Testing Requirements" section

## Test Execution Procedure

### 1. Environment Setup
```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate
```

### 2. Service Health Check
```bash
# Check all required services
curl -s http://localhost:8000/api/v1/health | jq  # Document processing
curl -s http://localhost:8007/api/v1/health | jq  # Entity extraction
curl -s http://localhost:8010/api/v1/health | jq  # GraphRAG
```

### 3. Run Standard Test
```bash
python tests/result_generator.py --mode FULL_GRAPHRAG --save --example
```

### 4. Run Comprehensive Pipeline Test
```bash
python tests/test_graphrag_comprehensive.py
```

## GraphRAG Modes

### FULL_GRAPHRAG
- Complete Microsoft GraphRAG implementation
- Entity extraction via AI-enhanced mode
- Full deduplication with 0.85 similarity threshold
- Leiden community detection (resolution 1.0, min size 3)
- AI-generated community summaries
- **Cost**: ~$0.10-0.20 per document
- **Use Case**: High-value documents requiring maximum accuracy

### LAZY_GRAPHRAG
- 99.9% cost reduction using NLP-based extraction
- SpaCy NER for entity extraction
- On-demand community summary generation
- Summaries only generated when relevance > 0.7
- Louvain community detection (no LLM cost)
- **Cost**: ~$0.0001-0.001 per document
- **Use Case**: Bulk processing, initial analysis

### HYBRID_MODE
- Intelligent mode selection based on document importance
- Combines FULL and LAZY approaches
- Optimizes for cost while maintaining quality
- **Default mode for production systems**
- **Use Case**: Mixed document sets with varying importance

## Pipeline Stages Testing

### 1. Document Upload
**Expected Metrics:**
- Duration: < 2000ms for PDF under 10MB
- Success rate: > 99%
- File size tracking: Required

### 2. Markdown Conversion
**Expected Metrics:**
- Duration: < 3000ms
- Content preservation: > 95%
- Table extraction accuracy: > 90%

### 3. Chunking
**Expected Metrics:**
- Duration: < 1000ms per MB
- Average chunk size: 500-1000 tokens
- Overlap handling: Proper context preservation

### 4. Entity Extraction
**Expected Metrics:**
- Duration: < 5000ms (AI mode), < 1000ms (regex)
- Entity count: > 0 for legal documents
- Citation extraction: > 90% accuracy

### 5. Embedding Generation
**Expected Metrics:**
- Duration: < 100ms per chunk
- Dimensions: 2048 (Jina v4)
- Coverage: 100% of chunks

### 6. Graph Construction
**Expected Metrics:**
- Duration: < 10000ms for 1000 entities
- Node creation: 100% of entities
- Edge creation: Based on relationships
- Community detection: > 0 communities for connected graphs

## Graph Metrics Requirements

### Node Metrics
- **Total count**: Must match sum of types
- **Type distribution**: Entity, document, chunk, community
- **Centrality scores**: Calculate for all nodes
- **Validation**: No orphan nodes

### Edge Metrics
- **Total count**: Must match sum of types
- **Type distribution**: Track all relationship types
- **Weight distribution**: 0.0 to 1.0 range
- **Validation**: No duplicate edges

### Community Metrics
- **Algorithm**: Leiden (FULL) or Louvain (LAZY)
- **Minimum size**: 3 nodes
- **Modularity score**: > 0.3 for good clustering
- **Coverage**: > 60% of nodes in communities

## Query Performance Benchmarks

### Local Search
- **Target**: < 100ms response time
- **Success rate**: > 95%
- **Scope**: 1-hop entity neighborhood

### Global Search
- **Target**: < 500ms response time
- **Success rate**: > 90%
- **Scope**: Community-based search

### Hybrid Search
- **Target**: < 300ms response time
- **Success rate**: > 93%
- **Scope**: Combined vector + graph

### Graph Traversal
- **1-hop**: < 50ms
- **2-hop**: < 200ms
- **3-hop**: < 500ms

## Quality Metrics

### Entity Deduplication
- **Target reduction**: 20-40%
- **Similarity threshold**: 0.85
- **Method**: Vector similarity + type matching

### Graph Connectivity
- **Connected components**: Ideally 1 for single document
- **Average degree**: > 2.0 for well-connected graph
- **Largest component**: > 80% of nodes

### Data Completeness
- **Entities with embeddings**: > 95%
- **Chunks with context**: 100%
- **Nodes in communities**: > 60%

## Result Storage

### Naming Convention
- JSON: `graphrag_[YYYYMMDD_HHMMSS].json`
- Markdown: `graphrag_[YYYYMMDD_HHMMSS].md`
- Logs: `pipeline_log_[YYYYMMDD_HHMMSS].txt`

### Storage Location
All results MUST be saved to: `/srv/luris/be/graphrag-service/tests/results/`

## Validation Checklist

Before marking a test as complete, verify:
- [ ] All service health checks pass
- [ ] Result structure matches standard
- [ ] All pipeline stages completed
- [ ] Graph metrics calculated
- [ ] Query performance tested
- [ ] Quality metrics within targets
- [ ] Markdown report generated
- [ ] Results saved with timestamp
- [ ] Data flow visualization included

## Common Issues and Solutions

### Issue: Service Dependencies Not Running
```bash
# Start all required services
sudo systemctl start luris-document-processing
sudo systemctl start luris-entity-extraction
sudo systemctl start luris-graphrag
```

### Issue: Database Connection Failed
```bash
# Check Supabase credentials
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_KEY

# Test connection
python -c "from src.clients.supabase_client import SupabaseClient; client = SupabaseClient(); print('Connected')"
```

### Issue: Embedding Service Unavailable
```bash
# Check vLLM embeddings service
sudo systemctl status luris-vllm-embeddings
curl http://localhost:8081/health
```

### Issue: Community Detection Failing
- Check minimum community size setting (default: 3)
- Verify edge weights are properly set
- Ensure graph has sufficient connectivity

### Issue: Memory Errors During Graph Construction
- Reduce batch size for entity processing
- Implement pagination for large graphs
- Monitor with: `htop` or `nvidia-smi`

## Integration Testing

### Full Pipeline Test
```bash
# Test complete pipeline from document to graph
python tests/test_graphrag_comprehensive.py \
    --document /srv/luris/be/tests/docs/Rahimi.pdf \
    --mode FULL_GRAPHRAG \
    --save-results
```

### Batch Processing Test
```bash
# Test multiple documents
for doc in /srv/luris/be/tests/docs/*.pdf; do
    python tests/result_generator.py \
        --document "$doc" \
        --mode LAZY_GRAPHRAG \
        --save
done
```

### Performance Stress Test
```bash
# Test with large document set
python tests/performance_test.py \
    --documents 100 \
    --concurrent 5 \
    --mode HYBRID_MODE
```

## Database Tables Used

### Graph Schema Tables
- `graph.document_registry` - Document catalog
- `graph.enhanced_contextual_chunks` - Chunk storage
- `graph.nodes` - Graph nodes
- `graph.edges` - Graph edges
- `graph.entities` - Extracted entities
- `graph.communities` - Community detection results
- `graph.embeddings` - Vector embeddings (2048-dim)

### Validation Queries
```sql
-- Check node count
SELECT COUNT(*) FROM graph.nodes WHERE client_id = 'test_client';

-- Check edge count
SELECT COUNT(*) FROM graph.edges WHERE client_id = 'test_client';

-- Check community distribution
SELECT community_id, COUNT(*) as size 
FROM graph.node_communities 
GROUP BY community_id 
ORDER BY size DESC;
```

## Reporting Requirements

Every test report MUST include:
1. Executive summary with pass/fail status
2. Service health matrix
3. Pipeline stage execution times
4. Graph construction metrics
5. Community detection results
6. Query performance benchmarks
7. Data flow visualization
8. Quality metrics analysis
9. Recommendations for optimization

## Test Automation

### Continuous Integration
```yaml
# Example GitHub Actions workflow
- name: Run GraphRAG Tests
  run: |
    cd graphrag-service
    source venv/bin/activate
    python tests/result_generator.py --mode FULL_GRAPHRAG --save
    python tests/result_generator.py --mode LAZY_GRAPHRAG --save
    python tests/result_generator.py --mode HYBRID_MODE --save
```

### Scheduled Testing
```bash
# Cron job for daily testing
0 2 * * * cd /srv/luris/be/graphrag-service && ./tests/run_daily_tests.sh
```

## Contact

For questions about testing standards:
- Review: `/srv/luris/be/AGENT_DEFINITIONS.md`
- Check: `/srv/luris/be/CLAUDE.md`
- Service API: `graphrag-service/api.md`
- Technical Spec: `specs/graphrag-tech-spec-v5.md`