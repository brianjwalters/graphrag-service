#!/usr/bin/env python3
"""
Validate Schema Data Script

Validates the completeness and accuracy of the schema data extracted from the database.
Performs consistency checks and generates a validation report.
"""

import json
import sys
from pathlib import Path


def validate_schema_data(schema_file_path: str):
    """
    Validate the schema data JSON file for completeness and consistency.

    Args:
        schema_file_path: Path to the schema_data.json file

    Returns:
        True if all validations pass, False otherwise
    """
    print("=" * 70)
    print("🔍 SCHEMA DATA VALIDATION")
    print("=" * 70)

    # Load schema data
    try:
        with open(schema_file_path, 'r') as f:
            data = json.load(f)
        print(f"✅ Successfully loaded schema data from {schema_file_path}")
    except Exception as e:
        print(f"❌ Failed to load schema data: {e}")
        return False

    validation_results = []

    # Validation 1: Check required top-level keys
    print("\n1. Checking required top-level keys...")
    required_keys = ['query_timestamp', 'schemas', 'tables', 'law_columns',
                     'client_columns', 'graph_columns', 'foreign_keys',
                     'indexes', 'rls_policies', 'summary']
    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        print(f"   ❌ Missing required keys: {missing_keys}")
        validation_results.append(False)
    else:
        print(f"   ✅ All {len(required_keys)} required keys present")
        validation_results.append(True)

    # Validation 2: Check schemas list
    print("\n2. Checking schemas...")
    expected_schemas = ['law', 'client', 'graph']
    if data['schemas'] == expected_schemas:
        print(f"   ✅ All expected schemas present: {data['schemas']}")
        validation_results.append(True)
    else:
        print(f"   ❌ Schema mismatch. Expected {expected_schemas}, got {data['schemas']}")
        validation_results.append(False)

    # Validation 3: Verify table counts
    print("\n3. Verifying table counts...")
    tables = data['tables']
    law_tables = [t for t in tables if t['table_schema'] == 'law']
    client_tables = [t for t in tables if t['table_schema'] == 'client']
    graph_tables = [t for t in tables if t['table_schema'] == 'graph']

    print(f"   Law schema: {len(law_tables)} tables")
    print(f"   Client schema: {len(client_tables)} tables")
    print(f"   Graph schema: {len(graph_tables)} tables")
    print(f"   Total: {len(tables)} tables")

    if len(tables) == data['summary']['total_tables']:
        print(f"   ✅ Table count matches summary")
        validation_results.append(True)
    else:
        print(f"   ❌ Table count mismatch")
        validation_results.append(False)

    # Validation 4: Verify column counts
    print("\n4. Verifying column counts...")
    total_columns = (len(data['law_columns']) +
                     len(data['client_columns']) +
                     len(data['graph_columns']))

    print(f"   Law columns: {len(data['law_columns'])}")
    print(f"   Client columns: {len(data['client_columns'])}")
    print(f"   Graph columns: {len(data['graph_columns'])}")
    print(f"   Total: {total_columns}")

    if total_columns == data['summary']['total_columns']:
        print(f"   ✅ Column count matches summary")
        validation_results.append(True)
    else:
        print(f"   ❌ Column count mismatch")
        validation_results.append(False)

    # Validation 5: Check foreign keys
    print("\n5. Checking foreign keys...")
    fk_count = len(data['foreign_keys'])
    print(f"   Total foreign keys: {fk_count}")

    if fk_count == data['summary']['total_foreign_keys']:
        print(f"   ✅ Foreign key count matches summary")
        validation_results.append(True)
    else:
        print(f"   ❌ Foreign key count mismatch")
        validation_results.append(False)

    # Validation 6: Verify essential tables exist
    print("\n6. Verifying essential tables exist...")
    essential_tables = {
        'law': ['documents', 'entities', 'entity_relationships'],
        'client': ['cases', 'clients', 'documents', 'entities'],
        'graph': ['document_registry', 'chunks', 'entities', 'nodes', 'edges', 'communities']
    }

    all_essential_present = True
    for schema, table_list in essential_tables.items():
        schema_tables = [t['table_name'] for t in tables if t['table_schema'] == schema]
        missing = [t for t in table_list if t not in schema_tables]
        if missing:
            print(f"   ❌ Missing essential tables in {schema}: {missing}")
            all_essential_present = False
        else:
            print(f"   ✅ All essential tables present in {schema} schema")

    validation_results.append(all_essential_present)

    # Validation 7: Check for vector columns (pgvector support)
    print("\n7. Checking for vector/embedding columns...")
    vector_columns = []
    for col in data['graph_columns']:
        if col['data_type'] in ['USER-DEFINED', 'vector']:
            vector_columns.append(f"{col['table_name']}.{col['column_name']}")

    print(f"   Found {len(vector_columns)} vector columns:")
    for vec_col in vector_columns:
        print(f"      - graph.{vec_col}")

    if len(vector_columns) > 0:
        print(f"   ✅ pgvector support detected")
        validation_results.append(True)
    else:
        print(f"   ⚠️  No vector columns found (expected for GraphRAG)")
        validation_results.append(False)

    # Validation 8: Check for multi-tenant columns
    print("\n8. Checking for multi-tenant architecture...")
    tenant_columns = []
    for schema_cols in [data['client_columns'], data['graph_columns']]:
        for col in schema_cols:
            if col['column_name'] in ['client_id', 'case_id']:
                tenant_columns.append(f"{col['table_name']}.{col['column_name']}")

    print(f"   Found {len(tenant_columns)} tenant identifier columns")

    if len(tenant_columns) > 0:
        print(f"   ✅ Multi-tenant architecture present")
        validation_results.append(True)
    else:
        print(f"   ⚠️  No tenant columns found")
        validation_results.append(False)

    # Validation 9: Check for JSONB metadata columns
    print("\n9. Checking for JSONB metadata columns...")
    jsonb_columns = []
    for schema_name, schema_cols in [
        ('law', data['law_columns']),
        ('client', data['client_columns']),
        ('graph', data['graph_columns'])
    ]:
        for col in schema_cols:
            if col['data_type'] == 'jsonb':
                jsonb_columns.append(f"{schema_name}.{col['table_name']}.{col['column_name']}")

    print(f"   Found {len(jsonb_columns)} JSONB columns:")
    for jsonb_col in jsonb_columns[:10]:  # Show first 10
        print(f"      - {jsonb_col}")
    if len(jsonb_columns) > 10:
        print(f"      ... and {len(jsonb_columns) - 10} more")

    if len(jsonb_columns) > 0:
        print(f"   ✅ Flexible metadata support with JSONB")
        validation_results.append(True)
    else:
        print(f"   ⚠️  No JSONB columns found")
        validation_results.append(False)

    # Validation 10: Verify RLS policies exist
    print("\n10. Checking Row Level Security policies...")
    rls_count = len(data['rls_policies'])
    print(f"   Total RLS policies: {rls_count}")

    if rls_count == data['summary']['total_rls_policies']:
        print(f"   ✅ RLS policy count matches summary")
        validation_results.append(True)
    else:
        print(f"   ❌ RLS policy count mismatch")
        validation_results.append(False)

    # Final validation summary
    print("\n" + "=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(validation_results)
    total = len(validation_results)
    percentage = (passed / total) * 100

    print(f"\nValidations Passed: {passed}/{total} ({percentage:.1f}%)")

    if passed == total:
        print("\n✅ All validations passed! Schema data is complete and accurate.")
        return True
    else:
        failed = total - passed
        print(f"\n⚠️  {failed} validation(s) failed. Review errors above.")
        return False


if __name__ == '__main__':
    schema_file = '/srv/luris/be/docs/database/schema_data.json'

    success = validate_schema_data(schema_file)

    if success:
        print(f"\n✅ Schema validation successful")
        print(f"   Data file: {schema_file}")
        print(f"   Summary: /srv/luris/be/docs/database/schema_summary.md")
        sys.exit(0)
    else:
        print(f"\n❌ Schema validation failed")
        sys.exit(1)
