#!/usr/bin/env python3
"""
Fix the embeddings table and view specifically
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

async def fix_embeddings_table():
    """Fix the embeddings table and view."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🔧 FIXING EMBEDDINGS TABLE")
    print("=" * 60)
    
    client = SupabaseClient(service_name="embeddings-fixer", use_service_role=True)
    
    # Drop and recreate the embeddings table and view
    fix_sql = '''
-- Drop existing view and table if they exist
DROP VIEW IF EXISTS public.graph_embeddings;
DROP TABLE IF EXISTS graph.embeddings;

-- Recreate embeddings table with correct structure
CREATE TABLE graph.embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id TEXT NOT NULL,
    source_type TEXT CHECK (source_type IN ('chunk', 'node', 'community')) NOT NULL,
    vector vector(2048) NOT NULL,
    embedding_type TEXT CHECK (embedding_type IN ('content', 'semantic', 'summary')) DEFAULT 'content',
    model_name TEXT DEFAULT 'jinaai/jina-embeddings-v4-vllm-code',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, source_type, embedding_type)
);

-- Create vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_graph_embeddings_vector ON graph.embeddings 
USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

-- Create other indexes
CREATE INDEX IF NOT EXISTS idx_graph_embeddings_source ON graph.embeddings(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_embeddings_type ON graph.embeddings(source_type);

-- Set permissions
GRANT SELECT ON graph.embeddings TO anon, authenticated;
GRANT ALL ON graph.embeddings TO service_role;

-- Create public view
CREATE OR REPLACE VIEW public.graph_embeddings AS SELECT * FROM graph.embeddings;
GRANT SELECT ON public.graph_embeddings TO anon, authenticated;

SELECT 'Embeddings table fixed' as status;
'''
    
    print("Fixing graph.embeddings table...")
    try:
        response = client.service_client.rpc('execute_sql', {'query': fix_sql}).execute()
        if response.data:
            print(f"  ✅ Embeddings table fixed: {response.data}")
        else:
            print("  ✅ Embeddings table fixed (no response data)")
            
        # Test access
        print("\n🧪 Testing embeddings table access...")
        result = client.anon_client.table('graph_embeddings').select("*").limit(1).execute()
        print("  ✅ graph_embeddings: Accessible")
        return True
        
    except Exception as e:
        print(f"  ❌ Fix failed: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(fix_embeddings_table())
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Embeddings table fixed")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)