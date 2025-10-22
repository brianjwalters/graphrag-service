#!/usr/bin/env python3
"""Test script to verify GraphRAG service can create complex graphs."""

import asyncio
import httpx
import json
from datetime import datetime

async def test_graph_creation():
    """Test creating a graph with entities, relationships, and communities."""
    
    base_url = "http://localhost:8010"
    
    # Test data for graph creation
    test_data = {
        "document_id": f"test_doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "graph_id": f"test_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "client_id": "test_client",
        "case_id": "test_case",
        "markdown_content": """# Test Legal Document

The **Supreme Court** of the United States, under the leadership of **Chief Justice Roberts**, 
has made several landmark decisions interpreting the **First Amendment** to the Constitution.

The Court's jurisprudence on free speech has evolved significantly over the decades.""",
        "entities": [
            {
                "entity_id": "entity_001",
                "entity_text": "Supreme Court",
                "entity_type": "COURT",
                "confidence": 0.95,
                "attributes": {"level": "federal", "jurisdiction": "national"}
            },
            {
                "entity_id": "entity_002",
                "entity_text": "Chief Justice Roberts",
                "entity_type": "JUDGE",
                "confidence": 0.92,
                "attributes": {"position": "chief_justice"}
            },
            {
                "entity_id": "entity_003",
                "entity_text": "First Amendment",
                "entity_type": "LAW",
                "confidence": 0.98,
                "attributes": {"type": "constitutional"}
            }
        ],
        "relationships": [
            {
                "relationship_id": "rel_001",
                "source_entity": "entity_002",
                "target_entity": "entity_001",
                "relationship_type": "PRESIDES_OVER",
                "confidence": 0.9,
                "evidence": "Chief Justice Roberts presides over the Supreme Court"
            },
            {
                "relationship_id": "rel_002",
                "source_entity": "entity_001",
                "target_entity": "entity_003",
                "relationship_type": "INTERPRETS",
                "confidence": 0.85,
                "evidence": "Supreme Court interprets the First Amendment"
            }
        ],
        "citations": [],
        "enable_deduplication": True,
        "enable_community_detection": True,
        "enable_analytics": True,
        "enable_cross_document_links": False
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 1: Create graph
            print("Test 1: Creating graph...")
            response = await client.post(
                f"{base_url}/api/v1/graph/create",
                json=test_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Graph created successfully!")
                print(f"   - Entities: {result.get('entities_count', 0)}")
                print(f"   - Relationships: {result.get('relationships_count', 0)}")
                print(f"   - Communities: {result.get('communities_count', 0)}")
                
                # Pretty print the response
                print("\nFull response:")
                print(json.dumps(result, indent=2))
                
                return True
            else:
                print(f"❌ Graph creation failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            return False

async def test_graph_query():
    """Test querying the graph."""
    
    base_url = "http://localhost:8010"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 2: Query graph stats
            print("\nTest 2: Querying graph stats...")
            response = await client.get(f"{base_url}/api/v1/graph/stats")
            
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Graph stats retrieved:")
                print(f"   - Total nodes: {stats.get('nodes_count', 0)}")
                print(f"   - Total edges: {stats.get('edges_count', 0)}")
                print(f"   - Total communities: {stats.get('communities_count', 0)}")
                return True
            else:
                print(f"❌ Stats query failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Query test failed: {e}")
            return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("GraphRAG Service Test Suite")
    print("=" * 60)
    
    # Run tests
    test1_result = await test_graph_creation()
    test2_result = await test_graph_query()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Graph Creation: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"  Graph Query: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    print("=" * 60)
    
    all_passed = test1_result and test2_result
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)