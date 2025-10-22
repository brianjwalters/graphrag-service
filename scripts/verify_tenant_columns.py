#!/usr/bin/env python3
"""
Verify tenant columns using GraphRAG's SupabaseClient
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import SupabaseClient

async def verify_tenant_columns():
    """Verify tenant columns were added to all graph tables"""
    
    print("🔍 Verifying Tenant Columns in Graph Schema")
    print("=" * 60)
    
    # Initialize client
    client = SupabaseClient()
    
    # Tables to check
    tables = [
        "graph.document_registry",
        "graph.contextual_chunks",
        "graph.embeddings",
        "graph.nodes",
        "graph.edges",
        "graph.communities"
    ]
    
    print("\n📊 Checking for tenant columns...")
    print("-" * 40)
    
    all_success = True
    
    for table in tables:
        table_name = table.split('.')[1]
        print(f"\n✔️  Checking {table}:")
        
        try:
            # Try to select with the new columns
            result = await client.select(
                table,
                columns="id, client_id, case_id",
                limit=1
            )
            
            if result.get("success"):
                print(f"   ✅ Both client_id and case_id columns exist")
                
                # Check if we can filter by these columns
                filter_test = await client.select(
                    table,
                    columns="id",
                    filters={"client_id": "is.null"},
                    limit=1
                )
                
                if filter_test.get("success"):
                    print(f"   ✅ Can filter by tenant columns")
            else:
                error = result.get("error", "Unknown error")
                if "column" in str(error).lower():
                    print(f"   ❌ Missing tenant columns")
                    all_success = False
                else:
                    print(f"   ⚠️  Unexpected error: {error}")
                    
        except Exception as e:
            print(f"   ❌ Error checking table: {e}")
            all_success = False
    
    # Test the helper functions
    print("\n📊 Testing helper functions...")
    print("-" * 40)
    
    try:
        # Test graph.get_client_documents
        test_client_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        
        result = await client.rpc(
            "get_client_documents",
            {"p_client_id": test_client_id},
            schema="graph"
        )
        
        if result.get("success"):
            count = len(result.get("data", []))
            print(f"✅ get_client_documents function works (returned {count} docs)")
        else:
            print(f"❌ get_client_documents function failed: {result.get('error')}")
            
    except Exception as e:
        print(f"⚠️  Helper functions may not exist yet: {e}")
    
    # Test the views
    print("\n📊 Testing views...")
    print("-" * 40)
    
    try:
        # Test vw_client_documents
        result = await client.select(
            "graph.vw_client_documents",
            columns="id, client_id, case_id",
            limit=1
        )
        
        if result.get("success"):
            print("✅ vw_client_documents view exists and is accessible")
        else:
            print(f"❌ vw_client_documents view error: {result.get('error')}")
            
        # Test vw_public_documents
        result = await client.select(
            "graph.vw_public_documents",
            columns="id, client_id, case_id",
            limit=1
        )
        
        if result.get("success"):
            print("✅ vw_public_documents view exists and is accessible")
        else:
            print(f"❌ vw_public_documents view error: {result.get('error')}")
            
    except Exception as e:
        print(f"⚠️  Views may not exist yet: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 MIGRATION VERIFICATION SUMMARY")
    print("=" * 60)
    
    if all_success:
        print("✅ All tenant columns successfully added!")
        print("\n🎯 Next Steps:")
        print("1. Update GraphRAG service to populate tenant columns")
        print("2. Add tenant filtering to all queries")
        print("3. Test with sample client data")
    else:
        print("⚠️  Some issues detected - check output above")
        print("\nTroubleshooting:")
        print("1. Check if migration completed fully")
        print("2. Verify foreign key constraints")
        print("3. Check database logs for errors")

if __name__ == "__main__":
    asyncio.run(verify_tenant_columns())