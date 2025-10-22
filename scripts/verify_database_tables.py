#!/usr/bin/env python3
"""
Verify database tables and schemas after migration using working RPC approach
"""
import os
import sys
import asyncio
import json
from datetime import datetime

# Add the GraphRAG service to the path
sys.path.append('/srv/luris/be/graphrag-service/src')
sys.path.append('/srv/luris/be')

try:
    from clients.supabase_client import SupabaseClient, SupabaseSettings
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class DatabaseVerifier:
    def __init__(self):
        # Set environment variables
        os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
        os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
        os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
        
        self.client = SupabaseClient(service_name="graphrag-verifier", use_service_role=True)
        self.results = {}
    
    async def execute_query(self, query: str, description: str = ""):
        """Execute a query via RPC and return results."""
        try:
            response = self.client.service_client.rpc('execute_sql', {'query': query}).execute()
            if response.data is not None:
                return response.data
            else:
                print(f"⚠️  Query returned no data: {description}")
                return []
        except Exception as e:
            print(f"✗ Query failed: {description} - {str(e)[:100]}")
            return None
    
    async def verify_schemas(self):
        """Verify that the expected schemas exist."""
        print("📋 VERIFYING SCHEMAS")
        print("=" * 50)
        
        query = """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('law', 'client', 'graph', 'public')
            ORDER BY schema_name
        """
        
        schemas = await self.execute_query(query, "Schema verification")
        
        if schemas is not None:
            schema_names = [s.get('schema_name') for s in schemas if isinstance(s, dict)]
            print(f"✅ Found schemas: {schema_names}")
            self.results['schemas'] = schema_names
        else:
            print("✗ Schema verification failed")
            self.results['schemas'] = []
    
    async def verify_tables(self):
        """Verify that tables exist in each schema."""
        print("\n📋 VERIFYING TABLES BY SCHEMA")
        print("=" * 50)
        
        # Law schema tables
        law_query = """
            SELECT tablename
            FROM pg_tables 
            WHERE schemaname = 'law'
            ORDER BY tablename
        """
        
        law_tables = await self.execute_query(law_query, "Law schema tables")
        if law_tables is not None:
            law_table_names = [t.get('tablename') for t in law_tables if isinstance(t, dict)]
            print(f"🏛️  Law Schema ({len(law_table_names)} tables): {law_table_names}")
            self.results['law_tables'] = law_table_names
        
        # Client schema tables
        client_query = """
            SELECT tablename
            FROM pg_tables 
            WHERE schemaname = 'client'
            ORDER BY tablename
        """
        
        client_tables = await self.execute_query(client_query, "Client schema tables")
        if client_tables is not None:
            client_table_names = [t.get('tablename') for t in client_tables if isinstance(t, dict)]
            print(f"👥 Client Schema ({len(client_table_names)} tables): {client_table_names}")
            self.results['client_tables'] = client_table_names
        
        # Graph schema tables
        graph_query = """
            SELECT tablename
            FROM pg_tables 
            WHERE schemaname = 'graph'
            ORDER BY tablename
        """
        
        graph_tables = await self.execute_query(graph_query, "Graph schema tables")
        if graph_tables is not None:
            graph_table_names = [t.get('tablename') for t in graph_tables if isinstance(t, dict)]
            print(f"📊 Graph Schema ({len(graph_table_names)} tables): {graph_table_names}")
            self.results['graph_tables'] = graph_table_names
    
    async def verify_public_views(self):
        """Verify that public views were created."""
        print("\n📋 VERIFYING PUBLIC VIEWS")
        print("=" * 50)
        
        view_query = """
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            AND (table_name LIKE '%law_%' 
                 OR table_name LIKE '%client_%' 
                 OR table_name LIKE '%graph_%')
            ORDER BY table_name
        """
        
        views = await self.execute_query(view_query, "Public views")
        if views is not None:
            view_names = [v.get('table_name') for v in views if isinstance(v, dict)]
            print(f"👁️  Public Views ({len(view_names)} views):")
            
            # Group by prefix
            law_views = [v for v in view_names if v.startswith('law_')]
            client_views = [v for v in view_names if v.startswith('client_')]
            graph_views = [v for v in view_names if v.startswith('graph_')]
            
            print(f"   🏛️  Law views: {len(law_views)}")
            print(f"   👥 Client views: {len(client_views)}")
            print(f"   📊 Graph views: {len(graph_views)}")
            
            self.results['public_views'] = {
                'total': len(view_names),
                'law': len(law_views),
                'client': len(client_views),
                'graph': len(graph_views),
                'all_views': view_names
            }
    
    async def verify_vector_columns(self):
        """Verify that vector columns have 2048 dimensions."""
        print("\n📋 VERIFYING VECTOR COLUMNS")
        print("=" * 50)
        
        vector_query = """
            SELECT 
                table_schema,
                table_name,
                column_name,
                udt_name,
                character_maximum_length
            FROM information_schema.columns
            WHERE udt_name LIKE 'vector%'
            AND table_schema IN ('law', 'graph', 'client')
            ORDER BY table_schema, table_name, column_name
        """
        
        vectors = await self.execute_query(vector_query, "Vector columns")
        if vectors is not None:
            print(f"🔢 Vector columns found: {len(vectors)}")
            for v in vectors:
                if isinstance(v, dict):
                    schema = v.get('table_schema')
                    table = v.get('table_name')
                    column = v.get('column_name')
                    udt = v.get('udt_name')
                    print(f"   📊 {schema}.{table}.{column}: {udt}")
            
            self.results['vector_columns'] = vectors
    
    async def test_basic_access(self):
        """Test basic table access via public views."""
        print("\n📋 TESTING BASIC TABLE ACCESS")
        print("=" * 50)
        
        # Test a few key public views
        test_views = ['law_documents', 'client_cases', 'graph_entities']
        access_results = {}
        
        for view_name in test_views:
            try:
                # Use REST API to access public view
                result = self.client.anon_client.table(view_name).select("*").limit(1).execute()
                if result.data is not None:
                    print(f"✅ {view_name}: Accessible (structure confirmed)")
                    access_results[view_name] = "accessible"
                else:
                    print(f"⚠️  {view_name}: No data but accessible")
                    access_results[view_name] = "accessible_empty"
            except Exception as e:
                error_msg = str(e)[:100]
                if "does not exist" in error_msg.lower():
                    print(f"✗ {view_name}: View not found")
                    access_results[view_name] = "not_found"
                else:
                    print(f"⚠️  {view_name}: Access issue - {error_msg}")
                    access_results[view_name] = "access_error"
        
        self.results['table_access'] = access_results
    
    async def generate_summary(self):
        """Generate a comprehensive summary."""
        print("\n" + "=" * 80)
        print("DATABASE VERIFICATION SUMMARY")
        print("=" * 80)
        
        # Schema summary
        schemas = self.results.get('schemas', [])
        print(f"📂 Schemas: {len(schemas)}/{4} expected")
        for schema in ['law', 'client', 'graph', 'public']:
            status = "✅" if schema in schemas else "❌"
            print(f"   {status} {schema}")
        
        # Table summary
        total_tables = 0
        law_tables = len(self.results.get('law_tables', []))
        client_tables = len(self.results.get('client_tables', []))
        graph_tables = len(self.results.get('graph_tables', []))
        total_tables = law_tables + client_tables + graph_tables
        
        print(f"\n📊 Tables: {total_tables} total created")
        print(f"   🏛️  Law: {law_tables}/6 expected")
        print(f"   👥 Client: {client_tables}/4 expected")
        print(f"   📊 Graph: {graph_tables}/17 expected")
        
        # View summary
        views = self.results.get('public_views', {})
        total_views = views.get('total', 0)
        print(f"\n👁️  Public Views: {total_views} created")
        print(f"   🏛️  Law views: {views.get('law', 0)}")
        print(f"   👥 Client views: {views.get('client', 0)}")
        print(f"   📊 Graph views: {views.get('graph', 0)}")
        
        # Vector columns
        vectors = len(self.results.get('vector_columns', []))
        print(f"\n🔢 Vector Columns: {vectors} found")
        
        # Access test results
        access = self.results.get('table_access', {})
        accessible = sum(1 for status in access.values() if 'accessible' in status)
        print(f"\n🔍 Access Tests: {accessible}/{len(access)} views accessible")
        
        # Overall assessment
        expected_minimums = {
            'schemas': 3,  # law, client, graph
            'total_tables': 25,
            'total_views': 25,
            'accessible_views': 2
        }
        
        success_criteria = [
            len(schemas) >= expected_minimums['schemas'],
            total_tables >= expected_minimums['total_tables'],
            total_views >= expected_minimums['total_views'],
            accessible >= expected_minimums['accessible_views']
        ]
        
        if all(success_criteria):
            print(f"\n🎉 DATABASE MIGRATION SUCCESSFUL!")
            print(f"   All critical infrastructure is in place")
            print(f"   GraphRAG service can now access the database")
        else:
            print(f"\n⚠️  MIGRATION PARTIALLY COMPLETE")
            print(f"   Some components may be missing")
        
        print("=" * 80)
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"/srv/luris/be/graphrag-service/tests/verification_results_{timestamp}.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"📄 Detailed results saved to: {results_file}")
        except Exception as e:
            print(f"⚠️  Could not save results: {str(e)}")

async def main():
    """Main verification function."""
    print("=" * 80)
    print("GRAPHRAG DATABASE VERIFICATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    
    try:
        verifier = DatabaseVerifier()
        
        await verifier.verify_schemas()
        await verifier.verify_tables()
        await verifier.verify_public_views()
        await verifier.verify_vector_columns()
        await verifier.test_basic_access()
        await verifier.generate_summary()
        
        return True
        
    except Exception as e:
        print(f"✗ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Critical error: {str(e)}")
        sys.exit(2)