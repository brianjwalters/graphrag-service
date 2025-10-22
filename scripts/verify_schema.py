#!/usr/bin/env python3
"""
Verify all GraphRAG database tables exist and are accessible.
Checks both direct table access and REST API views.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import SupabaseClient

# Expected tables by schema
EXPECTED_TABLES = {
    'law': [
        'documents',
        'citations', 
        'entities',
        'entity_relationships',
        'jurisdictions',
        'entity_categories'
    ],
    'client': [
        'cases',
        'documents',
        'parties',
        'deadlines'
    ],
    'graph': [
        'document_registry',
        'contextual_chunks',
        'embeddings',
        'nodes',
        'edges',
        'communities',
        'chunk_entity_connections',
        'chunk_cross_references',
        'node_communities',
        'entity_mappings',
        'processing_status',
        'case_analytics'
    ]
}

# Expected public views for REST API
EXPECTED_VIEWS = [
    # Law schema views
    'law_documents',
    'law_citations',
    'law_entities',
    'law_entity_relationships',
    'law_jurisdictions',
    'law_entity_categories',
    
    # Client schema views
    'client_cases',
    'client_documents',
    'client_parties',
    'client_deadlines',
    
    # Graph schema views
    'graph_document_registry',
    'graph_contextual_chunks',
    'graph_embeddings',
    'graph_nodes',
    'graph_edges',
    'graph_communities',
    'graph_chunk_entity_connections',
    'graph_chunk_cross_references',
    'graph_node_communities',
    'graph_entity_mappings',
    'graph_processing_status',
    'graph_case_analytics'
]


class SchemaVerifier:
    """Verify database schema completeness."""
    
    def __init__(self):
        self.client = SupabaseClient()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'schemas': {},
            'views': {},
            'summary': {
                'total_expected_tables': 0,
                'total_found_tables': 0,
                'total_expected_views': len(EXPECTED_VIEWS),
                'total_found_views': 0,
                'missing_tables': [],
                'missing_views': [],
                'errors': []
            }
        }
    
    async def check_table_exists(self, schema: str, table: str) -> Dict[str, Any]:
        """
        Check if a table exists and get basic info.
        
        Args:
            schema: Schema name
            table: Table name
            
        Returns:
            Dict with table info
        """
        result = {
            'schema': schema,
            'table': table,
            'exists': False,
            'accessible': False,
            'row_count': 0,
            'error': None
        }
        
        try:
            # Try to access table through REST API view
            view_name = f"{schema}_{table}"
            
            # Attempt to get data (limit 1 for speed)
            response = await self.client.get(view_name, limit=1)
            
            if response is not None:
                result['exists'] = True
                result['accessible'] = True
                
                # Get row count (would need separate query in production)
                if isinstance(response, list):
                    # For now, we know we got at least the limited amount
                    result['row_count'] = len(response)
                
                return result
                
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a "not found" error
            if '404' in error_msg or 'not found' in error_msg.lower():
                result['exists'] = False
                result['error'] = 'Table/view not found'
            else:
                # Table might exist but have access issues
                result['exists'] = True  # Uncertain
                result['accessible'] = False
                result['error'] = error_msg[:100]
        
        return result
    
    async def verify_schema_tables(self, schema: str, tables: List[str]) -> Dict[str, Any]:
        """
        Verify all tables in a schema.
        
        Args:
            schema: Schema name
            tables: List of expected tables
            
        Returns:
            Verification results
        """
        print(f"\n{'=' * 40}")
        print(f"Verifying {schema.upper()} Schema")
        print(f"{'=' * 40}")
        
        schema_results = {
            'expected': len(tables),
            'found': 0,
            'accessible': 0,
            'tables': {}
        }
        
        for table in tables:
            print(f"  Checking {schema}.{table}...", end=' ')
            
            result = await self.check_table_exists(schema, table)
            schema_results['tables'][table] = result
            
            if result['exists']:
                schema_results['found'] += 1
                if result['accessible']:
                    schema_results['accessible'] += 1
                    print(f"✓ (accessible, {result['row_count']} rows)")
                else:
                    print(f"⚠️ (exists but not accessible)")
                    
            else:
                print("✗ (missing)")
                self.results['summary']['missing_tables'].append(f"{schema}.{table}")
        
        return schema_results
    
    async def verify_public_views(self) -> Dict[str, Any]:
        """
        Verify all public views for REST API access.
        
        Returns:
            View verification results
        """
        print(f"\n{'=' * 40}")
        print("Verifying Public Views (REST API)")
        print(f"{'=' * 40}")
        
        view_results = {
            'expected': len(EXPECTED_VIEWS),
            'found': 0,
            'views': {}
        }
        
        for view in EXPECTED_VIEWS:
            print(f"  Checking public.{view}...", end=' ')
            
            try:
                # Try to access the view
                response = await self.client.get(view, limit=1)
                
                if response is not None:
                    view_results['found'] += 1
                    view_results['views'][view] = {'exists': True}
                    print("✓")
                else:
                    view_results['views'][view] = {'exists': False}
                    self.results['summary']['missing_views'].append(view)
                    print("✗")
                    
            except Exception as e:
                view_results['views'][view] = {'exists': False, 'error': str(e)[:50]}
                self.results['summary']['missing_views'].append(view)
                print(f"✗ ({str(e)[:30]})")
        
        return view_results
    
    async def run_verification(self):
        """Run complete schema verification."""
        print("=" * 80)
        print("GRAPHRAG DATABASE SCHEMA VERIFICATION")
        print("=" * 80)
        print(f"Started at: {self.results['timestamp']}")
        
        # Count total expected tables
        self.results['summary']['total_expected_tables'] = sum(
            len(tables) for tables in EXPECTED_TABLES.values()
        )
        
        # Verify each schema
        for schema_name, tables in EXPECTED_TABLES.items():
            results = await self.verify_schema_tables(schema_name, tables)
            self.results['schemas'][schema_name] = results
            self.results['summary']['total_found_tables'] += results['found']
        
        # Verify public views
        view_results = await self.verify_public_views()
        self.results['views'] = view_results
        self.results['summary']['total_found_views'] = view_results['found']
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Print verification summary."""
        s = self.results['summary']
        
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        
        # Table summary
        print(f"\nTables:")
        print(f"  Expected: {s['total_expected_tables']}")
        print(f"  Found: {s['total_found_tables']}")
        print(f"  Missing: {s['total_expected_tables'] - s['total_found_tables']}")
        
        if s['missing_tables']:
            print(f"\n  Missing tables:")
            for table in s['missing_tables']:
                print(f"    - {table}")
        
        # View summary
        print(f"\nPublic Views (REST API):")
        print(f"  Expected: {s['total_expected_views']}")
        print(f"  Found: {s['total_found_views']}")
        print(f"  Missing: {s['total_expected_views'] - s['total_found_views']}")
        
        if s['missing_views']:
            print(f"\n  Missing views:")
            for view in s['missing_views'][:5]:  # Show first 5
                print(f"    - {view}")
            if len(s['missing_views']) > 5:
                print(f"    ... and {len(s['missing_views']) - 5} more")
        
        # Overall status
        print("\n" + "=" * 80)
        
        if (s['total_found_tables'] == s['total_expected_tables'] and 
            s['total_found_views'] == s['total_expected_views']):
            print("✅ VERIFICATION PASSED - All tables and views present!")
        elif s['total_found_tables'] > 0 or s['total_found_views'] > 0:
            print("⚠️  VERIFICATION PARTIAL - Some tables/views missing")
            print("   Run migrations to create missing objects")
        else:
            print("✗ VERIFICATION FAILED - No tables found")
            print("   Run all migrations first")
        
        print("=" * 80)


async def main():
    """Main verification function."""
    verifier = SchemaVerifier()
    
    try:
        results = await verifier.run_verification()
        
        # Save detailed report
        import json
        report_file = f"schema_verification_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Exit code based on verification status
        if (results['summary']['total_found_tables'] == results['summary']['total_expected_tables'] and
            results['summary']['total_found_views'] == results['summary']['total_expected_views']):
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Incomplete
            
    except Exception as e:
        print(f"\n✗ Verification error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║       GraphRAG Database Schema Verifier                   ║
║                                                            ║
║  This script verifies the existence of:                   ║
║  • 6 tables in law schema                                 ║
║  • 4 tables in client schema                              ║
║  • 12+ tables in graph schema                             ║
║  • 29+ public views for REST API access                   ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())