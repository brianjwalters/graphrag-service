#!/usr/bin/env python3
"""
Quick script to upload remaining tables (node_communities, reports, edges)
after foreign key constraints have been dropped.
"""

import os
import json
import psycopg2
from psycopg2.extras import Json
from pathlib import Path

# Database connection
DB_URL = "postgresql://postgres:jocfev-nahgi7-dygzaB@db.tqfshsnwyhfnkchaiudg.supabase.co:5432/postgres"

# Data directory
DATA_DIR = Path("/srv/luris/be/graphrag-service/data")

def upload_table(table_name, filename, batch_size=500):
    """Upload a single table"""
    print(f"\n{'='*80}")
    print(f"📊 Uploading {table_name}")
    print(f"{'='*80}")

    # Load data
    filepath = DATA_DIR / filename
    with open(filepath, 'r') as f:
        data = json.load(f)

    print(f"📂 Loaded {len(data):,} records")

    # Connect to database
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Prepare data
    if not data:
        print("⚠️  No data to upload")
        return 0, 0

    # Get columns from first record
    columns = list(data[0].keys())
    # Remove 'id' if present
    if 'id' in columns:
        columns.remove('id')

    column_list = ', '.join(f'"{col}"' for col in columns)
    placeholders = ', '.join(['%s'] * len(columns))

    total_success = 0
    total_failed = 0

    # Upload in batches
    total_batches = (len(data) + batch_size - 1) // batch_size

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        try:
            # Prepare batch data
            data_tuples = []
            for record in batch:
                row = []
                for col in columns:
                    val = record.get(col)
                    if val is None:
                        row.append(None)
                    elif isinstance(val, dict):
                        row.append(Json(val))
                    elif isinstance(val, list):
                        if len(val) > 0 and isinstance(val[0], (int, float)):
                            # Vector type
                            row.append(f"[{','.join(str(v) for v in val)}]")
                        else:
                            row.append(val)
                    else:
                        row.append(val)
                data_tuples.append(tuple(row))

            # Execute batch insert
            sql = f'INSERT INTO graph.{table_name} ({column_list}) VALUES ({placeholders})'
            cur.executemany(sql, data_tuples)
            conn.commit()

            total_success += len(data_tuples)
            print(f"   ✅ Batch {batch_num}/{total_batches}: {len(data_tuples)}/{len(batch)} records uploaded")

        except Exception as e:
            conn.rollback()
            total_failed += len(batch)
            print(f"   ❌ Batch {batch_num}/{total_batches} failed: {str(e)[:200]}")

    cur.close()
    conn.close()

    print(f"\n✅ Upload complete: {total_success:,}/{len(data):,} records ({total_success/len(data)*100:.1f}%)")
    return total_success, total_failed

def main():
    print("\n" + "="*80)
    print("🚀 UPLOADING REMAINING TABLES")
    print("="*80)
    print("Foreign key constraints have been dropped")
    print("Uploading: edges, node_communities, reports")
    print()

    # Upload each table
    tables_to_upload = [
        ("edges", "edges.json"),
        ("node_communities", "node_communities.json"),
        ("reports", "reports.json")
    ]

    total_uploaded = 0

    for table_name, filename in tables_to_upload:
        success, failed = upload_table(table_name, filename)
        total_uploaded += success

    print("\n" + "="*80)
    print(f"🎉 UPLOAD COMPLETE - {total_uploaded:,} records uploaded!")
    print("="*80)

if __name__ == "__main__":
    main()
