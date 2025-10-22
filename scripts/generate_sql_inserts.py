#!/usr/bin/env python3
"""
Generate SQL INSERT Statements from JSON Data

This script converts JSON data files into PostgreSQL INSERT statements
that can be executed via MCP tools or psql.

Handles:
- Vector embeddings (2048-dimensional)
- UUID fields
- JSONB fields
- TEXT ARRAY fields
- Proper SQL escaping
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Data directory
DATA_DIR = Path("/srv/luris/be/graphrag-service/data")
SQL_OUTPUT_DIR = Path("/srv/luris/be/graphrag-service/sql_inserts")

def escape_sql_string(value: str) -> str:
    """Escape string for SQL insertion."""
    if value is None:
        return "NULL"
    # Replace single quotes with double single quotes
    return "'" + str(value).replace("'", "''") + "'"

def format_vector(vec: List[float]) -> str:
    """Format Python list as PostgreSQL vector."""
    if vec is None:
        return "NULL"
    # Format as '[0.1, 0.2, ...]'
    vec_str = "[" + ", ".join(str(v) for v in vec) + "]"
    return f"'{vec_str}'"

def format_jsonb(obj: Dict) -> str:
    """Format Python dict as PostgreSQL JSONB."""
    if obj is None:
        return "NULL"
    json_str = json.dumps(obj).replace("'", "''")
    return f"'{json_str}'"

def format_text_array(arr: List[str]) -> str:
    """Format Python list as PostgreSQL TEXT array."""
    if arr is None or len(arr) == 0:
        return "ARRAY[]::TEXT[]"
    # Format as ARRAY['val1', 'val2']
    escaped = [val.replace("'", "''") for val in arr]
    arr_str = "', '".join(escaped)
    return f"ARRAY['{arr_str}']::TEXT[]"

def format_uuid(uuid_str: Optional[str]) -> str:
    """Format UUID field."""
    if uuid_str is None:
        return "NULL"
    return f"'{uuid_str}'::UUID"

def generate_insert_statement(table: str, record: Dict[str, Any], column_spec: Dict[str, str]) -> str:
    """
    Generate INSERT statement for a single record.

    Args:
        table: Table name (e.g., 'graph.nodes')
        record: Dictionary with record data
        column_spec: Dictionary mapping column names to their types
    """
    columns = []
    values = []

    for col, col_type in column_spec.items():
        if col in record:
            columns.append(col)
            value = record[col]

            if value is None:
                values.append("NULL")
            elif col_type == "vector":
                values.append(format_vector(value))
            elif col_type == "jsonb":
                values.append(format_jsonb(value))
            elif col_type == "text_array":
                values.append(format_text_array(value))
            elif col_type == "uuid":
                values.append(format_uuid(value))
            elif col_type == "text":
                values.append(escape_sql_string(value))
            elif col_type in ["integer", "real", "double precision"]:
                values.append(str(value))
            elif col_type == "boolean":
                values.append("TRUE" if value else "FALSE")
            elif col_type == "timestamptz":
                values.append(escape_sql_string(value) if value else "NOW()")
            else:
                # Default: treat as text
                values.append(escape_sql_string(value))

    cols_str = ", ".join(columns)
    vals_str = ", ".join(values)

    return f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str});"

def generate_sql_file(
    json_file: str,
    table: str,
    column_spec: Dict[str, str],
    batch_size: int = 1000
) -> List[str]:
    """
    Generate SQL files from JSON data.

    Returns:
        List of generated SQL file paths
    """
    print(f"\n{'='*70}")
    print(f"Processing: {json_file} → {table}")
    print(f"{'='*70}")

    # Load JSON data
    json_path = DATA_DIR / json_file
    print(f"📂 Loading: {json_path}")

    with open(json_path, 'r') as f:
        records = json.load(f)

    print(f"✓ Loaded {len(records):,} records")

    # Create output directory
    SQL_OUTPUT_DIR.mkdir(exist_ok=True)

    # Generate SQL files in batches
    sql_files = []
    batch_num = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        batch_num += 1

        # Generate filename
        table_name = table.replace("graph.", "")
        sql_file = SQL_OUTPUT_DIR / f"{table_name}_batch_{batch_num:03d}.sql"

        print(f"  Generating batch {batch_num}: records {i+1:,}-{min(i+batch_size, len(records)):,} → {sql_file.name}")

        # Generate INSERT statements
        statements = []
        for record in batch:
            try:
                stmt = generate_insert_statement(table, record, column_spec)
                statements.append(stmt)
            except Exception as e:
                print(f"    ⚠️  Error generating statement for record: {e}")
                continue

        # Write to file
        with open(sql_file, 'w') as f:
            # Add header comment
            f.write(f"-- Batch {batch_num} for {table}\n")
            f.write(f"-- Records {i+1:,} to {min(i+batch_size, len(records)):,}\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")

            # Write statements
            f.write("\n".join(statements))
            f.write("\n")

        sql_files.append(str(sql_file))

    print(f"✓ Generated {batch_num} SQL files ({len(records):,} total records)")

    return sql_files

def main():
    """Main execution."""
    print("\n" + "="*70)
    print("SQL INSERT STATEMENT GENERATOR")
    print("="*70)
    print(f"Start time: {datetime.now().isoformat()}")

    # Define table specifications
    # Format: {json_file: (table_name, {column: type})}

    table_specs = {
        "document_registry.json": ("graph.document_registry", {
            "id": "uuid",
            "document_id": "text",
            "title": "text",
            "document_type": "text",
            "source_schema": "text",
            "status": "text",
            "metadata": "jsonb",
            "client_id": "uuid",
            "case_id": "uuid",
            "processing_status": "text",
            "created_at": "timestamptz",
            "updated_at": "timestamptz"
        }),

        "nodes.json": ("graph.nodes", {
            "id": "uuid",
            "node_id": "text",
            "node_type": "text",
            "title": "text",
            "description": "text",
            "source_id": "text",
            "source_type": "text",
            "node_degree": "integer",
            "community_id": "text",
            "rank_score": "double precision",
            "metadata": "jsonb",
            "client_id": "uuid",
            "case_id": "uuid",
            "embedding": "vector",
            "created_at": "timestamptz",
            "updated_at": "timestamptz"
        }),

        "communities.json": ("graph.communities", {
            "id": "uuid",
            "community_id": "text",
            "title": "text",
            "summary": "text",
            "description": "text",
            "level": "integer",
            "node_count": "integer",
            "edge_count": "integer",
            "coherence_score": "double precision",
            "parent_community_id": "text",
            "metadata": "jsonb",
            "client_id": "uuid",
            "case_id": "uuid",
            "summary_embedding": "vector",
            "created_at": "timestamptz",
            "updated_at": "timestamptz"
        }),

        "edges.json": ("graph.edges", {
            "id": "uuid",
            "edge_id": "text",
            "source_node_id": "text",
            "target_node_id": "text",
            "relationship_type": "text",
            "weight": "double precision",
            "evidence": "text",
            "confidence_score": "double precision",
            "extraction_method": "text",
            "metadata": "jsonb",
            "client_id": "uuid",
            "case_id": "uuid",
            "created_at": "timestamptz",
            "updated_at": "timestamptz"
        }),

        "node_communities.json": ("graph.node_communities", {
            "id": "uuid",
            "node_id": "text",
            "community_id": "text",
            "membership_strength": "real",
            "created_at": "timestamptz"
        }),

        "chunks.json": ("graph.chunks", {
            "id": "uuid",
            "chunk_id": "text",
            "document_id": "text",
            "chunk_index": "integer",
            "content": "text",
            "content_type": "text",
            "token_count": "integer",
            "chunk_size": "integer",
            "overlap_size": "integer",
            "chunk_method": "text",
            "parent_chunk_id": "text",
            "context_before": "text",
            "context_after": "text",
            "metadata": "jsonb",
            "content_embedding": "vector",
            "created_at": "timestamptz"
        }),

        "enhanced_contextual_chunks.json": ("graph.enhanced_contextual_chunks", {
            "id": "uuid",
            "chunk_id": "text",
            "document_id": "text",
            "chunk_index": "integer",
            "content": "text",
            "contextualized_content": "text",
            "chunk_size": "integer",
            "vector": "vector",
            "client_id": "text",  # TEXT, not UUID!
            "metadata": "jsonb",
            "created_at": "timestamptz",
            "updated_at": "timestamptz"
        }),

        "text_units.json": ("graph.text_units", {
            "id": "uuid",
            "text_unit_id": "text",
            "chunk_id": "text",
            "text": "text",
            "n_tokens": "integer",
            "document_ids": "text_array",
            "entity_ids": "text_array",
            "relationship_ids": "text_array",
            "covariate_ids": "text_array",
            "metadata": "jsonb",
            "created_at": "timestamptz"
        }),

        "reports.json": ("graph.reports", {
            "id": "uuid",
            "report_id": "text",
            "report_type": "text",
            "title": "text",
            "content": "text",
            "summary": "text",
            "community_id": "text",
            "node_id": "text",
            "rating": "double precision",
            "metadata": "jsonb",
            "report_embedding": "vector",
            "created_at": "timestamptz"
        })
    }

    # Generate SQL files for each table
    all_sql_files = {}

    for json_file, (table, column_spec) in table_specs.items():
        try:
            sql_files = generate_sql_file(json_file, table, column_spec, batch_size=500)
            all_sql_files[table] = sql_files
        except Exception as e:
            print(f"❌ Error processing {json_file}: {e}")
            continue

    # Print summary
    print(f"\n{'='*70}")
    print("GENERATION SUMMARY")
    print(f"{'='*70}")

    total_files = sum(len(files) for files in all_sql_files.values())
    print(f"Total SQL files generated: {total_files}")
    print(f"\nOutput directory: {SQL_OUTPUT_DIR}")

    for table, files in all_sql_files.items():
        print(f"  {table}: {len(files)} files")

    print(f"\nEnd time: {datetime.now().isoformat()}")
    print("\n✅ SQL generation complete!")
    print("\nNext step: Execute SQL files via MCP or psql")

    return 0

if __name__ == "__main__":
    exit(main())
