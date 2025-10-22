"""
Diagnostic script to discover actual database schema structure.

This script will:
1. Query PostgreSQL to discover schemas
2. List tables in each schema
3. Describe table columns
4. Test direct SQL access vs REST API access
"""

import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.supabase_client import create_admin_supabase_client


async def discover_schemas(client):
    """Discover all schemas in the database"""
    print("\n🔍 Discovering Database Schemas...")

    try:
        # Use RPC to query PostgreSQL system catalogs
        result = await client.rpc("get_schemas", {}, admin_operation=True)
        print(f"✅ Found schemas via RPC: {result}")
        return result
    except Exception as e:
        print(f"❌ RPC method failed: {e}")

    # Try alternative: query information_schema
    print("\n🔄 Trying alternative method...")
    try:
        # Query public schema to see what tables are exposed
        tables = [
            "law_documents", "law_chunks", "law_citations", "law_embeddings",
            "client_documents", "client_chunks", "client_citations", "client_embeddings",
            "graph_entities", "graph_relationships", "graph_communities"
        ]

        available_tables = []
        for table in tables:
            try:
                result = await client.get(table, limit=1, admin_operation=True)
                available_tables.append({
                    "table": table,
                    "accessible": True,
                    "sample_row_count": len(result)
                })
                print(f"   ✅ {table} - accessible ({len(result)} rows)")
            except Exception as e:
                error_msg = str(e)
                available_tables.append({
                    "table": table,
                    "accessible": False,
                    "error": error_msg[:100]
                })
                print(f"   ❌ {table} - {error_msg[:80]}")

        return available_tables

    except Exception as e:
        print(f"❌ Alternative method failed: {e}")
        return None


async def describe_table_columns(client, table_name):
    """Get column information for a table"""
    print(f"\n📋 Describing table: {table_name}")

    try:
        # Get a sample row to see the structure
        result = await client.get(table_name, limit=1, admin_operation=True)

        if result and len(result) > 0:
            columns = list(result[0].keys())
            print(f"   Columns ({len(columns)}): {', '.join(columns[:10])}")
            if len(columns) > 10:
                print(f"   ... and {len(columns) - 10} more")

            return {
                "table": table_name,
                "columns": columns,
                "sample_data": result[0] if result else None
            }
        else:
            print(f"   ⚠️  No data in table")
            return {"table": table_name, "columns": [], "sample_data": None}

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"table": table_name, "error": str(e)}


async def test_schema_qualified_access(client):
    """Test if schema-qualified names work"""
    print("\n🧪 Testing Schema-Qualified Access...")

    test_patterns = [
        # Dot notation (should be converted internally)
        "law.documents",
        "client.documents",
        "graph.entities",

        # Underscore notation (direct REST API format)
        "law_documents",
        "client_documents",
        "graph_entities",

        # Check if views exist
        "law_vwdocuments",
        "graph_vwentities"
    ]

    results = []
    for pattern in test_patterns:
        try:
            result = await client.get(pattern, limit=1, admin_operation=True)
            results.append({
                "pattern": pattern,
                "accessible": True,
                "rows": len(result)
            })
            print(f"   ✅ {pattern}: accessible ({len(result)} rows)")
        except Exception as e:
            error = str(e)
            results.append({
                "pattern": pattern,
                "accessible": False,
                "error": error[:80]
            })
            print(f"   ❌ {pattern}: {error[:60]}")

    return results


async def test_client_documents_structure(client):
    """Specifically test client.documents table structure"""
    print("\n🔬 Analyzing client_documents table structure...")

    try:
        # Get sample rows
        result = await client.get("client_documents", limit=5, admin_operation=True)

        if result:
            print(f"   ✅ Retrieved {len(result)} rows")
            print(f"   📋 Columns: {list(result[0].keys())}")

            # Check for expected columns
            expected_columns = ["id", "document_id", "client_name", "document_type", "status"]
            for col in expected_columns:
                if col in result[0]:
                    print(f"      ✅ {col} exists")
                else:
                    print(f"      ❌ {col} MISSING")

            return {
                "table": "client_documents",
                "accessible": True,
                "row_count": len(result),
                "columns": list(result[0].keys()),
                "sample": result[0]
            }
        else:
            print(f"   ⚠️  Table exists but has no data")
            return {"table": "client_documents", "accessible": True, "row_count": 0}

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"table": "client_documents", "error": str(e)}


async def main():
    """Main diagnostic execution"""
    print("="*80)
    print("DATABASE SCHEMA DIAGNOSTIC TOOL")
    print("="*80)

    client = create_admin_supabase_client("schema-diagnostic")
    print("✅ Admin client created\n")

    # 1. Discover schemas
    schemas = await discover_schemas(client)

    # 2. Test schema-qualified access
    access_results = await test_schema_qualified_access(client)

    # 3. Describe accessible tables
    accessible_tables = [r for r in access_results if r["accessible"]]
    print(f"\n📊 Found {len(accessible_tables)} accessible tables\n")

    table_structures = []
    for table_info in accessible_tables[:5]:  # Describe first 5 accessible tables
        structure = await describe_table_columns(client, table_info["pattern"])
        table_structures.append(structure)

    # 4. Specifically check client_documents
    client_docs_info = await test_client_documents_structure(client)

    # 5. Generate report
    report = {
        "schemas": schemas if isinstance(schemas, list) else [],
        "accessible_tables": accessible_tables,
        "schema_qualified_access": access_results,
        "table_structures": table_structures,
        "client_documents_analysis": client_docs_info,
        "summary": {
            "total_tables_tested": len(access_results),
            "accessible_count": len(accessible_tables),
            "inaccessible_count": len([r for r in access_results if not r["accessible"]])
        }
    }

    # Save report
    output_file = "/srv/luris/be/graphrag-service/tests/schema_diagnostic_report.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY")
    print("="*80)
    print(f"Total tables tested: {report['summary']['total_tables_tested']}")
    print(f"✅ Accessible: {report['summary']['accessible_count']}")
    print(f"❌ Inaccessible: {report['summary']['inaccessible_count']}")
    print(f"\n💾 Full report saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
