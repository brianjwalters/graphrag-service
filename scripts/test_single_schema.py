#!/usr/bin/env python3
"""
Test single schema creation with detailed error reporting
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

async def test_law_schema():
    """Test law schema creation with error details."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🧪 TESTING LAW SCHEMA CREATION")
    print("=" * 60)
    
    client = SupabaseClient(service_name="single-schema-test", use_service_role=True)
    
    # Test just creating the law schema first
    simple_law_schema = """
-- Simple law schema test
CREATE SCHEMA law;

CREATE TABLE law.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions
GRANT USAGE ON SCHEMA law TO anon, authenticated, service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA law TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA law TO service_role;

SELECT 'Law schema test completed' as status;
"""
    
    print("1. Testing simple law schema creation...")
    try:
        response = client.service_client.rpc('execute_sql', {'query': simple_law_schema}).execute()
        print(f"   Response: {response.data}")
        
        # Check if it was created
        check_query = "SELECT tablename FROM pg_tables WHERE schemaname = 'law'"
        check_response = client.service_client.rpc('execute_sql', {'query': check_query}).execute()
        print(f"   Tables created: {check_response.data}")
        
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
    
    # Test 2: Try creating a public view
    print("\n2. Testing public view creation...")
    view_sql = """
CREATE OR REPLACE VIEW public.law_documents AS
SELECT * FROM law.documents;

GRANT SELECT ON public.law_documents TO anon, authenticated;

SELECT 'Public view created' as status;
"""
    
    try:
        response = client.service_client.rpc('execute_sql', {'query': view_sql}).execute()
        print(f"   Response: {response.data}")
        
        # Test if we can access the view
        try:
            result = client.anon_client.table('law_documents').select("*").limit(1).execute()
            print(f"   ✅ View accessible: {len(result.data) if result.data else 0} rows")
        except Exception as ve:
            print(f"   ❌ View access failed: {str(ve)[:100]}")
        
    except Exception as e:
        print(f"   ❌ View creation failed: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(test_law_schema())
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()