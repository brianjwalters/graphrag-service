# GraphRAG Service - API Parity Test Results

**Generated:** 2025-10-20 17:05:34
**Results File:** tests/sample_results.json

## Test Summary

- **Total Tests:** 27
- **Passed:** 25 (92.6%)
- **Failed:** 2
- **Skipped:** 0
- **Total Duration:** 14.31s

## Results by Category

| Test Category | Passed | Failed | Skipped | Time |
|---------------|--------|--------|---------|------|
| CRUD Validation | 4/4 | 0 | 0 | 0.3s |
| Cross-Schema Tests | 3/3 | 0 | 0 | 1.1s |
| Multi-Tenant Tests | 3/3 | 0 | 0 | 0.8s |
| Performance Tests | 3/4 | 1 | 0 | 8.9s |
| QueryBuilder Tests | 3/3 | 0 | 0 | 0.5s |
| SelectQueryBuilder Tests | 9/10 | 1 | 0 | 2.5s |

## Performance Metrics

| Operation | Count | Avg(ms) | Max(ms) | Status |
|-----------|-------|---------|---------|--------|
| SELECT law.documents | 12 | 45 | 120 | ✓ PASS |
| SELECT graph.nodes (1K) | 5 | 230 | 480 | ✓ PASS |
| SELECT graph.nodes (5K) | 2 | 1200 | 1850 | ⚠ WARNING |
| COUNT queries | 8 | 85 | 180 | ✓ PASS |
| Cross-schema joins | 3 | 340 | 520 | ✓ PASS |

## Data Quality Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Multi-tenant isolation | 100% validated | ✓ PASS |
| NULL handling | Correct | ✓ PASS |
| Large dataset (>1K) | 4 tests | ✓ PASS |
| Pagination accuracy | 100% | ✓ PASS |
| Overall test pass rate | 92.6% (25/27) | ✓ PASS |

## Failed Tests

### ✗ test_with_range_filter

- **Category:** SelectQueryBuilder Tests
- **Duration:** 0.456s
- **Error:** assert len(results) == 10

### ✗ test_pagination_large_dataset

- **Category:** Performance Tests
- **Duration:** 1.234s
- **Error:** raise TimeoutError('Query exceeded timeout')

## Overall Status

**✗ 2 TESTS FAILED**
