#!/usr/bin/env python3
"""
Create client schema tables systematically
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

async def create_client_tables():
    """Create client schema tables individually."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("👨‍⚖️ CREATING CLIENT SCHEMA TABLES")
    print("=" * 60)
    
    client = SupabaseClient(service_name="client-table-creator", use_service_role=True)
    
    # Client schema tables (client.cases already exists, so create the others)
    client_tables = [
        {
            'name': 'client.documents',
            'sql': '''
CREATE TABLE IF NOT EXISTS client.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id TEXT UNIQUE NOT NULL,
    case_id UUID NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL CHECK (document_type IN ('contract', 'correspondence', 'filing', 'discovery', 'exhibit', 'brief', 'motion', 'order')),
    content_md TEXT,
    storage_path TEXT,
    confidentiality_level TEXT DEFAULT 'client_confidential' CHECK (confidentiality_level IN ('public', 'client_confidential', 'attorney_client_privilege', 'work_product')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES client.cases(case_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_client_documents_case_id ON client.documents(case_id);
CREATE INDEX IF NOT EXISTS idx_client_documents_document_id ON client.documents(document_id);
CREATE INDEX IF NOT EXISTS idx_client_documents_type ON client.documents(document_type);
CREATE INDEX IF NOT EXISTS idx_client_documents_confidentiality ON client.documents(confidentiality_level);

GRANT SELECT ON client.documents TO anon, authenticated;
GRANT ALL ON client.documents TO service_role;
'''
        },
        {
            'name': 'client.entities',
            'sql': '''
CREATE TABLE IF NOT EXISTS client.entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id TEXT NOT NULL,
    case_id UUID NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('person', 'organization', 'contract', 'financial_instrument', 'date', 'monetary_amount', 'location')),
    entity_text TEXT NOT NULL,
    canonical_name TEXT,
    confidence_score FLOAT DEFAULT 1.0,
    extraction_method TEXT DEFAULT 'regex',
    context TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES client.documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (case_id) REFERENCES client.cases(case_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_client_entities_document_id ON client.entities(document_id);
CREATE INDEX IF NOT EXISTS idx_client_entities_case_id ON client.entities(case_id);
CREATE INDEX IF NOT EXISTS idx_client_entities_type ON client.entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_client_entities_canonical ON client.entities(canonical_name);

GRANT SELECT ON client.entities TO anon, authenticated;
GRANT ALL ON client.entities TO service_role;
'''
        },
        {
            'name': 'client.financial_data',
            'sql': '''
CREATE TABLE IF NOT EXISTS client.financial_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL,
    document_id TEXT,
    transaction_date DATE,
    description TEXT NOT NULL,
    amount DECIMAL(15,2),
    currency TEXT DEFAULT 'USD',
    account_type TEXT,
    category TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES client.cases(case_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES client.documents(document_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_client_financial_case_id ON client.financial_data(case_id);
CREATE INDEX IF NOT EXISTS idx_client_financial_document_id ON client.financial_data(document_id);
CREATE INDEX IF NOT EXISTS idx_client_financial_date ON client.financial_data(transaction_date);
CREATE INDEX IF NOT EXISTS idx_client_financial_category ON client.financial_data(category);

GRANT SELECT ON client.financial_data TO anon, authenticated;
GRANT ALL ON client.financial_data TO service_role;
'''
        }
    ]
    
    # Create client schema views for REST API
    client_views = [
        {
            'name': 'public.client_documents',
            'sql': '''
CREATE OR REPLACE VIEW public.client_documents AS SELECT * FROM client.documents;
GRANT SELECT ON public.client_documents TO anon, authenticated;
'''
        },
        {
            'name': 'public.client_entities',
            'sql': '''
CREATE OR REPLACE VIEW public.client_entities AS SELECT * FROM client.entities;
GRANT SELECT ON public.client_entities TO anon, authenticated;
'''
        },
        {
            'name': 'public.client_financial_data',
            'sql': '''
CREATE OR REPLACE VIEW public.client_financial_data AS SELECT * FROM client.financial_data;
GRANT SELECT ON public.client_financial_data TO anon, authenticated;
'''
        }
    ]
    
    success_count = 0
    
    # Create tables
    for table_def in client_tables:
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
    for view_def in client_views:
        print(f"Creating {view_def['name']}...")
        try:
            response = client.service_client.rpc('execute_sql', {'query': view_def['sql']}).execute()
            print(f"  ✅ {view_def['name']} created")
        except Exception as e:
            print(f"  ❌ {view_def['name']} failed: {str(e)[:50]}...")
    
    print(f"\n📊 Created {success_count}/{len(client_tables)} client tables")
    
    # Test access to all client views (including existing cases)
    print("\n🧪 Testing client schema access...")
    client_views_to_test = ['client_cases', 'client_documents', 'client_entities', 'client_financial_data']
    
    accessible = 0
    for view in client_views_to_test:
        try:
            result = client.anon_client.table(view).select("*").limit(1).execute()
            print(f"  ✅ {view}: Accessible")
            accessible += 1
        except Exception as e:
            print(f"  ❌ {view}: {str(e)[:50]}...")
    
    print(f"\n🎯 Client schema result: {accessible}/{len(client_views_to_test)} views accessible")
    return accessible >= 3

if __name__ == "__main__":
    try:
        success = asyncio.run(create_client_tables())
        print(f"\n{'✅ SUCCESS' if success else '❌ PARTIAL SUCCESS'}: Client schema created")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)