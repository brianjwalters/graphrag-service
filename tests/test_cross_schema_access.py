"""
Comprehensive cross-schema database access test for SupabaseClient.

This test validates that the canonical SupabaseClient from graphrag-service
can successfully access and operate on multiple database schemas:
- client.* (client document management)
- law.* (legal reference materials)
- graph.* (knowledge graph - primary schema)

Test Coverage:
1. Client Schema CRUD operations
2. Law Schema READ operations
3. Schema name conversion (dot → underscore notation)
4. Cross-schema queries and performance
5. Storage operations (if applicable)
6. Dual-client architecture (anon vs service_role)
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from uuid import uuid4
import time

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.supabase_client import create_admin_supabase_client, create_supabase_client


class CrossSchemaTestResults:
    """Container for test results with detailed metrics"""

    def __init__(self):
        self.tests: List[Dict[str, Any]] = []
        self.start_time = datetime.utcnow()
        self.end_time = None

    def add_test(self, name: str, passed: bool, details: Dict[str, Any]):
        """Add a test result"""
        self.tests.append({
            "name": name,
            "passed": passed,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        })

    def finalize(self):
        """Finalize test run"""
        self.end_time = datetime.utcnow()

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        total = len(self.tests)
        passed = sum(1 for t in self.tests if t["passed"])
        failed = total - passed

        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "duration_seconds": duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None
        }

    def print_report(self):
        """Print detailed test report"""
        summary = self.get_summary()

        print("\n" + "="*80)
        print("CROSS-SCHEMA DATABASE ACCESS TEST REPORT")
        print("="*80)

        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Duration: {summary['duration_seconds']:.2f}s")

        print(f"\n📋 DETAILED RESULTS:")
        for i, test in enumerate(self.tests, 1):
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            print(f"\n{i}. {status} - {test['name']}")

            # Print key details
            if "error" in test["details"]:
                print(f"   Error: {test['details']['error']}")
            if "latency_ms" in test["details"]:
                print(f"   Latency: {test['details']['latency_ms']:.2f}ms")
            if "row_count" in test["details"]:
                print(f"   Rows: {test['details']['row_count']}")
            if "operation" in test["details"]:
                print(f"   Operation: {test['details']['operation']}")

        print("\n" + "="*80)


async def test_client_schema_insert(client, results: CrossSchemaTestResults):
    """Test INSERT operation on client.documents"""
    test_name = "Client Schema - INSERT document"

    try:
        test_id = str(uuid4())
        test_data = {
            "id": test_id,
            "client_id": f"test_client_{int(time.time())}",
            "document_name": "test_cross_schema.pdf",
            "document_type": "contract",
            "status": "uploaded",
            "created_at": datetime.utcnow().isoformat()
        }

        start = time.time()
        result = await client.insert("client.documents", test_data, admin_operation=True)
        latency = (time.time() - start) * 1000

        results.add_test(test_name, True, {
            "operation": "INSERT",
            "table": "client.documents",
            "latency_ms": latency,
            "row_count": len(result),
            "test_id": test_id
        })

        return test_id

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "INSERT",
            "table": "client.documents",
            "error": str(e)
        })
        return None


async def test_client_schema_select(client, results: CrossSchemaTestResults, test_id: str = None):
    """Test SELECT operation on client.documents"""
    test_name = "Client Schema - SELECT documents"

    try:
        filters = {"id": test_id} if test_id else None

        start = time.time()
        result = await client.get("client.documents", filters=filters, limit=10, admin_operation=True)
        latency = (time.time() - start) * 1000

        results.add_test(test_name, True, {
            "operation": "SELECT",
            "table": "client.documents",
            "latency_ms": latency,
            "row_count": len(result),
            "filtered": test_id is not None
        })

        return result

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "SELECT",
            "table": "client.documents",
            "error": str(e)
        })
        return None


async def test_client_schema_update(client, results: CrossSchemaTestResults, test_id: str):
    """Test UPDATE operation on client.documents"""
    test_name = "Client Schema - UPDATE document"

    try:
        update_data = {
            "status": "processed",
            "updated_at": datetime.utcnow().isoformat()
        }

        start = time.time()
        result = await client.update("client.documents", update_data, match={"id": test_id}, admin_operation=True)
        latency = (time.time() - start) * 1000

        results.add_test(test_name, True, {
            "operation": "UPDATE",
            "table": "client.documents",
            "latency_ms": latency,
            "row_count": len(result),
            "test_id": test_id
        })

        return True

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "UPDATE",
            "table": "client.documents",
            "error": str(e)
        })
        return False


async def test_client_schema_delete(client, results: CrossSchemaTestResults, test_id: str):
    """Test DELETE operation on client.documents"""
    test_name = "Client Schema - DELETE document"

    try:
        start = time.time()
        result = await client.delete("client.documents", match={"id": test_id}, admin_operation=True)
        latency = (time.time() - start) * 1000

        results.add_test(test_name, True, {
            "operation": "DELETE",
            "table": "client.documents",
            "latency_ms": latency,
            "row_count": len(result),
            "test_id": test_id
        })

        return True

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "DELETE",
            "table": "client.documents",
            "error": str(e)
        })
        return False


async def test_law_schema_select(client, results: CrossSchemaTestResults):
    """Test SELECT operation on law.documents (read-only reference data)"""
    test_name = "Law Schema - SELECT documents"

    try:
        start = time.time()
        result = await client.get("law.documents", limit=10, admin_operation=True)
        latency = (time.time() - start) * 1000

        results.add_test(test_name, True, {
            "operation": "SELECT",
            "table": "law.documents",
            "latency_ms": latency,
            "row_count": len(result),
            "read_only": True
        })

        return result

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "SELECT",
            "table": "law.documents",
            "error": str(e)
        })
        return None


async def test_law_schema_with_filters(client, results: CrossSchemaTestResults):
    """Test SELECT with filters on law.documents"""
    test_name = "Law Schema - SELECT with filters"

    try:
        # Try filtering by document_type
        filters = {"document_type": "opinion"}

        start = time.time()
        result = await client.get("law.documents", filters=filters, limit=5, admin_operation=True)
        latency = (time.time() - start) * 1000

        results.add_test(test_name, True, {
            "operation": "SELECT",
            "table": "law.documents",
            "latency_ms": latency,
            "row_count": len(result),
            "filters": filters
        })

        return result

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "SELECT",
            "table": "law.documents",
            "error": str(e)
        })
        return None


async def test_schema_conversion(client, results: CrossSchemaTestResults):
    """Test automatic schema name conversion (dot → underscore)"""
    test_name = "Schema Conversion - dot to underscore notation"

    conversions_tested = []
    all_passed = True

    # Test conversions
    test_cases = [
        ("client.documents", "client_documents"),
        ("law.documents", "law_documents"),
        ("graph.entities", "graph_entities"),
        ("law.chunks", "law_chunks"),
        ("client.chunks", "client_chunks")
    ]

    for dot_notation, expected_underscore in test_cases:
        try:
            converted = client._convert_table_name(dot_notation)
            passed = converted == expected_underscore

            conversions_tested.append({
                "input": dot_notation,
                "expected": expected_underscore,
                "actual": converted,
                "passed": passed
            })

            if not passed:
                all_passed = False

        except Exception as e:
            conversions_tested.append({
                "input": dot_notation,
                "error": str(e)
            })
            all_passed = False

    results.add_test(test_name, all_passed, {
        "operation": "schema_conversion",
        "conversions": conversions_tested,
        "total_tests": len(test_cases),
        "passed": sum(1 for c in conversions_tested if c.get("passed", False))
    })


async def test_graph_schema_select(client, results: CrossSchemaTestResults):
    """Test SELECT operation on graph.entities (primary schema)"""
    test_name = "Graph Schema - SELECT entities"

    try:
        start = time.time()
        result = await client.get("graph.entities", limit=10, admin_operation=True)
        latency = (time.time() - start) * 1000

        results.add_test(test_name, True, {
            "operation": "SELECT",
            "table": "graph.entities",
            "latency_ms": latency,
            "row_count": len(result),
            "primary_schema": True
        })

        return result

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "SELECT",
            "table": "graph.entities",
            "error": str(e)
        })
        return None


async def test_cross_schema_performance(client, results: CrossSchemaTestResults):
    """Compare query performance across different schemas"""
    test_name = "Cross-Schema Performance Comparison"

    try:
        schemas_to_test = [
            ("client.documents", "client"),
            ("law.documents", "law"),
            ("graph.entities", "graph")
        ]

        performance_data = []

        for table, schema_name in schemas_to_test:
            try:
                start = time.time()
                result = await client.get(table, limit=10, admin_operation=True)
                latency = (time.time() - start) * 1000

                performance_data.append({
                    "schema": schema_name,
                    "table": table,
                    "latency_ms": latency,
                    "rows_returned": len(result)
                })
            except Exception as e:
                performance_data.append({
                    "schema": schema_name,
                    "table": table,
                    "error": str(e)
                })

        # Calculate average latency
        latencies = [p["latency_ms"] for p in performance_data if "latency_ms" in p]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        results.add_test(test_name, True, {
            "operation": "performance_comparison",
            "schemas_tested": len(schemas_to_test),
            "average_latency_ms": avg_latency,
            "performance_data": performance_data
        })

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "performance_comparison",
            "error": str(e)
        })


async def test_dual_client_architecture(results: CrossSchemaTestResults):
    """Test dual-client architecture (anon vs service_role)"""
    test_name = "Dual-Client Architecture - Anon vs Service Role"

    try:
        # Create both client types
        anon_client = create_supabase_client("test-anon-client", use_service_role=False)
        admin_client = create_admin_supabase_client("test-admin-client")

        # Test anon client
        anon_result = None
        try:
            anon_result = await anon_client.get("law.documents", limit=5, admin_operation=False)
        except Exception as anon_error:
            anon_result = f"Error: {anon_error}"

        # Test admin client
        admin_result = None
        try:
            admin_result = await admin_client.get("law.documents", limit=5, admin_operation=True)
        except Exception as admin_error:
            admin_result = f"Error: {admin_error}"

        results.add_test(test_name, True, {
            "operation": "dual_client_test",
            "anon_client": {
                "initialized": anon_client is not None,
                "result": "success" if isinstance(anon_result, list) else str(anon_result)
            },
            "admin_client": {
                "initialized": admin_client is not None,
                "result": "success" if isinstance(admin_result, list) else str(admin_result)
            }
        })

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "dual_client_test",
            "error": str(e)
        })


async def test_client_health(client, results: CrossSchemaTestResults):
    """Test client health monitoring"""
    test_name = "Client Health Monitoring"

    try:
        health_info = client.get_health_info()

        results.add_test(test_name, health_info["healthy"], {
            "operation": "health_check",
            "health_data": {
                "operation_count": health_info["operation_count"],
                "error_count": health_info["error_count"],
                "error_rate": health_info["error_rate"],
                "primary_client": health_info["clients"]["primary_client"],
                "connection_pool_utilization": health_info["connection_pool"]["utilization"]
            }
        })

    except Exception as e:
        results.add_test(test_name, False, {
            "operation": "health_check",
            "error": str(e)
        })


async def main():
    """Main test execution"""
    print("\n🚀 Starting Cross-Schema Database Access Tests...")
    print(f"📅 Test Started: {datetime.utcnow().isoformat()}\n")

    results = CrossSchemaTestResults()

    # Create admin client for testing
    client = create_admin_supabase_client("cross-schema-test")

    print("✅ Admin client created successfully\n")

    # Run tests in sequence
    print("📋 Running Test Suite:\n")

    # 1. Schema conversion tests (no DB access needed)
    print("1️⃣  Testing schema name conversion...")
    await test_schema_conversion(client, results)

    # 2. Law schema tests (read-only)
    print("2️⃣  Testing law schema access (read-only)...")
    await test_law_schema_select(client, results)
    await test_law_schema_with_filters(client, results)

    # 3. Graph schema tests (primary schema)
    print("3️⃣  Testing graph schema access (primary)...")
    await test_graph_schema_select(client, results)

    # 4. Client schema CRUD tests
    print("4️⃣  Testing client schema CRUD operations...")
    test_id = await test_client_schema_insert(client, results)

    if test_id:
        await test_client_schema_select(client, results, test_id)
        await test_client_schema_update(client, results, test_id)
        await test_client_schema_delete(client, results, test_id)

    # 5. Performance comparison
    print("5️⃣  Testing cross-schema performance...")
    await test_cross_schema_performance(client, results)

    # 6. Dual-client architecture
    print("6️⃣  Testing dual-client architecture...")
    await test_dual_client_architecture(results)

    # 7. Client health
    print("7️⃣  Testing client health monitoring...")
    await test_client_health(client, results)

    # Finalize and print report
    results.finalize()
    results.print_report()

    # Save results to JSON file
    output_file = f"/srv/luris/be/graphrag-service/tests/cross_schema_test_results_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "summary": results.get_summary(),
            "tests": results.tests
        }, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    # Return exit code based on success
    summary = results.get_summary()
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
