#!/usr/bin/env python3
"""
Create remaining graph schema tables systematically
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

async def create_graph_tables():
    """Create remaining graph schema tables."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🕸️  CREATING GRAPH SCHEMA TABLES")
    print("=" * 60)
    
    client = SupabaseClient(service_name="graph-table-creator", use_service_role=True)
    
    # Remaining graph schema tables (document_registry and embeddings already exist)
    graph_tables = [
        {
            'name': 'graph.chunks',
            'sql': '''
CREATE TABLE IF NOT EXISTS graph.chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id TEXT UNIQUE NOT NULL,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT CHECK (content_type IN ('text', 'heading', 'list', 'table', 'code')) DEFAULT 'text',
    token_count INTEGER,
    chunk_size INTEGER,
    overlap_size INTEGER DEFAULT 0,
    chunk_method TEXT DEFAULT 'simple',
    parent_chunk_id TEXT,
    context_before TEXT,
    context_after TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES graph.document_registry(document_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_graph_chunks_document_id ON graph.chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_graph_chunks_chunk_id ON graph.chunks(chunk_id);
CREATE INDEX IF NOT EXISTS idx_graph_chunks_parent ON graph.chunks(parent_chunk_id);
CREATE INDEX IF NOT EXISTS idx_graph_chunks_index ON graph.chunks(chunk_index);

GRANT SELECT ON graph.chunks TO anon, authenticated;
GRANT ALL ON graph.chunks TO service_role;
'''
        },
        {
            'name': 'graph.nodes',
            'sql': '''
CREATE TABLE IF NOT EXISTS graph.nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id TEXT UNIQUE NOT NULL,
    node_type TEXT CHECK (node_type IN ('entity', 'concept', 'document', 'chunk')) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source_id TEXT,
    source_type TEXT,
    node_degree INTEGER DEFAULT 0,
    community_id TEXT,
    rank_score FLOAT DEFAULT 0.0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_node_id ON graph.nodes(node_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph.nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_community ON graph.nodes(community_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_rank ON graph.nodes(rank_score DESC);

GRANT SELECT ON graph.nodes TO anon, authenticated;
GRANT ALL ON graph.nodes TO service_role;
'''
        },
        {
            'name': 'graph.edges',
            'sql': '''
CREATE TABLE IF NOT EXISTS graph.edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    edge_id TEXT UNIQUE NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    weight FLOAT DEFAULT 1.0,
    evidence TEXT,
    confidence_score FLOAT DEFAULT 1.0,
    extraction_method TEXT DEFAULT 'co_occurrence',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_node_id) REFERENCES graph.nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES graph.nodes(node_id) ON DELETE CASCADE,
    UNIQUE(source_node_id, target_node_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph.edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph.edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_relationship ON graph.edges(relationship_type);
CREATE INDEX IF NOT EXISTS idx_graph_edges_weight ON graph.edges(weight DESC);

GRANT SELECT ON graph.edges TO anon, authenticated;
GRANT ALL ON graph.edges TO service_role;
'''
        },
        {
            'name': 'graph.communities',
            'sql': '''
CREATE TABLE IF NOT EXISTS graph.communities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    community_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    level INTEGER DEFAULT 0,
    node_count INTEGER DEFAULT 0,
    edge_count INTEGER DEFAULT 0,
    coherence_score FLOAT DEFAULT 0.0,
    parent_community_id TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_community_id) REFERENCES graph.communities(community_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_communities_community_id ON graph.communities(community_id);
CREATE INDEX IF NOT EXISTS idx_graph_communities_level ON graph.communities(level);
CREATE INDEX IF NOT EXISTS idx_graph_communities_parent ON graph.communities(parent_community_id);
CREATE INDEX IF NOT EXISTS idx_graph_communities_coherence ON graph.communities(coherence_score DESC);

GRANT SELECT ON graph.communities TO anon, authenticated;
GRANT ALL ON graph.communities TO service_role;
'''
        },
        {
            'name': 'graph.reports',
            'sql': '''
CREATE TABLE IF NOT EXISTS graph.reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id TEXT UNIQUE NOT NULL,
    report_type TEXT CHECK (report_type IN ('global', 'community', 'node')) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    community_id TEXT,
    node_id TEXT,
    rating FLOAT DEFAULT 0.0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (community_id) REFERENCES graph.communities(community_id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES graph.nodes(node_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_graph_reports_report_id ON graph.reports(report_id);
CREATE INDEX IF NOT EXISTS idx_graph_reports_type ON graph.reports(report_type);
CREATE INDEX IF NOT EXISTS idx_graph_reports_community ON graph.reports(community_id);
CREATE INDEX IF NOT EXISTS idx_graph_reports_rating ON graph.reports(rating DESC);

GRANT SELECT ON graph.reports TO anon, authenticated;
GRANT ALL ON graph.reports TO service_role;
'''
        },
        {
            'name': 'graph.covariates',
            'sql': '''
CREATE TABLE IF NOT EXISTS graph.covariates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    covariate_id TEXT UNIQUE NOT NULL,
    subject_id TEXT NOT NULL,
    subject_type TEXT CHECK (subject_type IN ('node', 'edge', 'community')) NOT NULL,
    covariate_type TEXT NOT NULL,
    covariate_value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_graph_covariates_covariate_id ON graph.covariates(covariate_id);
CREATE INDEX IF NOT EXISTS idx_graph_covariates_subject ON graph.covariates(subject_id);
CREATE INDEX IF NOT EXISTS idx_graph_covariates_type ON graph.covariates(covariate_type);

GRANT SELECT ON graph.covariates TO anon, authenticated;
GRANT ALL ON graph.covariates TO service_role;
'''
        },
        {
            'name': 'graph.text_units',
            'sql': '''
CREATE TABLE IF NOT EXISTS graph.text_units (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    text_unit_id TEXT UNIQUE NOT NULL,
    chunk_id TEXT NOT NULL,
    text TEXT NOT NULL,
    n_tokens INTEGER,
    document_ids TEXT[],
    entity_ids TEXT[],
    relationship_ids TEXT[],
    covariate_ids TEXT[],
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES graph.chunks(chunk_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_graph_text_units_text_unit_id ON graph.text_units(text_unit_id);
CREATE INDEX IF NOT EXISTS idx_graph_text_units_chunk_id ON graph.text_units(chunk_id);
CREATE INDEX IF NOT EXISTS idx_graph_text_units_document_ids ON graph.text_units USING GIN(document_ids);

GRANT SELECT ON graph.text_units TO anon, authenticated;
GRANT ALL ON graph.text_units TO service_role;
'''
        }
    ]
    
    # Create graph schema views for REST API
    graph_views = [
        {
            'name': 'public.graph_chunks',
            'sql': '''
CREATE OR REPLACE VIEW public.graph_chunks AS SELECT * FROM graph.chunks;
GRANT SELECT ON public.graph_chunks TO anon, authenticated;
'''
        },
        {
            'name': 'public.graph_nodes',
            'sql': '''
CREATE OR REPLACE VIEW public.graph_nodes AS SELECT * FROM graph.nodes;
GRANT SELECT ON public.graph_nodes TO anon, authenticated;
'''
        },
        {
            'name': 'public.graph_edges',
            'sql': '''
CREATE OR REPLACE VIEW public.graph_edges AS SELECT * FROM graph.edges;
GRANT SELECT ON public.graph_edges TO anon, authenticated;
'''
        },
        {
            'name': 'public.graph_communities',
            'sql': '''
CREATE OR REPLACE VIEW public.graph_communities AS SELECT * FROM graph.communities;
GRANT SELECT ON public.graph_communities TO anon, authenticated;
'''
        },
        {
            'name': 'public.graph_reports',
            'sql': '''
CREATE OR REPLACE VIEW public.graph_reports AS SELECT * FROM graph.reports;
GRANT SELECT ON public.graph_reports TO anon, authenticated;
'''
        },
        {
            'name': 'public.graph_covariates',
            'sql': '''
CREATE OR REPLACE VIEW public.graph_covariates AS SELECT * FROM graph.covariates;
GRANT SELECT ON public.graph_covariates TO anon, authenticated;
'''
        },
        {
            'name': 'public.graph_text_units',
            'sql': '''
CREATE OR REPLACE VIEW public.graph_text_units AS SELECT * FROM graph.text_units;
GRANT SELECT ON public.graph_text_units TO anon, authenticated;
'''
        }
    ]
    
    success_count = 0
    
    # Create tables
    for table_def in graph_tables:
        print(f"Creating {table_def['name']}...")
        try:
            response = client.service_client.rpc('execute_sql', {'query': table_def['sql']}).execute()
            if response.data is not None:
                print(f"  ✅ {table_def['name']} created")
                success_count += 1
            else:
                print(f"  ✅ {table_def['name']} created (no response data)")
                success_count += 1
        except Exception as e:
            print(f"  ❌ {table_def['name']} failed: {str(e)[:100]}...")
    
    # Create views
    for view_def in graph_views:
        print(f"Creating {view_def['name']}...")
        try:
            response = client.service_client.rpc('execute_sql', {'query': view_def['sql']}).execute()
            print(f"  ✅ {view_def['name']} created")
        except Exception as e:
            print(f"  ❌ {view_def['name']} failed: {str(e)[:50]}...")
    
    print(f"\n📊 Created {success_count}/{len(graph_tables)} graph tables")
    
    # Test access to all graph views (including existing ones)
    print("\n🧪 Testing graph schema access...")
    graph_views_to_test = [
        'graph_document_registry', 'graph_embeddings', 'graph_chunks', 'graph_nodes', 
        'graph_edges', 'graph_communities', 'graph_reports', 'graph_covariates', 'graph_text_units'
    ]
    
    accessible = 0
    for view in graph_views_to_test:
        try:
            result = client.anon_client.table(view).select("*").limit(1).execute()
            print(f"  ✅ {view}: Accessible")
            accessible += 1
        except Exception as e:
            print(f"  ❌ {view}: {str(e)[:50]}...")
    
    print(f"\n🎯 Graph schema result: {accessible}/{len(graph_views_to_test)} views accessible")
    return accessible >= 7

if __name__ == "__main__":
    try:
        success = asyncio.run(create_graph_tables())
        print(f"\n{'✅ SUCCESS' if success else '❌ PARTIAL SUCCESS'}: Graph schema created")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)