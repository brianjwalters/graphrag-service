#!/usr/bin/env python3
"""
Execute SQL migrations step by step using basic SQL statements
"""
import os
import sys
import json
from pathlib import Path

# Add the GraphRAG service to the path
sys.path.append('/srv/luris/be/graphrag-service/src')
sys.path.append('/srv/luris/be')

try:
    from clients.supabase_client import SupabaseClient, SupabaseSettings
except ImportError as e:
    print(f"Import error: {e}")
    print("Available paths:", sys.path)
    sys.exit(1)

def main():
    """Execute basic schema creation using SupabaseClient."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("=" * 80)
    print("STEP-BY-STEP SQL EXECUTION")
    print("=" * 80)
    
    try:
        # Initialize the Supabase client with service role
        print("🔧 Initializing SupabaseClient...")
        client = SupabaseClient(service_name="graphrag-migration", use_service_role=True)
        print("✅ SupabaseClient initialized successfully")
        
        # Test 1: Try to create the law schema
        print("\n📝 Step 1: Creating law schema...")
        try:
            # Try using service role client for admin operations
            result = client.execute_sql(
                query="CREATE SCHEMA IF NOT EXISTS law;",
                admin_operation=True
            )
            print(f"✅ Law schema created: {result}")
        except Exception as e:
            print(f"⚠️  Schema creation via SQL failed: {str(e)}")
            
        # Test 2: Try to enable extensions
        print("\n📝 Step 2: Enabling required extensions...")
        extensions = [
            'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";',
            'CREATE EXTENSION IF NOT EXISTS "vector";',
            'CREATE EXTENSION IF NOT EXISTS "pg_trgm";'
        ]
        
        for ext_sql in extensions:
            try:
                result = client.execute_sql(query=ext_sql, admin_operation=True)
                print(f"✅ Extension enabled: {ext_sql[:40]}...")
            except Exception as e:
                print(f"⚠️  Extension failed: {ext_sql[:40]}... - {str(e)[:100]}")
        
        # Test 3: Check what schemas exist
        print("\n📝 Step 3: Checking existing schemas...")
        try:
            # Try to query existing schemas
            result = client.execute_sql(
                query="""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name IN ('law', 'client', 'graph', 'public')
                ORDER BY schema_name;
                """,
                admin_operation=True
            )
            print(f"✅ Current schemas: {result}")
        except Exception as e:
            print(f"⚠️  Schema query failed: {str(e)}")
            
        # Test 4: Try basic table operations
        print("\n📝 Step 4: Testing table access...")
        try:
            # Check what tables exist in public schema
            result = client.get("public", table="information_schema.tables", query={
                "table_schema": "eq.public",
                "limit": 10
            })
            print(f"✅ Public tables accessible: {len(result) if result else 0}")
        except Exception as e:
            print(f"⚠️  Table access failed: {str(e)[:100]}")
            
        print("\n=" * 80)
        print("STEP-BY-STEP EXECUTION COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"✗ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()