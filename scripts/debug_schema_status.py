#!/usr/bin/env python3
"""
Debug what was actually created in the database
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

async def debug_database_status():
    """Check what actually exists in the database."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🔍 DEBUGGING DATABASE STATUS")
    print("=" * 60)
    
    client = SupabaseClient(service_name="debug-checker", use_service_role=True)
    
    # Check 1: What schemas exist?
    print("1. Checking schemas...")
    schema_query = """
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name IN ('law', 'client', 'graph', 'public')
        ORDER BY schema_name
    """
    
    try:
        response = client.service_client.rpc('execute_sql', {'query': schema_query}).execute()
        if response.data:
            schemas = [row.get('schema_name') for row in response.data if isinstance(row, dict)]
            print(f"   Found schemas: {schemas}")
        else:
            print("   No schema data returned")
    except Exception as e:
        print(f"   Schema check failed: {str(e)[:100]}")
    
    # Check 2: What tables exist in each schema?
    print("\n2. Checking tables in each schema...")
    
    for schema_name in ['law', 'client', 'graph']:
        table_query = f"""
            SELECT tablename
            FROM pg_tables 
            WHERE schemaname = '{schema_name}'
            ORDER BY tablename
        """
        
        try:
            response = client.service_client.rpc('execute_sql', {'query': table_query}).execute()
            if response.data:
                tables = [row.get('tablename') for row in response.data if isinstance(row, dict)]
                print(f"   {schema_name} schema: {tables}")
            else:
                print(f"   {schema_name} schema: No tables found")
        except Exception as e:
            print(f"   {schema_name} schema check failed: {str(e)[:100]}")
    
    # Check 3: What views exist in public schema?
    print("\n3. Checking public views...")
    view_query = """
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        AND (table_name LIKE 'law_%' OR table_name LIKE 'client_%' OR table_name LIKE 'graph_%')
        ORDER BY table_name
    """
    
    try:
        response = client.service_client.rpc('execute_sql', {'query': view_query}).execute()
        if response.data:
            views = [row.get('table_name') for row in response.data if isinstance(row, dict)]
            print(f"   Public views: {views}")
        else:
            print("   Public views: None found")
    except Exception as e:
        print(f"   View check failed: {str(e)[:100]}")
    
    # Check 4: Check for any errors in the last execution
    print("\n4. Testing a simple table creation...")
    test_query = """
        DO $$
        BEGIN
            CREATE SCHEMA IF NOT EXISTS test_schema;
            CREATE TABLE IF NOT EXISTS test_schema.test_table (id int);
            DROP TABLE test_schema.test_table;
            DROP SCHEMA test_schema;
            RAISE NOTICE 'Test creation and deletion successful';
        END $$;
    """
    
    try:
        response = client.service_client.rpc('execute_sql', {'query': test_query}).execute()
        print("   ✅ Basic SQL execution works")
    except Exception as e:
        print(f"   ❌ Basic SQL execution failed: {str(e)[:100]}")
    
    # Check 5: Check vector extension
    print("\n5. Checking vector extension...")
    vector_query = """
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname = 'vector'
    """
    
    try:
        response = client.service_client.rpc('execute_sql', {'query': vector_query}).execute()
        if response.data:
            print(f"   Vector extension: {response.data}")
        else:
            print("   Vector extension: Not found")
    except Exception as e:
        print(f"   Vector extension check failed: {str(e)[:100]}")

if __name__ == "__main__":
    try:
        asyncio.run(debug_database_status())
    except Exception as e:
        print(f"Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()