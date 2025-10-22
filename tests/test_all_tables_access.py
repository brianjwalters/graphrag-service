#!/usr/bin/env python3
"""
Comprehensive table access testing for GraphRAG SupabaseClient.
Tests all tables across law, graph, and client schemas.
Verifies both read and write operations with dual-client architecture.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4
import traceback

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import SupabaseClient
from src.core.config import get_settings

settings = get_settings()

class TableAccessTester:
    """Comprehensive table access testing for all schemas."""
    
    def __init__(self):
        self.client = SupabaseClient()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "law_schema": {},
            "graph_schema": {},
            "client_schema": {},
            "dual_client_tests": {},
            "errors": [],
            "summary": {}
        }
        
        # Define all known tables by schema
        self.law_tables = [
            "documents",
            "opinions", 
            "statutes",
            "regulations",
            "administrative_codes",
            "court_rules"
        ]
        
        self.graph_tables = [
            "documents",
            "document_registry",
            "entities",
            "entity_mentions",
            "relationships",
            "chunks",
            "communities",
            "community_members",
            "legal_provisions",
            "provision_relationships",
            "citation_graph"
        ]
        
        # Client schema tables will be discovered dynamically
        self.client_tables = []
    
    async def test_table_read(self, schema: str, table: str) -> Dict[str, Any]:
        """Test read access to a table."""
        result = {
            "table": f"{schema}.{table}",
            "read_access": False,
            "row_count": 0,
            "sample_data": None,
            "error": None
        }
        
        try:
            # Try to get row count and sample data
            response = await self.client.execute_sql(
                f"SELECT COUNT(*) as count FROM {schema}.{table}"
            )
            
            if response and "data" in response:
                result["read_access"] = True
                result["row_count"] = response["data"][0]["count"] if response["data"] else 0
                
                # Get sample row if table has data
                if result["row_count"] > 0:
                    sample_response = await self.client.execute_sql(
                        f"SELECT * FROM {schema}.{table} LIMIT 1"
                    )
                    if sample_response and "data" in sample_response and sample_response["data"]:
                        result["sample_data"] = {
                            "columns": list(sample_response["data"][0].keys()),
                            "first_row": sample_response["data"][0]
                        }
            
            print(f"✓ Read access to {schema}.{table}: {result['row_count']} rows")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"✗ Read access failed for {schema}.{table}: {str(e)}")
            
        return result
    
    async def test_table_write(self, schema: str, table: str) -> Dict[str, Any]:
        """Test write access to a table (insert/update/delete)."""
        result = {
            "table": f"{schema}.{table}",
            "insert_access": False,
            "update_access": False,
            "delete_access": False,
            "test_id": None,
            "error": None
        }
        
        # Skip write tests for certain system tables
        if table in ["court_rules", "administrative_codes", "regulations", "statutes", "opinions"]:
            result["error"] = "Skipped - protected reference table"
            return result
        
        test_id = str(uuid4())
        result["test_id"] = test_id
        
        try:
            # Prepare test data based on table
            test_data = self._prepare_test_data(schema, table, test_id)
            
            if not test_data:
                result["error"] = "Could not prepare test data for table"
                return result
            
            # Test INSERT
            try:
                insert_response = await self.client.insert(
                    f"{schema}.{table}",
                    test_data
                )
                if insert_response:
                    result["insert_access"] = True
                    print(f"  ✓ Insert to {schema}.{table}")
            except Exception as e:
                print(f"  ✗ Insert failed: {str(e)[:100]}")
            
            # Test UPDATE (if insert succeeded)
            if result["insert_access"]:
                try:
                    update_data = {"metadata": {"updated_at": datetime.now().isoformat()}}
                    update_response = await self.client.update(
                        f"{schema}.{table}",
                        update_data,
                        {"id": test_id}
                    )
                    if update_response:
                        result["update_access"] = True
                        print(f"  ✓ Update in {schema}.{table}")
                except Exception as e:
                    print(f"  ✗ Update failed: {str(e)[:100]}")
            
            # Test DELETE (cleanup)
            if result["insert_access"]:
                try:
                    delete_response = await self.client.delete(
                        f"{schema}.{table}",
                        {"id": test_id}
                    )
                    if delete_response:
                        result["delete_access"] = True
                        print(f"  ✓ Delete from {schema}.{table}")
                except Exception as e:
                    print(f"  ✗ Delete failed: {str(e)[:100]}")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"✗ Write test failed for {schema}.{table}: {str(e)[:100]}")
            
        return result
    
    def _prepare_test_data(self, schema: str, table: str, test_id: str) -> Optional[Dict]:
        """Prepare test data based on schema and table."""
        base_data = {
            "id": test_id,
            "created_at": datetime.now().isoformat(),
            "metadata": {"test": True, "tester": "TableAccessTester"}
        }
        
        # Schema-specific test data
        if schema == "law":
            if table == "documents":
                return {
                    **base_data,
                    "title": f"Test Document {test_id[:8]}",
                    "content": "Test content for access verification",
                    "document_type": "test",
                    "jurisdiction": "test"
                }
                
        elif schema == "graph":
            if table == "documents":
                return {
                    **base_data,
                    "source_id": test_id,
                    "title": f"Test Graph Document {test_id[:8]}",
                    "content": "Test graph document content",
                    "document_type": "test"
                }
            elif table == "entities":
                return {
                    **base_data,
                    "name": f"Test Entity {test_id[:8]}",
                    "entity_type": "test",
                    "description": "Test entity for access verification"
                }
            elif table == "chunks":
                return {
                    **base_data,
                    "document_id": test_id,
                    "content": "Test chunk content",
                    "chunk_index": 0,
                    "metadata": {"test": True}
                }
                
        elif schema == "client":
            # Generic test data for client schema
            return {
                **base_data,
                "name": f"Test Client Item {test_id[:8]}",
                "description": "Test item for client schema access"
            }
        
        return None
    
    async def discover_client_tables(self) -> List[str]:
        """Discover tables in the client schema."""
        try:
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'client' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            response = await self.client.execute_sql(query)
            
            if response and "data" in response:
                tables = [row["table_name"] for row in response["data"]]
                print(f"\nDiscovered {len(tables)} tables in client schema:")
                for table in tables:
                    print(f"  - client.{table}")
                return tables
            
        except Exception as e:
            print(f"Failed to discover client tables: {str(e)}")
            self.results["errors"].append(f"Client table discovery: {str(e)}")
            
        return []
    
    async def test_dual_client_access(self) -> Dict[str, Any]:
        """Test the difference between anon and service_role clients."""
        results = {
            "anon_client": {},
            "service_client": {},
            "differences": []
        }
        
        try:
            # Test with anon client (default)
            print("\n=== Testing with anon client ===")
            anon_test = await self.test_table_read("graph", "entities")
            results["anon_client"] = anon_test
            
            # Test with service client (if available)
            if hasattr(self.client, "_service_client"):
                print("\n=== Testing with service_role client ===")
                # Temporarily switch to service client
                original_client = self.client._client
                self.client._client = self.client._service_client
                
                service_test = await self.test_table_read("graph", "entities")
                results["service_client"] = service_test
                
                # Restore original client
                self.client._client = original_client
                
                # Compare results
                if anon_test["row_count"] != service_test["row_count"]:
                    results["differences"].append(
                        f"Row count difference: anon={anon_test['row_count']}, "
                        f"service={service_test['row_count']}"
                    )
            
        except Exception as e:
            results["error"] = str(e)
            print(f"Dual client test failed: {str(e)}")
            
        return results
    
    async def run_all_tests(self):
        """Run all table access tests."""
        print("=" * 80)
        print("COMPREHENSIVE TABLE ACCESS TESTING")
        print("=" * 80)
        print(f"Started at: {self.results['timestamp']}")
        print()
        
        # Test law schema tables
        print("\n" + "=" * 40)
        print("TESTING LAW SCHEMA TABLES")
        print("=" * 40)
        for table in self.law_tables:
            read_result = await self.test_table_read("law", table)
            write_result = await self.test_table_write("law", table)
            self.results["law_schema"][table] = {
                "read": read_result,
                "write": write_result
            }
            print()
        
        # Test graph schema tables
        print("\n" + "=" * 40)
        print("TESTING GRAPH SCHEMA TABLES")
        print("=" * 40)
        for table in self.graph_tables:
            read_result = await self.test_table_read("graph", table)
            write_result = await self.test_table_write("graph", table)
            self.results["graph_schema"][table] = {
                "read": read_result,
                "write": write_result
            }
            print()
        
        # Discover and test client schema tables
        print("\n" + "=" * 40)
        print("DISCOVERING & TESTING CLIENT SCHEMA")
        print("=" * 40)
        self.client_tables = await self.discover_client_tables()
        for table in self.client_tables:
            read_result = await self.test_table_read("client", table)
            write_result = await self.test_table_write("client", table)
            self.results["client_schema"][table] = {
                "read": read_result,
                "write": write_result
            }
            print()
        
        # Test dual-client architecture
        print("\n" + "=" * 40)
        print("TESTING DUAL-CLIENT ARCHITECTURE")
        print("=" * 40)
        dual_results = await self.test_dual_client_access()
        self.results["dual_client_tests"] = dual_results
        
        # Generate summary
        self._generate_summary()
        
        # Save results
        await self._save_results()
        
        # Print summary
        self._print_summary()
    
    def _generate_summary(self):
        """Generate test summary statistics."""
        summary = {
            "total_tables_tested": 0,
            "successful_reads": 0,
            "successful_writes": 0,
            "failed_operations": 0,
            "total_rows_found": 0,
            "schemas_tested": ["law", "graph", "client"],
            "dual_client_working": False
        }
        
        # Count successes across all schemas
        for schema_name, schema_results in [
            ("law", self.results["law_schema"]),
            ("graph", self.results["graph_schema"]),
            ("client", self.results["client_schema"])
        ]:
            for table_name, table_results in schema_results.items():
                summary["total_tables_tested"] += 1
                
                if table_results["read"]["read_access"]:
                    summary["successful_reads"] += 1
                    summary["total_rows_found"] += table_results["read"]["row_count"]
                
                if table_results["write"].get("insert_access"):
                    summary["successful_writes"] += 1
                
                if table_results["read"].get("error") or table_results["write"].get("error"):
                    summary["failed_operations"] += 1
        
        # Check dual client
        if self.results["dual_client_tests"]:
            if not self.results["dual_client_tests"].get("error"):
                summary["dual_client_working"] = True
        
        self.results["summary"] = summary
    
    def _print_summary(self):
        """Print test summary to console."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        s = self.results["summary"]
        print(f"Total Tables Tested: {s['total_tables_tested']}")
        print(f"Successful Reads: {s['successful_reads']}")
        print(f"Successful Writes: {s['successful_writes']}")
        print(f"Failed Operations: {s['failed_operations']}")
        print(f"Total Rows Found: {s['total_rows_found']:,}")
        print(f"Schemas Tested: {', '.join(s['schemas_tested'])}")
        print(f"Dual Client Working: {'✓' if s['dual_client_working'] else '✗'}")
        
        if self.results["errors"]:
            print(f"\nErrors Encountered: {len(self.results['errors'])}")
            for error in self.results["errors"][:5]:  # Show first 5 errors
                print(f"  - {error[:100]}")
        
        print("\n" + "=" * 80)
    
    async def _save_results(self):
        """Save test results to file."""
        output_file = Path(__file__).parent / f"table_access_results_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        try:
            with open(output_file, "w") as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Failed to save results: {str(e)}")


async def main():
    """Main test execution."""
    tester = TableAccessTester()
    
    try:
        await tester.run_all_tests()
        
        # Return appropriate exit code
        if tester.results["summary"]["failed_operations"] > 0:
            print("\n⚠️  Some operations failed. Check results for details.")
            sys.exit(1)
        else:
            print("\n✓ All tests completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n✗ Critical test failure: {str(e)}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())