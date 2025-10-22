#!/usr/bin/env python3
"""
Batch Upload Script for GraphRAG Synthetic Data to Supabase

This script uploads ~135,000+ records across 9 tables to the Supabase graph schema.
All 122 columns are populated with synthetic data including 2048-dimensional vector embeddings.

Usage:
    cd /srv/luris/be/graphrag-service
    source venv/bin/activate
    python scripts/upload_to_database.py [--test] [--batch-size BATCH_SIZE]

Options:
    --test              Test mode - upload only 10 records per table
    --batch-size SIZE   Batch size for insertions (default: 500)
    --skip-tables       Comma-separated list of tables to skip
"""

import os
import sys
import json
import asyncio
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

# Add src directory to path for imports
service_root = Path(__file__).parent.parent
sys.path.insert(0, str(service_root))

# Import SupabaseClient
from src.clients.supabase_client import SupabaseClient, SupabaseSettings


class DatabaseUploader:
    """Handles batch upload of GraphRAG data to Supabase"""

    # Upload order respecting foreign key constraints
    UPLOAD_ORDER = [
        "document_registry",
        "nodes",
        "communities",
        "edges",
        "node_communities",
        "chunks",
        "enhanced_contextual_chunks",
        "text_units",
        "reports"
    ]

    # File mapping to table names
    FILE_TO_TABLE = {
        "document_registry.json": "document_registry",
        "nodes.json": "nodes",
        "communities.json": "communities",
        "edges.json": "edges",
        "node_communities.json": "node_communities",
        "chunks.json": "chunks",
        "enhanced_contextual_chunks.json": "enhanced_contextual_chunks",
        "text_units.json": "text_units",
        "reports.json": "reports"
    }

    # Vector field mapping for proper formatting
    VECTOR_FIELDS = {
        "nodes": "embedding",
        "chunks": "content_embedding",
        "enhanced_contextual_chunks": "vector",
        "communities": "summary_embedding",
        "reports": "report_embedding"
    }

    def __init__(self, data_dir: str, batch_size: int = 500, test_mode: bool = False):
        """
        Initialize the uploader

        Args:
            data_dir: Directory containing JSON data files
            batch_size: Number of records per batch insert
            test_mode: If True, upload only 10 records per table for testing
        """
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        self.test_mode = test_mode
        self.client: Optional[SupabaseClient] = None

        # Statistics tracking
        self.stats = {
            "total_records": 0,
            "uploaded_records": 0,
            "failed_records": 0,
            "tables_completed": 0,
            "errors": defaultdict(list),
            "start_time": None,
            "end_time": None
        }

        # Per-table statistics
        self.table_stats = {}

        print(f"🚀 Database Uploader Initialized")
        print(f"   Data Directory: {self.data_dir}")
        print(f"   Batch Size: {self.batch_size}")
        print(f"   Test Mode: {'ON (10 records per table)' if self.test_mode else 'OFF'}")
        print()

    async def initialize(self):
        """Initialize database connection"""
        print("🔌 Initializing Supabase connection...")

        try:
            settings = SupabaseSettings(service_name="graphrag-upload-script")
            self.client = SupabaseClient(
                settings=settings,
                service_name="graphrag-upload-script",
                use_service_role=True  # Use admin client for bulk operations
            )
            print("✅ Supabase connection established (service_role client)")
            print()

        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            raise

    def load_data(self, filename: str) -> List[Dict[str, Any]]:
        """Load JSON data from file"""
        filepath = self.data_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        print(f"📂 Loading data from {filename}...")
        start = time.time()

        with open(filepath, 'r') as f:
            data = json.load(f)

        # In test mode, limit to 10 records
        if self.test_mode and len(data) > 10:
            data = data[:10]
            print(f"   ⚠️  Test mode: Limited to 10 records")

        elapsed = time.time() - start
        print(f"   ✅ Loaded {len(data):,} records in {elapsed:.2f}s")

        return data

    def prepare_record(self, record: Dict[str, Any], table: str) -> Dict[str, Any]:
        """
        Prepare a record for insertion by handling special data types

        Args:
            record: The record to prepare
            table: The target table name

        Returns:
            Prepared record with proper formatting
        """
        prepared = record.copy()

        # Remove 'id' field - let PostgreSQL generate UUIDs
        if 'id' in prepared:
            del prepared['id']

        # Handle vector embeddings - convert list to PostgreSQL array format
        if table in self.VECTOR_FIELDS:
            vector_field = self.VECTOR_FIELDS[table]
            if vector_field in prepared and prepared[vector_field]:
                # Vectors should be kept as Python lists - SupabaseClient handles conversion
                # Just ensure they're actually lists
                if not isinstance(prepared[vector_field], list):
                    print(f"   ⚠️  Warning: {vector_field} is not a list, converting...")
                    prepared[vector_field] = list(prepared[vector_field])

        # Handle timestamp fields - ensure ISO format
        timestamp_fields = ['created_at', 'updated_at']
        for field in timestamp_fields:
            if field in prepared and prepared[field]:
                if isinstance(prepared[field], str):
                    # Already a string, ensure it's valid ISO format
                    try:
                        datetime.fromisoformat(prepared[field].replace('Z', '+00:00'))
                    except:
                        # Invalid timestamp, use current time
                        prepared[field] = datetime.utcnow().isoformat()

        # Handle JSONB fields - ensure they're valid JSON
        jsonb_fields = ['metadata']
        for field in jsonb_fields:
            if field in prepared and prepared[field]:
                if isinstance(prepared[field], str):
                    try:
                        prepared[field] = json.loads(prepared[field])
                    except:
                        # Invalid JSON, set to empty dict
                        prepared[field] = {}

        # Handle UUID fields - some tables use TEXT, others use UUID
        # SupabaseClient handles this automatically, but we can validate
        uuid_fields = ['client_id', 'case_id']
        for field in uuid_fields:
            if field in prepared and prepared[field]:
                # Ensure it's a string (SupabaseClient expects strings for UUIDs)
                if not isinstance(prepared[field], str):
                    prepared[field] = str(prepared[field])

        return prepared

    async def upload_batch_via_sql(
        self,
        table: str,
        records: List[Dict[str, Any]],
        batch_num: int,
        total_batches: int
    ) -> tuple[int, int]:
        """
        Upload a batch via direct SQL using psycopg2

        This bypasses PostgREST cache issues by using direct PostgreSQL connection
        """
        try:
            import psycopg2
            from psycopg2.extras import execute_values, Json

            # Get database URL from environment
            db_url = os.getenv("DATABASE_URL") or self._construct_db_url()

            # Prepare all records in batch
            prepared_records = [self.prepare_record(r, table) for r in records]

            if not prepared_records:
                return 0, len(records)

            # Connect to database
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()

            # Get columns from first record
            columns = list(prepared_records[0].keys())
            column_list = ', '.join(f'"{col}"' for col in columns)
            placeholders = ', '.join(['%s'] * len(columns))

            # Convert records to tuples for bulk insert
            data_tuples = []
            for record in prepared_records:
                row = []
                for col in columns:
                    val = record.get(col)
                    # Handle different data types
                    if val is None:
                        row.append(None)
                    elif isinstance(val, dict):
                        # JSONB type - use psycopg2 Json adapter
                        row.append(Json(val))
                    elif isinstance(val, list):
                        if len(val) > 0 and isinstance(val[0], (int, float)):
                            # Vector type - convert to PostgreSQL vector literal string
                            row.append(f"[{','.join(str(v) for v in val)}]")
                        elif len(val) > 0 and isinstance(val[0], str):
                            # TEXT[] array
                            row.append(val)
                        else:
                            # Empty list or other list type
                            row.append(val)
                    else:
                        # String, int, float, etc.
                        row.append(val)
                data_tuples.append(tuple(row))

            # Execute batch insert
            sql = f'INSERT INTO graph.{table} ({column_list}) VALUES ({placeholders})'
            cur.executemany(sql, data_tuples)
            conn.commit()

            successful = len(data_tuples)

            cur.close()
            conn.close()

            print(f"   ✅ Batch {batch_num}/{total_batches}: {successful}/{len(records)} records uploaded")
            return successful, 0

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Batch {batch_num}/{total_batches} failed: {error_msg[:200]}")
            self.stats["errors"][table].append({
                "batch": batch_num,
                "error": error_msg,
                "record_count": len(records)
            })
            return 0, len(records)

    def _construct_db_url(self) -> str:
        """Construct PostgreSQL connection URL from Supabase credentials"""
        url = os.getenv("SUPABASE_URL", "")
        # Extract project ID from Supabase URL
        # Format: https://PROJECT_ID.supabase.co
        project_id = url.replace("https://", "").replace(".supabase.co", "")

        # Supabase direct PostgreSQL connection
        # postgres://postgres:[YOUR-PASSWORD]@db.PROJECT_ID.supabase.co:5432/postgres
        password = os.getenv("SUPABASE_DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")

        if not password:
            raise ValueError("DATABASE_URL or SUPABASE_DB_PASSWORD required for direct SQL uploads")

        return f"postgres://postgres.{project_id}:{password}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

    async def upload_batch(
        self,
        table: str,
        records: List[Dict[str, Any]],
        batch_num: int,
        total_batches: int
    ) -> tuple[int, int]:
        """
        Upload a batch of records to a table

        Args:
            table: Target table name
            records: List of records to upload
            batch_num: Current batch number (1-indexed)
            total_batches: Total number of batches

        Returns:
            Tuple of (successful_count, failed_count)
        """
        # Try SQL-based upload if PostgREST cache issues persist
        if os.getenv("USE_DIRECT_SQL", "false").lower() == "true":
            return await self.upload_batch_via_sql(table, records, batch_num, total_batches)

        try:
            # Prepare all records in batch
            prepared_records = [self.prepare_record(r, table) for r in records]

            # Insert batch using admin operation
            result = await self.client.insert(
                f"graph.{table}",
                prepared_records,
                admin_operation=True
            )

            successful = len(result) if result else 0
            failed = len(records) - successful

            print(f"   ✅ Batch {batch_num}/{total_batches}: {successful}/{len(records)} records uploaded")

            return successful, failed

        except Exception as e:
            error_msg = str(e)
            # If it's a schema cache error, suggest using direct SQL
            if "schema cache" in error_msg.lower() or "pgrst204" in error_msg.lower():
                print(f"   ⚠️  Schema cache error detected - retry with USE_DIRECT_SQL=true")

            print(f"   ❌ Batch {batch_num}/{total_batches} failed: {error_msg[:200]}")
            self.stats["errors"][table].append({
                "batch": batch_num,
                "error": error_msg,
                "record_count": len(records)
            })
            return 0, len(records)

    async def upload_table(self, table: str, skip_if_exists: bool = False) -> Dict[str, Any]:
        """
        Upload all data for a specific table

        Args:
            table: Table name to upload
            skip_if_exists: If True, skip upload if table already has data

        Returns:
            Dictionary with upload statistics for this table
        """
        print(f"\n{'='*80}")
        print(f"📊 Uploading to graph.{table}")
        print(f"{'='*80}")

        start_time = time.time()

        # Check if table already has data
        if skip_if_exists:
            try:
                existing = await self.client.get(
                    f"graph.{table}",
                    limit=1,
                    admin_operation=True
                )
                if existing and len(existing) > 0:
                    print(f"⏭️  Table graph.{table} already has data, skipping...")
                    return {
                        "table": table,
                        "skipped": True,
                        "existing_records": len(existing)
                    }
            except Exception as e:
                print(f"⚠️  Warning: Could not check existing data: {e}")

        # Find and load data file
        filename = None
        for file, tbl in self.FILE_TO_TABLE.items():
            if tbl == table:
                filename = file
                break

        if not filename:
            print(f"❌ No data file found for table {table}")
            return {
                "table": table,
                "error": "No data file found",
                "records_uploaded": 0,
                "records_failed": 0
            }

        # Load data
        try:
            records = self.load_data(filename)
        except Exception as e:
            print(f"❌ Failed to load data: {e}")
            return {
                "table": table,
                "error": f"Load failed: {e}",
                "records_uploaded": 0,
                "records_failed": 0
            }

        if not records:
            print(f"⚠️  No records to upload for {table}")
            return {
                "table": table,
                "records_uploaded": 0,
                "records_failed": 0
            }

        # Upload in batches
        total_records = len(records)
        total_batches = (total_records + self.batch_size - 1) // self.batch_size

        print(f"📦 Total Records: {total_records:,}")
        print(f"📦 Batch Size: {self.batch_size}")
        print(f"📦 Total Batches: {total_batches}")
        print()

        successful = 0
        failed = 0

        for i in range(0, total_records, self.batch_size):
            batch = records[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1

            batch_success, batch_failed = await self.upload_batch(
                table, batch, batch_num, total_batches
            )

            successful += batch_success
            failed += batch_failed

            # Small delay between batches to avoid overwhelming the database
            if batch_num < total_batches:
                await asyncio.sleep(0.1)

        elapsed = time.time() - start_time

        print()
        print(f"✅ Table upload completed in {elapsed:.2f}s")
        print(f"   Success: {successful:,}/{total_records:,} records")
        print(f"   Failed: {failed:,}/{total_records:,} records")
        print(f"   Success Rate: {(successful/total_records*100):.1f}%")

        table_result = {
            "table": table,
            "total_records": total_records,
            "records_uploaded": successful,
            "records_failed": failed,
            "elapsed_seconds": elapsed,
            "success_rate": successful / total_records if total_records > 0 else 0
        }

        self.table_stats[table] = table_result
        self.stats["total_records"] += total_records
        self.stats["uploaded_records"] += successful
        self.stats["failed_records"] += failed
        self.stats["tables_completed"] += 1

        return table_result

    async def verify_upload(self) -> Dict[str, Any]:
        """Verify the upload by counting records in each table"""
        print(f"\n{'='*80}")
        print(f"🔍 VERIFYING DATABASE UPLOAD")
        print(f"{'='*80}\n")

        verification_results = {}

        for table in self.UPLOAD_ORDER:
            try:
                # Get row count using limit and count
                result = await self.client.get(
                    f"graph.{table}",
                    limit=1,
                    admin_operation=True
                )

                # For accurate count, we need to use a count query
                # This is a simplified version - in production, use RPC or raw SQL
                count_result = await self.client.get(
                    f"graph.{table}",
                    select="*",
                    limit=100000,  # Large limit to get all records
                    admin_operation=True
                )

                row_count = len(count_result) if count_result else 0
                expected = self.table_stats.get(table, {}).get("total_records", 0)

                status = "✅" if row_count == expected else "⚠️"
                print(f"{status} graph.{table}: {row_count:,} rows (expected: {expected:,})")

                verification_results[table] = {
                    "actual_count": row_count,
                    "expected_count": expected,
                    "match": row_count == expected
                }

            except Exception as e:
                print(f"❌ graph.{table}: Verification failed - {e}")
                verification_results[table] = {
                    "actual_count": 0,
                    "expected_count": 0,
                    "match": False,
                    "error": str(e)
                }

        return verification_results

    async def run(self, skip_tables: Optional[List[str]] = None, skip_if_exists: bool = False):
        """
        Main execution method

        Args:
            skip_tables: List of table names to skip
            skip_if_exists: Skip tables that already have data
        """
        self.stats["start_time"] = time.time()
        skip_tables = skip_tables or []

        print(f"\n{'='*80}")
        print(f"🚀 STARTING BATCH UPLOAD TO SUPABASE")
        print(f"{'='*80}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Mode: {'TEST (10 records per table)' if self.test_mode else 'FULL UPLOAD'}")
        if skip_tables:
            print(f"Skipping tables: {', '.join(skip_tables)}")
        print()

        # Initialize connection
        await self.initialize()

        # Upload each table in order
        for table in self.UPLOAD_ORDER:
            if table in skip_tables:
                print(f"⏭️  Skipping {table} (user requested)")
                continue

            try:
                await self.upload_table(table, skip_if_exists=skip_if_exists)
            except Exception as e:
                print(f"❌ Critical error uploading {table}: {e}")
                self.stats["errors"][table].append({
                    "error": f"Critical: {e}",
                    "fatal": True
                })

        # Verify upload
        verification = await self.verify_upload()

        # Final statistics
        self.stats["end_time"] = time.time()
        self.print_final_report(verification)

    def print_final_report(self, verification: Dict[str, Any]):
        """Print final upload report"""
        total_time = self.stats["end_time"] - self.stats["start_time"]

        print(f"\n{'='*80}")
        print(f"📊 FINAL UPLOAD REPORT")
        print(f"{'='*80}\n")

        print(f"⏱️  Total Execution Time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
        print(f"📦 Total Records Processed: {self.stats['total_records']:,}")
        print(f"✅ Successfully Uploaded: {self.stats['uploaded_records']:,}")
        print(f"❌ Failed Uploads: {self.stats['failed_records']:,}")
        print(f"📋 Tables Completed: {self.stats['tables_completed']}/{len(self.UPLOAD_ORDER)}")

        overall_success_rate = (
            self.stats['uploaded_records'] / self.stats['total_records'] * 100
            if self.stats['total_records'] > 0 else 0
        )
        print(f"📈 Overall Success Rate: {overall_success_rate:.1f}%")

        # Per-table breakdown
        print(f"\n{'='*80}")
        print(f"📊 PER-TABLE STATISTICS")
        print(f"{'='*80}\n")

        for table in self.UPLOAD_ORDER:
            if table in self.table_stats:
                stats = self.table_stats[table]
                verify = verification.get(table, {})

                status = "✅" if verify.get("match", False) else "⚠️"
                print(f"{status} {table}:")
                print(f"   Uploaded: {stats['records_uploaded']:,}/{stats['total_records']:,}")
                print(f"   Verified: {verify.get('actual_count', 0):,}")
                print(f"   Time: {stats['elapsed_seconds']:.2f}s")
                print(f"   Rate: {stats['success_rate']*100:.1f}%")
                print()

        # Error summary
        if self.stats['errors']:
            print(f"\n{'='*80}")
            print(f"❌ ERROR SUMMARY")
            print(f"{'='*80}\n")

            for table, errors in self.stats['errors'].items():
                if errors:
                    print(f"Table: {table}")
                    for err in errors[:5]:  # Show first 5 errors
                        print(f"  - {err.get('error', 'Unknown error')[:200]}")
                    if len(errors) > 5:
                        print(f"  ... and {len(errors) - 5} more errors")
                    print()

        print(f"{'='*80}")
        print(f"✅ Upload Complete!")
        print(f"{'='*80}\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Upload GraphRAG synthetic data to Supabase database"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode - upload only 10 records per table"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for insertions (default: 500)"
    )
    parser.add_argument(
        "--skip-tables",
        type=str,
        help="Comma-separated list of tables to skip"
    )
    parser.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Skip tables that already have data"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="/srv/luris/be/graphrag-service/data",
        help="Directory containing JSON data files"
    )

    args = parser.parse_args()

    skip_tables = []
    if args.skip_tables:
        skip_tables = [t.strip() for t in args.skip_tables.split(',')]

    # Create uploader
    uploader = DatabaseUploader(
        data_dir=args.data_dir,
        batch_size=args.batch_size,
        test_mode=args.test
    )

    try:
        await uploader.run(
            skip_tables=skip_tables,
            skip_if_exists=args.skip_if_exists
        )
    except KeyboardInterrupt:
        print("\n⚠️  Upload interrupted by user")
        uploader.print_final_report({})
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
