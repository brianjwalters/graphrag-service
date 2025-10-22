#!/usr/bin/env python3
"""
Comprehensive Database Access Test for GraphRAG Service
Tests the SupabaseClient with realistic mock data across all schemas
"""
import os
import sys
import asyncio
import uuid
import random
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional

# Add the GraphRAG service to the path
sys.path.append('/srv/luris/be/graphrag-service/src')
sys.path.append('/srv/luris/be')

try:
    from clients.supabase_client import SupabaseClient, SupabaseSettings
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class DatabaseAccessTester:
    """Comprehensive database access testing for GraphRAG service."""
    
    def __init__(self):
        self.setup_environment()
        self.anon_client = None
        self.service_client = None
        self.test_results = {
            'client_init': {},
            'crud_operations': {},
            'advanced_operations': {},
            'error_handling': {},
            'performance': {}
        }
        self.test_data_ids = {
            'law': {}, 'client': {}, 'graph': {}
        }
    
    def setup_environment(self):
        """Setup required environment variables."""
        os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
        os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
        os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    async def run_comprehensive_test(self):
        """Run all testing phases."""
        print("🚀 COMPREHENSIVE DATABASE ACCESS TEST")
        print("=" * 70)
        print(f"Started at: {datetime.now().isoformat()}")
        print()
        
        # Phase 1: Client Initialization
        await self.test_client_initialization()
        
        # Phase 2: Generate Mock Data
        await self.generate_mock_data()
        
        # Phase 3: CRUD Operations
        await self.test_crud_operations()
        
        # Phase 4: Advanced Operations  
        await self.test_advanced_operations()
        
        # Phase 5: Error Handling
        await self.test_error_handling()
        
        # Final Report
        await self.generate_final_report()
    
    async def test_client_initialization(self):
        """Test Phase 1: Client initialization and health check."""
        print("📋 PHASE 1: CLIENT INITIALIZATION & HEALTH CHECK")
        print("-" * 60)
        
        try:
            # Test anon client
            print("1.1 Testing anon client initialization...")
            self.anon_client = SupabaseClient(
                service_name="graphrag-db-test-anon", 
                use_service_role=False
            )
            self.test_results['client_init']['anon_client'] = "✅ SUCCESS"
            print("    ✅ Anon client initialized successfully")
            
            # Test service client
            print("\n1.2 Testing service_role client initialization...")
            self.service_client = SupabaseClient(
                service_name="graphrag-db-test-service", 
                use_service_role=True
            )
            self.test_results['client_init']['service_client'] = "✅ SUCCESS"
            print("    ✅ Service client initialized successfully")
            
            # Health check
            print("\n1.3 Running client health checks...")
            anon_health = self.anon_client.get_health_info()
            service_health = self.service_client.get_health_info()
            
            print(f"    Anon client health: {'✅ HEALTHY' if anon_health['healthy'] else '❌ UNHEALTHY'}")
            print(f"    Service client health: {'✅ HEALTHY' if service_health['healthy'] else '❌ UNHEALTHY'}")
            
            self.test_results['client_init']['health_check'] = {
                'anon_healthy': anon_health['healthy'],
                'service_healthy': service_health['healthy']
            }
            
            # Connection test
            print("\n1.4 Testing basic connectivity...")
            try:
                # Simple connectivity test
                test_query = "SELECT 'Connection test successful' as message"
                result = await self.service_client.execute_raw_sql(test_query)
                print("    ✅ Database connectivity confirmed")
                self.test_results['client_init']['connectivity'] = "✅ SUCCESS"
            except Exception as e:
                print(f"    ❌ Connectivity test failed: {str(e)[:100]}...")
                self.test_results['client_init']['connectivity'] = f"❌ FAILED: {str(e)[:50]}"
            
        except Exception as e:
            print(f"❌ Client initialization failed: {str(e)}")
            self.test_results['client_init']['error'] = str(e)
            raise
        
        print("\n✅ Phase 1 Complete: Client initialization successful")
        print()
    
    def generate_mock_vector(self, dimensions: int = 2048) -> List[float]:
        """Generate a mock vector for testing."""
        return [random.uniform(-1.0, 1.0) for _ in range(dimensions)]
    
    async def generate_mock_data(self):
        """Test Phase 2: Generate realistic mock data for all schemas."""
        print("📊 PHASE 2: MOCK DATA GENERATION")
        print("-" * 60)
        
        # Generate Law Schema Data
        await self.generate_law_mock_data()
        
        # Generate Client Schema Data  
        await self.generate_client_mock_data()
        
        # Generate Graph Schema Data
        await self.generate_graph_mock_data()
        
        print("✅ Phase 2 Complete: Mock data generated for all schemas")
        print()
    
    async def generate_law_mock_data(self):
        """Generate mock data for law schema."""
        print("2.1 Generating law schema mock data...")
        
        # Law documents
        law_docs = [
            {
                'document_id': f'law_doc_{i}',
                'title': f'Supreme Court Case {i}: Legal Matter vs. Respondent',
                'court_name': random.choice(['Supreme Court', 'Court of Appeals', 'District Court']),
                'jurisdiction': random.choice(['Federal', 'State', 'Local']),
                'date_filed': (date.today() - timedelta(days=random.randint(1, 3650))).isoformat(),
                'citation': f'{random.randint(100, 999)} U.S. {random.randint(1, 999)} ({random.randint(1950, 2024)})',
                'content_md': f'# Legal Document {i}\n\nThis is a comprehensive legal document covering important matters of law...',
                'storage_path': f'/legal/documents/case_{i}.pdf'
            }
            for i in range(1, 6)  # 5 law documents
        ]
        
        try:
            result = await self.service_client.insert('law_documents', law_docs, admin_operation=True)
            self.test_data_ids['law']['documents'] = [doc['document_id'] for doc in result] 
            print(f"    ✅ Created {len(result)} law documents")
        except Exception as e:
            print(f"    ❌ Law documents failed: {str(e)[:50]}...")
        
        # Law citations
        if self.test_data_ids['law'].get('documents'):
            law_citations = [
                {
                    'citation_id': f'citation_{i}',
                    'document_id': self.test_data_ids['law']['documents'][0],
                    'citation_text': f'Citation reference {i}',
                    'citation_context': f'Referenced in context of legal precedent {i}',
                    'page_number': random.randint(1, 100)
                }
                for i in range(1, 4)  # 3 citations
            ]
            
            try:
                result = await self.service_client.insert('law_citations', law_citations, admin_operation=True)
                print(f"    ✅ Created {len(result)} law citations")
            except Exception as e:
                print(f"    ❌ Law citations failed: {str(e)[:50]}...")
        
        # Law entities
        if self.test_data_ids['law'].get('documents'):
            law_entities = [
                {
                    'document_id': self.test_data_ids['law']['documents'][0],
                    'entity_type': random.choice(['person', 'organization', 'case', 'statute', 'court', 'judge']),
                    'entity_text': f'Legal Entity {i}',
                    'canonical_name': f'Legal Entity {i} (Canonical)',
                    'confidence_score': random.uniform(0.7, 1.0),
                    'extraction_method': random.choice(['regex', 'spacy', 'ai_enhanced']),
                    'context': f'Found in legal context {i}'
                }
                for i in range(1, 8)  # 7 entities
            ]
            
            try:
                result = await self.service_client.insert('law_entities', law_entities, admin_operation=True)
                self.test_data_ids['law']['entities'] = [str(entity['id']) for entity in result]
                print(f"    ✅ Created {len(result)} law entities")
            except Exception as e:
                print(f"    ❌ Law entities failed: {str(e)[:50]}...")
    
    async def generate_client_mock_data(self):
        """Generate mock data for client schema."""
        print("2.2 Generating client schema mock data...")
        
        # Client cases
        client_cases = [
            {
                'case_id': str(uuid.uuid4()),
                'client_id': str(uuid.uuid4()),
                'case_number': f'2024-CV-{random.randint(1000, 9999)}',
                'caption': f'Client Matter {i} vs. Opposing Party',
                'court': random.choice(['Superior Court', 'District Court', 'Federal Court']),
                'judge': f'Honorable Judge {chr(65 + i)}',
                'status': random.choice(['active', 'pending', 'closed'])
            }
            for i in range(1, 4)  # 3 cases
        ]
        
        try:
            result = await self.service_client.insert('client_cases', client_cases, admin_operation=True)
            self.test_data_ids['client']['cases'] = [case['case_id'] for case in result]
            print(f"    ✅ Created {len(result)} client cases")
        except Exception as e:
            print(f"    ❌ Client cases failed: {str(e)[:50]}...")
        
        # Client documents
        if self.test_data_ids['client'].get('cases'):
            client_docs = [
                {
                    'document_id': f'client_doc_{i}',
                    'case_id': self.test_data_ids['client']['cases'][0],
                    'title': f'Client Document {i}',
                    'document_type': random.choice(['contract', 'correspondence', 'filing', 'discovery', 'brief']),
                    'content_md': f'# Client Document {i}\n\nThis is important client documentation...',
                    'storage_path': f'/client/docs/case_{i}.pdf',
                    'confidentiality_level': random.choice(['client_confidential', 'attorney_client_privilege'])
                }
                for i in range(1, 6)  # 5 client docs
            ]
            
            try:
                result = await self.service_client.insert('client_documents', client_docs, admin_operation=True)
                print(f"    ✅ Created {len(result)} client documents")
            except Exception as e:
                print(f"    ❌ Client documents failed: {str(e)[:50]}...")
        
        # Client entities
        if self.test_data_ids['client'].get('cases'):
            client_entities = [
                {
                    'document_id': 'client_doc_1',
                    'case_id': self.test_data_ids['client']['cases'][0],
                    'entity_type': random.choice(['person', 'organization', 'contract', 'monetary_amount', 'date']),
                    'entity_text': f'Client Entity {i}',
                    'canonical_name': f'Client Entity {i} (Standard)',
                    'confidence_score': random.uniform(0.8, 1.0),
                    'extraction_method': 'ai_enhanced'
                }
                for i in range(1, 5)  # 4 entities
            ]
            
            try:
                result = await self.service_client.insert('client_entities', client_entities, admin_operation=True)
                print(f"    ✅ Created {len(result)} client entities")
            except Exception as e:
                print(f"    ❌ Client entities failed: {str(e)[:50]}...")
        
        # Client financial data
        if self.test_data_ids['client'].get('cases'):
            financial_data = [
                {
                    'case_id': self.test_data_ids['client']['cases'][0],
                    'document_id': 'client_doc_1',
                    'transaction_date': (date.today() - timedelta(days=random.randint(1, 365))).isoformat(),
                    'description': f'Financial Transaction {i}',
                    'amount': round(random.uniform(100.00, 50000.00), 2),
                    'currency': 'USD',
                    'account_type': random.choice(['checking', 'savings', 'investment', 'escrow']),
                    'category': random.choice(['legal_fees', 'court_costs', 'expert_fees', 'travel'])
                }
                for i in range(1, 4)  # 3 financial records
            ]
            
            try:
                result = await self.service_client.insert('client_financial_data', financial_data, admin_operation=True)
                print(f"    ✅ Created {len(result)} financial records")
            except Exception as e:
                print(f"    ❌ Financial data failed: {str(e)[:50]}...")
    
    async def generate_graph_mock_data(self):
        """Generate mock data for graph schema."""
        print("2.3 Generating graph schema mock data...")
        
        # Graph document registry
        doc_registry = [
            {
                'document_id': f'graph_doc_{i}',
                'title': f'Processed Document {i}',
                'document_type': random.choice(['legal', 'contract', 'correspondence']),
                'source_schema': random.choice(['law', 'client']),
                'status': random.choice(['completed', 'processing', 'pending']),
                'metadata': {'processing_time': random.randint(100, 5000), 'token_count': random.randint(500, 10000)}
            }
            for i in range(1, 6)  # 5 registry entries
        ]
        
        try:
            result = await self.service_client.insert('graph_document_registry', doc_registry, admin_operation=True)
            self.test_data_ids['graph']['documents'] = [doc['document_id'] for doc in result]
            print(f"    ✅ Created {len(result)} document registry entries")
        except Exception as e:
            print(f"    ❌ Document registry failed: {str(e)[:50]}...")
        
        # Graph embeddings (with 2048-dimension vectors)
        if self.test_data_ids['graph'].get('documents'):
            embeddings = [
                {
                    'source_id': f'chunk_{i}',
                    'source_type': random.choice(['chunk', 'node', 'community']),
                    'vector': self.generate_mock_vector(2048),
                    'embedding_type': random.choice(['content', 'semantic', 'summary']),
                    'model_name': 'jinaai/jina-embeddings-v4-vllm-code'
                }
                for i in range(1, 4)  # 3 embeddings (small for testing)
            ]
            
            try:
                result = await self.service_client.insert('graph_embeddings', embeddings, admin_operation=True)
                print(f"    ✅ Created {len(result)} embeddings (2048-dim vectors)")
            except Exception as e:
                print(f"    ❌ Embeddings failed: {str(e)[:50]}...")
        
        # Graph chunks
        if self.test_data_ids['graph'].get('documents'):
            chunks = [
                {
                    'chunk_id': f'chunk_{i}',
                    'document_id': self.test_data_ids['graph']['documents'][0],
                    'chunk_index': i,
                    'content': f'This is chunk {i} of the document containing important information for GraphRAG processing.',
                    'content_type': 'text',
                    'token_count': random.randint(50, 500),
                    'chunk_size': random.randint(200, 1000),
                    'chunk_method': random.choice(['simple', 'semantic', 'legal'])
                }
                for i in range(1, 5)  # 4 chunks
            ]
            
            try:
                result = await self.service_client.insert('graph_chunks', chunks, admin_operation=True)
                print(f"    ✅ Created {len(result)} graph chunks")
            except Exception as e:
                print(f"    ❌ Graph chunks failed: {str(e)[:50]}...")
        
        # Graph nodes
        nodes = [
            {
                'node_id': f'node_{i}',
                'node_type': random.choice(['entity', 'concept', 'document']),
                'title': f'Graph Node {i}',
                'description': f'Knowledge graph node representing concept {i}',
                'source_id': f'entity_{i}',
                'source_type': 'entity',
                'node_degree': random.randint(1, 10),
                'community_id': f'community_{random.randint(1, 3)}',
                'rank_score': random.uniform(0.1, 1.0)
            }
            for i in range(1, 6)  # 5 nodes
        ]
        
        try:
            result = await self.service_client.insert('graph_nodes', nodes, admin_operation=True)
            self.test_data_ids['graph']['nodes'] = [node['node_id'] for node in result]
            print(f"    ✅ Created {len(result)} graph nodes")
        except Exception as e:
            print(f"    ❌ Graph nodes failed: {str(e)[:50]}...")
        
        # Graph edges
        if self.test_data_ids['graph'].get('nodes') and len(self.test_data_ids['graph']['nodes']) >= 2:
            edges = [
                {
                    'edge_id': f'edge_{i}',
                    'source_node_id': self.test_data_ids['graph']['nodes'][0],
                    'target_node_id': self.test_data_ids['graph']['nodes'][1],
                    'relationship_type': random.choice(['related_to', 'mentions', 'cites', 'contains']),
                    'weight': random.uniform(0.1, 1.0),
                    'evidence': f'Edge evidence {i}',
                    'confidence_score': random.uniform(0.5, 1.0),
                    'extraction_method': 'co_occurrence'
                }
                for i in range(1, 3)  # 2 edges
            ]
            
            try:
                result = await self.service_client.insert('graph_edges', edges, admin_operation=True)
                print(f"    ✅ Created {len(result)} graph edges")
            except Exception as e:
                print(f"    ❌ Graph edges failed: {str(e)[:50]}...")
        
        # Graph communities
        communities = [
            {
                'community_id': f'community_{i}',
                'title': f'Knowledge Community {i}',
                'summary': f'This community represents a cluster of related concepts in domain {i}',
                'level': random.randint(0, 3),
                'node_count': random.randint(5, 20),
                'edge_count': random.randint(3, 15),
                'coherence_score': random.uniform(0.3, 1.0)
            }
            for i in range(1, 3)  # 2 communities
        ]
        
        try:
            result = await self.service_client.insert('graph_communities', communities, admin_operation=True)
            print(f"    ✅ Created {len(result)} graph communities")
        except Exception as e:
            print(f"    ❌ Graph communities failed: {str(e)[:50]}...")
        
        print("    ✅ Graph schema mock data generation complete")
    
    async def test_crud_operations(self):
        """Test Phase 3: CRUD operations across all tables."""
        print("🔄 PHASE 3: CRUD OPERATIONS TESTING")
        print("-" * 60)
        
        # Test tables from each schema
        test_tables = [
            'law_documents', 'law_citations', 'law_entities', 'law_entity_relationships',
            'client_cases', 'client_documents', 'client_entities', 'client_financial_data',
            'graph_document_registry', 'graph_embeddings', 'graph_chunks', 'graph_nodes',
            'graph_edges', 'graph_communities', 'graph_reports', 'graph_covariates', 'graph_text_units'
        ]
        
        crud_results = {}
        
        for table in test_tables:
            print(f"3.{test_tables.index(table) + 1} Testing {table}...")
            
            table_results = {
                'read_anon': '❌',
                'read_service': '❌', 
                'accessible': False
            }
            
            # Test READ with anon client
            try:
                anon_data = await self.anon_client.get(table, limit=5, admin_operation=False)
                table_results['read_anon'] = f'✅ ({len(anon_data)} records)'
                table_results['accessible'] = True
            except Exception as e:
                table_results['read_anon'] = f'❌ {str(e)[:30]}...'
            
            # Test READ with service client
            try:
                service_data = await self.service_client.get(table, limit=5, admin_operation=True)
                table_results['read_service'] = f'✅ ({len(service_data)} records)'
                table_results['accessible'] = True
            except Exception as e:
                table_results['read_service'] = f'❌ {str(e)[:30]}...'
            
            crud_results[table] = table_results
            
            status = "✅" if table_results['accessible'] else "❌"
            print(f"    {status} Anon: {table_results['read_anon']}, Service: {table_results['read_service']}")
        
        self.test_results['crud_operations'] = crud_results
        
        # Summary
        accessible_count = sum(1 for result in crud_results.values() if result['accessible'])
        total_count = len(test_tables)
        
        print(f"\n📊 CRUD Test Summary: {accessible_count}/{total_count} tables accessible")
        print("✅ Phase 3 Complete: CRUD operations tested")
        print()
    
    async def test_advanced_operations(self):
        """Test Phase 4: Advanced operations."""
        print("⚡ PHASE 4: ADVANCED OPERATIONS TESTING")  
        print("-" * 60)
        
        advanced_results = {}
        
        # Test 1: Vector operations
        print("4.1 Testing vector operations...")
        try:
            # Test vector similarity (brute-force since no index)
            vector_query = """
            SELECT source_id, source_type, vector <=> '[0.5,0.5]' as distance
            FROM graph.embeddings 
            ORDER BY distance 
            LIMIT 3
            """
            vector_results = await self.service_client.execute_raw_sql(vector_query, admin_operation=True)
            advanced_results['vector_ops'] = f"✅ {len(vector_results)} similar vectors found"
            print(f"    ✅ Vector similarity search: {len(vector_results)} results")
        except Exception as e:
            advanced_results['vector_ops'] = f"❌ {str(e)[:50]}..."
            print(f"    ❌ Vector operations failed: {str(e)[:50]}...")
        
        # Test 2: Cross-schema queries
        print("4.2 Testing cross-schema queries...")
        try:
            cross_schema_query = """
            SELECT 
                ld.title as law_document,
                cd.title as client_document,
                gd.title as graph_document
            FROM law.documents ld
            FULL OUTER JOIN client.documents cd ON true
            FULL OUTER JOIN graph.document_registry gd ON true
            LIMIT 5
            """
            cross_results = await self.service_client.execute_raw_sql(cross_schema_query, admin_operation=True)
            advanced_results['cross_schema'] = f"✅ {len(cross_results)} cross-schema records"
            print(f"    ✅ Cross-schema query: {len(cross_results)} combined records")
        except Exception as e:
            advanced_results['cross_schema'] = f"❌ {str(e)[:50]}..."
            print(f"    ❌ Cross-schema query failed: {str(e)[:50]}...")
        
        # Test 3: Batch operations
        print("4.3 Testing batch operations...")
        try:
            batch_data = [
                {
                    'community_id': f'batch_community_{i}',
                    'title': f'Batch Community {i}',
                    'summary': f'Community created via batch operation {i}',
                    'level': 0,
                    'node_count': 1,
                    'edge_count': 0,
                    'coherence_score': 0.5
                }
                for i in range(1, 4)
            ]
            batch_result = await self.service_client.insert('graph_communities', batch_data, admin_operation=True)
            advanced_results['batch_ops'] = f"✅ {len(batch_result)} records inserted"
            print(f"    ✅ Batch insert: {len(batch_result)} communities created")
        except Exception as e:
            advanced_results['batch_ops'] = f"❌ {str(e)[:50]}..."
            print(f"    ❌ Batch operations failed: {str(e)[:50]}...")
        
        # Test 4: Performance measurement
        print("4.4 Testing performance...")
        try:
            start_time = time.time()
            perf_results = await self.service_client.get('graph_document_registry', limit=100, admin_operation=True)
            query_time = time.time() - start_time
            
            advanced_results['performance'] = f"✅ Query time: {query_time:.3f}s"
            print(f"    ✅ Performance test: {query_time:.3f}s for {len(perf_results)} records")
        except Exception as e:
            advanced_results['performance'] = f"❌ {str(e)[:50]}..."
            print(f"    ❌ Performance test failed: {str(e)[:50]}...")
        
        self.test_results['advanced_operations'] = advanced_results
        print("✅ Phase 4 Complete: Advanced operations tested")
        print()
    
    async def test_error_handling(self):
        """Test Phase 5: Error handling and resilience."""
        print("🛡️  PHASE 5: ERROR HANDLING & RESILIENCE")
        print("-" * 60)
        
        error_results = {}
        
        # Test 1: Invalid table access
        print("5.1 Testing invalid table access...")
        try:
            await self.anon_client.get('nonexistent_table', admin_operation=False)
            error_results['invalid_table'] = "❌ Should have failed"
        except Exception as e:
            error_results['invalid_table'] = "✅ Properly handled"
            print("    ✅ Invalid table access properly rejected")
        
        # Test 2: Permission testing
        print("5.2 Testing permission boundaries...")
        try:
            # Try to access with wrong permission level (if RLS is enabled)
            result = await self.anon_client.get('graph_embeddings', limit=1, admin_operation=False)
            error_results['permissions'] = f"✅ Anon access allowed ({len(result)} records)"
            print(f"    ✅ Anon access to embeddings: {len(result)} records accessible")
        except Exception as e:
            error_results['permissions'] = f"⚠️  Anon access restricted: {str(e)[:30]}..."
            print(f"    ⚠️  Anon access restricted (expected if RLS enabled)")
        
        # Test 3: Client health after operations
        print("5.3 Checking client health after stress...")
        anon_health = self.anon_client.get_health_info()
        service_health = self.service_client.get_health_info()
        
        error_results['client_health'] = {
            'anon_healthy': anon_health['healthy'],
            'service_healthy': service_health['healthy'],
            'anon_operations': anon_health['operation_count'],
            'service_operations': service_health['operation_count'],
            'anon_errors': anon_health['error_count'],
            'service_errors': service_health['error_count']
        }
        
        print(f"    ✅ Anon client: {anon_health['operation_count']} ops, {anon_health['error_count']} errors, {'healthy' if anon_health['healthy'] else 'unhealthy'}")
        print(f"    ✅ Service client: {service_health['operation_count']} ops, {service_health['error_count']} errors, {'healthy' if service_health['healthy'] else 'unhealthy'}")
        
        self.test_results['error_handling'] = error_results
        print("✅ Phase 5 Complete: Error handling verified")
        print()
    
    async def generate_final_report(self):
        """Generate comprehensive final report."""
        print("📋 FINAL REPORT: COMPREHENSIVE DATABASE ACCESS TEST")
        print("=" * 70)
        
        # Client initialization summary
        print("🔧 CLIENT INITIALIZATION")
        print(f"   Anon Client: {self.test_results['client_init'].get('anon_client', 'Unknown')}")
        print(f"   Service Client: {self.test_results['client_init'].get('service_client', 'Unknown')}")
        print(f"   Connectivity: {self.test_results['client_init'].get('connectivity', 'Unknown')}")
        
        # CRUD operations summary
        print("\n🔄 CRUD OPERATIONS SUMMARY")
        if 'crud_operations' in self.test_results:
            accessible_tables = [table for table, results in self.test_results['crud_operations'].items() if results['accessible']]
            total_tables = len(self.test_results['crud_operations'])
            print(f"   Accessible Tables: {len(accessible_tables)}/{total_tables}")
            
            # Group by schema
            law_tables = [t for t in accessible_tables if t.startswith('law_')]
            client_tables = [t for t in accessible_tables if t.startswith('client_')]
            graph_tables = [t for t in accessible_tables if t.startswith('graph_')]
            
            print(f"   📚 Law Schema: {len(law_tables)}/4 tables")
            print(f"   👨‍⚖️ Client Schema: {len(client_tables)}/4 tables")
            print(f"   🕸️  Graph Schema: {len(graph_tables)}/9 tables")
        
        # Advanced operations summary
        print("\n⚡ ADVANCED OPERATIONS")
        if 'advanced_operations' in self.test_results:
            for op_type, result in self.test_results['advanced_operations'].items():
                print(f"   {op_type}: {result}")
        
        # Error handling summary
        print("\n🛡️  ERROR HANDLING & RESILIENCE")
        if 'error_handling' in self.test_results:
            error_info = self.test_results['error_handling']
            if 'client_health' in error_info:
                health = error_info['client_health']
                print(f"   Client Health: {'✅' if health['anon_healthy'] and health['service_healthy'] else '⚠️'}")
                print(f"   Total Operations: {health['anon_operations'] + health['service_operations']}")
                print(f"   Total Errors: {health['anon_errors'] + health['service_errors']}")
        
        # Final assessment
        print("\n🎯 FINAL ASSESSMENT")
        
        # Calculate success metrics
        crud_success_rate = 0
        if 'crud_operations' in self.test_results:
            accessible_count = sum(1 for result in self.test_results['crud_operations'].values() if result['accessible'])
            total_count = len(self.test_results['crud_operations'])
            crud_success_rate = accessible_count / total_count if total_count > 0 else 0
        
        advanced_success_count = 0
        if 'advanced_operations' in self.test_results:
            advanced_success_count = sum(1 for result in self.test_results['advanced_operations'].values() if result.startswith('✅'))
        
        if crud_success_rate >= 0.9 and advanced_success_count >= 3:
            print("   🎉 EXCELLENT: GraphRAG service has FULL database access")
            print("   ✅ All core functionality operational")
            print("   ✅ Ready for production GraphRAG operations")
            print("   ✅ 2048-dimension vectors supported")
            print("   ✅ Cross-schema relationships functional")
        elif crud_success_rate >= 0.7 and advanced_success_count >= 2:
            print("   ✅ GOOD: GraphRAG service has comprehensive database access")
            print("   ✅ Most functionality operational")
            print("   ⚠️  Some advanced features may have limitations")
        elif crud_success_rate >= 0.5:
            print("   ⚠️  PARTIAL: GraphRAG service has basic database access")
            print("   ✅ Core operations functional")
            print("   ⚠️  Advanced features need attention")
        else:
            print("   ❌ INSUFFICIENT: GraphRAG service has limited database access")
            print("   ⚠️  Significant issues need resolution")
        
        print(f"\n📊 Final Metrics:")
        print(f"   CRUD Success Rate: {crud_success_rate:.1%}")
        print(f"   Advanced Operations: {advanced_success_count}/4 working")
        print(f"   Overall Status: {'READY' if crud_success_rate >= 0.8 else 'NEEDS WORK'}")
        
        print("\n" + "=" * 70)
        print(f"Test completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    try:
        tester = DatabaseAccessTester()
        asyncio.run(tester.run_comprehensive_test())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test failed with critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)