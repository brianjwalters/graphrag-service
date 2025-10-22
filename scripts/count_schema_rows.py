#!/usr/bin/env python3
"""
Schema Row Count Script

Uses SupabaseClient fluent API to count rows in all tables across
graph, law, and client schemas.

Usage:
    cd /srv/luris/be/graphrag-service
    source venv/bin/activate
    python scripts/count_schema_rows.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import SupabaseClient, SupabaseSettings
from rich.console import Console
from rich.table import Table
from rich import box


async def get_table_row_count(client: SupabaseClient, schema: str, table: str) -> int:
    """
    Get row count for a specific table using fluent API.

    Args:
        client: SupabaseClient instance
        schema: Schema name (graph, law, client)
        table: Table name

    Returns:
        Row count
    """
    try:
        result = await client.schema(schema).table(table) \
            .select('*', count='exact') \
            .limit(1) \
            .execute()

        return result.count if result.count is not None else 0
    except Exception as e:
        print(f"Error counting {schema}.{table}: {e}")
        return -1


async def count_all_tables() -> Dict[str, List[Dict[str, any]]]:
    """
    Count rows in all tables across graph, law, and client schemas.

    Returns:
        Dictionary mapping schema names to list of table counts
    """
    # Initialize Supabase client
    settings = SupabaseSettings()
    client = SupabaseClient(settings=settings, service_name="row-count-script")

    # Define tables for each schema
    schemas = {
        "law": [
            "documents",
            "entities"
        ],
        "client": [
            "cases",
            "documents",
            "entities"
        ],
        "graph": [
            "chunks",
            "nodes",
            "edges",
            "entities",
            "communities",
            "node_communities",
            "document_registry",
            "text_units",
            "enhanced_contextual_chunks",
            "reports"
        ]
    }

    results = {}

    # Count rows for each schema
    for schema_name, tables in schemas.items():
        print(f"\n📊 Counting rows in {schema_name} schema...")
        schema_results = []

        for table_name in tables:
            print(f"  Querying {schema_name}.{table_name}...", end=" ")
            count = await get_table_row_count(client, schema_name, table_name)

            schema_results.append({
                "table": table_name,
                "row_count": count
            })

            if count >= 0:
                print(f"✅ {count:,} rows")
            else:
                print("❌ Error")

        results[schema_name] = schema_results

    await client.close()
    return results


def display_results_table(results: Dict[str, List[Dict[str, any]]]):
    """
    Display row count results in a formatted table.

    Args:
        results: Dictionary mapping schema names to table counts
    """
    console = Console()

    # Create main table
    table = Table(
        title="📊 Supabase Schema Row Counts (Fluent API)",
        box=box.HEAVY_HEAD,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Schema", style="cyan", width=12)
    table.add_column("Table", style="yellow", width=30)
    table.add_column("Row Count", justify="right", style="green", width=15)
    table.add_column("Status", justify="center", width=10)

    # Add rows for each schema
    total_rows = 0
    total_tables = 0

    for schema_name in ["law", "client", "graph"]:
        if schema_name not in results:
            continue

        schema_tables = results[schema_name]
        schema_total = sum(t["row_count"] for t in schema_tables if t["row_count"] >= 0)

        # Add schema rows
        for i, table_data in enumerate(schema_tables):
            row_count = table_data["row_count"]
            status = "✅" if row_count >= 0 else "❌"

            # Only show schema name on first row
            schema_col = schema_name if i == 0 else ""

            table.add_row(
                schema_col,
                table_data["table"],
                f"{row_count:,}" if row_count >= 0 else "Error",
                status
            )

            if row_count >= 0:
                total_rows += row_count
                total_tables += 1

        # Add schema subtotal
        table.add_row(
            "",
            f"[bold]{schema_name} total[/bold]",
            f"[bold green]{schema_total:,}[/bold green]",
            "",
            style="italic"
        )
        table.add_section()

    # Add grand total
    table.add_row(
        "",
        "[bold white]GRAND TOTAL[/bold white]",
        f"[bold yellow]{total_rows:,}[/bold yellow]",
        f"[bold]{total_tables}[/bold]",
        style="bold"
    )

    console.print("\n")
    console.print(table)
    console.print(f"\n[bold green]✅ Successfully counted {total_tables} tables[/bold green]")
    console.print(f"[bold cyan]📈 Total rows across all schemas: {total_rows:,}[/bold cyan]\n")


def display_markdown_table(results: Dict[str, List[Dict[str, any]]]):
    """
    Display results in markdown table format.

    Args:
        results: Dictionary mapping schema names to table counts
    """
    print("\n## Schema Row Counts\n")
    print("| Schema | Table | Row Count |")
    print("|--------|-------|-----------|")

    total_rows = 0

    for schema_name in ["law", "client", "graph"]:
        if schema_name not in results:
            continue

        schema_tables = results[schema_name]

        for i, table_data in enumerate(schema_tables):
            row_count = table_data["row_count"]

            if i == 0:
                print(f"| **{schema_name}** | `{table_data['table']}` | {row_count:,} |")
            else:
                print(f"| | `{table_data['table']}` | {row_count:,} |")

            if row_count >= 0:
                total_rows += row_count

        # Schema subtotal
        schema_total = sum(t["row_count"] for t in schema_tables if t["row_count"] >= 0)
        print(f"| | *{schema_name} subtotal* | *{schema_total:,}* |")

    print(f"| **TOTAL** | | **{total_rows:,}** |")
    print()


async def main():
    """Main entry point."""
    print("🚀 Starting schema row count using SupabaseClient fluent API...\n")

    # Get row counts
    results = await count_all_tables()

    # Display results in rich table
    display_results_table(results)

    # Also display markdown table
    print("\n" + "="*80)
    print("MARKDOWN FORMAT")
    print("="*80)
    display_markdown_table(results)


if __name__ == "__main__":
    asyncio.run(main())
