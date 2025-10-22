#!/usr/bin/env python3
"""
Test specific table access via public views to confirm migration success
"""
import os
import sys
import asyncio

# Add the GraphRAG service to the path
sys.path.append('/srv/luris/be/graphrag-service/src')
sys.path.append('/srv/luris/be')

try:
    from clients.supabase_client import SupabaseClient, SupabaseSettings
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

async def main():
    """Test direct access to public views that should exist."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("=" * 80)
    print("SPECIFIC ACCESS TESTING")
    print("=" * 80)
    
    client = SupabaseClient(service_name="access-tester", use_service_role=False)
    
    # Test public views that should exist based on our migration
    test_views = [
        # Law schema views
        'law_documents', 'law_opinions', 'law_statutes', 'law_regulations',
        'law_administrative_codes', 'law_court_rules',
        
        # Client schema views  
        'client_cases', 'client_documents', 'client_parties', 'client_deadlines',
        
        # Graph schema views (selection)
        'graph_entities', 'graph_relationships', 'graph_document_registry',
        'graph_chunks', 'graph_embeddings', 'graph_communities'
    ]
    
    accessible_views = []
    missing_views = []
    
    print("🔍 Testing public view access...")
    
    for view_name in test_views:
        try:
            # Try to access the view with minimal select
            result = client.anon_client.table(view_name).select("*").limit(1).execute()
            if result.data is not None:
                print(f"✅ {view_name}: Accessible")
                accessible_views.append(view_name)
            else:
                print(f"⚠️  {view_name}: Accessible but empty")
                accessible_views.append(view_name)
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg.lower() or "not found" in error_msg.lower():
                print(f"❌ {view_name}: Not found")
                missing_views.append(view_name)
            else:
                print(f"⚠️  {view_name}: Error - {error_msg[:50]}...")
    
    print(f"\n📊 RESULTS:")
    print(f"   ✅ Accessible views: {len(accessible_views)}/{len(test_views)}")
    print(f"   ❌ Missing views: {len(missing_views)}")
    
    if accessible_views:
        print(f"\n✅ ACCESSIBLE VIEWS:")
        for view in accessible_views:
            print(f"   - {view}")
    
    if missing_views:
        print(f"\n❌ MISSING VIEWS:")
        for view in missing_views:
            print(f"   - {view}")
    
    # Test a few direct table operations via service role
    print(f"\n🔧 Testing service role access to schema tables...")
    
    try:
        # Try to query a law table directly
        response = client.service_client.rpc('execute_sql', {
            'query': "SELECT COUNT(*) as count FROM law.documents LIMIT 1"
        }).execute()
        if response.data:
            print(f"✅ law.documents table accessible via service role")
        else:
            print(f"⚠️  law.documents query returned no data")
    except Exception as e:
        print(f"❌ law.documents not accessible: {str(e)[:50]}...")
    
    try:
        # Try to query a graph table directly  
        response = client.service_client.rpc('execute_sql', {
            'query': "SELECT COUNT(*) as count FROM graph.entities LIMIT 1"
        }).execute()
        if response.data:
            print(f"✅ graph.entities table accessible via service role")
        else:
            print(f"⚠️  graph.entities query returned no data")
    except Exception as e:
        print(f"❌ graph.entities not accessible: {str(e)[:50]}...")
    
    # Summary
    success_rate = len(accessible_views) / len(test_views)
    
    print(f"\n{'=' * 80}")
    print(f"ACCESS TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"Success Rate: {success_rate:.1%} ({len(accessible_views)}/{len(test_views)})")
    
    if success_rate >= 0.8:  # 80% or more accessible
        print(f"🎉 MIGRATION SUCCESSFUL!")
        print(f"   Most views are accessible - GraphRAG service should work")
    elif success_rate >= 0.5:  # 50% or more accessible
        print(f"⚠️  MIGRATION PARTIALLY SUCCESSFUL")
        print(f"   Some views missing - may need investigation")
    else:
        print(f"❌ MIGRATION ISSUES DETECTED")
        print(f"   Many views missing - needs troubleshooting")
    
    print(f"{'=' * 80}")
    
    return success_rate >= 0.5

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Critical error: {str(e)}")
        sys.exit(2)