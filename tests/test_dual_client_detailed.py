#!/usr/bin/env python3
"""
Detailed dual-client architecture testing.
Tests the difference between anon and service_role clients.
Discovers actual schema tables using service client.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Add parent directory to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import SupabaseClient

class DualClientTester:
    """Test dual-client architecture and permissions."""
    
    def __init__(self):
        self.client = SupabaseClient()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "client_comparison": {},
            "discovered_tables": {
                "law": [],
                "graph": [], 
                "client": []
            },
            "permission_differences": [],
            "summary": {}
        }
    
    async def test_dual_client_comparison(self):
        """Compare access between anon and service clients."""
        print("=" * 80)
        print("TESTING DUAL-CLIENT ARCHITECTURE")
        print("=" * 80)
        
        # Test tables that should show different access patterns
        test_tables = [
            "law_documents",
            "graph_entities",
            "graph_document_registry",
            "client_documents"
        ]
        
        for table in test_tables:
            print(f"\nTesting {table}:")
            comparison = {
                "table": table,
                "anon_access": {},
                "service_access": {},
                "differences": []
            }
            
            # Test with anon client (default)
            print("  With anon client:")
            try:
                anon_result = await self.client.get(table, limit=2)
                comparison["anon_access"] = {
                    "accessible": True,
                    "row_count": len(anon_result) if anon_result else 0,
                    "error": None
                }
                print(f"    ✓ Accessible, {comparison['anon_access']['row_count']} rows")
            except Exception as e:
                comparison["anon_access"] = {
                    "accessible": False,
                    "row_count": 0,
                    "error": str(e)[:100]
                }
                print(f"    ✗ Not accessible: {str(e)[:50]}")
            
            # Test with service client (admin=True)
            print("  With service_role client:")
            try:
                service_result = await self.client.get(table, limit=2, admin_operation=True)
                comparison["service_access"] = {
                    "accessible": True,
                    "row_count": len(service_result) if service_result else 0,
                    "error": None
                }
                print(f"    ✓ Accessible, {comparison['service_access']['row_count']} rows")
            except Exception as e:
                comparison["service_access"] = {
                    "accessible": False,
                    "row_count": 0,
                    "error": str(e)[:100]
                }
                print(f"    ✗ Not accessible: {str(e)[:50]}")
            
            # Compare results
            if comparison["anon_access"]["accessible"] != comparison["service_access"]["accessible"]:
                diff = f"Access difference: anon={comparison['anon_access']['accessible']}, service={comparison['service_access']['accessible']}"
                comparison["differences"].append(diff)
                self.results["permission_differences"].append(f"{table}: {diff}")
            
            if (comparison["anon_access"]["accessible"] and comparison["service_access"]["accessible"] and 
                comparison["anon_access"]["row_count"] != comparison["service_access"]["row_count"]):
                diff = f"Row count difference: anon={comparison['anon_access']['row_count']}, service={comparison['service_access']['row_count']}"
                comparison["differences"].append(diff)
                self.results["permission_differences"].append(f"{table}: {diff}")
            
            self.results["client_comparison"][table] = comparison
    
    async def discover_schema_tables(self):
        """Try to discover actual tables in each schema using different methods."""
        print("\n" + "=" * 80)
        print("DISCOVERING SCHEMA TABLES")
        print("=" * 80)
        
        # Method 1: Try known table patterns
        known_patterns = {
            "law": ["documents", "opinions", "statutes", "regulations", "cases", "citations"],
            "graph": ["entities", "relationships", "documents", "chunks", "communities", "document_registry"],
            "client": ["documents", "contracts", "matters", "entities", "correspondence", "notes"]
        }
        
        for schema, tables in known_patterns.items():
            print(f"\nTesting {schema} schema tables:")
            found_tables = []
            
            for table in tables:
                table_name = f"{schema}_{table}"
                try:
                    # Try with service client for better access
                    result = await self.client.get(table_name, limit=1, admin_operation=True)
                    if result is not None:
                        found_tables.append(table)
                        print(f"  ✓ {table_name} exists")
                except Exception as e:
                    if "does not exist" not in str(e):
                        # Table might exist but have access issues
                        print(f"  ? {table_name} may exist (access error)")
                    else:
                        print(f"  ✗ {table_name} not found")
            
            self.results["discovered_tables"][schema] = found_tables
    
    async def test_permission_operations(self):
        """Test specific operations that might differ between clients."""
        print("\n" + "=" * 80)
        print("TESTING PERMISSION-SENSITIVE OPERATIONS")
        print("=" * 80)
        
        test_results = {}
        
        # Test 1: Try to insert a test record
        print("\n1. Testing INSERT permissions on graph_entities:")
        test_id = str(uuid4())
        test_entity = {
            "id": test_id,
            "entity_name": f"Test Entity {test_id[:8]}",
            "entity_type": "test_permission",
            "confidence_score": 0.99,
            "created_at": datetime.now().isoformat()
        }
        
        # Try with anon client
        print("  With anon client:")
        try:
            anon_insert = await self.client.insert("graph_entities", test_entity, admin_operation=False)
            print(f"    ✓ Insert successful")
            test_results["anon_insert"] = True
            
            # Try to delete
            await self.client.delete("graph_entities", {"id": test_id}, admin_operation=False)
        except Exception as e:
            print(f"    ✗ Insert failed: {str(e)[:100]}")
            test_results["anon_insert"] = False
        
        # Try with service client
        print("  With service_role client:")
        try:
            service_insert = await self.client.insert("graph_entities", test_entity, admin_operation=True)
            print(f"    ✓ Insert successful")
            test_results["service_insert"] = True
            
            # Try to delete
            await self.client.delete("graph_entities", {"id": test_id}, admin_operation=True)
        except Exception as e:
            print(f"    ✗ Insert failed: {str(e)[:100]}")
            test_results["service_insert"] = False
        
        # Test 2: Try to access potentially restricted data
        print("\n2. Testing access to potentially restricted tables:")
        restricted_tables = ["auth_users", "auth_audit", "storage_objects"]
        
        for table in restricted_tables:
            print(f"  Testing {table}:")
            
            # Anon client
            try:
                await self.client.get(table, limit=1, admin_operation=False)
                print(f"    Anon: ✓ Accessible")
                test_results[f"{table}_anon"] = True
            except:
                print(f"    Anon: ✗ Not accessible")
                test_results[f"{table}_anon"] = False
            
            # Service client
            try:
                await self.client.get(table, limit=1, admin_operation=True)
                print(f"    Service: ✓ Accessible")
                test_results[f"{table}_service"] = True
            except:
                print(f"    Service: ✗ Not accessible")
                test_results[f"{table}_service"] = False
        
        self.results["permission_tests"] = test_results
    
    async def run_all_tests(self):
        """Run all dual-client tests."""
        print("=" * 80)
        print("DUAL-CLIENT ARCHITECTURE TESTING")
        print("=" * 80)
        print(f"Started at: {self.results['timestamp']}")
        print()
        
        # Check if dual-client is properly configured
        has_service_client = hasattr(self.client, '_service_client') and self.client._service_client is not None
        print(f"Service client configured: {'✓' if has_service_client else '✗'}")
        
        if not has_service_client:
            print("⚠️  Service client not configured. Some tests may be limited.")
        
        # Run tests
        await self.test_dual_client_comparison()
        await self.discover_schema_tables()
        await self.test_permission_operations()
        
        # Generate summary
        self._generate_summary()
        
        # Save results
        self._save_results()
        
        # Print summary
        self._print_summary()
    
    def _generate_summary(self):
        """Generate test summary."""
        self.results["summary"] = {
            "dual_client_configured": hasattr(self.client, '_service_client') and self.client._service_client is not None,
            "tables_tested": len(self.results["client_comparison"]),
            "permission_differences_found": len(self.results["permission_differences"]),
            "law_tables_discovered": len(self.results["discovered_tables"]["law"]),
            "graph_tables_discovered": len(self.results["discovered_tables"]["graph"]),
            "client_tables_discovered": len(self.results["discovered_tables"]["client"])
        }
    
    def _print_summary(self):
        """Print test summary."""
        s = self.results["summary"]
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Dual Client Configured: {'✓' if s['dual_client_configured'] else '✗'}")
        print(f"Tables Tested: {s['tables_tested']}")
        print(f"Permission Differences Found: {s['permission_differences_found']}")
        
        if s['permission_differences_found'] > 0:
            print("\nPermission Differences:")
            for diff in self.results["permission_differences"][:5]:
                print(f"  - {diff}")
        
        print(f"\nDiscovered Tables:")
        print(f"  Law Schema: {s['law_tables_discovered']} tables")
        if self.results["discovered_tables"]["law"]:
            print(f"    Tables: {', '.join(self.results['discovered_tables']['law'])}")
        
        print(f"  Graph Schema: {s['graph_tables_discovered']} tables")
        if self.results["discovered_tables"]["graph"]:
            print(f"    Tables: {', '.join(self.results['discovered_tables']['graph'])}")
        
        print(f"  Client Schema: {s['client_tables_discovered']} tables")
        if self.results["discovered_tables"]["client"]:
            print(f"    Tables: {', '.join(self.results['discovered_tables']['client'])}")
        
        print("=" * 80)
    
    def _save_results(self):
        """Save results to file."""
        output_file = Path(__file__).parent / f"dual_client_results_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        try:
            with open(output_file, "w") as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Failed to save results: {str(e)}")


async def main():
    """Main test execution."""
    tester = DualClientTester()
    
    try:
        await tester.run_all_tests()
        sys.exit(0)
            
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())