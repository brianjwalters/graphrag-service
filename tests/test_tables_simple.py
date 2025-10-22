#!/usr/bin/env python3
"""
Simple table access testing using standard CRUD methods.
Tests all tables across law, graph, and client schemas using Supabase REST API.
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

class SimpleTableTester:
    """Simple table access testing using standard CRUD operations."""
    
    def __init__(self):
        self.client = SupabaseClient()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tables_tested": {},
            "summary": {
                "total_tables": 0,
                "accessible_tables": 0,
                "tables_with_data": 0,
                "total_rows": 0,
                "errors": []
            }
        }
        
        # Define all tables to test (using REST API naming convention)
        self.tables_to_test = [
            # Law schema tables
            "law_documents",
            "law_opinions", 
            "law_statutes",
            "law_regulations",
            "law_administrative_codes",
            "law_court_rules",
            
            # Graph schema tables
            "graph_documents",
            "graph_document_registry",
            "graph_entities",
            "graph_entity_mentions",
            "graph_relationships",
            "graph_chunks",
            "graph_communities",
            "graph_community_members",
            "graph_legal_provisions",
            "graph_provision_relationships",
            "graph_citation_graph",
            
            # Client schema tables (common ones)
            "client_documents",
            "client_contracts",
            "client_matters",
            "client_entities",
            "client_correspondence"
        ]
    
    async def test_table_access(self, table_name: str) -> Dict[str, Any]:
        """Test access to a table using standard get method."""
        result = {
            "table": table_name,
            "accessible": False,
            "row_count": 0,
            "sample_columns": [],
            "error": None,
            "has_data": False
        }
        
        try:
            # Try to get data from the table (limit to 5 rows for testing)
            response = await self.client.get(
                table_name,
                limit=5
            )
            
            if response is not None:
                result["accessible"] = True
                
                # Check if we got any data
                if isinstance(response, list):
                    result["row_count"] = len(response)
                    result["has_data"] = len(response) > 0
                    
                    # Get column names from first row if available
                    if len(response) > 0 and isinstance(response[0], dict):
                        result["sample_columns"] = list(response[0].keys())
                        
                    print(f"✓ {table_name}: Accessible, {len(response)} rows retrieved")
                else:
                    print(f"✓ {table_name}: Accessible, no data format info")
            else:
                print(f"✓ {table_name}: Accessible but empty")
                result["accessible"] = True
                
        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg[:200]  # Truncate long errors
            
            # Check if it's a "not found" error (table doesn't exist)
            if "404" in error_msg or "not found" in error_msg.lower():
                print(f"✗ {table_name}: Table not found")
            else:
                print(f"✗ {table_name}: {error_msg[:100]}")
        
        return result
    
    async def test_write_access(self, table_name: str) -> Dict[str, Any]:
        """Test write access to a table."""
        result = {
            "table": table_name,
            "can_insert": False,
            "can_update": False,
            "can_delete": False,
            "error": None
        }
        
        # Skip write tests for reference/system tables
        protected_tables = [
            "law_opinions", "law_statutes", "law_regulations", 
            "law_administrative_codes", "law_court_rules"
        ]
        
        if table_name in protected_tables:
            result["error"] = "Protected reference table - skipping write test"
            return result
        
        test_id = str(uuid4())
        
        try:
            # Prepare minimal test data
            test_data = {
                "id": test_id,
                "test_field": "access_test",
                "created_at": datetime.now().isoformat()
            }
            
            # Adjust data based on known table structures
            if "documents" in table_name:
                test_data = {
                    "id": test_id,
                    "title": f"Test Document {test_id[:8]}",
                    "content": "Test content",
                    "document_type": "test"
                }
            elif "entities" in table_name:
                test_data = {
                    "id": test_id,
                    "name": f"Test Entity {test_id[:8]}",
                    "entity_type": "test"
                }
            
            # Test INSERT
            try:
                insert_result = await self.client.insert(table_name, test_data)
                if insert_result:
                    result["can_insert"] = True
                    print(f"  ✓ Can insert to {table_name}")
                    
                    # Try to clean up
                    try:
                        delete_result = await self.client.delete(
                            table_name,
                            {"id": test_id}
                        )
                        if delete_result:
                            result["can_delete"] = True
                            print(f"  ✓ Can delete from {table_name}")
                    except:
                        pass
                        
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"  ✗ Cannot insert to {table_name}: {error_msg}")
                
        except Exception as e:
            result["error"] = str(e)[:200]
            
        return result
    
    async def run_all_tests(self):
        """Run all table access tests."""
        print("=" * 80)
        print("SIMPLE TABLE ACCESS TESTING")
        print("=" * 80)
        print(f"Started at: {self.results['timestamp']}")
        print(f"Testing {len(self.tables_to_test)} tables...")
        print()
        
        # Test each table
        for table_name in self.tables_to_test:
            self.results["summary"]["total_tables"] += 1
            
            # Test read access
            read_result = await self.test_table_access(table_name)
            
            # Test write access for accessible tables
            write_result = None
            if read_result["accessible"]:
                self.results["summary"]["accessible_tables"] += 1
                if read_result["has_data"]:
                    self.results["summary"]["tables_with_data"] += 1
                    self.results["summary"]["total_rows"] += read_result["row_count"]
                
                # Test write access
                write_result = await self.test_write_access(table_name)
            
            # Store results
            self.results["tables_tested"][table_name] = {
                "read": read_result,
                "write": write_result
            }
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        # Print summary
        self._print_summary()
        
        # Save results
        self._save_results()
    
    def _print_summary(self):
        """Print test summary."""
        s = self.results["summary"]
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Tables Tested: {s['total_tables']}")
        print(f"Accessible Tables: {s['accessible_tables']}")
        print(f"Tables With Data: {s['tables_with_data']}")
        print(f"Total Rows Found: {s['total_rows']}")
        
        # List accessible tables
        if s['accessible_tables'] > 0:
            print("\nAccessible Tables:")
            for table_name, results in self.results["tables_tested"].items():
                if results["read"]["accessible"]:
                    row_info = f" ({results['read']['row_count']} rows)" if results["read"]["has_data"] else " (empty)"
                    print(f"  - {table_name}{row_info}")
        
        # List tables with errors
        error_tables = [
            table for table, results in self.results["tables_tested"].items()
            if results["read"].get("error") and "not found" not in str(results["read"]["error"]).lower()
        ]
        
        if error_tables:
            print(f"\nTables with Errors: {len(error_tables)}")
            for table in error_tables[:5]:  # Show first 5
                print(f"  - {table}")
        
        print("=" * 80)
    
    def _save_results(self):
        """Save results to file."""
        output_file = Path(__file__).parent / f"simple_test_results_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        try:
            with open(output_file, "w") as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"\nResults saved to: {output_file}")
        except Exception as e:
            print(f"Failed to save results: {str(e)}")


async def main():
    """Main test execution."""
    tester = SimpleTableTester()
    
    try:
        await tester.run_all_tests()
        
        # Return exit code based on results
        if tester.results["summary"]["accessible_tables"] == 0:
            print("\n✗ No tables were accessible!")
            sys.exit(1)
        else:
            print(f"\n✓ Successfully accessed {tester.results['summary']['accessible_tables']} tables")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())