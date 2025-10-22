# API Parity Testing Report - Real Data Validation

**Report Generated**: `{TIMESTAMP}`
**Test Framework Version**: 1.0.0
**Database**: Supabase Production
**Test Environment**: GraphRAG Service

---

## Executive Summary

### Overall Results

| Metric | Value |
|--------|-------|
| **Total Tests** | `{TOTAL_TESTS}` |
| **Tests Passed** | `{TESTS_PASSED}` |
| **Tests Failed** | `{TESTS_FAILED}` |
| **Pass Rate** | `{PASS_RATE}%` |
| **Execution Time** | `{EXECUTION_TIME}` seconds |
| **Average Test Time** | `{AVG_TEST_TIME}` ms |

### Status

```
{STATUS_INDICATOR}
✅ PASS - All tests passed, API is production-ready
⚠️ PARTIAL - Some tests failed, review required
❌ FAIL - Critical tests failed, deployment blocked
```

**Current Status**: `{CURRENT_STATUS}`

---

## Test Category Breakdown

### Summary Table

| Test Category | Total | Passed | Failed | Pass Rate | Avg Time |
|--------------|-------|--------|--------|-----------|----------|
| QueryBuilder Tests | `{QB_TOTAL}` | `{QB_PASSED}` | `{QB_FAILED}` | `{QB_PASS_RATE}%` | `{QB_AVG_TIME}ms` |
| SelectQueryBuilder Tests | `{SQB_TOTAL}` | `{SQB_PASSED}` | `{SQB_FAILED}` | `{SQB_PASS_RATE}%` | `{SQB_AVG_TIME}ms` |
| Cross-Schema Tests | `{CS_TOTAL}` | `{CS_PASSED}` | `{CS_FAILED}` | `{CS_PASS_RATE}%` | `{CS_AVG_TIME}ms` |
| CRUD Validation | `{CRUD_TOTAL}` | `{CRUD_PASSED}` | `{CRUD_FAILED}` | `{CRUD_PASS_RATE}%` | `{CRUD_AVG_TIME}ms` |
| Performance Tests | `{PERF_TOTAL}` | `{PERF_PASSED}` | `{PERF_FAILED}` | `{PERF_PASS_RATE}%` | `{PERF_AVG_TIME}ms` |
| Multi-Tenant Tests | `{MT_TOTAL}` | `{MT_PASSED}` | `{MT_FAILED}` | `{MT_PASS_RATE}%` | `{MT_AVG_TIME}ms` |
| **TOTAL** | `{TOTAL_TESTS}` | `{TESTS_PASSED}` | `{TESTS_FAILED}` | `{PASS_RATE}%` | `{AVG_TEST_TIME}ms` |

---

## Test Category Details

### 1. QueryBuilder Tests (Schema/Table Selection)

**Purpose**: Validate schema and table selection with fluent syntax

**Test Cases**:
```
{QB_TEST_LIST}
✅ test_schema_selection_law
✅ test_schema_selection_graph
✅ test_schema_selection_client
✅ test_table_selection_documents
✅ test_table_selection_entities
✅ test_chained_schema_table_selection
```

**Results**:
- **Passed**: `{QB_PASSED}` / `{QB_TOTAL}`
- **Failed**: `{QB_FAILED}` tests
- **Performance**: Average `{QB_AVG_TIME}ms` per test

**Data Sources**:
- Law schema: 15,001 documents, 59,919 entities
- Graph schema: 141,000 nodes, 81,974 edges
- Client schema: 50 cases (limited data)

**Issues**: `{QB_ISSUES}`

---

### 2. SelectQueryBuilder Tests (Filters/Modifiers)

**Purpose**: Validate filters, modifiers, and pagination

**Test Cases**:
```
{SQB_TEST_LIST}
✅ test_eq_filter
✅ test_gte_filter
✅ test_lte_filter
✅ test_in_filter
✅ test_text_search
✅ test_order_ascending
✅ test_order_descending
✅ test_limit
✅ test_offset_pagination
✅ test_count_exact
```

**Results**:
- **Passed**: `{SQB_PASSED}` / `{SQB_TOTAL}`
- **Failed**: `{SQB_FAILED}` tests
- **Performance**: Average `{SQB_AVG_TIME}ms` per test

**Filter Performance**:
| Filter Type | Avg Time | Records Tested |
|-------------|----------|----------------|
| .eq() | `{EQ_AVG_TIME}ms` | `{EQ_RECORDS}` |
| .gte() | `{GTE_AVG_TIME}ms` | `{GTE_RECORDS}` |
| .lte() | `{LTE_AVG_TIME}ms` | `{LTE_RECORDS}` |
| .in_() | `{IN_AVG_TIME}ms` | `{IN_RECORDS}` |
| .text_search() | `{TEXT_SEARCH_AVG_TIME}ms` | `{TEXT_SEARCH_RECORDS}` |

**Issues**: `{SQB_ISSUES}`

---

### 3. Cross-Schema Tests

**Purpose**: Validate operations across law/client/graph schemas

**Test Cases**:
```
{CS_TEST_LIST}
✅ test_law_schema_documents_query
✅ test_law_schema_entities_query
✅ test_graph_schema_nodes_query
✅ test_graph_schema_edges_query
✅ test_graph_schema_communities_query
✅ test_client_schema_cases_query
```

**Results**:
- **Passed**: `{CS_PASSED}` / `{CS_TOTAL}`
- **Failed**: `{CS_FAILED}` tests
- **Performance**: Average `{CS_AVG_TIME}ms` per test

**Schema Performance**:
| Schema | Tables Tested | Avg Query Time | Records Returned |
|--------|--------------|----------------|------------------|
| Law | documents, entities | `{LAW_AVG_TIME}ms` | `{LAW_RECORDS}` |
| Graph | nodes, edges, communities | `{GRAPH_AVG_TIME}ms` | `{GRAPH_RECORDS}` |
| Client | cases | `{CLIENT_AVG_TIME}ms` | `{CLIENT_RECORDS}` |

**Issues**: `{CS_ISSUES}`

---

### 4. CRUD Validation (Insert/Update/Delete/Upsert)

**Purpose**: Validate Insert/Update/Delete/Upsert builders

**Test Cases**:
```
{CRUD_TEST_LIST}
✅ test_insert_single_record
✅ test_insert_batch_records
✅ test_update_with_filter
✅ test_delete_with_filter
✅ test_upsert_conflict_resolution
```

**Results**:
- **Passed**: `{CRUD_PASSED}` / `{CRUD_TOTAL}`
- **Failed**: `{CRUD_FAILED}` tests
- **Performance**: Average `{CRUD_AVG_TIME}ms` per test

**Safety Validation**:
- ✅ All write operations performed on test tables only
- ✅ No production data modified
- ✅ Read-only validation on production tables

**Issues**: `{CRUD_ISSUES}`

---

### 5. Performance Tests

**Purpose**: Validate performance with large datasets

**Test Cases**:
```
{PERF_TEST_LIST}
✅ test_small_query_performance (10 records)
✅ test_medium_query_performance (100 records)
✅ test_large_query_performance (1,000 records)
✅ test_extra_large_query_performance (5,000 records)
✅ test_pagination_performance
✅ test_count_query_performance
```

**Results**:
- **Passed**: `{PERF_PASSED}` / `{PERF_TOTAL}`
- **Failed**: `{PERF_FAILED}` tests
- **Performance**: Average `{PERF_AVG_TIME}ms` per test

**Performance Metrics**:
| Query Type | Records | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) |
|------------|---------|----------|----------|----------|----------|
| Small (10) | 10 | `{SMALL_P50}` | `{SMALL_P95}` | `{SMALL_P99}` | `{SMALL_MAX}` |
| Medium (100) | 100 | `{MED_P50}` | `{MED_P95}` | `{MED_P99}` | `{MED_MAX}` |
| Large (1K) | 1,000 | `{LARGE_P50}` | `{LARGE_P95}` | `{LARGE_P99}` | `{LARGE_MAX}` |
| Extra Large (5K) | 5,000 | `{XL_P50}` | `{XL_P95}` | `{XL_P99}` | `{XL_MAX}` |
| Pagination | 1,000 | `{PAG_P50}` | `{PAG_P95}` | `{PAG_P99}` | `{PAG_MAX}` |
| Count | N/A | `{COUNT_P50}` | `{COUNT_P95}` | `{COUNT_P99}` | `{COUNT_MAX}` |

**Performance Analysis**:
```
{PERFORMANCE_ANALYSIS}
✅ All queries within acceptable performance ranges
✅ No timeout issues detected
✅ Memory usage stable across all test sizes
```

**Issues**: `{PERF_ISSUES}`

---

### 6. Multi-Tenant Tests

**Purpose**: Validate tenant isolation and safety

**Test Cases**:
```
{MT_TEST_LIST}
✅ test_case_id_filtering
✅ test_client_id_filtering
✅ test_cross_tenant_isolation
```

**Results**:
- **Passed**: `{MT_PASSED}` / `{MT_TOTAL}`
- **Failed**: `{MT_FAILED}` tests
- **Performance**: Average `{MT_AVG_TIME}ms` per test

**Security Validation**:
- ✅ case_id filtering prevents cross-tenant access
- ✅ client_id filtering enforces data isolation
- ✅ No data leaks detected

**Issues**: `{MT_ISSUES}`

---

## Performance Analysis

### Query Execution Time Distribution

```
{QUERY_TIME_DISTRIBUTION}

Query Time Ranges:
  0-50ms:    {PCT_0_50}% of queries  ████████████████████
  50-100ms:  {PCT_50_100}% of queries  ██████████
  100-200ms: {PCT_100_200}% of queries  █████
  200-500ms: {PCT_200_500}% of queries  ██
  500ms+:    {PCT_500_PLUS}% of queries  █
```

### Slowest Queries

| Query | Time (ms) | Records | Table |
|-------|-----------|---------|-------|
| `{SLOW_1_QUERY}` | `{SLOW_1_TIME}` | `{SLOW_1_RECORDS}` | `{SLOW_1_TABLE}` |
| `{SLOW_2_QUERY}` | `{SLOW_2_TIME}` | `{SLOW_2_RECORDS}` | `{SLOW_2_TABLE}` |
| `{SLOW_3_QUERY}` | `{SLOW_3_TIME}` | `{SLOW_3_RECORDS}` | `{SLOW_3_TABLE}` |
| `{SLOW_4_QUERY}` | `{SLOW_4_TIME}` | `{SLOW_4_RECORDS}` | `{SLOW_4_TABLE}` |
| `{SLOW_5_QUERY}` | `{SLOW_5_TIME}` | `{SLOW_5_RECORDS}` | `{SLOW_5_TABLE}` |

### Fastest Queries

| Query | Time (ms) | Records | Table |
|-------|-----------|---------|-------|
| `{FAST_1_QUERY}` | `{FAST_1_TIME}` | `{FAST_1_RECORDS}` | `{FAST_1_TABLE}` |
| `{FAST_2_QUERY}` | `{FAST_2_TIME}` | `{FAST_2_RECORDS}` | `{FAST_2_TABLE}` |
| `{FAST_3_QUERY}` | `{FAST_3_TIME}` | `{FAST_3_RECORDS}` | `{FAST_3_TABLE}` |

---

## Issues and Failures

### Failed Tests

```
{FAILED_TESTS_SECTION}

Test: {FAILED_TEST_1_NAME}
Status: ❌ FAILED
Error: {FAILED_TEST_1_ERROR}
Traceback: {FAILED_TEST_1_TRACEBACK}

Test: {FAILED_TEST_2_NAME}
Status: ❌ FAILED
Error: {FAILED_TEST_2_ERROR}
Traceback: {FAILED_TEST_2_TRACEBACK}

(No failures - all tests passed!)
```

### Warnings

```
{WARNINGS_SECTION}

⚠️ Warning: {WARNING_1_MESSAGE}
   Impact: {WARNING_1_IMPACT}
   Recommendation: {WARNING_1_RECOMMENDATION}

⚠️ Warning: {WARNING_2_MESSAGE}
   Impact: {WARNING_2_IMPACT}
   Recommendation: {WARNING_2_RECOMMENDATION}

(No warnings)
```

### Performance Issues

```
{PERFORMANCE_ISSUES_SECTION}

⚠️ Issue: {PERF_ISSUE_1_DESCRIPTION}
   Query: {PERF_ISSUE_1_QUERY}
   Time: {PERF_ISSUE_1_TIME}ms (expected: {PERF_ISSUE_1_EXPECTED}ms)
   Recommendation: {PERF_ISSUE_1_RECOMMENDATION}

(No performance issues detected)
```

---

## Recommendations

### Priority 1: Critical Issues

```
{CRITICAL_RECOMMENDATIONS}

❌ {CRITICAL_1_ISSUE}
   Impact: {CRITICAL_1_IMPACT}
   Action: {CRITICAL_1_ACTION}
   Owner: {CRITICAL_1_OWNER}
   Timeline: {CRITICAL_1_TIMELINE}

(No critical issues)
```

### Priority 2: Performance Improvements

```
{PERFORMANCE_RECOMMENDATIONS}

⚠️ {PERF_REC_1_ISSUE}
   Impact: {PERF_REC_1_IMPACT}
   Action: {PERF_REC_1_ACTION}
   Expected Improvement: {PERF_REC_1_IMPROVEMENT}

⚠️ {PERF_REC_2_ISSUE}
   Impact: {PERF_REC_2_IMPACT}
   Action: {PERF_REC_2_ACTION}
   Expected Improvement: {PERF_REC_2_IMPROVEMENT}

(No performance recommendations)
```

### Priority 3: Code Quality Improvements

```
{QUALITY_RECOMMENDATIONS}

ℹ️ {QUALITY_1_ISSUE}
   Impact: {QUALITY_1_IMPACT}
   Action: {QUALITY_1_ACTION}

(No quality recommendations)
```

---

## Test Data Summary

### Data Sources Used

| Schema | Table | Records Available | Records Tested | Coverage |
|--------|-------|------------------|----------------|----------|
| law | documents | 15,001 | `{LAW_DOCS_TESTED}` | `{LAW_DOCS_COVERAGE}%` |
| law | entities | 59,919 | `{LAW_ENTITIES_TESTED}` | `{LAW_ENTITIES_COVERAGE}%` |
| graph | nodes | 141,000 | `{GRAPH_NODES_TESTED}` | `{GRAPH_NODES_COVERAGE}%` |
| graph | edges | 81,974 | `{GRAPH_EDGES_TESTED}` | `{GRAPH_EDGES_COVERAGE}%` |
| graph | communities | 1,000 | `{GRAPH_COMMUNITIES_TESTED}` | `{GRAPH_COMMUNITIES_COVERAGE}%` |
| client | cases | 50 | `{CLIENT_CASES_TESTED}` | `{CLIENT_CASES_COVERAGE}%` |

### Data Quality

- ✅ **Law Schema**: Real production legal documents
- ⚠️ **Graph Schema**: Synthetic test data (suitable for performance testing)
- ⚠️ **Client Schema**: Limited data (cases only, no documents/entities)

---

## Test Environment

### Configuration

```yaml
Service: graphrag-service
Port: 8010
Database: Supabase Production
Base URL: {SUPABASE_URL}

Client Configuration:
  Service Role: {USE_SERVICE_ROLE}
  Timeout: {TIMEOUT_SECONDS}s
  Max Retries: {MAX_RETRIES}
  Circuit Breaker: {CIRCUIT_BREAKER_ENABLED}

Test Configuration:
  Safe Limits Enforced: Yes
  Read-Only Mode: Yes
  Performance Tracking: Yes
  Memory Profiling: {MEMORY_PROFILING_ENABLED}
```

### System Information

```
Python Version: {PYTHON_VERSION}
Pytest Version: {PYTEST_VERSION}
Test Framework: {TEST_FRAMEWORK_VERSION}
OS: {OS_INFO}
Memory Available: {MEMORY_AVAILABLE} GB
```

---

## Code Coverage

### Overall Coverage

```
{COVERAGE_SUMMARY}

Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
src/clients/supabase_client.py             245     12    95%   120-125, 340-342
src/clients/query_builder.py              180      5    97%   85, 156-158
src/clients/select_query_builder.py       220      8    96%   45, 190-195
src/clients/insert_query_builder.py       120      3    97%   78-80
src/clients/update_query_builder.py       115      4    96%   92-95
src/clients/delete_query_builder.py        95      2    98%   67-68
src/clients/upsert_query_builder.py       130      6    95%   105-110
-----------------------------------------------------------------------
TOTAL                                     1105     40    96%
```

**Target**: 95%+ coverage
**Achieved**: `{COVERAGE_PERCENTAGE}%`
**Status**: `{COVERAGE_STATUS}`

---

## Deployment Readiness

### Checklist

- [ ] **All Tests Passed**: `{ALL_TESTS_PASSED}`
- [ ] **Performance Acceptable**: `{PERFORMANCE_ACCEPTABLE}`
- [ ] **No Critical Issues**: `{NO_CRITICAL_ISSUES}`
- [ ] **Coverage ≥ 95%**: `{COVERAGE_OK}`
- [ ] **Documentation Updated**: `{DOCS_UPDATED}`
- [ ] **Multi-Tenant Isolation Validated**: `{MULTI_TENANT_OK}`

**Overall Status**: `{DEPLOYMENT_STATUS}`

```
{DEPLOYMENT_RECOMMENDATION}

✅ APPROVED FOR DEPLOYMENT
   All tests passed, performance acceptable, no critical issues

⚠️ CONDITIONAL APPROVAL
   Minor issues detected, review recommendations before deployment

❌ DEPLOYMENT BLOCKED
   Critical issues must be resolved before deployment
```

---

## Next Steps

### Immediate Actions

1. `{NEXT_STEP_1}`
2. `{NEXT_STEP_2}`
3. `{NEXT_STEP_3}`

### Follow-up Tasks

1. `{FOLLOW_UP_1}`
2. `{FOLLOW_UP_2}`
3. `{FOLLOW_UP_3}`

---

## Appendix

### Test Command

```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate
pytest tests/test_fluent_api_comprehensive.py -v \
  --cov=src.clients.supabase_client \
  --cov-report=html
```

### Related Documentation

- **API Testing Guide**: `/srv/luris/be/graphrag-service/tests/API_TESTING_GUIDE.md`
- **Test Data Inventory**: `/srv/luris/be/graphrag-service/tests/results/test_data_inventory.md`
- **Quick Reference**: `/srv/luris/be/graphrag-service/tests/results/QUICK_REFERENCE.md`
- **GraphRAG API**: `/srv/luris/be/graphrag-service/api.md`

### Report Metadata

```
Report Template Version: 1.0.0
Generated By: pytest + custom report generator
Report Format: Markdown
Auto-Generated: Yes
Manual Review Required: {MANUAL_REVIEW_REQUIRED}
```

---

**Report Generated**: `{TIMESTAMP}`
**Status**: `{CURRENT_STATUS}`
**Next Review**: `{NEXT_REVIEW_DATE}`
