#!/usr/bin/env python3
"""
Create only the core tables needed for GraphRAG to work
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

async def create_core_tables():
    """Create core tables individually with error reporting."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🏗️  CREATING CORE GRAPHRAG TABLES")
    print("=" * 60)
    
    client = SupabaseClient(service_name="core-table-creator", use_service_role=True)
    
    # Core tables we absolutely need
    core_table_sqls = [
        {
            'name': 'client.cases',
            'sql': '''
CREATE SCHEMA IF NOT EXISTS client;
CREATE TABLE IF NOT EXISTS client.cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID UNIQUE NOT NULL,
    client_id UUID NOT NULL,
    case_number TEXT NOT NULL,
    caption TEXT NOT NULL,
    court TEXT,
    judge TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
GRANT USAGE ON SCHEMA client TO anon, authenticated, service_role;
GRANT SELECT ON client.cases TO anon, authenticated;
GRANT ALL ON client.cases TO service_role;
'''
        },
        {
            'name': 'graph.document_registry',
            'sql': '''
CREATE SCHEMA IF NOT EXISTS graph;
CREATE TABLE IF NOT EXISTS graph.document_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    source_schema TEXT,
    status TEXT DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
GRANT USAGE ON SCHEMA graph TO anon, authenticated, service_role;
GRANT SELECT ON graph.document_registry TO anon, authenticated;
GRANT ALL ON graph.document_registry TO service_role;
'''
        },
        {
            'name': 'graph.embeddings',
            'sql': '''
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS graph.embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    vector vector(2048) NOT NULL,
    embedding_type TEXT DEFAULT 'content',
    model_name TEXT DEFAULT 'jinaai/jina-embeddings-v4-vllm-code',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, source_type, embedding_type)
);
CREATE INDEX IF NOT EXISTS idx_graph_embeddings_vector ON graph.embeddings 
USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);
GRANT SELECT ON graph.embeddings TO anon, authenticated;
GRANT ALL ON graph.embeddings TO service_role;
'''
        }
    ]
    
    # Public views
    public_views = [
        {
            'name': 'public.client_cases',
            'sql': '''
CREATE OR REPLACE VIEW public.client_cases AS SELECT * FROM client.cases;
GRANT SELECT ON public.client_cases TO anon, authenticated;
'''
        },
        {
            'name': 'public.graph_document_registry', 
            'sql': '''
CREATE OR REPLACE VIEW public.graph_document_registry AS SELECT * FROM graph.document_registry;
GRANT SELECT ON public.graph_document_registry TO anon, authenticated;
'''
        },
        {
            'name': 'public.graph_embeddings',
            'sql': '''
CREATE OR REPLACE VIEW public.graph_embeddings AS SELECT * FROM graph.embeddings;
GRANT SELECT ON public.graph_embeddings TO anon, authenticated;
'''
        }
    ]
    
    success_count = 0
    
    # Create core tables
    for table_def in core_table_sqls:
        print(f"Creating {table_def['name']}...")
        try:
            response = client.service_client.rpc('execute_sql', {'query': table_def['sql']}).execute()
            if response.data is not None:
                print(f"  ✅ {table_def['name']} created")
                success_count += 1
            else:
                print(f"  ⚠️  {table_def['name']} - no response data")
        except Exception as e:
            print(f"  ❌ {table_def['name']} failed: {str(e)[:100]}")
    
    # Create public views
    for view_def in public_views:
        print(f"Creating {view_def['name']}...")
        try:
            response = client.service_client.rpc('execute_sql', {'query': view_def['sql']}).execute()
            if response.data is not None:
                print(f"  ✅ {view_def['name']} created")
            else:
                print(f"  ⚠️  {view_def['name']} - no response data")
        except Exception as e:
            print(f"  ❌ {view_def['name']} failed: {str(e)[:100]}")
    
    print(f"\n📊 Created {success_count}/{len(core_table_sqls)} core tables")
    
    # Test access
    print("\n🧪 Testing access to created tables...")
    test_views = ['client_cases', 'graph_document_registry', 'graph_embeddings']
    
    accessible = 0
    for view in test_views:
        try:
            result = client.anon_client.table(view).select("*").limit(1).execute()
            print(f"  ✅ {view}: Accessible")
            accessible += 1
        except Exception as e:
            print(f"  ❌ {view}: {str(e)[:50]}...")
    
    print(f"\n🎯 Result: {accessible}/{len(test_views)} views accessible")
    return accessible >= 2

if __name__ == "__main__":
    try:
        success = asyncio.run(create_core_tables())
        print(f"\n{'✅ SUCCESS' if success else '❌ PARTIAL SUCCESS'}: Core tables created")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)