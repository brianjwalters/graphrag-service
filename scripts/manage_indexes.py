#!/usr/bin/env python3
"""
Manage Vector Indexes for GraphRAG Upload

This script drops vector indexes before upload and recreates them after
to optimize upload performance (10-100x faster without indexes).

Based on PostgreSQL pgvector best practices.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import create_admin_supabase_client


# Vector index definitions
VECTOR_INDEXES = {
    "graph.nodes": {
        "column": "embedding",
        "index_name": "idx_nodes_embedding",
        "index_type": "hnsw",
        "distance": "vector_cosine_ops",
        "params": {"m": 16, "ef_construction": 64}
    },
    "graph.chunks": {
        "column": "content_embedding",
        "index_name": "idx_chunks_content_embedding",
        "index_type": "hnsw",
        "distance": "vector_cosine_ops",
        "params": {"m": 16, "ef_construction": 64}
    },
    "graph.enhanced_contextual_chunks": {
        "column": "vector",
        "index_name": "idx_enhanced_chunks_vector",
        "index_type": "hnsw",
        "distance": "vector_cosine_ops",
        "params": {"m": 16, "ef_construction": 64}
    },
    "graph.communities": {
        "column": "summary_embedding",
        "index_name": "idx_communities_summary_embedding",
        "index_type": "hnsw",
        "distance": "vector_cosine_ops",
        "params": {"m": 16, "ef_construction": 64}
    },
    "graph.reports": {
        "column": "report_embedding",
        "index_name": "idx_reports_report_embedding",
        "index_type": "hnsw",
        "distance": "vector_cosine_ops",
        "params": {"m": 16, "ef_construction": 64}
    }
}


async def drop_indexes(supabase):
    """Drop all vector indexes before upload."""
    print("\n" + "="*70)
    print("DROPPING VECTOR INDEXES")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Purpose: Optimize upload performance (10-100x faster)\n")

    dropped = []
    failed = []

    for table, config in VECTOR_INDEXES.items():
        index_name = config["index_name"]
        print(f"📊 {table}.{config['column']}")
        print(f"   Index: {index_name}")

        try:
            # Drop index if exists (idempotent)
            sql = f"DROP INDEX IF EXISTS {index_name};"

            # Note: SupabaseClient doesn't have direct SQL execution via MCP
            # We'll need to use a PostgreSQL RPC function or direct connection
            # For now, we'll use the execute_sql method if available

            try:
                await supabase.execute_sql(sql, admin_operation=True)
                print(f"   ✅ Dropped successfully\n")
                dropped.append(index_name)
            except AttributeError:
                # execute_sql might not be available, try RPC
                try:
                    await supabase.rpc('execute_sql', {'query': sql}, admin_operation=True)
                    print(f"   ✅ Dropped successfully (via RPC)\n")
                    dropped.append(index_name)
                except Exception as rpc_error:
                    print(f"   ⚠️  Could not drop via SupabaseClient: {rpc_error}")
                    print(f"   💡 Manual SQL required:")
                    print(f"      {sql}\n")
                    failed.append(index_name)

        except Exception as e:
            print(f"   ❌ Failed: {e}\n")
            failed.append(index_name)

    print("="*70)
    print("DROP SUMMARY")
    print("="*70)
    print(f"Successfully dropped: {len(dropped)}")
    print(f"Failed/Manual required: {len(failed)}")

    if failed:
        print("\n⚠️  MANUAL ACTION REQUIRED:")
        print("Execute these SQL statements via Supabase dashboard or psql:\n")
        for table, config in VECTOR_INDEXES.items():
            if config["index_name"] in failed:
                print(f"DROP INDEX IF EXISTS {config['index_name']};")

    return dropped, failed


async def create_indexes(supabase):
    """Recreate vector indexes after upload with optimal settings."""
    print("\n" + "="*70)
    print("CREATING VECTOR INDEXES")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Purpose: Enable fast vector similarity search\n")

    created = []
    failed = []

    for table, config in VECTOR_INDEXES.items():
        index_name = config["index_name"]
        column = config["column"]
        index_type = config["index_type"]
        distance = config["distance"]
        params = config["params"]

        print(f"📊 {table}.{column}")
        print(f"   Index: {index_name}")
        print(f"   Type: {index_type.upper()}")
        print(f"   Distance: {distance}")
        print(f"   Parameters: m={params['m']}, ef_construction={params['ef_construction']}")

        try:
            # Build CREATE INDEX statement
            sql = f"""
CREATE INDEX {index_name}
ON {table}
USING {index_type} ({column} {distance})
WITH (m = {params['m']}, ef_construction = {params['ef_construction']});
""".strip()

            try:
                await supabase.execute_sql(sql, admin_operation=True)
                print(f"   ✅ Created successfully\n")
                created.append(index_name)
            except AttributeError:
                # Try RPC
                try:
                    await supabase.rpc('execute_sql', {'query': sql}, admin_operation=True)
                    print(f"   ✅ Created successfully (via RPC)\n")
                    created.append(index_name)
                except Exception as rpc_error:
                    print(f"   ⚠️  Could not create via SupabaseClient: {rpc_error}")
                    print(f"   💡 Manual SQL required:")
                    print(f"      {sql}\n")
                    failed.append(index_name)

        except Exception as e:
            print(f"   ❌ Failed: {e}\n")
            failed.append(index_name)

    print("="*70)
    print("CREATE SUMMARY")
    print("="*70)
    print(f"Successfully created: {len(created)}")
    print(f"Failed/Manual required: {len(failed)}")

    if failed:
        print("\n⚠️  MANUAL ACTION REQUIRED:")
        print("Execute these SQL statements via Supabase dashboard or psql:\n")
        for table, config in VECTOR_INDEXES.items():
            if config["index_name"] in failed:
                params = config["params"]
                print(f"""
CREATE INDEX {config['index_name']}
ON {table}
USING {config['index_type']} ({config['column']} {config['distance']})
WITH (m = {params['m']}, ef_construction = {params['ef_construction']});
""".strip())

    return created, failed


async def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage vector indexes for GraphRAG upload")
    parser.add_argument("action", choices=["drop", "create", "status"],
                       help="Action to perform")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("VECTOR INDEX MANAGEMENT")
    print("="*70)
    print(f"Action: {args.action.upper()}")

    # Initialize Supabase client
    try:
        supabase = create_admin_supabase_client(
            service_name="index-manager"
        )
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        print("\n💡 Make sure environment variables are set:")
        print("   SUPABASE_URL")
        print("   SUPABASE_SERVICE_KEY")
        return 1

    try:
        if args.action == "drop":
            dropped, failed = await drop_indexes(supabase)
            if failed:
                print("\n⚠️  Some indexes require manual dropping.")
                print("   Review the SQL statements above and execute via Supabase dashboard.")
                return 2
            else:
                print("\n✅ All indexes dropped successfully!")
                return 0

        elif args.action == "create":
            created, failed = await create_indexes(supabase)
            if failed:
                print("\n⚠️  Some indexes require manual creation.")
                print("   Review the SQL statements above and execute via Supabase dashboard.")
                return 2
            else:
                print("\n✅ All indexes created successfully!")
                return 0

        elif args.action == "status":
            print("\nVector Index Definitions:")
            print("-" * 70)
            for table, config in VECTOR_INDEXES.items():
                print(f"\n{table}.{config['column']}")
                print(f"  Index: {config['index_name']}")
                print(f"  Type: {config['index_type']}")
                print(f"  Distance: {config['distance']}")
                print(f"  Parameters: {config['params']}")
            return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
