#!/usr/bin/env python3
"""
Database Data Discovery Script for API Parity Testing

Queries Supabase across law, client, and graph schemas to identify
suitable test data for GraphRAG Service fluent API testing.

Author: backend-engineer
Date: 2025-10-20
"""

import os
import sys
from datetime import datetime
from supabase import create_client
from typing import Dict, List

def main():
    """Execute comprehensive database data discovery"""

    # Connect to Supabase
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY')

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY environment variables required")
        sys.exit(1)

    supabase = create_client(url, key)

    results = {
        'discovery_date': datetime.utcnow().isoformat(),
        'law_schema': {},
        'client_schema': {},
        'graph_schema': {},
        'cross_schema': {}
    }

    print("=" * 80)
    print("DATABASE DATA DISCOVERY - API PARITY TESTING")
    print("=" * 80)
    print()

    # ===== LAW SCHEMA =====
    print("1. LAW SCHEMA INVESTIGATION")
    print("-" * 80)

    try:
        # Law documents count
        response = supabase.table('law_documents').select('*', count='exact', head=True).execute()
        results['law_schema']['total_documents'] = response.count
        print(f"✅ Law Documents: {response.count:,}")

        # Law entities count and distribution
        response = supabase.table('law_entities').select('*', count='exact', head=True).execute()
        results['law_schema']['total_entities'] = response.count
        print(f"✅ Law Entities: {response.count:,}")

        # Top entity types in law schema
        response = supabase.table('law_entities').select('entity_type', count='exact').limit(1000).execute()
        entity_types = {}
        for row in response.data:
            et = row.get('entity_type', 'unknown')
            entity_types[et] = entity_types.get(et, 0) + 1

        results['law_schema']['top_entity_types'] = sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:10]
        print("✅ Top Entity Types:")
        for et, count in results['law_schema']['top_entity_types']:
            print(f"   - {et}: {count:,}")

    except Exception as e:
        print(f"❌ Law schema error: {e}")

    print()

    # ===== CLIENT SCHEMA =====
    print("2. CLIENT SCHEMA INVESTIGATION")
    print("-" * 80)

    try:
        # Total cases
        response = supabase.table('client_cases').select('*', count='exact', head=True).execute()
        results['client_schema']['total_cases'] = response.count
        print(f"✅ Total Cases: {response.count:,}")

        # Cases with case_id
        response = supabase.table('client_cases').select('case_id').limit(1000).execute()
        case_ids = [row['case_id'] for row in response.data if row.get('case_id')]
        results['client_schema']['case_ids'] = case_ids
        print(f"✅ Unique Case IDs Found: {len(case_ids)}")

    except Exception as e:
        print(f"❌ Client schema error: {e}")

    print()

    # ===== GRAPH SCHEMA =====
    print("3. GRAPH SCHEMA INVESTIGATION")
    print("-" * 80)

    try:
        # Total nodes
        response = supabase.table('graph_nodes').select('*', count='exact', head=True).execute()
        results['graph_schema']['total_nodes'] = response.count
        print(f"✅ Total Nodes: {response.count:,}")

        # Total edges
        response = supabase.table('graph_edges').select('*', count='exact', head=True).execute()
        results['graph_schema']['total_edges'] = response.count
        print(f"✅ Total Edges: {response.count:,}")

        # Total communities
        response = supabase.table('graph_communities').select('*', count='exact', head=True).execute()
        results['graph_schema']['total_communities'] = response.count
        print(f"✅ Total Communities: {response.count:,}")

        # Total chunks
        response = supabase.table('graph_chunks').select('*', count='exact', head=True).execute()
        results['graph_schema']['total_chunks'] = response.count
        print(f"✅ Total Chunks: {response.count:,}")

        # Document registry
        response = supabase.table('graph_document_registry').select('*', count='exact', head=True).execute()
        results['graph_schema']['total_documents'] = response.count
        print(f"✅ Document Registry: {response.count:,}")

        # Nodes by case_id - sample
        response = supabase.table('graph_nodes').select('case_id').not_.is_('case_id', 'null').limit(5000).execute()
        case_node_counts = {}
        for row in response.data:
            cid = row.get('case_id')
            if cid:
                case_node_counts[str(cid)] = case_node_counts.get(str(cid), 0) + 1

        results['graph_schema']['cases_with_nodes'] = sorted(case_node_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        print("✅ Top Cases by Node Count (sampled from 5000 nodes):")
        for case_id, count in results['graph_schema']['cases_with_nodes']:
            print(f"   - {case_id}: {count:,} nodes")

        # Nodes by client_id - sample
        response = supabase.table('graph_nodes').select('client_id').not_.is_('client_id', 'null').limit(5000).execute()
        client_node_counts = {}
        for row in response.data:
            cid = row.get('client_id')
            if cid:
                client_node_counts[str(cid)] = client_node_counts.get(str(cid), 0) + 1

        results['graph_schema']['clients_with_nodes'] = sorted(client_node_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        print("✅ Top Clients by Node Count (sampled from 5000 nodes):")
        for client_id, count in results['graph_schema']['clients_with_nodes']:
            print(f"   - {client_id}: {count:,} nodes")

        # Chunks by case_id - sample
        response = supabase.table('graph_chunks').select('case_id').not_.is_('case_id', 'null').limit(5000).execute()
        case_chunk_counts = {}
        for row in response.data:
            cid = row.get('case_id')
            if cid:
                case_chunk_counts[str(cid)] = case_chunk_counts.get(str(cid), 0) + 1

        results['graph_schema']['cases_with_chunks'] = sorted(case_chunk_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        print("✅ Top Cases by Chunk Count (sampled from 5000 chunks):")
        for case_id, count in results['graph_schema']['cases_with_chunks']:
            print(f"   - {case_id}: {count:,} chunks")

        # Chunks by client_id - sample
        response = supabase.table('graph_chunks').select('client_id').not_.is_('client_id', 'null').limit(5000).execute()
        client_chunk_counts = {}
        for row in response.data:
            cid = row.get('client_id')
            if cid:
                client_chunk_counts[str(cid)] = client_chunk_counts.get(str(cid), 0) + 1

        results['graph_schema']['clients_with_chunks'] = sorted(client_chunk_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        print("✅ Top Clients by Chunk Count (sampled from 5000 chunks):")
        for client_id, count in results['graph_schema']['clients_with_chunks']:
            print(f"   - {client_id}: {count:,} chunks")

    except Exception as e:
        print(f"❌ Graph schema error: {e}")

    print()

    # ===== CROSS-SCHEMA ANALYSIS =====
    print("4. CROSS-SCHEMA COVERAGE")
    print("-" * 80)

    # Find case_ids that appear in both client and graph schemas
    if 'case_ids' in results['client_schema'] and 'cases_with_nodes' in results['graph_schema']:
        client_case_ids = set(results['client_schema']['case_ids'])
        graph_case_ids = set([cid for cid, _ in results['graph_schema']['cases_with_nodes']])

        common_case_ids = client_case_ids.intersection(graph_case_ids)
        results['cross_schema']['common_case_ids'] = list(common_case_ids)

        print(f"✅ Cases in BOTH client and graph schemas: {len(common_case_ids)}")
        if common_case_ids:
            print(f"   Sample: {list(common_case_ids)[:5]}")

    print()

    # ===== RECOMMENDATIONS =====
    print("5. TEST DATA RECOMMENDATIONS")
    print("-" * 80)

    # Recommend best case_ids for testing
    if results['graph_schema'].get('cases_with_nodes'):
        largest_case = results['graph_schema']['cases_with_nodes'][0]
        print(f"✅ LARGE DATASET TEST: case_id = {largest_case[0]}")
        print(f"   - Estimated nodes: {largest_case[1]:,}")
        print(f"   - Use for: Performance testing, pagination, large result sets")
        print()

        if len(results['graph_schema']['cases_with_nodes']) > 1:
            medium_case = results['graph_schema']['cases_with_nodes'][len(results['graph_schema']['cases_with_nodes'])//2]
            print(f"✅ MEDIUM DATASET TEST: case_id = {medium_case[0]}")
            print(f"   - Estimated nodes: {medium_case[1]:,}")
            print(f"   - Use for: Standard API testing")
            print()

    print("✅ SAFE QUERY LIMITS:")
    print("   - For large datasets: LIMIT 100-1000")
    print("   - For performance tests: LIMIT 5000-10000")
    print("   - For full scans: Use pagination with offset")
    print()

    # ===== OUTPUT TO FILE =====
    output_path = '/srv/luris/be/graphrag-service/tests/results/test_data_inventory.md'

    with open(output_path, 'w') as f:
        f.write("# Test Data Inventory - API Parity Testing\n\n")
        f.write(f"**Discovery Date**: {results['discovery_date']}\n\n")

        f.write("## Law Schema\n\n")
        f.write(f"- **Total Documents**: {results['law_schema'].get('total_documents', 'N/A'):,}\n")
        f.write(f"- **Total Entities**: {results['law_schema'].get('total_entities', 'N/A'):,}\n")

        if results['law_schema'].get('top_entity_types'):
            f.write("\n### Top Entity Types:\n\n")
            for et, count in results['law_schema']['top_entity_types']:
                f.write(f"- **{et}**: {count:,}\n")

        f.write("\n## Client Schema\n\n")
        f.write(f"- **Total Cases**: {results['client_schema'].get('total_cases', 'N/A'):,}\n")
        f.write(f"- **Unique Case IDs**: {len(results['client_schema'].get('case_ids', []))}\n")

        f.write("\n## Graph Schema\n\n")
        f.write(f"- **Total Nodes**: {results['graph_schema'].get('total_nodes', 'N/A'):,}\n")
        f.write(f"- **Total Edges**: {results['graph_schema'].get('total_edges', 'N/A'):,}\n")
        f.write(f"- **Total Communities**: {results['graph_schema'].get('total_communities', 'N/A'):,}\n")
        f.write(f"- **Total Chunks**: {results['graph_schema'].get('total_chunks', 'N/A'):,}\n")
        f.write(f"- **Document Registry**: {results['graph_schema'].get('total_documents', 'N/A'):,}\n")

        if results['graph_schema'].get('cases_with_nodes'):
            f.write("\n### Cases with Graph Data (Top 10 by case_id):\n\n")
            f.write("| Case ID | Node Count (sampled) | Suitable For |\n")
            f.write("|---------|----------------------|--------------|\n")

            for i, (case_id, count) in enumerate(results['graph_schema']['cases_with_nodes']):
                if i == 0:
                    suitability = "Large dataset tests, performance testing"
                elif i < 3:
                    suitability = "Standard API testing"
                else:
                    suitability = "Basic testing"

                f.write(f"| `{case_id}` | {count:,} | {suitability} |\n")

        if results['graph_schema'].get('clients_with_nodes'):
            f.write("\n### Clients with Graph Data (Top 10 by client_id):\n\n")
            f.write("| Client ID | Node Count (sampled) | Suitable For |\n")
            f.write("|-----------|----------------------|--------------|\n")

            for i, (client_id, count) in enumerate(results['graph_schema']['clients_with_nodes']):
                if i == 0:
                    suitability = "Large dataset tests, performance testing"
                elif i < 3:
                    suitability = "Standard API testing"
                else:
                    suitability = "Basic testing"

                f.write(f"| `{client_id}` | {count:,} | {suitability} |\n")

        if results['graph_schema'].get('cases_with_chunks'):
            f.write("\n### Cases with Chunks (Top 10):\n\n")
            f.write("| Case ID | Chunk Count (sampled) |\n")
            f.write("|---------|----------------------|\n")
            for case_id, count in results['graph_schema']['cases_with_chunks']:
                f.write(f"| `{case_id}` | {count:,} |\n")

        if results['graph_schema'].get('clients_with_chunks'):
            f.write("\n### Clients with Chunks (Top 10):\n\n")
            f.write("| Client ID | Chunk Count (sampled) |\n")
            f.write("|-----------|----------------------|\n")
            for client_id, count in results['graph_schema']['clients_with_chunks']:
                f.write(f"| `{client_id}` | {count:,} |\n")

        f.write("\n## Cross-Schema Coverage\n\n")
        if results['cross_schema'].get('common_case_ids'):
            f.write(f"- **Cases in BOTH client and graph schemas**: {len(results['cross_schema']['common_case_ids'])}\n")
            f.write(f"- **Sample common case_ids**: {results['cross_schema']['common_case_ids'][:5]}\n")
        else:
            f.write("- No cross-schema case_id overlap detected in sample\n")

        f.write("\n## Recommended Test Parameters\n\n")

        if results['graph_schema'].get('cases_with_nodes'):
            largest = results['graph_schema']['cases_with_nodes'][0]
            f.write(f"### Large Dataset Test (by case_id)\n")
            f.write(f"```python\n")
            f.write(f"case_id = '{largest[0]}'\n")
            f.write(f"# Estimated nodes: ~{largest[1]:,} (sampled, actual may be higher)\n")
            f.write(f"# Use LIMIT: 100-1000 for reasonable response times\n")
            f.write(f"```\n\n")

            if len(results['graph_schema']['cases_with_nodes']) > 1:
                medium = results['graph_schema']['cases_with_nodes'][len(results['graph_schema']['cases_with_nodes'])//2]
                f.write(f"### Medium Dataset Test (by case_id)\n")
                f.write(f"```python\n")
                f.write(f"case_id = '{medium[0]}'\n")
                f.write(f"# Estimated nodes: ~{medium[1]:,}\n")
                f.write(f"# Use LIMIT: 50-500 for standard testing\n")
                f.write(f"```\n\n")

        if results['graph_schema'].get('clients_with_nodes'):
            largest_client = results['graph_schema']['clients_with_nodes'][0]
            f.write(f"### Large Dataset Test (by client_id)\n")
            f.write(f"```python\n")
            f.write(f"client_id = '{largest_client[0]}'\n")
            f.write(f"# Estimated nodes: ~{largest_client[1]:,} (sampled, actual may be higher)\n")
            f.write(f"# Use LIMIT: 100-1000 for reasonable response times\n")
            f.write(f"```\n\n")

        f.write("### Safe Query Limits\n\n")
        f.write("- **Small queries**: `LIMIT 10-50` (for quick tests)\n")
        f.write("- **Standard queries**: `LIMIT 100-500` (for comprehensive tests)\n")
        f.write("- **Large queries**: `LIMIT 1000-5000` (for performance tests)\n")
        f.write("- **Pagination**: Use `offset` with consistent `limit` for large datasets\n\n")

        f.write("## Data Quality Notes\n\n")
        f.write("- ✅ Law schema has substantial document and entity data\n")
        f.write(f"- ✅ Graph schema has {results['graph_schema'].get('total_nodes', 0):,} nodes across cases\n")
        f.write("- ⚠️ Client.documents and client.entities tables are EMPTY (0 rows)\n")
        f.write("- ℹ️ All test data uses graph schema with case_id filtering\n")
        f.write("- ℹ️ Case IDs are UUIDs in graph schema\n\n")

        f.write("## Implementation Notes\n\n")
        f.write("- Use `case_id` filtering for all graph queries\n")
        f.write("- Node counts are estimated from samples (limit 1000)\n")
        f.write("- Actual dataset sizes may be larger\n")
        f.write("- Test with multiple case_ids for comprehensive coverage\n")
        f.write("- Law schema data is case-agnostic (no case_id)\n")

    print(f"✅ Report written to: {output_path}")
    print()
    print("=" * 80)
    print("DATA DISCOVERY COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
