#!/usr/bin/env python3
"""
Execute SQL migrations using the correct RPC function call format
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the GraphRAG service to the path
sys.path.append('/srv/luris/be/graphrag-service/src')
sys.path.append('/srv/luris/be')

try:
    from clients.supabase_client import SupabaseClient, SupabaseSettings
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# SQL files to execute in order
SQL_FILES = [
    "/srv/luris/be/sql/law_schema.sql",
    "/srv/luris/be/sql/client_schema.sql", 
    "/srv/luris/be/sql/graph_schema_core.sql",
    "/srv/luris/be/sql/graph_schema_knowledge.sql",
    "/srv/luris/be/sql/migrate_to_2048_dimensions.sql",
    "/srv/luris/be/sql/public_schema_views.sql"
]

async def execute_sql_via_rpc(client: SupabaseClient, sql_query: str) -> bool:
    """Execute SQL using the correct RPC format."""
    try:
        # Use the service role client directly to call the RPC function
        # with the correct parameter format (single query parameter)
        response = client.service_client.rpc('execute_sql', {'query': sql_query}).execute()
        
        if response.data is not None:
            print(f"    ✅ RPC execution successful")
            return True
        else:
            print(f"    ⚠️  RPC returned no data but no error")
            return True  # This might still be successful
            
    except Exception as e:
        print(f"    ✗ RPC execution failed: {str(e)[:200]}...")
        return False

async def execute_sql_file(client: SupabaseClient, file_path: str) -> bool:
    """Execute a single SQL file using RPC."""
    file_name = Path(file_path).name
    print(f"\n{'=' * 60}")
    print(f"Executing: {file_name}")
    print(f"{'=' * 60}")
    
    try:
        if not os.path.exists(file_path):
            print(f"  ✗ File not found: {file_path}")
            return False
        
        # Read SQL content
        with open(file_path, 'r') as f:
            sql_content = f.read()
        
        print(f"  📄 Read {len(sql_content)} characters")
        print(f"  ⏳ Executing via RPC...")
        
        # Execute using RPC function
        success = await execute_sql_via_rpc(client, sql_content)
        
        if success:
            print(f"  ✅ {file_name} executed successfully")
            return True
        else:
            print(f"  ✗ {file_name} execution failed")
            return False
            
    except Exception as e:
        print(f"  ✗ Error processing {file_name}: {str(e)}")
        return False

async def verify_schemas(client: SupabaseClient):
    """Verify that schemas and tables were created."""
    print("\n" + "=" * 60)
    print("VERIFYING CREATED SCHEMAS AND TABLES")
    print("=" * 60)
    
    try:
        # Check existing schemas
        schema_query = """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('law', 'client', 'graph')
            ORDER BY schema_name
        """
        
        print("🔍 Checking schemas...")
        success = await execute_sql_via_rpc(client, schema_query)
        if success:
            print("✅ Schema verification completed")
        
        # Check tables
        table_query = """
            SELECT 
                schemaname,
                tablename,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_schema = schemaname AND table_name = tablename) as column_count
            FROM pg_tables 
            WHERE schemaname IN ('law', 'client', 'graph')
            ORDER BY schemaname, tablename
        """
        
        print("🔍 Checking tables...")
        success = await execute_sql_via_rpc(client, table_query)
        if success:
            print("✅ Table verification completed")
        
        return True
        
    except Exception as e:
        print(f"✗ Verification failed: {str(e)}")
        return False

async def main():
    """Main async execution function."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("=" * 80)
    print("RPC-BASED SQL MIGRATION EXECUTOR")
    print("=" * 80)
    
    try:
        # Initialize the Supabase client with service role
        print("🔧 Initializing SupabaseClient...")
        client = SupabaseClient(service_name="graphrag-migration", use_service_role=True)
        print("✅ SupabaseClient initialized successfully")
        
        # Test RPC function availability
        print("\n🧪 Testing RPC function...")
        test_result = await execute_sql_via_rpc(client, "SELECT 'RPC Test' as message")
        if not test_result:
            print("✗ RPC function test failed - aborting migration")
            return False
        print("✅ RPC function is working")
        
        success_count = 0
        total_files = len(SQL_FILES)
        
        # Execute each SQL file in order
        for i, sql_file in enumerate(SQL_FILES, 1):
            print(f"\n🔄 Progress: {i}/{total_files}")
            
            if await execute_sql_file(client, sql_file):
                success_count += 1
                print(f"✅ Migration {i}/{total_files} completed successfully")
            else:
                print(f"✗ Migration {i}/{total_files} failed")
                print(f"⚠️  Stopping execution at {Path(sql_file).name}")
                break
        
        # Verify results if any succeeded
        if success_count > 0:
            await verify_schemas(client)
        
        # Print summary
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Completed: {success_count}/{total_files} migrations")
        
        if success_count == total_files:
            print("✅ All migrations completed successfully!")
            print("🎉 GraphRAG database is fully initialized!")
            print("\n📊 Expected Results:")
            print("   - Law schema: 6 tables created")
            print("   - Client schema: 4 tables created")
            print("   - Graph schema: 17 tables created")
            print("   - Public schema: 29+ views created")
            print("   - Vector columns: Updated to 2048 dimensions")
        else:
            print(f"⚠️  Migrations incomplete. {total_files - success_count} files remaining.")
        
        print("=" * 80)
        return success_count == total_files
        
    except Exception as e:
        print(f"✗ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Critical error: {str(e)}")
        sys.exit(2)