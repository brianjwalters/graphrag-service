#!/usr/bin/env python3
"""Test Supabase table name format requirements"""

import asyncio
from supabase import create_client
import os

async def test_table_names():
    # Get credentials from environment
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return
    
    client = create_client(url, key)
    
    print("Testing Supabase table name formats...")
    print("=" * 60)
    
    # Test 1: Dot notation "graph.nodes"
    print("\n Test 1: Using dot notation 'graph.nodes'")
    try:
        result = client.table("graph.nodes").select("*", count='exact').limit(1).execute()
        print(f"    ✅ SUCCESS: {result.count if hasattr(result, 'count') else 'N/A'} rows found")
    except Exception as e:
        print(f"    ❌ FAILED: {str(e)[:100]}")
    
    # Test 2: Underscore notation "graph_nodes"
    print("\n✦ Test 2: Using underscore notation 'graph_nodes'")
    try:
        result = client.table("graph_nodes").select("*", count='exact').limit(1).execute()
        print(f"    ✅ SUCCESS: {result.count if hasattr(result, 'count') else 'N/A'} rows found")
    except Exception as e:
        print(f"    ❌ FAILED: {str(e)[:100]}")
    
    # Test 3: Dot notation "graph.document_registry"
    print("\n✦ Test 3: Using dot notation 'graph.document_registry'")
    try:
        result = client.table("graph.document_registry").select("*", count='exact').limit(1).execute()
        print(f"    ✅ SUCCESS: {result.count if hasattr(result, 'count') else 'N/A'} rows found")
    except Exception as e:
        print(f"    ❌ FAILED: {str(e)[:100]}")
    
    # Test 4: Underscore notation "graph_document_registry"
    print("\n✦ Test 4: Using underscore notation 'graph_document_registry'")
    try:
        result = client.table("graph_document_registry").select("*", count='exact').limit(1).execute()
        print(f"    ✅ SUCCESS: {result.count if hasattr(result, 'count') else 'N/A'} rows found")
    except Exception as e:
        print(f"    ❌ FAILED: {str(e)[:100]}")
    
    print("\n" + "=" * 60)
    print("✅ Test complete")

if __name__ == "__main__":
    asyncio.run(test_table_names())
