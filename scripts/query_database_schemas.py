#!/usr/bin/env python3
"""
Query Database Schemas Script

Queries all schema information from Supabase database for law, client, and graph schemas.
Outputs comprehensive schema information including tables, columns, foreign keys, indexes, and RLS policies.

This script uses psql directly for reliable database access.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_psql_query(query: str) -> list:
    """
    Execute a SQL query using psql and return results as list of dicts.

    Args:
        query: SQL query to execute

    Returns:
        List of dictionaries representing query results
    """
    # Database connection details from environment
    db_password = "jocfev-nahgi7-dygzaB"
    db_host = "db.tqfshsnwyhfnkchaiudg.supabase.co"
    db_user = "postgres"
    db_name = "postgres"

    # Set environment variable for password
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password

    # Execute psql with JSON output format
    cmd = [
        'psql',
        '-h', db_host,
        '-U', db_user,
        '-d', db_name,
        '-t',  # Tuples only (no headers)
        '-A',  # Unaligned output
        '-F', '\t',  # Tab-separated
        '-c', query
    ]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            print(f"❌ psql error: {result.stderr}")
            return []

        # Parse tab-separated output
        lines = result.stdout.strip().split('\n')
        if not lines or not lines[0]:
            return []

        # Get column names from first query result
        # We'll need to track this per query type
        return lines

    except subprocess.TimeoutExpired:
        print(f"❌ Query timeout after 30 seconds")
        return []
    except Exception as e:
        print(f"❌ Error executing query: {e}")
        return []


def parse_tsv_to_dict(lines: list, columns: list) -> list:
    """Parse tab-separated values into list of dictionaries."""
    results = []
    for line in lines:
        if not line.strip():
            continue
        values = line.split('\t')
        row_dict = {}
        for i, col in enumerate(columns):
            row_dict[col] = values[i] if i < len(values) else None
        results.append(row_dict)
    return results


def query_schemas():
    """Query all schema information from Supabase database"""

    print("=" * 70)
    print("🔍 LURIS DATABASE SCHEMA QUERY")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Querying schemas: law, client, graph")
    print("=" * 70)

    # 1. Query all tables
    print("\n📊 Step 1/7: Querying tables...")
    tables_query = """
    SELECT table_schema, table_name, table_type
    FROM information_schema.tables
    WHERE table_schema IN ('law', 'client', 'graph')
    ORDER BY table_schema, table_name;
    """

    tables_raw = run_psql_query(tables_query)
    tables = parse_tsv_to_dict(tables_raw, ['table_schema', 'table_name', 'table_type'])
    print(f"✅ Found {len(tables)} tables")

    # 2. Query all columns for law schema
    print("📊 Step 2/7: Querying law schema columns...")
    law_columns_query = """
    SELECT
        table_name,
        column_name,
        data_type,
        character_maximum_length,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = 'law'
    ORDER BY table_name, ordinal_position;
    """

    law_columns_raw = run_psql_query(law_columns_query)
    law_columns = parse_tsv_to_dict(law_columns_raw, [
        'table_name', 'column_name', 'data_type',
        'character_maximum_length', 'is_nullable', 'column_default'
    ])
    print(f"✅ Found {len(law_columns)} columns in law schema")

    # 3. Query all columns for client schema
    print("📊 Step 3/7: Querying client schema columns...")
    client_columns_query = """
    SELECT
        table_name,
        column_name,
        data_type,
        character_maximum_length,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = 'client'
    ORDER BY table_name, ordinal_position;
    """

    client_columns_raw = run_psql_query(client_columns_query)
    client_columns = parse_tsv_to_dict(client_columns_raw, [
        'table_name', 'column_name', 'data_type',
        'character_maximum_length', 'is_nullable', 'column_default'
    ])
    print(f"✅ Found {len(client_columns)} columns in client schema")

    # 4. Query all columns for graph schema
    print("📊 Step 4/7: Querying graph schema columns...")
    graph_columns_query = """
    SELECT
        table_name,
        column_name,
        data_type,
        character_maximum_length,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = 'graph'
    ORDER BY table_name, ordinal_position;
    """

    graph_columns_raw = run_psql_query(graph_columns_query)
    graph_columns = parse_tsv_to_dict(graph_columns_raw, [
        'table_name', 'column_name', 'data_type',
        'character_maximum_length', 'is_nullable', 'column_default'
    ])
    print(f"✅ Found {len(graph_columns)} columns in graph schema")

    # 5. Query foreign keys
    print("📊 Step 5/7: Querying foreign keys...")
    fk_query = """
    SELECT
        tc.table_schema,
        tc.table_name,
        kcu.column_name,
        ccu.table_schema AS foreign_table_schema,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name,
        tc.constraint_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema IN ('law', 'client', 'graph')
    ORDER BY tc.table_schema, tc.table_name;
    """

    foreign_keys_raw = run_psql_query(fk_query)
    foreign_keys = parse_tsv_to_dict(foreign_keys_raw, [
        'table_schema', 'table_name', 'column_name',
        'foreign_table_schema', 'foreign_table_name',
        'foreign_column_name', 'constraint_name'
    ])
    print(f"✅ Found {len(foreign_keys)} foreign key relationships")

    # 6. Query indexes
    print("📊 Step 6/7: Querying indexes...")
    indexes_query = """
    SELECT
        schemaname,
        tablename,
        indexname,
        indexdef
    FROM pg_indexes
    WHERE schemaname IN ('law', 'client', 'graph')
    ORDER BY schemaname, tablename, indexname;
    """

    indexes_raw = run_psql_query(indexes_query)
    indexes = parse_tsv_to_dict(indexes_raw, [
        'schemaname', 'tablename', 'indexname', 'indexdef'
    ])
    print(f"✅ Found {len(indexes)} indexes")

    # 7. Query RLS policies
    print("📊 Step 7/7: Querying RLS policies...")
    rls_query = """
    SELECT
        schemaname,
        tablename,
        policyname,
        permissive,
        cmd,
        qual,
        with_check
    FROM pg_policies
    WHERE schemaname IN ('law', 'client', 'graph')
    ORDER BY schemaname, tablename, policyname;
    """

    rls_policies_raw = run_psql_query(rls_query)
    rls_policies = parse_tsv_to_dict(rls_policies_raw, [
        'schemaname', 'tablename', 'policyname', 'permissive',
        'cmd', 'qual', 'with_check'
    ])
    print(f"✅ Found {len(rls_policies)} RLS policies")

    # Compile results
    schema_data = {
        "query_timestamp": datetime.now().isoformat(),
        "schemas": ["law", "client", "graph"],
        "tables": tables,
        "law_columns": law_columns,
        "client_columns": client_columns,
        "graph_columns": graph_columns,
        "foreign_keys": foreign_keys,
        "indexes": indexes,
        "rls_policies": rls_policies,
        "summary": {
            "total_tables": len(tables),
            "total_columns": len(law_columns) + len(client_columns) + len(graph_columns),
            "total_foreign_keys": len(foreign_keys),
            "total_indexes": len(indexes),
            "total_rls_policies": len(rls_policies)
        }
    }

    # Save to JSON file
    output_file = "/srv/luris/be/docs/database/schema_data.json"
    with open(output_file, 'w') as f:
        json.dump(schema_data, f, indent=2, default=str)

    print(f"\n✅ Schema data saved to {output_file}")

    # Print detailed summary
    print("\n" + "=" * 70)
    print("📊 DATABASE SCHEMA SUMMARY")
    print("=" * 70)

    # Group tables by schema
    law_tables = [t for t in tables if t['table_schema'] == 'law']
    client_tables = [t for t in tables if t['table_schema'] == 'client']
    graph_tables = [t for t in tables if t['table_schema'] == 'graph']

    print(f"\n📚 LAW SCHEMA ({len(law_tables)} tables):")
    for table in law_tables:
        col_count = len([c for c in law_columns if c['table_name'] == table['table_name']])
        print(f"   - {table['table_name']:30} ({col_count:2d} columns)")

    print(f"\n👤 CLIENT SCHEMA ({len(client_tables)} tables):")
    for table in client_tables:
        col_count = len([c for c in client_columns if c['table_name'] == table['table_name']])
        print(f"   - {table['table_name']:30} ({col_count:2d} columns)")

    print(f"\n🕸️  GRAPH SCHEMA ({len(graph_tables)} tables):")
    for table in graph_tables:
        col_count = len([c for c in graph_columns if c['table_name'] == table['table_name']])
        print(f"   - {table['table_name']:30} ({col_count:2d} columns)")

    print(f"\n🔗 RELATIONSHIPS:")
    print(f"   - Foreign Keys: {len(foreign_keys)}")
    print(f"   - Indexes: {len(indexes)}")
    print(f"   - RLS Policies: {len(rls_policies)}")

    # Print detailed table information for each schema
    print("\n" + "=" * 70)
    print("📋 DETAILED TABLE INFORMATION")
    print("=" * 70)

    # Law Schema Details
    if law_tables:
        print(f"\n📚 LAW SCHEMA TABLES:")
        for table in law_tables:
            table_columns = [c for c in law_columns if c['table_name'] == table['table_name']]
            print(f"\n   Table: {table['table_name']} ({len(table_columns)} columns)")
            for col in table_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                print(f"      - {col['column_name']:30} {col['data_type']}{max_len:10} {nullable:8}{default}")

    # Client Schema Details
    if client_tables:
        print(f"\n👤 CLIENT SCHEMA TABLES:")
        for table in client_tables:
            table_columns = [c for c in client_columns if c['table_name'] == table['table_name']]
            print(f"\n   Table: {table['table_name']} ({len(table_columns)} columns)")
            for col in table_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                print(f"      - {col['column_name']:30} {col['data_type']}{max_len:10} {nullable:8}{default}")

    # Graph Schema Details
    if graph_tables:
        print(f"\n🕸️  GRAPH SCHEMA TABLES:")
        for table in graph_tables:
            table_columns = [c for c in graph_columns if c['table_name'] == table['table_name']]
            print(f"\n   Table: {table['table_name']} ({len(table_columns)} columns)")
            for col in table_columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                print(f"      - {col['column_name']:30} {col['data_type']}{max_len:10} {nullable:8}{default}")

    # Foreign Keys Details
    if foreign_keys:
        print(f"\n🔗 FOREIGN KEY RELATIONSHIPS:")
        for fk in foreign_keys:
            print(f"   - {fk['table_schema']}.{fk['table_name']}.{fk['column_name']}")
            print(f"     → {fk['foreign_table_schema']}.{fk['foreign_table_name']}.{fk['foreign_column_name']}")
            print(f"     ({fk['constraint_name']})")

    # Indexes Summary
    if indexes:
        print(f"\n📇 INDEXES (showing first 20):")
        for i, idx in enumerate(indexes[:20]):
            print(f"   {i+1}. {idx['schemaname']}.{idx['tablename']}.{idx['indexname']}")

    # RLS Policies
    if rls_policies:
        print(f"\n🔒 ROW LEVEL SECURITY POLICIES:")
        for policy in rls_policies:
            print(f"   - {policy['schemaname']}.{policy['tablename']}")
            print(f"     Policy: {policy['policyname']}")
            print(f"     Command: {policy['cmd']}")

    print("\n" + "=" * 70)
    print("✅ SCHEMA QUERY COMPLETE")
    print("=" * 70)

    return schema_data


if __name__ == '__main__':
    try:
        result = query_schemas()

        if result is None:
            print("\n❌ Schema query failed")
            sys.exit(1)
        else:
            print(f"\n✅ Schema query successful")
            print(f"   Total tables: {result['summary']['total_tables']}")
            print(f"   Total columns: {result['summary']['total_columns']}")
            print(f"   Total foreign keys: {result['summary']['total_foreign_keys']}")
            print(f"   Total indexes: {result['summary']['total_indexes']}")
            print(f"   Total RLS policies: {result['summary']['total_rls_policies']}")
            print(f"\n📄 Results saved to: /srv/luris/be/docs/database/schema_data.json")
            sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
