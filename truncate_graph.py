#!/usr/bin/env python3
"""
Truncate all graph schema tables to start fresh.
"""

import sys
import asyncio

# Add GraphRAG service to path
sys.path.insert(0, "/srv/luris/be/graphrag-service")

from src.clients.supabase_client import SupabaseClient


async def truncate_graph_tables():
    """Truncate all graph schema tables."""

    print("🗑️  Truncating Graph Schema Tables")
    print("=" * 60)

    # Create Supabase client
    client = SupabaseClient()

    # List of tables to truncate (in order to respect foreign keys)
    tables = [
        "node_communities",            # Junction table first
        "chunk_entity_connections",
        "chunk_cross_references",
        "text_units",
        "enhanced_contextual_chunks",
        "chunks",
        "edges",                       # Edges before nodes
        "communities",                 # Communities before nodes
        "nodes",                       # Nodes
        "document_registry"            # Document registry last
    ]

    truncated = []
    failed = []

    for table in tables:
        try:
            print(f"\n📋 Truncating graph.{table}...")

            # Delete all rows (TRUNCATE might not work with RLS)
            result = await client.delete(
                table=table,
                filters={},  # Empty filters = delete all
                schema="graph"
            )

            print(f"   ✅ Cleared graph.{table}")
            truncated.append(table)

        except Exception as e:
            print(f"   ⚠️  Error with graph.{table}: {e}")
            # Try alternative approach - select and delete
            try:
                print(f"   🔄 Trying alternative deletion method...")

                # This might work better with RLS policies
                from supabase import create_client
                import os

                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

                if supabase_url and supabase_key:
                    supabase = create_client(supabase_url, supabase_key)
                    result = supabase.from_(f"graph_{table}").delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                    print(f"   ✅ Cleared graph.{table} (alternative method)")
                    truncated.append(table)
                else:
                    failed.append((table, "Missing Supabase credentials"))

            except Exception as e2:
                print(f"   ❌ Failed: {e2}")
                failed.append((table, str(e2)))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TRUNCATION SUMMARY")
    print("=" * 60)
    print(f"\n✅ Successfully cleared: {len(truncated)} tables")
    for table in truncated:
        print(f"   - graph.{table}")

    if failed:
        print(f"\n❌ Failed to clear: {len(failed)} tables")
        for table, error in failed:
            print(f"   - graph.{table}: {error[:100]}...")
    else:
        print("\n🎉 All graph schema tables successfully cleared!")

    print("\n✅ Graph schema reset complete!")


if __name__ == "__main__":
    asyncio.run(truncate_graph_tables())
