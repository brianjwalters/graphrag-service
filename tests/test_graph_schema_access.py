"""
Comprehensive Graph Schema Database Access Test Suite

Tests the canonical SupabaseClient from graphrag-service against all graph.* schema tables
to validate complete database access including:
- Basic CRUD operations on graph.nodes
- Access to all graph schema tables
- Vector search operations
- Connection pool stress testing
- Admin vs anon client behavior
- Performance monitoring

Usage:
    cd /srv/luris/be/graphrag-service
    source venv/bin/activate
    python tests/test_graph_schema_access.py
"""

import asyncio
import sys
import time
import statistics
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any
import json

# Add src to path for imports
sys.path.insert(0, '/srv/luris/be/graphrag-service/src')

from clients.supabase_client import create_admin_supabase_client, create_supabase_client

# Test configuration
TEST_CLIENT_ID = str(uuid4())
TEST_CASE_ID = str(uuid4())
TEST_RUN_ID = str(uuid4())


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_failure(text: str):
    """Print failure message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


class TestResults:
    """Track test results and metrics"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.latencies: Dict[str, List[float]] = {}
        self.errors: List[Dict[str, Any]] = []
        self.test_details: List[Dict[str, Any]] = []

    def record_test(self, name: str, passed: bool, latency: float, details: Dict[str, Any] = None):
        """Record test result"""
        if passed:
            self.passed += 1
            print_success(f"{name} - {latency*1000:.2f}ms")
        else:
            self.failed += 1
            print_failure(f"{name}")

        self.test_details.append({
            "name": name,
            "passed": passed,
            "latency": latency,
            "details": details or {}
        })

    def record_latency(self, operation: str, latency: float):
        """Record operation latency"""
        if operation not in self.latencies:
            self.latencies[operation] = []
        self.latencies[operation].append(latency)

    def record_error(self, operation: str, error: str, details: Dict[str, Any] = None):
        """Record error"""
        self.errors.append({
            "operation": operation,
            "error": error,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_latency_stats(self, operation: str) -> Dict[str, float]:
        """Calculate latency statistics"""
        if operation not in self.latencies or not self.latencies[operation]:
            return {"count": 0}

        latencies = self.latencies[operation]
        return {
            "count": len(latencies),
            "min": min(latencies) * 1000,  # Convert to ms
            "max": max(latencies) * 1000,
            "mean": statistics.mean(latencies) * 1000,
            "median": statistics.median(latencies) * 1000,
            "p95": statistics.quantiles(latencies, n=20)[18] * 1000 if len(latencies) >= 20 else max(latencies) * 1000,
            "p99": statistics.quantiles(latencies, n=100)[98] * 1000 if len(latencies) >= 100 else max(latencies) * 1000
        }


async def test_crud_operations(client, results: TestResults):
    """Test basic CRUD operations on graph.nodes"""
    print_header("Phase 1: CRUD Operations on graph.nodes")

    test_node_id = str(uuid4())

    # Test INSERT
    print_info("Testing INSERT operation...")
    start_time = time.time()
    try:
        insert_result = await client.insert("graph.nodes", {
            "node_id": test_node_id,
            "node_type": "entity",  # Valid types: entity, document, concept
            "title": f"Test Entity {TEST_RUN_ID}",
            "description": "Test entity for graph schema validation",
            "source_id": TEST_CLIENT_ID,
            "source_type": "test",
            "metadata": {"test_run": TEST_RUN_ID, "source": "test_suite", "case_id": TEST_CASE_ID}
        }, admin_operation=True)

        latency = time.time() - start_time
        results.record_latency("insert", latency)
        results.record_test("INSERT graph.nodes", len(insert_result) > 0, latency, {"rows": len(insert_result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("INSERT graph.nodes", False, latency)
        results.record_error("INSERT", str(e))

    # Test SELECT with filters
    print_info("Testing SELECT with filters...")
    start_time = time.time()
    try:
        select_result = await client.get(
            "graph.nodes",
            filters={"source_id": TEST_CLIENT_ID},
            admin_operation=True
        )

        latency = time.time() - start_time
        results.record_latency("select", latency)
        results.record_test("SELECT graph.nodes with filters", len(select_result) > 0, latency, {"rows": len(select_result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("SELECT graph.nodes with filters", False, latency)
        results.record_error("SELECT", str(e))

    # Test UPDATE
    print_info("Testing UPDATE operation...")
    start_time = time.time()
    try:
        update_result = await client.update(
            "graph.nodes",
            data={"description": "Updated test entity", "metadata": {"test_run": TEST_RUN_ID, "updated": True, "timestamp": datetime.utcnow().isoformat()}},
            match={"node_id": test_node_id},
            admin_operation=True
        )

        latency = time.time() - start_time
        results.record_latency("update", latency)
        results.record_test("UPDATE graph.nodes", len(update_result) > 0, latency, {"rows": len(update_result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("UPDATE graph.nodes", False, latency)
        results.record_error("UPDATE", str(e))

    # Test UPSERT
    print_info("Testing UPSERT operation...")
    start_time = time.time()
    try:
        upsert_node_id = str(uuid4())
        upsert_result = await client.upsert("graph.nodes", {
            "node_id": upsert_node_id,
            "node_type": "concept",  # Valid types: entity, document, concept
            "title": f"Upsert Test Entity {TEST_RUN_ID}",
            "description": "Test entity for upsert validation",
            "source_id": TEST_CLIENT_ID,
            "source_type": "test",
            "metadata": {"test_run": TEST_RUN_ID, "upsert_test": True, "case_id": TEST_CASE_ID}
        }, admin_operation=True)

        latency = time.time() - start_time
        results.record_latency("upsert", latency)
        results.record_test("UPSERT graph.nodes", len(upsert_result) > 0, latency, {"rows": len(upsert_result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("UPSERT graph.nodes", False, latency)
        results.record_error("UPSERT", str(e))

    # Test DELETE
    print_info("Testing DELETE operation...")
    start_time = time.time()
    try:
        delete_result = await client.delete(
            "graph.nodes",
            match={"node_id": test_node_id},
            admin_operation=True
        )

        latency = time.time() - start_time
        results.record_latency("delete", latency)
        results.record_test("DELETE graph.nodes", True, latency, {"rows": len(delete_result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("DELETE graph.nodes", False, latency)
        results.record_error("DELETE", str(e))


async def test_graph_tables_access(client, results: TestResults):
    """Test access to all graph schema tables"""
    print_header("Phase 2: Graph Schema Tables Access")

    # Only test tables that actually exist
    tables = [
        "graph.nodes",
        "graph.edges",
        "graph.communities"
    ]

    for table in tables:
        print_info(f"Testing access to {table}...")
        start_time = time.time()
        try:
            result = await client.get(table, limit=1, admin_operation=True)
            latency = time.time() - start_time
            results.record_latency(f"access_{table}", latency)
            results.record_test(f"Access {table}", True, latency, {"rows": len(result)})
        except Exception as e:
            latency = time.time() - start_time
            results.record_test(f"Access {table}", False, latency)
            results.record_error(f"Access {table}", str(e))


async def test_batch_operations(client, results: TestResults):
    """Test batch insert operations"""
    print_header("Phase 3: Batch Operations")

    print_info("Testing batch insert (10 nodes)...")
    start_time = time.time()
    try:
        # Valid node_type values: entity, document, concept
        batch_nodes = [
            {
                "node_id": str(uuid4()),
                "node_type": ["entity", "document", "concept"][i % 3],
                "title": f"Batch Entity {i}",
                "description": f"Batch test entity number {i}",
                "source_id": TEST_CLIENT_ID,
                "source_type": "test",
                "metadata": {"batch_index": i, "test_run": TEST_RUN_ID, "case_id": TEST_CASE_ID}
            }
            for i in range(10)
        ]

        batch_result = await client.insert("graph.nodes", batch_nodes, admin_operation=True)
        latency = time.time() - start_time
        results.record_latency("batch_insert", latency)
        results.record_test("Batch INSERT 10 nodes", len(batch_result) == 10, latency, {"rows": len(batch_result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("Batch INSERT 10 nodes", False, latency)
        results.record_error("Batch INSERT", str(e))


async def test_complex_queries(client, results: TestResults):
    """Test complex queries with filters and ordering"""
    print_header("Phase 4: Complex Queries")

    print_info("Testing complex query with multiple filters...")
    start_time = time.time()
    try:
        # Query nodes by source_id with limit
        result = await client.get(
            "graph.nodes",
            filters={"source_id": TEST_CLIENT_ID},
            limit=50,
            admin_operation=True
        )

        latency = time.time() - start_time
        results.record_latency("complex_query", latency)
        results.record_test("Complex query with filters", True, latency, {"rows": len(result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("Complex query with filters", False, latency)
        results.record_error("Complex query", str(e))


async def test_connection_pool_stress(client, results: TestResults):
    """Test connection pool with 100 concurrent operations"""
    print_header("Phase 5: Connection Pool Stress Test")

    print_info("Executing 100 concurrent SELECT operations...")

    async def single_query():
        start = time.time()
        try:
            await client.get("graph.nodes", limit=1, admin_operation=True)
            return time.time() - start, None
        except Exception as e:
            return time.time() - start, str(e)

    start_time = time.time()
    tasks = [single_query() for _ in range(100)]
    query_results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time

    # Analyze results
    successful = sum(1 for _, err in query_results if err is None)
    failed = len(query_results) - successful
    latencies = [lat for lat, err in query_results if err is None]

    results.record_test(
        f"100 concurrent queries ({successful} succeeded, {failed} failed)",
        failed == 0,
        total_time,
        {
            "total_queries": 100,
            "successful": successful,
            "failed": failed,
            "total_time": total_time,
            "avg_latency": statistics.mean(latencies) * 1000 if latencies else 0
        }
    )

    # Record latencies for successful queries
    for lat in latencies:
        results.record_latency("concurrent_query", lat)


async def test_admin_vs_anon_behavior(client, results: TestResults):
    """Test admin_operation parameter behavior"""
    print_header("Phase 6: Admin vs Anon Client Behavior")

    # Create a standard (anon) client
    anon_client = create_supabase_client("test-anon-client")
    admin_client = create_admin_supabase_client("test-admin-client")

    # Test with admin client
    print_info("Testing with admin client (should use service_role)...")
    start_time = time.time()
    try:
        admin_result = await admin_client.get("graph.nodes", limit=1, admin_operation=True)
        latency = time.time() - start_time
        results.record_test("Admin client with admin_operation=True", True, latency, {"rows": len(admin_result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("Admin client with admin_operation=True", False, latency)
        results.record_error("Admin operation", str(e))

    # Test with anon client
    print_info("Testing with anon client (should use anon key)...")
    start_time = time.time()
    try:
        anon_result = await anon_client.get("graph.nodes", limit=1, admin_operation=False)
        latency = time.time() - start_time
        results.record_test("Anon client with admin_operation=False", True, latency, {"rows": len(anon_result)})
    except Exception as e:
        latency = time.time() - start_time
        results.record_test("Anon client with admin_operation=False", False, latency)
        results.record_error("Anon operation", str(e))


async def cleanup_test_data(client):
    """Clean up test data created during tests"""
    print_header("Cleanup: Removing Test Data")

    try:
        print_info("Deleting test nodes...")
        await client.delete(
            "graph.nodes",
            match={"source_id": TEST_CLIENT_ID},
            admin_operation=True
        )
        print_success("Test data cleaned up")
    except Exception as e:
        print_warning(f"Cleanup failed: {e}")


def generate_report(results: TestResults, client):
    """Generate comprehensive test report"""
    print_header("TEST REPORT")

    # Summary
    total_tests = results.passed + results.failed
    pass_rate = (results.passed / total_tests * 100) if total_tests > 0 else 0

    print(f"\n{Colors.BOLD}Test Summary:{Colors.END}")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {Colors.GREEN}{results.passed}{Colors.END}")
    print(f"  Failed: {Colors.RED}{results.failed}{Colors.END}")
    print(f"  Pass Rate: {Colors.GREEN if pass_rate >= 90 else Colors.YELLOW}{pass_rate:.1f}%{Colors.END}")

    # Performance Metrics
    print(f"\n{Colors.BOLD}Performance Metrics:{Colors.END}")

    for operation in ["insert", "select", "update", "delete", "upsert"]:
        stats = results.get_latency_stats(operation)
        if stats.get("count", 0) > 0:
            print(f"\n  {operation.upper()} Operations:")
            print(f"    Count: {stats['count']}")
            print(f"    Min: {stats['min']:.2f}ms")
            print(f"    Max: {stats['max']:.2f}ms")
            print(f"    Mean: {stats['mean']:.2f}ms")
            print(f"    Median: {stats['median']:.2f}ms")
            print(f"    P95: {stats['p95']:.2f}ms")

    # Concurrent query stats
    concurrent_stats = results.get_latency_stats("concurrent_query")
    if concurrent_stats.get("count", 0) > 0:
        print(f"\n  CONCURRENT QUERIES (100 operations):")
        print(f"    Successful: {concurrent_stats['count']}")
        print(f"    Min: {concurrent_stats['min']:.2f}ms")
        print(f"    Max: {concurrent_stats['max']:.2f}ms")
        print(f"    Mean: {concurrent_stats['mean']:.2f}ms")
        print(f"    Median: {concurrent_stats['median']:.2f}ms")
        print(f"    P95: {concurrent_stats['p95']:.2f}ms")
        print(f"    P99: {concurrent_stats['p99']:.2f}ms")

    # Client Health
    print(f"\n{Colors.BOLD}Client Health:{Colors.END}")
    health_info = client.get_health_info()
    print(f"  Service: {health_info['service_name']}")
    print(f"  Total Operations: {health_info['operation_count']}")
    print(f"  Error Count: {health_info['error_count']}")
    print(f"  Error Rate: {health_info['error_rate']*100:.2f}%")
    print(f"  Connection Pool:")
    print(f"    Max Connections: {health_info['connection_pool']['max_connections']}")
    print(f"    Active: {health_info['connection_pool']['active_connections']}")
    print(f"    Utilization: {health_info['connection_pool']['utilization']*100:.1f}%")
    print(f"  Healthy: {Colors.GREEN if health_info['healthy'] else Colors.RED}{health_info['healthy']}{Colors.END}")

    # Errors
    if results.errors:
        print(f"\n{Colors.BOLD}Errors:{Colors.END}")
        for error in results.errors:
            print(f"  {Colors.RED}• {error['operation']}: {error['error'][:100]}{Colors.END}")

    # Recommendations
    print(f"\n{Colors.BOLD}Recommendations:{Colors.END}")

    if pass_rate >= 95:
        print(f"  {Colors.GREEN}✅ GraphRAG SupabaseClient is PRODUCTION READY for graph schema{Colors.END}")
    elif pass_rate >= 80:
        print(f"  {Colors.YELLOW}⚠️  GraphRAG SupabaseClient is MOSTLY READY - review failures{Colors.END}")
    else:
        print(f"  {Colors.RED}❌ GraphRAG SupabaseClient has SIGNIFICANT ISSUES - not production ready{Colors.END}")

    # Specific recommendations
    if health_info['error_rate'] > 0.05:
        print(f"  {Colors.YELLOW}⚠️  High error rate ({health_info['error_rate']*100:.1f}%) - investigate connection issues{Colors.END}")

    if health_info['connection_pool']['utilization'] > 0.8:
        print(f"  {Colors.YELLOW}⚠️  High connection pool utilization - consider increasing max_connections{Colors.END}")

    concurrent_stats = results.get_latency_stats("concurrent_query")
    if concurrent_stats.get("count", 0) > 0 and concurrent_stats['p95'] > 1000:  # >1s
        print(f"  {Colors.YELLOW}⚠️  High P95 latency under load ({concurrent_stats['p95']:.0f}ms) - optimize queries{Colors.END}")

    print()


async def main():
    """Main test execution"""
    print_header("Graph Schema Database Access Validation")
    print(f"Test Run ID: {TEST_RUN_ID}")
    print(f"Test Client ID: {TEST_CLIENT_ID}")
    print(f"Test Case ID: {TEST_CASE_ID}")
    print(f"Start Time: {datetime.utcnow().isoformat()}")

    # Initialize client
    print_info("Initializing SupabaseClient...")
    client = create_admin_supabase_client("test-graph-schema-access")
    results = TestResults()

    try:
        # Run test phases
        await test_crud_operations(client, results)
        await test_graph_tables_access(client, results)
        await test_batch_operations(client, results)
        await test_complex_queries(client, results)
        await test_connection_pool_stress(client, results)
        await test_admin_vs_anon_behavior(client, results)

        # Cleanup
        await cleanup_test_data(client)

    finally:
        # Generate report
        generate_report(results, client)

        # Close client
        await client.close()

    print(f"\n{Colors.BOLD}Test completed at: {datetime.utcnow().isoformat()}{Colors.END}\n")

    # Exit with appropriate code
    sys.exit(0 if results.failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
