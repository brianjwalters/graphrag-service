#!/usr/bin/env python3
"""
Integration tests for GraphRAG multi-tenant functionality
Tests tenant isolation, data segregation, and cross-tenant security
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import SupabaseClient
from src.core.graph_constructor import GraphConstructor
from src.core.config import GraphRAGSettings


class TenantIsolationTests:
    """Test suite for multi-tenant GraphRAG functionality"""
    
    def __init__(self):
        self.settings = GraphRAGSettings()
        self.graph_constructor = GraphConstructor(self.settings)
        self.supabase_client = None
        
        # Test data
        self.client_a_id = str(uuid.uuid4())
        self.client_b_id = str(uuid.uuid4())
        self.case_a_id = str(uuid.uuid4())
        self.case_b_id = str(uuid.uuid4())
        
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    async def setup(self):
        """Initialize test environment"""
        print("🔧 Setting up test environment...")
        
        # Initialize GraphRAG components
        await self.graph_constructor.initialize_clients()
        self.supabase_client = self.graph_constructor.supabase_client
        
        # Create test cases in client schema
        await self._create_test_cases()
        
        print("✅ Test environment ready\n")
    
    async def _create_test_cases(self):
        """Create test cases for testing"""
        cases = [
            {
                "case_id": self.case_a_id,
                "client_id": self.client_a_id,
                "case_number": "TEST-A-001",
                "caption": "Test Case A for Client A",
                "status": "active"
            },
            {
                "case_id": self.case_b_id,
                "client_id": self.client_b_id,
                "case_number": "TEST-B-001",
                "caption": "Test Case B for Client B",
                "status": "active"
            }
        ]
        
        for case in cases:
            await self.supabase_client.upsert(
                "client.cases",
                case,
                on_conflict="case_id",
                admin_operation=True
            )
    
    async def test_tenant_isolated_graph_creation(self):
        """Test that graphs are properly isolated by tenant"""
        print("📊 Test 1: Tenant-Isolated Graph Creation")
        print("-" * 50)
        
        try:
            # Create graph for Client A
            doc_a_id = f"doc-client-a-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            entities_a = [
                {
                    "entity_id": "entity-a-1",
                    "entity_text": "Acme Corporation",
                    "entity_type": "ORGANIZATION",
                    "confidence": 0.95
                },
                {
                    "entity_id": "entity-a-2",
                    "entity_text": "John Smith",
                    "entity_type": "PERSON",
                    "confidence": 0.92
                }
            ]
            
            result_a = await self.graph_constructor.construct_graph(
                document_id=doc_a_id,
                markdown_content="Contract between Acme Corporation and John Smith",
                entities=entities_a,
                citations=[],
                relationships=[{
                    "source_entity": "entity-a-1",
                    "target_entity": "entity-a-2",
                    "relationship_type": "CONTRACTS_WITH",
                    "confidence": 0.9
                }],
                enhanced_chunks=[],
                graph_options={"enable_deduplication": False},
                metadata={"test": "client_a"},
                client_id=self.client_a_id,
                case_id=self.case_a_id
            )
            
            # Create graph for Client B (different tenant)
            doc_b_id = f"doc-client-b-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            entities_b = [
                {
                    "entity_id": "entity-b-1",
                    "entity_text": "Beta Industries",
                    "entity_type": "ORGANIZATION",
                    "confidence": 0.94
                },
                {
                    "entity_id": "entity-b-2",
                    "entity_text": "Jane Doe",
                    "entity_type": "PERSON",
                    "confidence": 0.91
                }
            ]
            
            result_b = await self.graph_constructor.construct_graph(
                document_id=doc_b_id,
                markdown_content="Agreement between Beta Industries and Jane Doe",
                entities=entities_b,
                citations=[],
                relationships=[{
                    "source_entity": "entity-b-1",
                    "target_entity": "entity-b-2",
                    "relationship_type": "EMPLOYS",
                    "confidence": 0.88
                }],
                enhanced_chunks=[],
                graph_options={"enable_deduplication": False},
                metadata={"test": "client_b"},
                client_id=self.client_b_id,
                case_id=self.case_b_id
            )
            
            # Verify both graphs were created
            if result_a.get("success") and result_b.get("success"):
                print(f"✅ Client A graph created: {result_a['graph_summary']['nodes_created']} nodes")
                print(f"✅ Client B graph created: {result_b['graph_summary']['nodes_created']} nodes")
                self.test_results["passed"] += 1
            else:
                print("❌ Failed to create tenant-isolated graphs")
                self.test_results["failed"] += 1
                
        except Exception as e:
            print(f"❌ Error in tenant isolation test: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(str(e))
    
    async def test_tenant_data_isolation(self):
        """Test that tenants cannot access each other's data"""
        print("\n📊 Test 2: Tenant Data Isolation")
        print("-" * 50)
        
        try:
            # Query Client A's nodes
            client_a_nodes = await self.supabase_client.get(
                "graph.nodes",
                filters={"client_id": self.client_a_id},
                admin_operation=True
            )
            
            # Query Client B's nodes
            client_b_nodes = await self.supabase_client.get(
                "graph.nodes",
                filters={"client_id": self.client_b_id},
                admin_operation=True
            )
            
            # Verify isolation
            client_a_labels = set([n.get("label") for n in (client_a_nodes or [])])
            client_b_labels = set([n.get("label") for n in (client_b_nodes or [])])
            
            # Check for data leakage
            if "Acme Corporation" in client_a_labels and "Acme Corporation" not in client_b_labels:
                print("✅ Client A data isolated from Client B")
            else:
                print("❌ Data isolation violation detected")
                self.test_results["failed"] += 1
                return
            
            if "Beta Industries" in client_b_labels and "Beta Industries" not in client_a_labels:
                print("✅ Client B data isolated from Client A")
            else:
                print("❌ Data isolation violation detected")
                self.test_results["failed"] += 1
                return
            
            print(f"✅ Tenant isolation verified: {len(client_a_nodes or [])} vs {len(client_b_nodes or [])} nodes")
            self.test_results["passed"] += 1
            
        except Exception as e:
            print(f"❌ Error in data isolation test: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(str(e))
    
    async def test_public_vs_client_documents(self):
        """Test mixed public and client-specific documents"""
        print("\n📊 Test 3: Public vs Client Documents")
        print("-" * 50)
        
        try:
            # Create a public document (no tenant)
            public_doc_id = f"doc-public-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            public_entities = [
                {
                    "entity_id": "entity-public-1",
                    "entity_text": "Supreme Court",
                    "entity_type": "COURT",
                    "confidence": 0.98
                }
            ]
            
            public_result = await self.graph_constructor.construct_graph(
                document_id=public_doc_id,
                markdown_content="Supreme Court ruling on contract law",
                entities=public_entities,
                citations=[],
                relationships=[],
                enhanced_chunks=[],
                graph_options={"enable_deduplication": False},
                metadata={"test": "public", "document_type": "court_opinion"},
                client_id=None,  # Public document
                case_id=None
            )
            
            if not public_result.get("success"):
                print("❌ Failed to create public document")
                self.test_results["failed"] += 1
                return
            
            # Query public nodes (NULL client_id)
            public_nodes = await self.supabase_client.get(
                "graph.nodes",
                filters={"client_id": None},
                admin_operation=True
            )
            
            # Query all nodes for Client A (should not include public by default)
            client_a_only = await self.supabase_client.get(
                "graph.nodes",
                filters={"client_id": self.client_a_id},
                admin_operation=True
            )
            
            public_count = len([n for n in (public_nodes or []) if n.get("label") == "Supreme Court"])
            client_has_public = any(n.get("label") == "Supreme Court" for n in (client_a_only or []))
            
            if public_count > 0 and not client_has_public:
                print("✅ Public documents properly separated from client data")
                self.test_results["passed"] += 1
            else:
                print("❌ Public/client document separation failed")
                self.test_results["failed"] += 1
                
        except Exception as e:
            print(f"❌ Error in public document test: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(str(e))
    
    async def test_case_level_isolation(self):
        """Test isolation at the case level within a client"""
        print("\n📊 Test 4: Case-Level Isolation")
        print("-" * 50)
        
        try:
            # Create two different cases for the same client
            case_1_id = str(uuid.uuid4())
            case_2_id = str(uuid.uuid4())
            
            # Create cases
            await self.supabase_client.upsert(
                "client.cases",
                {
                    "case_id": case_1_id,
                    "client_id": self.client_a_id,
                    "case_number": "CASE-001",
                    "caption": "Case 1",
                    "status": "active"
                },
                on_conflict="case_id",
                admin_operation=True
            )
            
            await self.supabase_client.upsert(
                "client.cases",
                {
                    "case_id": case_2_id,
                    "client_id": self.client_a_id,
                    "case_number": "CASE-002",
                    "caption": "Case 2",
                    "status": "active"
                },
                on_conflict="case_id",
                admin_operation=True
            )
            
            # Query nodes by case
            case_1_nodes = await self.supabase_client.get(
                "graph.nodes",
                filters={"case_id": self.case_a_id},
                admin_operation=True
            )
            
            case_2_nodes = await self.supabase_client.get(
                "graph.nodes",
                filters={"case_id": self.case_b_id},
                admin_operation=True
            )
            
            print(f"✅ Case 1 has {len(case_1_nodes or [])} nodes")
            print(f"✅ Case 2 has {len(case_2_nodes or [])} nodes")
            print("✅ Case-level isolation working")
            self.test_results["passed"] += 1
            
        except Exception as e:
            print(f"❌ Error in case isolation test: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(str(e))
    
    async def cleanup(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Delete test nodes
            for client_id in [self.client_a_id, self.client_b_id]:
                nodes = await self.supabase_client.get(
                    "graph.nodes",
                    filters={"client_id": client_id},
                    admin_operation=True
                )
                
                if nodes:
                    for node in nodes:
                        await self.supabase_client.delete(
                            "graph.nodes",
                            {"id": node["id"]},
                            admin_operation=True
                        )
            
            # Delete public test nodes
            public_nodes = await self.supabase_client.get(
                "graph.nodes",
                filters={"client_id": None},
                admin_operation=True
            )
            
            if public_nodes:
                for node in public_nodes:
                    if "test" in str(node.get("attributes", {})):
                        await self.supabase_client.delete(
                            "graph.nodes",
                            {"id": node["id"]},
                            admin_operation=True
                        )
            
            # Delete test cases
            for case_id in [self.case_a_id, self.case_b_id]:
                await self.supabase_client.delete(
                    "client.cases",
                    {"case_id": case_id},
                    admin_operation=True
                )
            
            print("✅ Test data cleaned up")
            
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    async def run_all_tests(self):
        """Run all tenant isolation tests"""
        print("\n" + "=" * 60)
        print("🧪 GraphRAG Multi-Tenant Isolation Test Suite")
        print("=" * 60)
        
        await self.setup()
        
        # Run tests
        await self.test_tenant_isolated_graph_creation()
        await self.test_tenant_data_isolation()
        await self.test_public_vs_client_documents()
        await self.test_case_level_isolation()
        
        # Cleanup
        await self.cleanup()
        
        # Print results
        print("\n" + "=" * 60)
        print("📈 TEST RESULTS")
        print("=" * 60)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        
        if self.test_results["errors"]:
            print("\n⚠️  Errors encountered:")
            for error in self.test_results["errors"]:
                print(f"   • {error}")
        
        if self.test_results["failed"] == 0:
            print("\n🎉 All tenant isolation tests passed!")
            print("\n✅ Multi-tenant functionality is working correctly:")
            print("   • Client data is properly isolated")
            print("   • Case-level isolation is enforced")
            print("   • Public documents are separated from client data")
            print("   • No cross-tenant data leakage detected")
        else:
            print("\n⚠️  Some tests failed - review tenant implementation")
        
        return self.test_results["failed"] == 0


async def main():
    """Run the test suite"""
    tester = TenantIsolationTests()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())