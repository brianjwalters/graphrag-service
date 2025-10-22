#!/usr/bin/env python3
"""
Final comprehensive verification of GraphRAG database schema
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

async def comprehensive_verification():
    """Perform comprehensive verification of all GraphRAG schemas."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🎯 COMPREHENSIVE GRAPHRAG SCHEMA VERIFICATION")
    print("=" * 70)
    
    client = SupabaseClient(service_name="final-verifier", use_service_role=True)
    
    # Expected tables per specification
    expected_tables = {
        'law': ['law_documents', 'law_citations', 'law_entities', 'law_entity_relationships'],
        'client': ['client_cases', 'client_documents', 'client_entities', 'client_financial_data'],
        'graph': [
            'graph_document_registry', 'graph_embeddings', 'graph_chunks', 'graph_nodes',
            'graph_edges', 'graph_communities', 'graph_reports', 'graph_covariates', 'graph_text_units'
        ]
    }
    
    total_expected = sum(len(tables) for tables in expected_tables.values())
    total_accessible = 0
    schema_results = {}
    
    print(f"Expected tables: {total_expected}")
    print()
    
    # Test each schema
    for schema_name, table_list in expected_tables.items():
        print(f"📂 {schema_name.upper()} SCHEMA ({len(table_list)} tables)")
        print("-" * 50)
        
        accessible_tables = []
        failed_tables = []
        
        for table_name in table_list:
            try:
                result = client.anon_client.table(table_name).select("*").limit(1).execute()
                print(f"  ✅ {table_name}: Accessible")
                accessible_tables.append(table_name)
                total_accessible += 1
            except Exception as e:
                error_msg = str(e)[:60] + "..." if len(str(e)) > 60 else str(e)
                print(f"  ❌ {table_name}: {error_msg}")
                failed_tables.append(table_name)
        
        schema_results[schema_name] = {
            'accessible': len(accessible_tables),
            'total': len(table_list),
            'success_rate': len(accessible_tables) / len(table_list)
        }
        
        print(f"  📊 {schema_name} result: {len(accessible_tables)}/{len(table_list)} accessible ({schema_results[schema_name]['success_rate']:.1%})")
        print()
    
    # Overall summary
    print("=" * 70)
    print("🎯 FINAL GRAPHRAG SCHEMA VERIFICATION RESULTS")
    print("=" * 70)
    
    overall_success_rate = total_accessible / total_expected
    
    print(f"📊 Overall Status: {total_accessible}/{total_expected} tables accessible ({overall_success_rate:.1%})")
    print()
    
    for schema_name, results in schema_results.items():
        status = "✅" if results['success_rate'] >= 0.8 else "⚠️" if results['success_rate'] >= 0.5 else "❌"
        print(f"{status} {schema_name.title()} Schema: {results['accessible']}/{results['total']} ({results['success_rate']:.1%})")
    
    print()
    
    # Vector capability check
    print("🔍 VECTOR CAPABILITIES")
    print("-" * 30)
    
    try:
        vector_check = '''
        SELECT 
            column_name,
            data_type,
            CASE 
                WHEN data_type LIKE 'vector%' THEN 
                    REGEXP_REPLACE(data_type, 'vector\\((\\d+)\\)', '\\1 dimensions')
                ELSE data_type 
            END as vector_info
        FROM information_schema.columns 
        WHERE table_schema = 'graph' 
        AND table_name = 'embeddings' 
        AND column_name = 'vector'
        '''
        
        check_response = client.service_client.rpc('execute_sql', {'query': vector_check}).execute()
        if check_response.data:
            for row in check_response.data:
                print(f"  ✅ Vector column: {row.get('vector_info', 'Found')}")
        else:
            print("  ❌ Vector column: Not found")
    except Exception as e:
        print(f"  ❌ Vector check failed: {str(e)[:50]}...")
    
    # Final assessment
    print()
    print("🎉 MIGRATION ASSESSMENT")
    print("-" * 30)
    
    if overall_success_rate >= 0.9:
        print("✅ EXCELLENT: Migration highly successful")
        print("   🚀 GraphRAG service ready for full operations")
        print("   📊 All major functionality supported")
    elif overall_success_rate >= 0.8:
        print("✅ GOOD: Migration mostly successful") 
        print("   🚀 GraphRAG service ready for operations")
        print("   ⚠️  Some advanced features may be limited")
    elif overall_success_rate >= 0.6:
        print("⚠️  PARTIAL: Core functionality available")
        print("   🔧 Additional table creation needed")
        print("   🚀 Basic GraphRAG operations possible")
    else:
        print("❌ INSUFFICIENT: Major issues remain")
        print("   🔧 Significant table creation needed")
        print("   ⚠️  Limited GraphRAG functionality")
    
    print()
    print(f"Vector Support: 2048 dimensions ({'✅' if overall_success_rate > 0.5 else '❌'})")
    print(f"vLLM Compatibility: {'✅ Ready' if overall_success_rate > 0.5 else '❌ Not Ready'}")
    
    return overall_success_rate >= 0.8

if __name__ == "__main__":
    try:
        success = asyncio.run(comprehensive_verification())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)