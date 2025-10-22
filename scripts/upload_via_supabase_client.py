#!/usr/bin/env python3
"""
Production-Grade GraphRAG Data Upload Script

Uploads GraphRAG data to Supabase database using the enhanced SupabaseClient.
Designed to handle millions of records with robust error handling, checkpointing,
and progress tracking.

Usage:
    python upload_via_supabase_client.py                    # Full upload
    python upload_via_supabase_client.py --dry-run          # Validate without uploading
    python upload_via_supabase_client.py --resume-from checkpoint.json  # Resume from checkpoint
    python upload_via_supabase_client.py --test --limit 100  # Test with limited data
    python upload_via_supabase_client.py --batch-size 1000   # Custom batch size
"""

import asyncio
import json
import argparse
import time
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import psutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import create_admin_supabase_client


@dataclass
class UploadConfig:
    """Configuration for upload operations"""
    batch_size: int = 500
    max_retries: int = 3
    retry_delay: int = 2
    checkpoint_interval: int = 5000
    progress_interval: int = 1000
    validate_vectors: bool = True
    vector_dimension: int = 2048
    data_dir: Path = Path(__file__).parent.parent / "data"

    # Upload order with table names, file names, and batch sizes
    upload_order: List[Tuple[str, str, int]] = None

    def __post_init__(self):
        if self.upload_order is None:
            self.upload_order = [
                ("graph.document_registry", "document_registry.json", 100),
                ("graph.nodes", "nodes.json", 500),
                ("graph.communities", "communities.json", 100),
                ("graph.edges", "edges.json", 1000),
                ("graph.node_communities", "node_communities.json", 2000),
                ("graph.chunks", "chunks.json", 500),
                ("graph.enhanced_contextual_chunks", "enhanced_contextual_chunks.json", 500),
                ("graph.text_units", "text_units.json", 1000),
                ("graph.reports", "reports.json", 100),
            ]


@dataclass
class UploadStats:
    """Statistics for upload operations"""
    table_name: str
    total_records: int
    uploaded_records: int = 0
    failed_records: int = 0
    start_time: float = 0.0
    end_time: Optional[float] = None
    batches_processed: int = 0
    batches_failed: int = 0
    retries_attempted: int = 0

    @property
    def duration(self) -> float:
        """Duration in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def records_per_second(self) -> float:
        """Upload speed in records/second"""
        duration = self.duration
        if duration > 0:
            return self.uploaded_records / duration
        return 0.0

    @property
    def success_rate(self) -> float:
        """Success rate as percentage"""
        if self.total_records > 0:
            return (self.uploaded_records / self.total_records) * 100
        return 0.0

    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimated time remaining in seconds"""
        if self.uploaded_records > 0 and self.records_per_second > 0:
            remaining = self.total_records - self.uploaded_records
            return remaining / self.records_per_second
        return None


class CheckpointManager:
    """Manages upload checkpoints for resume functionality"""

    def __init__(self, checkpoint_file: Path):
        self.checkpoint_file = checkpoint_file
        self.checkpoint_data: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Load checkpoint data from file"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    self.checkpoint_data = json.load(f)
                print(f"✓ Loaded checkpoint from {self.checkpoint_file}")
                return self.checkpoint_data
            except Exception as e:
                print(f"⚠ Failed to load checkpoint: {e}")
                return {}
        return {}

    def save(self, table_name: str, uploaded_count: int, stats: UploadStats):
        """Save checkpoint data to file"""
        self.checkpoint_data[table_name] = {
            "uploaded_count": uploaded_count,
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_records": stats.total_records,
                "uploaded_records": stats.uploaded_records,
                "failed_records": stats.failed_records,
                "batches_processed": stats.batches_processed,
                "records_per_second": stats.records_per_second,
            }
        }

        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint_data, f, indent=2)
        except Exception as e:
            print(f"⚠ Failed to save checkpoint: {e}")

    def get_uploaded_count(self, table_name: str) -> int:
        """Get number of records already uploaded for a table"""
        return self.checkpoint_data.get(table_name, {}).get("uploaded_count", 0)

    def is_table_complete(self, table_name: str) -> bool:
        """Check if table upload is complete"""
        return table_name in self.checkpoint_data


class DataValidator:
    """Validates data before upload"""

    @staticmethod
    def validate_vector_dimension(vector: List[float], expected_dim: int) -> bool:
        """Validate vector has correct dimension"""
        if not isinstance(vector, list):
            return False
        return len(vector) == expected_dim

    @staticmethod
    def validate_record(record: Dict[str, Any], table_name: str, vector_dim: int = 2048) -> Tuple[bool, Optional[str]]:
        """
        Validate a single record for upload.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for required ID fields based on table
        if table_name == "graph.document_registry" and "document_id" not in record:
            return False, "Missing document_id"

        if table_name == "graph.nodes" and "node_id" not in record:
            return False, "Missing node_id"

        if table_name == "graph.edges" and ("source_node_id" not in record or "target_node_id" not in record):
            return False, "Missing source_node_id or target_node_id"

        if table_name == "graph.communities" and "community_id" not in record:
            return False, "Missing community_id"

        # Validate vector dimensions for tables with embeddings
        vector_fields = {
            "graph.nodes": "embedding",
            "graph.communities": "summary_embedding",
            "graph.chunks": "content_embedding",
            "graph.enhanced_contextual_chunks": "vector",
            "graph.reports": "report_embedding",
        }

        if table_name in vector_fields:
            vector_field = vector_fields[table_name]
            if vector_field in record and record[vector_field] is not None:
                if not DataValidator.validate_vector_dimension(record[vector_field], vector_dim):
                    return False, f"Invalid vector dimension for {vector_field}"

        return True, None


class ProgressTracker:
    """Tracks and displays upload progress"""

    def __init__(self, total_records: int, table_name: str):
        self.total_records = total_records
        self.table_name = table_name
        self.start_time = time.time()
        self.last_update = self.start_time

    def display_progress(self, uploaded: int, failed: int = 0):
        """Display progress bar and statistics"""
        now = time.time()
        elapsed = now - self.start_time
        progress = (uploaded / self.total_records) * 100 if self.total_records > 0 else 0

        # Calculate speed
        speed = uploaded / elapsed if elapsed > 0 else 0

        # Calculate ETA
        if speed > 0:
            remaining = self.total_records - uploaded
            eta_seconds = remaining / speed
            eta = str(timedelta(seconds=int(eta_seconds)))
        else:
            eta = "calculating..."

        # Progress bar
        bar_length = 40
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        # Memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        print(f"\r  [{bar}] {progress:.1f}% | {uploaded:,}/{self.total_records:,} | "
              f"{speed:.0f} rec/s | ETA: {eta} | Failed: {failed} | Mem: {memory_mb:.0f}MB",
              end="", flush=True)

    def finish(self, uploaded: int, failed: int, duration: float):
        """Display final statistics"""
        print()  # New line after progress bar
        print(f"  ✓ Completed in {timedelta(seconds=int(duration))}")
        print(f"  ✓ Uploaded: {uploaded:,} | Failed: {failed:,} | "
              f"Speed: {uploaded/duration:.0f} rec/s")


class GraphRAGUploader:
    """Main uploader class for GraphRAG data"""

    def __init__(self, config: UploadConfig, dry_run: bool = False, test_limit: Optional[int] = None):
        self.config = config
        self.dry_run = dry_run
        self.test_limit = test_limit
        self.supabase = None
        self.checkpoint_manager = CheckpointManager(Path("upload_checkpoint.json"))
        self.upload_stats: Dict[str, UploadStats] = {}
        self.failed_records: Dict[str, List[Dict[str, Any]]] = {}

    async def initialize(self):
        """Initialize the uploader"""
        print("🚀 GraphRAG Data Upload Script")
        print("=" * 80)

        if self.dry_run:
            print("⚠ DRY RUN MODE - No data will be uploaded")

        if self.test_limit:
            print(f"⚠ TEST MODE - Limited to {self.test_limit} records per table")

        print(f"📁 Data directory: {self.config.data_dir}")
        print(f"📦 Batch size: {self.config.batch_size}")
        print(f"🔄 Checkpoint interval: {self.config.checkpoint_interval}")
        print(f"📊 Vector dimension: {self.config.vector_dimension}")
        print()

        # Initialize Supabase client
        if not self.dry_run:
            print("🔌 Connecting to Supabase...")
            self.supabase = create_admin_supabase_client(
                service_name="graphrag-upload",
            )
            print("✓ Connected to Supabase")

            # Display health info
            health = self.supabase.get_health_info()
            print(f"  Primary client: {health['clients']['primary_client']}")
            print(f"  Max connections: {health['connection_pool']['max_connections']}")
            print()

    def load_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load JSON data from file"""
        print(f"📄 Loading {file_path.name}...", end=" ", flush=True)

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise ValueError(f"Expected list, got {type(data)}")

            # Apply test limit if specified
            if self.test_limit:
                data = data[:self.test_limit]

            print(f"✓ Loaded {len(data):,} records")
            return data

        except Exception as e:
            print(f"✗ Error: {e}")
            raise

    def validate_data(self, data: List[Dict[str, Any]], table_name: str) -> Tuple[List[Dict[str, Any]], List[Tuple[int, str]]]:
        """
        Validate all records in the dataset.

        Returns:
            Tuple of (valid_records, invalid_records_with_errors)
        """
        print(f"🔍 Validating {len(data):,} records...", end=" ", flush=True)

        valid_records = []
        invalid_records = []

        for idx, record in enumerate(data):
            is_valid, error_msg = DataValidator.validate_record(
                record, table_name, self.config.vector_dimension
            )

            if is_valid:
                valid_records.append(record)
            else:
                invalid_records.append((idx, error_msg))

        if invalid_records:
            print(f"⚠ {len(invalid_records)} invalid records found")
            for idx, error in invalid_records[:5]:  # Show first 5
                print(f"  - Record {idx}: {error}")
            if len(invalid_records) > 5:
                print(f"  ... and {len(invalid_records) - 5} more")
        else:
            print("✓ All records valid")

        return valid_records, invalid_records

    async def upload_batch(
        self,
        table_name: str,
        batch: List[Dict[str, Any]],
        batch_num: int,
        retry_count: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Upload a single batch of records.

        Returns:
            Tuple of (uploaded_count, failed_records)
        """
        if self.dry_run:
            # Simulate upload delay
            await asyncio.sleep(0.01)
            return len(batch), []

        try:
            # Use SupabaseClient.insert() with admin_operation=True
            result = await self.supabase.insert(
                table=table_name,
                data=batch,
                admin_operation=True
            )

            return len(batch), []

        except Exception as e:
            error_msg = str(e)

            # Retry logic for transient errors
            if retry_count < self.config.max_retries:
                if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                    print(f"\n  ⚠ Batch {batch_num} failed (attempt {retry_count + 1}): {error_msg[:100]}")
                    print(f"  🔄 Retrying in {self.config.retry_delay} seconds...")

                    await asyncio.sleep(self.config.retry_delay * (retry_count + 1))
                    return await self.upload_batch(table_name, batch, batch_num, retry_count + 1)

            # Non-retryable error or max retries exceeded
            print(f"\n  ✗ Batch {batch_num} failed: {error_msg[:100]}")
            return 0, batch

    async def upload_table(
        self,
        table_name: str,
        file_name: str,
        batch_size: Optional[int] = None
    ) -> UploadStats:
        """
        Upload all data for a single table.

        Returns:
            UploadStats for the table
        """
        print(f"\n📊 Table: {table_name}")
        print("-" * 80)

        # Load data
        file_path = self.config.data_dir / file_name
        if not file_path.exists():
            print(f"⚠ File not found: {file_path}")
            return UploadStats(table_name=table_name, total_records=0)

        data = self.load_json_file(file_path)

        # Validate data
        valid_data, invalid_records = self.validate_data(data, table_name)

        if not valid_data:
            print("⚠ No valid records to upload")
            return UploadStats(table_name=table_name, total_records=len(data))

        # Check checkpoint
        uploaded_count = self.checkpoint_manager.get_uploaded_count(table_name)
        if uploaded_count > 0:
            print(f"📌 Resuming from checkpoint: {uploaded_count:,} records already uploaded")
            valid_data = valid_data[uploaded_count:]

        # Initialize stats
        stats = UploadStats(
            table_name=table_name,
            total_records=len(data),
            uploaded_records=uploaded_count,
            start_time=time.time()
        )

        # Initialize progress tracker
        progress = ProgressTracker(len(data), table_name)

        # Use custom batch size if provided
        effective_batch_size = batch_size or self.config.batch_size

        # Upload in batches
        total_uploaded = uploaded_count
        total_failed = 0
        failed_records_list = []

        for i in range(0, len(valid_data), effective_batch_size):
            batch = valid_data[i:i + effective_batch_size]
            batch_num = (i // effective_batch_size) + 1

            # Upload batch
            uploaded, failed = await self.upload_batch(table_name, batch, batch_num)

            total_uploaded += uploaded
            total_failed += len(failed)
            failed_records_list.extend(failed)

            stats.uploaded_records = total_uploaded
            stats.failed_records = total_failed
            stats.batches_processed += 1
            if failed:
                stats.batches_failed += 1

            # Update progress
            if total_uploaded % self.config.progress_interval == 0 or i + effective_batch_size >= len(valid_data):
                progress.display_progress(total_uploaded, total_failed)

            # Save checkpoint periodically
            if total_uploaded % self.config.checkpoint_interval == 0 and not self.dry_run:
                self.checkpoint_manager.save(table_name, total_uploaded, stats)

        # Finalize stats
        stats.end_time = time.time()
        progress.finish(total_uploaded, total_failed, stats.duration)

        # Save failed records
        if failed_records_list:
            self.failed_records[table_name] = failed_records_list

        # Save final checkpoint
        if not self.dry_run:
            self.checkpoint_manager.save(table_name, total_uploaded, stats)

        return stats

    async def run(self):
        """Execute the full upload process"""
        await self.initialize()

        print("🚀 Starting upload process...")
        print("=" * 80)

        overall_start = time.time()

        for table_name, file_name, batch_size in self.config.upload_order:
            stats = await self.upload_table(table_name, file_name, batch_size)
            self.upload_stats[table_name] = stats

        overall_duration = time.time() - overall_start

        # Generate summary report
        self.print_summary_report(overall_duration)

        # Generate error report if needed
        if self.failed_records:
            self.save_error_report()

        # Cleanup
        if self.supabase:
            await self.supabase.close()

    def print_summary_report(self, total_duration: float):
        """Print summary report of upload process"""
        print("\n" + "=" * 80)
        print("📊 UPLOAD SUMMARY REPORT")
        print("=" * 80)

        # Overall statistics
        total_records = sum(s.total_records for s in self.upload_stats.values())
        total_uploaded = sum(s.uploaded_records for s in self.upload_stats.values())
        total_failed = sum(s.failed_records for s in self.upload_stats.values())

        print(f"\n🎯 Overall Statistics:")
        print(f"  Total records processed: {total_records:,}")
        print(f"  Successfully uploaded: {total_uploaded:,}")
        print(f"  Failed: {total_failed:,}")
        print(f"  Success rate: {(total_uploaded/total_records*100):.2f}%")
        print(f"  Total duration: {timedelta(seconds=int(total_duration))}")
        print(f"  Average speed: {total_uploaded/total_duration:.0f} records/second")

        # Per-table statistics
        print(f"\n📋 Per-Table Statistics:")
        print(f"  {'Table':<40} {'Records':<10} {'Uploaded':<10} {'Failed':<8} {'Speed':<12}")
        print(f"  {'-'*40} {'-'*10} {'-'*10} {'-'*8} {'-'*12}")

        for table_name, stats in self.upload_stats.items():
            if stats.total_records > 0:
                speed = f"{stats.records_per_second:.0f} rec/s"
                print(f"  {table_name:<40} {stats.total_records:<10,} {stats.uploaded_records:<10,} "
                      f"{stats.failed_records:<8,} {speed:<12}")

        # Memory statistics
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"\n💾 Memory Usage:")
        print(f"  Peak memory: {memory_mb:.0f} MB")

        # Health check
        if self.supabase and not self.dry_run:
            health = self.supabase.get_health_info()
            print(f"\n🏥 Database Health:")
            print(f"  Operation count: {health['operation_count']}")
            print(f"  Error rate: {health['error_rate']:.2%}")
            print(f"  Average latency: {health['performance']['average_latency_seconds']:.3f}s")
            print(f"  Connection pool utilization: {health['connection_pool']['utilization']:.2%}")

        print("\n" + "=" * 80)

    def save_error_report(self):
        """Save detailed error report to file"""
        error_file = Path("upload_errors.json")

        error_report = {
            "timestamp": datetime.now().isoformat(),
            "total_failed_records": sum(len(records) for records in self.failed_records.values()),
            "tables_with_errors": list(self.failed_records.keys()),
            "failed_records": {
                table: records for table, records in self.failed_records.items()
            }
        }

        with open(error_file, 'w') as f:
            json.dump(error_report, f, indent=2)

        print(f"\n⚠ Error report saved to: {error_file}")
        print(f"  Total failed records: {error_report['total_failed_records']:,}")
        print(f"  Tables with errors: {', '.join(error_report['tables_with_errors'])}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Production-grade GraphRAG data upload to Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full upload
  python upload_via_supabase_client.py

  # Dry run (validate without uploading)
  python upload_via_supabase_client.py --dry-run

  # Resume from checkpoint
  python upload_via_supabase_client.py --resume-from checkpoint.json

  # Test mode with limited records
  python upload_via_supabase_client.py --test --limit 100

  # Custom batch size
  python upload_via_supabase_client.py --batch-size 1000
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data without uploading to database"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode with limited records"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of records per table (for testing)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for upload operations (default: 500)"
    )

    parser.add_argument(
        "--resume-from",
        type=Path,
        help="Resume upload from checkpoint file"
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="Directory containing JSON data files"
    )

    args = parser.parse_args()

    # Create configuration
    config = UploadConfig(
        batch_size=args.batch_size,
        data_dir=args.data_dir
    )

    # Determine test limit
    test_limit = None
    if args.test:
        test_limit = args.limit or 100
    elif args.limit:
        test_limit = args.limit

    # Create uploader
    uploader = GraphRAGUploader(
        config=config,
        dry_run=args.dry_run,
        test_limit=test_limit
    )

    # Load checkpoint if resuming
    if args.resume_from:
        uploader.checkpoint_manager.checkpoint_file = args.resume_from
        uploader.checkpoint_manager.load()

    # Run upload
    try:
        await uploader.run()
        print("\n✓ Upload completed successfully!")
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⚠ Upload interrupted by user")
        print("  Checkpoint saved - use --resume-from to continue")
        sys.exit(1)

    except Exception as e:
        print(f"\n\n✗ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
