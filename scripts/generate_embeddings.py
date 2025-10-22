#!/usr/bin/env python3
"""
Synthetic Vector Embedding Generator for GraphRAG Service

Generates 60,700 normalized 2048-dimensional vector embeddings for:
- 10,000 node embeddings
- 25,000 chunk embeddings
- 25,000 enhanced chunk embeddings
- 500 community embeddings
- 200 report embeddings

All vectors are normalized to unit length (L2 norm = 1.0) for cosine similarity.
Implements batch processing with incremental file writing for memory efficiency.
"""

import numpy as np
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


class EmbeddingGenerator:
    """Generate normalized synthetic embeddings with validation."""

    EMBEDDING_DIM = 2048
    BATCH_SIZE = 5000

    def __init__(self, output_dir: str = "/srv/luris/be/graphrag-service/data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Embedding counts for each table
        self.embedding_specs = {
            "nodes": 10000,
            "chunks": 25000,
            "enhanced_chunks": 25000,
            "communities": 500,
            "reports": 200
        }

        self.total_embeddings = sum(self.embedding_specs.values())
        self.validation_stats = {}

    def generate_synthetic_embedding(self, dim: int = EMBEDDING_DIM, seed: int = None) -> List[float]:
        """
        Generate normalized random vector for semantic search testing.

        Args:
            dim: Embedding dimensionality (default 2048)
            seed: Random seed for reproducibility

        Returns:
            List of floats: 2048-dimensional normalized vector (unit length)
        """
        if seed is not None:
            np.random.seed(seed)

        # Generate random vector from normal distribution
        # This approximates the distribution of real embeddings
        vec = np.random.randn(dim).astype(np.float32)

        # Normalize to unit length (required for cosine similarity)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()

    def validate_embedding(self, embedding: List[float]) -> Tuple[bool, float]:
        """
        Validate embedding dimensions and normalization.

        Returns:
            Tuple of (is_valid, norm_value)
        """
        if len(embedding) != self.EMBEDDING_DIM:
            return False, 0.0

        # Calculate L2 norm
        norm = np.linalg.norm(embedding)

        # Check if normalized (norm should be ~1.0, allow small floating point error)
        is_normalized = abs(norm - 1.0) < 1e-5

        return is_normalized, norm

    def generate_embedding_batch(self, count: int, base_seed: int = 42) -> List[List[float]]:
        """
        Generate multiple embeddings with different seeds.

        Args:
            count: Number of embeddings to generate
            base_seed: Base seed for reproducibility

        Returns:
            List of normalized embeddings
        """
        embeddings = []
        for i in range(count):
            emb = self.generate_synthetic_embedding(self.EMBEDDING_DIM, seed=base_seed + i)
            embeddings.append(emb)
        return embeddings

    def write_embeddings_incremental(self, embedding_type: str, total_count: int, base_seed: int):
        """
        Generate and write embeddings incrementally to avoid memory issues.

        Args:
            embedding_type: Type of embedding (nodes, chunks, etc.)
            total_count: Total number of embeddings to generate
            base_seed: Base seed for this embedding type
        """
        output_file = self.output_dir / f"embeddings_{embedding_type}.json"

        print(f"\n{'='*80}")
        print(f"Generating {total_count:,} {embedding_type} embeddings...")
        print(f"Output: {output_file}")
        print(f"{'='*80}")

        all_embeddings = []
        norms = []

        batches = (total_count + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        start_time = time.time()

        for batch_idx in range(batches):
            batch_start = batch_idx * self.BATCH_SIZE
            batch_end = min(batch_start + self.BATCH_SIZE, total_count)
            batch_count = batch_end - batch_start

            # Generate batch
            batch_embeddings = self.generate_embedding_batch(
                batch_count,
                base_seed + batch_start
            )

            # Validate batch
            for emb in batch_embeddings:
                is_valid, norm = self.validate_embedding(emb)
                if not is_valid:
                    raise ValueError(f"Invalid embedding generated! Norm: {norm}")
                norms.append(norm)

            all_embeddings.extend(batch_embeddings)

            # Progress update every batch
            elapsed = time.time() - start_time
            progress = batch_end / total_count * 100
            rate = batch_end / elapsed if elapsed > 0 else 0

            print(f"  Progress: {batch_end:,}/{total_count:,} ({progress:.1f}%) | "
                  f"Rate: {rate:.0f} emb/sec | Elapsed: {elapsed:.1f}s")

        # Write to file
        print(f"\n  Writing {len(all_embeddings):,} embeddings to disk...")
        write_start = time.time()

        with open(output_file, 'w') as f:
            json.dump(all_embeddings, f)

        write_time = time.time() - write_start
        total_time = time.time() - start_time

        # Store validation statistics
        self.validation_stats[embedding_type] = {
            "count": len(all_embeddings),
            "min_norm": float(min(norms)),
            "max_norm": float(max(norms)),
            "avg_norm": float(np.mean(norms)),
            "std_norm": float(np.std(norms)),
            "generation_time_sec": round(total_time, 2),
            "write_time_sec": round(write_time, 2),
            "file_size_mb": round(output_file.stat().st_size / (1024 * 1024), 2),
            "sample_embedding": all_embeddings[0][:10]  # First 10 dims of first embedding
        }

        print(f"  ✅ Complete! Total time: {total_time:.1f}s | Write time: {write_time:.1f}s")
        print(f"  📊 Validation: min_norm={min(norms):.6f}, max_norm={max(norms):.6f}, "
              f"avg_norm={np.mean(norms):.6f}")
        print(f"  💾 File size: {self.validation_stats[embedding_type]['file_size_mb']:.2f} MB")

    def generate_all_embeddings(self):
        """Generate all embeddings with different base seeds for variety."""

        print("\n" + "="*80)
        print("SYNTHETIC EMBEDDING GENERATION FOR GRAPHRAG SERVICE")
        print("="*80)
        print(f"\nTotal embeddings to generate: {self.total_embeddings:,}")
        print(f"Embedding dimension: {self.EMBEDDING_DIM}")
        print(f"Batch size: {self.BATCH_SIZE:,}")
        print(f"Output directory: {self.output_dir}")
        print("\nEmbedding counts:")
        for emb_type, count in self.embedding_specs.items():
            print(f"  - {emb_type}: {count:,}")

        overall_start = time.time()

        # Generate embeddings with different base seeds for variety
        base_seeds = {
            "nodes": 42,
            "chunks": 100000,
            "enhanced_chunks": 200000,
            "communities": 300000,
            "reports": 400000
        }

        for embedding_type, count in self.embedding_specs.items():
            self.write_embeddings_incremental(
                embedding_type,
                count,
                base_seeds[embedding_type]
            )

        overall_time = time.time() - overall_start

        # Generate metadata file
        self.write_metadata(overall_time)

        # Print final summary
        self.print_summary(overall_time)

    def write_metadata(self, generation_time: float):
        """Write metadata file with generation details."""

        metadata = {
            "generation_timestamp": datetime.now().isoformat(),
            "total_embeddings": self.total_embeddings,
            "embedding_dimension": self.EMBEDDING_DIM,
            "batch_size": self.BATCH_SIZE,
            "total_generation_time_sec": round(generation_time, 2),
            "embedding_types": self.embedding_specs,
            "validation_stats": self.validation_stats,
            "output_files": {
                emb_type: f"embeddings_{emb_type}.json"
                for emb_type in self.embedding_specs.keys()
            }
        }

        metadata_file = self.output_dir / "embeddings_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\n  ✅ Metadata written to: {metadata_file}")

    def print_summary(self, total_time: float):
        """Print comprehensive generation summary."""

        print("\n" + "="*80)
        print("GENERATION COMPLETE - SUMMARY")
        print("="*80)

        print(f"\n📊 OVERALL STATISTICS")
        print(f"  Total embeddings generated: {self.total_embeddings:,}")
        print(f"  Total generation time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        print(f"  Average rate: {self.total_embeddings/total_time:.0f} embeddings/sec")

        print(f"\n📁 OUTPUT FILES")
        total_size_mb = 0
        for emb_type, stats in self.validation_stats.items():
            print(f"  - embeddings_{emb_type}.json: {stats['count']:,} vectors, "
                  f"{stats['file_size_mb']:.2f} MB")
            total_size_mb += stats['file_size_mb']
        print(f"  Total disk space: {total_size_mb:.2f} MB")

        print(f"\n✅ VALIDATION RESULTS")
        all_valid = True
        for emb_type, stats in self.validation_stats.items():
            norm_ok = abs(stats['avg_norm'] - 1.0) < 1e-5
            status = "✅" if norm_ok else "❌"
            print(f"  {status} {emb_type}: avg_norm={stats['avg_norm']:.6f}, "
                  f"range=[{stats['min_norm']:.6f}, {stats['max_norm']:.6f}]")
            all_valid = all_valid and norm_ok

        if all_valid:
            print(f"\n  🎉 All embeddings are properly normalized!")
        else:
            print(f"\n  ⚠️  WARNING: Some embeddings may not be properly normalized!")

        print(f"\n📝 SAMPLE EMBEDDING (first 10 dimensions of nodes[0]):")
        sample = self.validation_stats['nodes']['sample_embedding']
        print(f"  {sample}")

        print(f"\n💾 METADATA")
        print(f"  File: {self.output_dir}/embeddings_metadata.json")

        print("\n" + "="*80)
        print("Ready for database insertion!")
        print("="*80 + "\n")


def main():
    """Main execution function."""

    try:
        generator = EmbeddingGenerator()
        generator.generate_all_embeddings()
        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
