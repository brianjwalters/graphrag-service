#!/usr/bin/env python3
"""
Fix the embeddings table without vector index (due to 2000 dim limit)
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

async def fix_embeddings_table_no_index():
    """Fix the embeddings table without vector index."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🔧 FIXING EMBEDDINGS TABLE (NO VECTOR INDEX)")
    print("=" * 60)
    print("⚠️  Vector index skipped due to 2000-dimension limit")
    
    client = SupabaseClient(service_name="embeddings-no-index-fixer", use_service_role=True)
    
    # Drop and recreate the embeddings table without vector index
    fix_sql = '''
-- Drop existing view and table if they exist
DROP VIEW IF EXISTS public.graph_embeddings;
DROP TABLE IF EXISTS graph.embeddings CASCADE;

-- Recreate embeddings table with correct structure for 2048 dimensions
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

-- Create non-vector indexes only
CREATE INDEX IF NOT EXISTS idx_graph_embeddings_source ON graph.embeddings(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_embeddings_type ON graph.embeddings(source_type);
CREATE INDEX IF NOT EXISTS idx_graph_embeddings_embedding_type ON graph.embeddings(embedding_type);

-- Set permissions
GRANT SELECT ON graph.embeddings TO anon, authenticated;
GRANT ALL ON graph.embeddings TO service_role;

-- Create public view
CREATE OR REPLACE VIEW public.graph_embeddings AS SELECT * FROM graph.embeddings;
GRANT SELECT ON public.graph_embeddings TO anon, authenticated;

SELECT 'Embeddings table fixed without vector index' as status;
'''
    
    print("Creating graph.embeddings table without vector index...")
    try:
        response = client.service_client.rpc('execute_sql', {'query': fix_sql}).execute()
        if response.data:
            print(f"  ✅ Embeddings table created: {response.data}")
        else:
            print("  ✅ Embeddings table created (no response data)")
            
        # Test access
        print("\n🧪 Testing embeddings table access...")
        result = client.anon_client.table('graph_embeddings').select("*").limit(1).execute()
        print("  ✅ graph_embeddings: Accessible")
        
        print("\n💡 NOTE: Vector similarity search will use brute force (slower)")
        print("   Consider upgrading pgvector for 2048-dimension indexes")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Fix failed: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(fix_embeddings_table_no_index())
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Embeddings table fixed")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)