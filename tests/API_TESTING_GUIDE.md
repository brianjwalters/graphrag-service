# API Parity Testing Guide

Complete guide for testing the fluent API implementation with real database data from the GraphRAG Service.

**Version**: 1.0.0
**Last Updated**: 2025-10-20
**Status**: ✅ Production-ready testing framework

---

## Table of Contents

1. [Overview](#overview)
2. [Test Data Sources](#test-data-sources)
3. [Writing Tests](#writing-tests)
4. [Running Tests](#running-tests)
5. [Understanding Results](#understanding-results)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This guide explains how to test the new QueryBuilder fluent API using real production data from the GraphRAG Service database. The fluent API provides a chainable, builder-pattern interface while maintaining full feature parity with the traditional SupabaseClient.

### What is the Fluent API?

**Traditional API** (direct method calls):
```python
result = await client.get(
    table="law.documents",
    filters={"document_type": "opinion", "status": "published"},
    limit=100,
    order_by="created_at"
)
```

**Fluent API** (chainable builder pattern):
```python
result = await client.schema('law').table('documents') \
    .select('*') \
    .eq('document_type', 'opinion') \
    .eq('status', 'published') \
    .order('created_at', desc=True) \
    .limit(100) \
    .execute()
```

### Why Test with Real Data?

- ✅ **Validates actual behavior** on production data structures
- ✅ **Catches edge cases** not found in synthetic test data
- ✅ **Performance testing** with realistic data volumes (15K+ documents, 141K+ nodes)
- ✅ **Schema compatibility** ensures API works across law/client/graph schemas
- ✅ **Data safety** confirms read-only operations don't modify production data

---

## Test Data Sources

### Law Schema (Primary Test Data) ✅

**Available Data**:
```
law.documents: 15,001 legal documents
law.entities: 59,919 extracted legal entities
```

**Document Types**:
- Court opinions
- Statutes
- Regulations
- Case law
- Legal briefs

**Use Cases**:
- ✅ Core API functionality testing
- ✅ Document filtering and search
- ✅ Entity extraction validation
- ✅ Real-world data validation
- ✅ Citation parsing and validation

**Example Queries**:
```python
# Get legal opinions
docs = await client.schema('law').table('documents') \
    .select('*') \
    .eq('document_type', 'opinion') \
    .limit(100) \
    .execute()

# Get high-confidence entities
entities = await client.schema('law').table('entities') \
    .select('*') \
    .gte('confidence_score', 0.8) \
    .limit(500) \
    .execute()
```

### Graph Schema (Performance Test Data) ✅

**Available Data**:
```
graph.nodes: 141,000 nodes (entities + chunks)
graph.edges: 81,974 relationships
graph.communities: 1,000 detected communities
graph.chunks: 30,000 document chunks
graph.document_registry: 1,030 documents tracked
```

**Characteristics**:
- ⚠️ **Synthetic test data** (not production-representative)
- ✅ **Large volume** sufficient for performance testing
- ✅ **Complete graph structure** (nodes, edges, communities)

**Use Cases**:
- ✅ Large dataset pagination (141K nodes)
- ✅ Performance stress testing
- ✅ Graph traversal operations
- ✅ Community detection validation
- ❌ NOT suitable for case_id/client_id filtering (columns not exposed)

**Example Queries**:
```python
# Test pagination with large dataset
nodes = await client.schema('graph').table('nodes') \
    .select('*') \
    .limit(1000) \
    .offset(5000) \
    .execute()

# Query communities
communities = await client.schema('graph').table('communities') \
    .select('*') \
    .gte('node_count', 10) \
    .order('coherence_score', desc=True) \
    .limit(50) \
    .execute()
```

### Client Schema (Limited Data) ⚠️

**Available Data**:
```
client.cases: 50 case records
client.documents: 0 documents (empty)
client.entities: 0 entities (empty)
```

**Use Cases**:
- ⚠️ **Limited to case management** operations only
- ❌ Cannot test document/entity operations (no data)
- ✅ Can test case filtering and metadata queries

**Example Queries**:
```python
# Query cases only
cases = await client.schema('client').table('cases') \
    .select('*') \
    .eq('status', 'active') \
    .limit(50) \
    .execute()
```

### Recommended Test Data Strategy

**Priority 1: Law Schema** (Core Functionality)
- Use for all standard API tests
- Real legal data ensures production-readiness
- 15K documents + 60K entities = substantial test coverage

**Priority 2: Graph Schema** (Performance)
- Use for pagination and large dataset tests
- 141K nodes ideal for stress testing
- Validate query performance under load

**Priority 3: Client Schema** (Limited)
- Use only for case management tests
- Need to upload test documents for full testing

---

## Writing Tests

### Test Structure Template

```python
"""
Test module description.

This test validates [specific functionality] using [data source].
"""

import pytest
import asyncio
from src.clients.supabase_client import create_supabase_client


class TestFluentAPI:
    """Fluent API test suite"""

    @pytest.fixture
    async def client(self):
        """Create test client with service_role access"""
        client = create_supabase_client(
            service_name="test",
            use_service_role=True  # Bypass RLS for testing
        )
        yield client
        # Cleanup if needed


    @pytest.mark.asyncio
    async def test_basic_select(self, client):
        """Test basic SELECT with LIMIT"""
        result = await client.schema('law').table('documents') \
            .select('*') \
            .limit(10) \
            .execute()

        assert result.data is not None
        assert len(result.data) <= 10
        assert len(result.data) > 0  # Assumes data exists


    @pytest.mark.asyncio
    async def test_filtered_select(self, client):
        """Test SELECT with equality filter"""
        result = await client.schema('law').table('documents') \
            .select('*') \
            .eq('document_type', 'opinion') \
            .limit(100) \
            .execute()

        assert result.data is not None
        for doc in result.data:
            assert doc['document_type'] == 'opinion'


    @pytest.mark.asyncio
    async def test_pagination(self, client):
        """Test pagination with LIMIT and OFFSET"""
        page_size = 100
        page_1 = await client.schema('law').table('documents') \
            .select('*') \
            .limit(page_size) \
            .offset(0) \
            .execute()

        page_2 = await client.schema('law').table('documents') \
            .select('*') \
            .limit(page_size) \
            .offset(page_size) \
            .execute()

        assert len(page_1.data) == page_size
        assert len(page_2.data) <= page_size
        # Ensure different pages
        assert page_1.data[0]['document_id'] != page_2.data[0]['document_id']


    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_large_dataset_performance(self, client):
        """Test performance with large result set"""
        import time

        start = time.time()
        result = await client.schema('graph').table('nodes') \
            .select('*') \
            .limit(5000) \
            .execute()
        elapsed = time.time() - start

        assert result.data is not None
        assert len(result.data) == 5000
        assert elapsed < 1.0  # Should complete in under 1 second
```

### Test Categories

#### 1. QueryBuilder Tests (Schema/Table Selection)

```python
@pytest.mark.asyncio
async def test_schema_selection(self, client):
    """Test schema selection with .schema()"""
    # Law schema
    law_result = await client.schema('law').table('documents') \
        .select('*').limit(5).execute()
    assert law_result.data is not None

    # Graph schema
    graph_result = await client.schema('graph').table('nodes') \
        .select('*').limit(5).execute()
    assert graph_result.data is not None

    # Client schema
    client_result = await client.schema('client').table('cases') \
        .select('*').limit(5).execute()
    assert client_result.data is not None
```

#### 2. SelectQueryBuilder Tests (Filters/Modifiers)

```python
@pytest.mark.asyncio
async def test_equality_filter(self, client):
    """Test .eq() equality filter"""
    result = await client.schema('law').table('documents') \
        .select('*') \
        .eq('document_type', 'opinion') \
        .limit(100) \
        .execute()

    for doc in result.data:
        assert doc['document_type'] == 'opinion'


@pytest.mark.asyncio
async def test_range_filters(self, client):
    """Test .gte() and .lte() range filters"""
    result = await client.schema('law').table('entities') \
        .select('*') \
        .gte('confidence_score', 0.8) \
        .lte('confidence_score', 1.0) \
        .limit(500) \
        .execute()

    for entity in result.data:
        score = entity['confidence_score']
        assert 0.8 <= score <= 1.0


@pytest.mark.asyncio
async def test_ordering(self, client):
    """Test .order() sorting"""
    result = await client.schema('graph').table('communities') \
        .select('*') \
        .order('node_count', desc=True) \
        .limit(50) \
        .execute()

    # Verify descending order
    counts = [c['node_count'] for c in result.data]
    assert counts == sorted(counts, reverse=True)


@pytest.mark.asyncio
async def test_count_query(self, client):
    """Test count operation"""
    result = await client.schema('law').table('documents') \
        .select('*', count='exact') \
        .eq('document_type', 'opinion') \
        .execute()

    assert result.count is not None
    assert result.count > 0
```

#### 3. Cross-Schema Tests

```python
@pytest.mark.asyncio
async def test_cross_schema_queries(self, client):
    """Test queries across multiple schemas"""
    # Law schema query
    law_docs = await client.schema('law').table('documents') \
        .select('*').limit(10).execute()

    # Graph schema query
    graph_nodes = await client.schema('graph').table('nodes') \
        .select('*').limit(10).execute()

    # Both should succeed
    assert len(law_docs.data) > 0
    assert len(graph_nodes.data) > 0
```

#### 4. Performance Tests

```python
@pytest.mark.asyncio
@pytest.mark.performance
async def test_pagination_performance(self, client):
    """Test pagination efficiency on large dataset"""
    import time

    page_size = 1000
    total_pages = 5

    timings = []
    for page in range(total_pages):
        start = time.time()
        result = await client.schema('graph').table('nodes') \
            .select('*') \
            .limit(page_size) \
            .offset(page * page_size) \
            .execute()
        elapsed = time.time() - start
        timings.append(elapsed)

        assert len(result.data) == page_size

    # Average time should be reasonable
    avg_time = sum(timings) / len(timings)
    assert avg_time < 0.5  # Less than 500ms per page
```

### Best Practices for Test Writing

#### 1. Always Use LIMIT for Safety

```python
# ✅ CORRECT - Always limit results
result = await client.table('documents').select('*').limit(100).execute()

# ❌ WRONG - Can return 15K+ records
result = await client.table('documents').select('*').execute()
```

#### 2. Use Appropriate Limit Values

```python
# Safe limit values by table
SAFE_LIMITS = {
    "law_documents": 1000,      # 15K total
    "law_entities": 500,        # 60K total
    "graph_nodes": 5000,        # 141K total
    "graph_edges": 1000,        # 82K total
    "graph_communities": 100    # 1K total
}

# Example usage
result = await client.schema('law').table('documents') \
    .select('*') \
    .limit(SAFE_LIMITS["law_documents"]) \
    .execute()
```

#### 3. Validate Result Structure

```python
@pytest.mark.asyncio
async def test_result_structure(self, client):
    """Validate result object structure"""
    result = await client.schema('law').table('documents') \
        .select('*').limit(5).execute()

    # Check result object
    assert result.data is not None
    assert isinstance(result.data, list)

    # Check first record structure
    if len(result.data) > 0:
        doc = result.data[0]
        assert 'document_id' in doc
        assert 'document_type' in doc
        assert 'created_at' in doc
```

#### 4. Test Error Handling

```python
@pytest.mark.asyncio
async def test_invalid_table_error(self, client):
    """Test error handling for invalid table"""
    with pytest.raises(Exception):
        await client.schema('law').table('nonexistent_table') \
            .select('*').limit(10).execute()


@pytest.mark.asyncio
async def test_invalid_filter_error(self, client):
    """Test error handling for invalid filter"""
    with pytest.raises(Exception):
        await client.schema('law').table('documents') \
            .select('*') \
            .eq('nonexistent_column', 'value') \
            .execute()
```

#### 5. Use Fixtures for Reusable Setup

```python
@pytest.fixture
async def sample_documents(self, client):
    """Fixture to get sample documents for testing"""
    result = await client.schema('law').table('documents') \
        .select('*').limit(10).execute()
    return result.data


@pytest.mark.asyncio
async def test_with_fixture(self, sample_documents):
    """Test using fixture data"""
    assert len(sample_documents) == 10
    assert all('document_id' in doc for doc in sample_documents)
```

---

## Running Tests

### Basic Test Execution

```bash
# Navigate to service directory
cd /srv/luris/be/graphrag-service

# Activate virtual environment (MANDATORY)
source venv/bin/activate

# Verify venv activation
which python  # Should show: .../venv/bin/python

# Run all tests
pytest tests/test_fluent_api_comprehensive.py -v

# Run specific test class
pytest tests/test_fluent_api_comprehensive.py::TestQueryBuilder -v

# Run specific test method
pytest tests/test_fluent_api_comprehensive.py::TestQueryBuilder::test_schema_selection -v
```

### Test Discovery

```bash
# List all tests without running
pytest tests/ --collect-only

# List tests matching pattern
pytest tests/ -k "fluent" --collect-only

# Show test markers
pytest tests/ --markers
```

### Running Specific Test Categories

```bash
# Run only performance tests
pytest tests/ -v -m performance

# Run all except performance tests
pytest tests/ -v -m "not performance"

# Run multiple markers
pytest tests/ -v -m "fluent or api"
```

### Coverage Reporting

```bash
# Basic coverage
pytest tests/test_fluent_api_comprehensive.py -v \
  --cov=src.clients.supabase_client

# HTML coverage report
pytest tests/test_fluent_api_comprehensive.py -v \
  --cov=src.clients.supabase_client \
  --cov-report=html

# Open report in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Performance Testing

```bash
# Run with timing information
pytest tests/test_fluent_api_comprehensive.py -v --durations=20

# Run with detailed output (timing, print statements)
pytest tests/test_fluent_api_comprehensive.py -v -s --durations=20

# Run performance tests only
pytest tests/test_fluent_api_comprehensive.py -v -m performance -s
```

### Debugging Failed Tests

```bash
# Stop on first failure
pytest tests/test_fluent_api_comprehensive.py -v -x

# Enter debugger on failure
pytest tests/test_fluent_api_comprehensive.py -v --pdb

# Show full traceback
pytest tests/test_fluent_api_comprehensive.py -v --tb=long

# Show local variables in traceback
pytest tests/test_fluent_api_comprehensive.py -v --tb=short -l
```

---

## Understanding Results

### Test Output Format

```
tests/test_fluent_api_comprehensive.py::TestQueryBuilder::test_schema_selection PASSED    [10%]
tests/test_fluent_api_comprehensive.py::TestQueryBuilder::test_table_selection PASSED     [20%]
tests/test_fluent_api_comprehensive.py::TestSelectQueryBuilder::test_eq_filter PASSED     [30%]
tests/test_fluent_api_comprehensive.py::TestSelectQueryBuilder::test_gte_filter PASSED    [40%]
...

================================ 83 passed in 45.23s ================================
```

### Performance Metrics

```
============================== slowest 10 durations ==============================
2.45s call     tests/test_fluent_api_comprehensive.py::test_large_dataset
0.85s call     tests/test_fluent_api_comprehensive.py::test_pagination
0.42s call     tests/test_fluent_api_comprehensive.py::test_complex_filter
0.28s call     tests/test_fluent_api_comprehensive.py::test_count_query
...
```

### Coverage Report

```
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
src/clients/supabase_client.py             245     12    95%   120-125, 340-342
src/clients/query_builder.py              180      5    97%   85, 156-158
src/clients/select_query_builder.py       220      8    96%   45, 190-195
-----------------------------------------------------------------------
TOTAL                                      645     25    96%
```

### Test Result Summary

After running tests, check `tests/results/api_parity_real_data_report.md` for:

1. **Pass/Fail Summary**: Overall test success rate
2. **Performance Metrics**: Query execution times
3. **Issues Found**: Failing tests and errors
4. **Recommendations**: Suggested improvements

---

## Best Practices

### 1. Always Activate venv First

```bash
# ✅ CORRECT
cd /srv/luris/be/graphrag-service
source venv/bin/activate
pytest tests/ -v

# ❌ WRONG - Will fail with import errors
cd /srv/luris/be/graphrag-service
pytest tests/ -v  # Missing venv activation!
```

### 2. Use Service Role for Testing

```python
# ✅ CORRECT - Bypass RLS for testing
client = create_supabase_client(
    service_name="test",
    use_service_role=True
)

# ⚠️ LIMITED - May fail on some tables due to RLS
client = create_supabase_client(
    service_name="test",
    use_service_role=False
)
```

### 3. Always Use LIMIT

```python
# ✅ CORRECT
result = await client.table('documents').select('*').limit(100).execute()

# ❌ DANGEROUS - Can return 15K+ records
result = await client.table('documents').select('*').execute()
```

### 4. Test with Multiple Data Sources

```python
# ✅ CORRECT - Test across schemas
@pytest.mark.asyncio
async def test_cross_schema(self, client):
    law_result = await client.schema('law').table('documents') \
        .select('*').limit(10).execute()

    graph_result = await client.schema('graph').table('nodes') \
        .select('*').limit(10).execute()

    assert len(law_result.data) > 0
    assert len(graph_result.data) > 0
```

### 5. Validate Result Structure

```python
# ✅ CORRECT - Check result structure
result = await client.table('documents').select('*').limit(5).execute()

assert result.data is not None
assert isinstance(result.data, list)
if len(result.data) > 0:
    assert 'document_id' in result.data[0]
```

### 6. Use Descriptive Test Names

```python
# ✅ CORRECT - Clear test purpose
async def test_select_law_documents_with_eq_filter_returns_filtered_results()

# ❌ POOR - Unclear purpose
async def test_query()
```

### 7. Organize Tests Logically

```python
class TestQueryBuilder:
    """Tests for QueryBuilder (schema/table selection)"""
    # Schema selection tests
    # Table selection tests


class TestSelectQueryBuilder:
    """Tests for SelectQueryBuilder (filters/modifiers)"""
    # Filter tests (.eq, .gte, .lte, etc.)
    # Modifier tests (.order, .limit, .offset)
    # Count tests


class TestCrossSchema:
    """Tests for cross-schema operations"""
    # Law schema tests
    # Graph schema tests
    # Client schema tests
```

---

## Troubleshooting

### Common Issues

#### Issue 1: ModuleNotFoundError

**Symptoms**:
```
ModuleNotFoundError: No module named 'src.clients.supabase_client'
```

**Solution**:
```bash
# Activate virtual environment
cd /srv/luris/be/graphrag-service
source venv/bin/activate

# Verify activation
which python  # Should show: .../venv/bin/python

# Run tests again
pytest tests/ -v
```

#### Issue 2: Database Connection Timeout

**Symptoms**:
```
TimeoutError: Database connection timed out after 30s
```

**Solution**:
```bash
# Check Supabase service health
curl -I https://your-project.supabase.co/rest/v1/
# Expected: HTTP/2 200 OK

# Check network connectivity
ping supabase.co

# Verify environment variables
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY
```

#### Issue 3: Permission Denied Errors

**Symptoms**:
```
PermissionError: Row Level Security policy violation
```

**Solution**:
```python
# Use service_role client to bypass RLS
client = create_supabase_client(
    service_name="test",
    use_service_role=True  # ✅ Bypass RLS
)
```

#### Issue 4: Tests Run Slowly

**Symptoms**: Tests take > 5 minutes to complete

**Solution**:
```python
# Reduce LIMIT values
# Before (slow)
result = await client.table('nodes').select('*').limit(50000).execute()

# After (fast)
result = await client.table('nodes').select('*').limit(1000).execute()
```

#### Issue 5: Memory Errors

**Symptoms**:
```
MemoryError: Unable to allocate array
```

**Solution**:
```python
# Use pagination for large datasets
page_size = 1000
for offset in range(0, 100000, page_size):
    result = await client.table('nodes') \
        .select('*') \
        .limit(page_size) \
        .offset(offset) \
        .execute()
    # Process result.data in chunks
```

### Performance Debugging

#### Slow Query Diagnosis

```python
import time

# Add timing to identify bottleneck
start = time.time()
result = await client.schema('graph').table('nodes') \
    .select('*').limit(5000).execute()
elapsed = time.time() - start

print(f"Query took {elapsed:.2f}s")
print(f"Records returned: {len(result.data)}")
print(f"Records per second: {len(result.data) / elapsed:.0f}")
```

**Expected Performance**:
- Small queries (10-100 records): < 50ms
- Medium queries (100-1000 records): 50-200ms
- Large queries (1000-5000 records): 200ms-1s

#### Memory Profiling

```python
import tracemalloc

# Profile memory usage
tracemalloc.start()

result = await client.table('nodes').select('*').limit(10000).execute()

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

tracemalloc.stop()
```

---

## Related Documentation

- **`results/README.md`**: Test results directory overview
- **`results/test_data_inventory.md`**: Complete database inventory (15K+ docs)
- **`results/QUICK_REFERENCE.md`**: Quick-start guide for test data
- **`/srv/luris/be/graphrag-service/api.md`**: GraphRAG Service API reference
- **`/srv/luris/be/CLAUDE.md`**: Project-wide development standards

---

**Last Updated**: 2025-10-20
**Status**: ✅ Production-ready testing guide
**Test Framework Version**: 1.0.0
