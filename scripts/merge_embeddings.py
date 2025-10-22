#!/usr/bin/env python3
"""
Merge Embeddings into Data Files

This script merges the separately generated 2048-dimensional embeddings
into their respective data files, creating complete records ready for
database insertion.

Embeddings to merge:
- nodes.json + embeddings_nodes.json → nodes.embedding
- chunks.json + embeddings_chunks.json → chunks.content_embedding
- enhanced_contextual_chunks.json + embeddings_enhanced_chunks.json → enhanced_contextual_chunks.vector
- communities.json + embeddings_communities.json → communities.summary_embedding
- reports.json + embeddings_reports.json → reports.report_embedding
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Data directory
DATA_DIR = Path("/srv/luris/be/graphrag-service/data")

def load_json_file(filepath: Path) -> Any:
    """Load JSON file with error handling."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return None

def save_json_file(filepath: Path, data: Any) -> bool:
    """Save JSON file with error handling."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving {filepath}: {e}")
        return False

def merge_embeddings(
    data_file: str,
    embeddings_file: str,
    embedding_field: str,
    description: str
) -> bool:
    """
    Merge embeddings into data file.

    Args:
        data_file: Name of the data file (e.g., 'nodes.json')
        embeddings_file: Name of the embeddings file (e.g., 'embeddings_nodes.json')
        embedding_field: Field name to populate (e.g., 'embedding')
        description: Description for logging

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{'='*70}")
    print(f"Merging: {description}")
    print(f"{'='*70}")

    # Load data file
    data_path = DATA_DIR / data_file
    print(f"📂 Loading data file: {data_path}")
    data = load_json_file(data_path)
    if data is None:
        return False
    print(f"✓ Loaded {len(data)} records")

    # Load embeddings file
    embeddings_path = DATA_DIR / embeddings_file
    print(f"📂 Loading embeddings file: {embeddings_path}")
    embeddings = load_json_file(embeddings_path)
    if embeddings is None:
        return False
    print(f"✓ Loaded {len(embeddings)} embeddings")

    # Validate counts match
    if len(data) != len(embeddings):
        print(f"⚠️  Warning: Counts don't match! Data: {len(data)}, Embeddings: {len(embeddings)}")
        print(f"   Will only merge up to min({len(data)}, {len(embeddings)}) records")

    # Merge embeddings into data
    merge_count = min(len(data), len(embeddings))
    print(f"🔄 Merging {merge_count} embeddings into '{embedding_field}' field...")

    for i in range(merge_count):
        data[i][embedding_field] = embeddings[i]

        # Progress indicator
        if (i + 1) % 5000 == 0:
            print(f"   Processed {i + 1:,}/{merge_count:,} records...")

    print(f"✓ Merged all {merge_count:,} embeddings")

    # Validate first record
    if data[0].get(embedding_field):
        emb = data[0][embedding_field]
        if isinstance(emb, list) and len(emb) == 2048:
            print(f"✓ Validation: First embedding is 2048-dimensional list")
        else:
            print(f"⚠️  Validation warning: First embedding type={type(emb)}, len={len(emb) if isinstance(emb, list) else 'N/A'}")

    # Save merged data
    output_path = DATA_DIR / data_file
    print(f"💾 Saving merged data to: {output_path}")
    if save_json_file(output_path, data):
        # Get file size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"✓ Saved successfully ({size_mb:.2f} MB)")
        return True
    else:
        return False

def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("EMBEDDINGS MERGE SCRIPT")
    print("="*70)
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Data directory: {DATA_DIR}")

    # Define merge operations
    merge_operations = [
        {
            "data_file": "nodes.json",
            "embeddings_file": "embeddings_nodes.json",
            "embedding_field": "embedding",
            "description": "Nodes (graph.nodes.embedding)"
        },
        {
            "data_file": "chunks.json",
            "embeddings_file": "embeddings_chunks.json",
            "embedding_field": "content_embedding",
            "description": "Chunks (graph.chunks.content_embedding)"
        },
        {
            "data_file": "enhanced_contextual_chunks.json",
            "embeddings_file": "embeddings_enhanced_chunks.json",
            "embedding_field": "vector",
            "description": "Enhanced Chunks (graph.enhanced_contextual_chunks.vector)"
        },
        {
            "data_file": "communities.json",
            "embeddings_file": "embeddings_communities.json",
            "embedding_field": "summary_embedding",
            "description": "Communities (graph.communities.summary_embedding)"
        },
        {
            "data_file": "reports.json",
            "embeddings_file": "embeddings_reports.json",
            "embedding_field": "report_embedding",
            "description": "Reports (graph.reports.report_embedding)"
        }
    ]

    # Track results
    results = []

    # Execute merge operations
    for op in merge_operations:
        success = merge_embeddings(
            data_file=op["data_file"],
            embeddings_file=op["embeddings_file"],
            embedding_field=op["embedding_field"],
            description=op["description"]
        )
        results.append({
            "operation": op["description"],
            "success": success
        })

    # Print summary
    print(f"\n{'='*70}")
    print("MERGE SUMMARY")
    print(f"{'='*70}")

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    for result in results:
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"{status}: {result['operation']}")

    print(f"\nTotal: {successful}/{total} operations successful")
    print(f"End time: {datetime.now().isoformat()}")

    if successful == total:
        print("\n✅ All embeddings merged successfully!")
        print("\nNext steps:")
        print("1. Verify merged files in /srv/luris/be/graphrag-service/data/")
        print("2. Upload data via GraphRAG API (/api/v1/graph/create)")
        print("3. Verify database population")
        return 0
    else:
        print("\n⚠️  Some merge operations failed. Check logs above.")
        return 1

if __name__ == "__main__":
    exit(main())
