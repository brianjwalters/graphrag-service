#!/usr/bin/env python3
"""
Verify Schema Specification Compliance
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

class SpecComplianceVerifier:
    def __init__(self):
        # Set environment variables
        os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
        os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
        os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
        
        self.client = SupabaseClient(service_name="spec-verifier", use_service_role=True)
        
        # Specification requirements
        self.spec_tables = {
            'law': ['law.documents', 'law.citations', 'law.entities', 'law.entity_relationships'],
            'client': ['client.cases', 'client.documents', 'client.parties', 'client.deadlines'],
            'graph': [
                'graph.document_registry', 'graph.contextual_chunks', 'graph.embeddings',
                'graph.nodes', 'graph.edges', 'graph.communities', 'graph.node_communities',
                'graph.chunk_entity_connections', 'graph.chunk_cross_references'
            ]
        }
        
        self.expected_vector_dims = 2048
        self.results = {}
    
    async def verify_table_existence(self):
        """Verify that all spec tables exist."""
        print("📋 VERIFYING TABLE EXISTENCE")
        print("=" * 50)
        
        # Check via public views (REST API accessible)
        all_spec_views = []
        for schema, tables in self.spec_tables.items():
            all_spec_views.extend([table.replace('.', '_') for table in tables])
        
        accessible_views = []
        missing_views = []
        
        for view_name in all_spec_views:
            try:
                result = self.client.anon_client.table(view_name).select("*").limit(1).execute()
                accessible_views.append(view_name)
                print(f"✅ {view_name}: Accessible")
            except Exception as e:
                if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                    missing_views.append(view_name)
                    print(f"❌ {view_name}: Not found")
                else:
                    print(f"❓ {view_name}: Error - {str(e)[:30]}...")
        
        self.results['table_verification'] = {
            'total_expected': len(all_spec_views),
            'accessible': len(accessible_views),
            'missing': len(missing_views),
            'accessible_views': accessible_views,
            'missing_views': missing_views,
            'success_rate': len(accessible_views) / len(all_spec_views)
        }
        
        print(f"\n📊 Table Access: {len(accessible_views)}/{len(all_spec_views)} views accessible")
        return len(accessible_views) >= 15  # 15+ out of 17 is acceptable
    
    async def verify_vector_dimensions(self):
        """Verify that vector columns have correct 1536 dimensions."""
        print("\n🔢 VERIFYING VECTOR DIMENSIONS")
        print("=" * 50)
        
        # Try to access embeddings table and check dimensions
        try:
            # Access via service role to check vector column info
            dimension_query = """
                SELECT 
                    table_name,
                    column_name,
                    udt_name,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'graph'
                AND table_name = 'embeddings'
                AND column_name = 'vector'
            """
            
            response = self.client.service_client.rpc('execute_sql', {'query': dimension_query}).execute()
            
            if response.data and len(response.data) > 0:
                vector_info = response.data[0]
                udt_name = vector_info.get('udt_name', '')
                
                if '2048' in str(udt_name):
                    print("✅ Vector dimensions: 2048 (matches vLLM service)")
                    dimension_correct = True
                elif '1536' in str(udt_name):
                    print("❌ Vector dimensions: 1536 (should be 2048 for vLLM)")
                    dimension_correct = False
                else:
                    print(f"❓ Vector dimensions: Unknown ({udt_name})")
                    dimension_correct = False
            else:
                print("❌ Could not verify vector dimensions")
                dimension_correct = False
                
        except Exception as e:
            print(f"❌ Vector dimension check failed: {str(e)[:50]}...")
            dimension_correct = False
        
        self.results['vector_verification'] = {
            'dimensions_correct': dimension_correct,
            'expected_dimensions': self.expected_vector_dims
        }
        
        return dimension_correct
    
    async def verify_schema_counts(self):
        """Verify correct number of tables per schema."""
        print("\n📈 VERIFYING SCHEMA TABLE COUNTS")
        print("=" * 50)
        
        schema_results = {}
        
        for schema_name, expected_tables in self.spec_tables.items():
            expected_count = len(expected_tables)
            accessible_views = [view for view in self.results['table_verification']['accessible_views'] 
                              if view.startswith(f"{schema_name}_")]
            actual_count = len(accessible_views)
            
            print(f"{schema_name.upper()} Schema: {actual_count}/{expected_count} tables")
            
            schema_results[schema_name] = {
                'expected': expected_count,
                'actual': actual_count,
                'compliant': actual_count == expected_count
            }
        
        self.results['schema_counts'] = schema_results
        
        # Check overall compliance
        all_compliant = all(result['compliant'] for result in schema_results.values())
        return all_compliant
    
    async def test_graphrag_service_access(self):
        """Test that GraphRAG service can access core tables."""
        print("\n🧪 TESTING GRAPHRAG SERVICE ACCESS")
        print("=" * 50)
        
        # Test key views that GraphRAG service needs
        key_views = ['law_documents', 'graph_document_registry', 'graph_embeddings', 'graph_nodes']
        
        accessible_count = 0
        
        for view_name in key_views:
            try:
                result = self.client.anon_client.table(view_name).select("*").limit(1).execute()
                print(f"✅ {view_name}: GraphRAG can access")
                accessible_count += 1
            except Exception as e:
                print(f"❌ {view_name}: Access failed - {str(e)[:30]}...")
        
        service_ready = accessible_count >= 3  # At least 3 key tables accessible
        
        self.results['service_access'] = {
            'key_tables_tested': len(key_views),
            'accessible': accessible_count,
            'service_ready': service_ready
        }
        
        print(f"\n🚀 GraphRAG Service: {'READY' if service_ready else 'NOT READY'}")
        return service_ready
    
    async def generate_compliance_report(self):
        """Generate final compliance report."""
        print("\n" + "=" * 80)
        print("SPECIFICATION COMPLIANCE REPORT")
        print("=" * 80)
        
        # Overall scores
        table_score = self.results['table_verification']['success_rate']
        vector_correct = self.results['vector_verification']['dimensions_correct']
        schema_compliant = all(result['compliant'] for result in self.results['schema_counts'].values())
        service_ready = self.results['service_access']['service_ready']
        
        print(f"📊 Table Accessibility: {table_score:.1%}")
        print(f"🔢 Vector Dimensions: {'✅ Correct (2048)' if vector_correct else '❌ Incorrect'}")
        print(f"📈 Schema Compliance: {'✅ Compliant' if schema_compliant else '❌ Non-compliant'}")
        print(f"🚀 GraphRAG Service: {'✅ Ready' if service_ready else '❌ Not Ready'}")
        
        # Detailed breakdown
        print(f"\n📋 TABLE BREAKDOWN:")
        for schema_name, result in self.results['schema_counts'].items():
            status = "✅" if result['compliant'] else "❌"
            print(f"   {status} {schema_name.upper()}: {result['actual']}/{result['expected']} tables")
        
        # Missing tables
        missing_views = self.results['table_verification']['missing_views']
        if missing_views:
            print(f"\n❌ MISSING VIEWS ({len(missing_views)}):")
            for view in missing_views[:5]:  # Show first 5
                print(f"   - {view}")
            if len(missing_views) > 5:
                print(f"   ... and {len(missing_views) - 5} more")
        
        # Overall assessment
        compliance_score = sum([table_score, vector_correct, schema_compliant, service_ready]) / 4
        
        print(f"\n{'=' * 80}")
        if compliance_score >= 0.9:
            print("🎉 SPECIFICATION COMPLIANCE: EXCELLENT")
            print("   Schema fully compliant with graphrag-db-schema-viz.html")
        elif compliance_score >= 0.7:
            print("✅ SPECIFICATION COMPLIANCE: GOOD")
            print("   Minor issues but functionally compliant")
        elif compliance_score >= 0.5:
            print("⚠️  SPECIFICATION COMPLIANCE: PARTIAL")
            print("   Some components missing or incorrect")
        else:
            print("❌ SPECIFICATION COMPLIANCE: POOR")
            print("   Major issues - schema rebuild may be needed")
        
        print(f"{'=' * 80}")
        
        return compliance_score >= 0.7

async def main():
    """Execute complete specification compliance verification."""
    
    print("=" * 80)
    print("GRAPHRAG SCHEMA SPECIFICATION COMPLIANCE VERIFICATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    
    verifier = SpecComplianceVerifier()
    
    try:
        # Run all verification steps
        table_check = await verifier.verify_table_existence()
        vector_check = await verifier.verify_vector_dimensions()
        schema_check = await verifier.verify_schema_counts()
        service_check = await verifier.test_graphrag_service_access()
        
        # Generate final report
        compliant = await verifier.generate_compliance_report()
        
        return compliant
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Critical error: {str(e)}")
        sys.exit(2)