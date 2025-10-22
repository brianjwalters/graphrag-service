#!/usr/bin/env python3
"""
Create law schema tables systematically
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

async def create_law_tables():
    """Create law schema tables individually."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🏛️ CREATING LAW SCHEMA TABLES")
    print("=" * 60)
    
    client = SupabaseClient(service_name="law-table-creator", use_service_role=True)
    
    # Law schema tables in order
    law_tables = [
        {
            'name': 'law.documents',
            'sql': '''
CREATE SCHEMA IF NOT EXISTS law;

CREATE TABLE IF NOT EXISTS law.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    court_name TEXT,
    jurisdiction TEXT,
    date_filed DATE,
    citation TEXT,
    content_md TEXT,
    storage_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_law_documents_document_id ON law.documents(document_id);
CREATE INDEX IF NOT EXISTS idx_law_documents_court_name ON law.documents(court_name);
CREATE INDEX IF NOT EXISTS idx_law_documents_jurisdiction ON law.documents(jurisdiction);

GRANT USAGE ON SCHEMA law TO anon, authenticated, service_role;
GRANT SELECT ON law.documents TO anon, authenticated;
GRANT ALL ON law.documents TO service_role;
'''
        },
        {
            'name': 'law.citations',
            'sql': '''
CREATE TABLE IF NOT EXISTS law.citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citing_document_id TEXT NOT NULL,
    cited_document_id TEXT NOT NULL,
    citation_text TEXT NOT NULL,
    citation_context TEXT,
    page_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (citing_document_id) REFERENCES law.documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (cited_document_id) REFERENCES law.documents(document_id) ON DELETE CASCADE,
    UNIQUE(citing_document_id, cited_document_id, page_number)
);

CREATE INDEX IF NOT EXISTS idx_law_citations_citing ON law.citations(citing_document_id);
CREATE INDEX IF NOT EXISTS idx_law_citations_cited ON law.citations(cited_document_id);

GRANT SELECT ON law.citations TO anon, authenticated;
GRANT ALL ON law.citations TO service_role;
'''
        },
        {
            'name': 'law.entities',
            'sql': '''
CREATE TABLE IF NOT EXISTS law.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('person', 'organization', 'case', 'statute', 'regulation', 'court', 'judge')),
    entity_text TEXT NOT NULL,
    canonical_name TEXT,
    confidence_score FLOAT DEFAULT 1.0,
    extraction_method TEXT DEFAULT 'regex',
    context TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES law.documents(document_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_law_entities_document_id ON law.entities(document_id);
CREATE INDEX IF NOT EXISTS idx_law_entities_type ON law.entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_law_entities_canonical ON law.entities(canonical_name);

GRANT SELECT ON law.entities TO anon, authenticated;
GRANT ALL ON law.entities TO service_role;
'''
        },
        {
            'name': 'law.entity_relationships',
            'sql': '''
CREATE TABLE IF NOT EXISTS law.entity_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity_id UUID NOT NULL,
    target_entity_id UUID NOT NULL,
    relationship_type TEXT NOT NULL,
    relationship_strength FLOAT DEFAULT 1.0,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_entity_id) REFERENCES law.entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_entity_id) REFERENCES law.entities(id) ON DELETE CASCADE,
    UNIQUE(source_entity_id, target_entity_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_law_relationships_source ON law.entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_law_relationships_target ON law.entity_relationships(target_entity_id);

GRANT SELECT ON law.entity_relationships TO anon, authenticated;
GRANT ALL ON law.entity_relationships TO service_role;
'''
        }
    ]
    
    # Create law schema views for REST API
    law_views = [
        {
            'name': 'public.law_documents',
            'sql': '''
CREATE OR REPLACE VIEW public.law_documents AS SELECT * FROM law.documents;
GRANT SELECT ON public.law_documents TO anon, authenticated;
'''
        },
        {
            'name': 'public.law_citations',
            'sql': '''
CREATE OR REPLACE VIEW public.law_citations AS SELECT * FROM law.citations;
GRANT SELECT ON public.law_citations TO anon, authenticated;
'''
        },
        {
            'name': 'public.law_entities',
            'sql': '''
CREATE OR REPLACE VIEW public.law_entities AS SELECT * FROM law.entities;
GRANT SELECT ON public.law_entities TO anon, authenticated;
'''
        },
        {
            'name': 'public.law_entity_relationships',
            'sql': '''
CREATE OR REPLACE VIEW public.law_entity_relationships AS SELECT * FROM law.entity_relationships;
GRANT SELECT ON public.law_entity_relationships TO anon, authenticated;
'''
        }
    ]
    
    success_count = 0
    
    # Create tables
    for table_def in law_tables:
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
    for view_def in law_views:
        print(f"Creating {view_def['name']}...")
        try:
            response = client.service_client.rpc('execute_sql', {'query': view_def['sql']}).execute()
            print(f"  ✅ {view_def['name']} created")
        except Exception as e:
            print(f"  ❌ {view_def['name']} failed: {str(e)[:50]}...")
    
    print(f"\n📊 Created {success_count}/{len(law_tables)} law tables")
    
    # Test access to law views
    print("\n🧪 Testing law schema access...")
    law_views_to_test = ['law_documents', 'law_citations', 'law_entities', 'law_entity_relationships']
    
    accessible = 0
    for view in law_views_to_test:
        try:
            result = client.anon_client.table(view).select("*").limit(1).execute()
            print(f"  ✅ {view}: Accessible")
            accessible += 1
        except Exception as e:
            print(f"  ❌ {view}: {str(e)[:50]}...")
    
    print(f"\n🎯 Law schema result: {accessible}/{len(law_views_to_test)} views accessible")
    return accessible >= 3

if __name__ == "__main__":
    try:
        success = asyncio.run(create_law_tables())
        print(f"\n{'✅ SUCCESS' if success else '❌ PARTIAL SUCCESS'}: Law schema created")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)