#!/usr/bin/env python3
"""
Phase 1: Complete schema cleanup - Drop all existing schemas
"""
import os
import sys
import asyncio
from datetime import datetime

# Add the GraphRAG service to the path
sys.path.append('/srv/luris/be/graphrag-service/src')
sys.path.append('/srv/luris/be')

try:
    from clients.supabase_client import SupabaseClient, SupabaseSettings
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

async def cleanup_schemas():
    """Drop all existing schemas completely."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("=" * 80)
    print("PHASE 1: COMPLETE SCHEMA CLEANUP")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    
    client = SupabaseClient(service_name="schema-cleanup", use_service_role=True)
    
    cleanup_sql = """
-- ============================================================================
-- COMPLETE SCHEMA CLEANUP
-- Drop all existing schemas and related objects
-- ============================================================================

-- Drop all public views first (to avoid dependency issues)
DROP VIEW IF EXISTS public.law_documents CASCADE;
DROP VIEW IF EXISTS public.law_citations CASCADE;
DROP VIEW IF EXISTS public.law_entities CASCADE;
DROP VIEW IF EXISTS public.law_entity_relationships CASCADE;
DROP VIEW IF EXISTS public.law_opinions CASCADE;
DROP VIEW IF EXISTS public.law_statutes CASCADE;
DROP VIEW IF EXISTS public.law_regulations CASCADE;
DROP VIEW IF EXISTS public.law_administrative_codes CASCADE;
DROP VIEW IF EXISTS public.law_court_rules CASCADE;

DROP VIEW IF EXISTS public.client_cases CASCADE;
DROP VIEW IF EXISTS public.client_documents CASCADE;
DROP VIEW IF EXISTS public.client_parties CASCADE;
DROP VIEW IF EXISTS public.client_deadlines CASCADE;

DROP VIEW IF EXISTS public.graph_document_registry CASCADE;
DROP VIEW IF EXISTS public.graph_contextual_chunks CASCADE;
DROP VIEW IF EXISTS public.graph_embeddings CASCADE;
DROP VIEW IF EXISTS public.graph_nodes CASCADE;
DROP VIEW IF EXISTS public.graph_edges CASCADE;
DROP VIEW IF EXISTS public.graph_communities CASCADE;
DROP VIEW IF EXISTS public.graph_node_communities CASCADE;
DROP VIEW IF EXISTS public.graph_chunk_entity_connections CASCADE;
DROP VIEW IF EXISTS public.graph_chunk_cross_references CASCADE;
DROP VIEW IF EXISTS public.graph_entity_mappings CASCADE;
DROP VIEW IF EXISTS public.graph_processing_status CASCADE;
DROP VIEW IF EXISTS public.graph_case_analytics CASCADE;
DROP VIEW IF EXISTS public.graph_search_index CASCADE;
DROP VIEW IF EXISTS public.graph_graph_metrics CASCADE;

-- Drop all schemas completely with CASCADE to remove all dependencies
DROP SCHEMA IF EXISTS graph CASCADE;
DROP SCHEMA IF EXISTS client CASCADE;
DROP SCHEMA IF EXISTS law CASCADE;

-- Clean up any remaining functions or types
DROP FUNCTION IF EXISTS public.execute_sql(text) CASCADE;

SELECT 'All schemas dropped successfully' as status;
"""
    
    try:
        print("🧹 Executing complete schema cleanup...")
        
        # Execute the cleanup SQL
        response = client.service_client.rpc('execute_sql', {'query': cleanup_sql}).execute()
        
        if response.data is not None:
            print("✅ Schema cleanup completed successfully")
            print("   - All law, client, graph schemas dropped")
            print("   - All public views removed")
            print("   - All dependencies cleaned up")
            return True
        else:
            print("⚠️  Cleanup executed but no confirmation returned")
            return True
            
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        return False

async def verify_cleanup():
    """Verify that all schemas have been removed."""
    
    print("\n🔍 Verifying cleanup...")
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    client = SupabaseClient(service_name="cleanup-verifier", use_service_role=True)
    
    verification_sql = """
-- Check for any remaining schemas
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name IN ('law', 'client', 'graph')
ORDER BY schema_name;
"""
    
    try:
        response = client.service_client.rpc('execute_sql', {'query': verification_sql}).execute()
        
        if response.data is not None and len(response.data) == 0:
            print("✅ Verification passed: All schemas successfully removed")
            return True
        else:
            remaining = [row.get('schema_name') for row in response.data] if response.data else []
            print(f"⚠️  Some schemas may still exist: {remaining}")
            return False
            
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False

async def main():
    """Execute the complete cleanup process."""
    
    try:
        # Phase 1: Drop all schemas
        cleanup_success = await cleanup_schemas()
        
        if cleanup_success:
            # Verify cleanup
            verify_success = await verify_cleanup()
            
            print("\n" + "=" * 80)
            print("CLEANUP SUMMARY")
            print("=" * 80)
            
            if verify_success:
                print("🎉 PHASE 1 COMPLETE: All schemas successfully cleaned up")
                print("   Database is ready for spec-compliant rebuild")
            else:
                print("⚠️  Phase 1 completed but verification had issues")
                print("   May need manual cleanup")
            
            print("=" * 80)
            return verify_success
        else:
            print("\n❌ Schema cleanup failed")
            return False
            
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Critical error: {str(e)}")
        sys.exit(2)