#!/usr/bin/env python3
"""
Validate Generated Embeddings

Performs comprehensive validation of generated synthetic embeddings:
- Verifies file integrity and JSON format
- Checks embedding dimensions (must be 2048)
- Validates normalization (L2 norm = 1.0)
- Samples random embeddings for spot checking
- Generates detailed validation report
"""

import json
import numpy as np
import random
from pathlib import Path
from datetime import datetime


class EmbeddingValidator:
    """Validate synthetic embeddings for GraphRAG service."""

    EXPECTED_DIM = 2048
    NORM_TOLERANCE = 1e-5

    def __init__(self, data_dir: str = "/srv/luris/be/graphrag-service/data"):
        self.data_dir = Path(data_dir)
        self.validation_results = {}

    def validate_file(self, file_path: Path, expected_count: int) -> dict:
        """
        Validate a single embedding file.

        Returns:
            dict: Validation results with statistics
        """
        print(f"\n{'='*80}")
        print(f"Validating: {file_path.name}")
        print(f"{'='*80}")

        result = {
            "file": file_path.name,
            "expected_count": expected_count,
            "actual_count": 0,
            "file_size_mb": 0,
            "errors": [],
            "warnings": [],
            "validation_passed": True,
            "sample_validations": []
        }

        # Check file exists
        if not file_path.exists():
            result["errors"].append(f"File not found: {file_path}")
            result["validation_passed"] = False
            return result

        result["file_size_mb"] = round(file_path.stat().st_size / (1024 * 1024), 2)

        # Load and parse JSON
        try:
            with open(file_path, 'r') as f:
                embeddings = json.load(f)
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON format: {str(e)}")
            result["validation_passed"] = False
            return result
        except Exception as e:
            result["errors"].append(f"Failed to read file: {str(e)}")
            result["validation_passed"] = False
            return result

        # Check type
        if not isinstance(embeddings, list):
            result["errors"].append(f"Expected list, got {type(embeddings).__name__}")
            result["validation_passed"] = False
            return result

        result["actual_count"] = len(embeddings)

        # Check count
        if result["actual_count"] != expected_count:
            result["errors"].append(
                f"Count mismatch: expected {expected_count}, got {result['actual_count']}"
            )
            result["validation_passed"] = False

        print(f"  ✅ File loaded: {result['actual_count']:,} embeddings, {result['file_size_mb']:.2f} MB")

        # Validate random sample (10 embeddings or all if less)
        sample_size = min(10, len(embeddings))
        sample_indices = random.sample(range(len(embeddings)), sample_size)

        norms = []
        dimension_errors = 0
        normalization_errors = 0

        print(f"  🔍 Validating sample of {sample_size} embeddings...")

        for idx in sample_indices:
            emb = embeddings[idx]

            # Check type
            if not isinstance(emb, list):
                result["errors"].append(f"Embedding {idx} is not a list")
                result["validation_passed"] = False
                continue

            # Check dimensions
            if len(emb) != self.EXPECTED_DIM:
                dimension_errors += 1
                result["errors"].append(
                    f"Embedding {idx}: expected {self.EXPECTED_DIM} dims, got {len(emb)}"
                )
                result["validation_passed"] = False
                continue

            # Check normalization
            norm = np.linalg.norm(emb)
            norms.append(norm)

            is_normalized = abs(norm - 1.0) < self.NORM_TOLERANCE

            sample_validation = {
                "index": idx,
                "dimension": len(emb),
                "norm": float(norm),
                "is_normalized": bool(is_normalized),
                "first_10_values": [float(x) for x in emb[:10]]
            }
            result["sample_validations"].append(sample_validation)

            if not is_normalized:
                normalization_errors += 1
                result["warnings"].append(
                    f"Embedding {idx}: norm={norm:.10f} (expected ~1.0)"
                )

        if norms:
            result["norm_stats"] = {
                "min": float(min(norms)),
                "max": float(max(norms)),
                "avg": float(np.mean(norms)),
                "std": float(np.std(norms))
            }

            print(f"  📊 Norm statistics:")
            print(f"     min: {result['norm_stats']['min']:.10f}")
            print(f"     max: {result['norm_stats']['max']:.10f}")
            print(f"     avg: {result['norm_stats']['avg']:.10f}")
            print(f"     std: {result['norm_stats']['std']:.10e}")

        if dimension_errors > 0:
            print(f"  ❌ Dimension errors: {dimension_errors}/{sample_size}")
        else:
            print(f"  ✅ All dimensions correct: {self.EXPECTED_DIM}")

        if normalization_errors > 0:
            print(f"  ⚠️  Normalization warnings: {normalization_errors}/{sample_size}")
        else:
            print(f"  ✅ All norms within tolerance: ±{self.NORM_TOLERANCE}")

        if result["validation_passed"]:
            print(f"  🎉 Validation PASSED!")
        else:
            print(f"  ❌ Validation FAILED!")

        return result

    def validate_all(self):
        """Validate all embedding files."""

        print("\n" + "="*80)
        print("EMBEDDING VALIDATION")
        print("="*80)
        print(f"\nData directory: {self.data_dir}")
        print(f"Expected dimension: {self.EXPECTED_DIM}")
        print(f"Normalization tolerance: ±{self.NORM_TOLERANCE}")

        # Expected counts for each file
        expected_counts = {
            "embeddings_nodes.json": 10000,
            "embeddings_chunks.json": 25000,
            "embeddings_enhanced_chunks.json": 25000,
            "embeddings_communities.json": 500,
            "embeddings_reports.json": 200
        }

        all_passed = True

        for filename, expected_count in expected_counts.items():
            file_path = self.data_dir / filename
            result = self.validate_file(file_path, expected_count)
            self.validation_results[filename] = result

            if not result["validation_passed"]:
                all_passed = False

        # Print summary
        self.print_summary(all_passed)

        # Write validation report
        self.write_report()

        return all_passed

    def print_summary(self, all_passed: bool):
        """Print validation summary."""

        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)

        total_embeddings = 0
        total_size_mb = 0
        total_errors = 0
        total_warnings = 0

        for filename, result in self.validation_results.items():
            status = "✅ PASS" if result["validation_passed"] else "❌ FAIL"
            print(f"\n{status} {filename}")
            print(f"  Count: {result['actual_count']:,}/{result['expected_count']:,}")
            print(f"  Size: {result['file_size_mb']:.2f} MB")

            if result.get("norm_stats"):
                print(f"  Norm: avg={result['norm_stats']['avg']:.10f}, "
                      f"range=[{result['norm_stats']['min']:.10f}, {result['norm_stats']['max']:.10f}]")

            if result["errors"]:
                print(f"  ❌ Errors: {len(result['errors'])}")
                for error in result["errors"][:3]:  # Show first 3 errors
                    print(f"     - {error}")
                if len(result["errors"]) > 3:
                    print(f"     ... and {len(result['errors']) - 3} more")

            if result["warnings"]:
                print(f"  ⚠️  Warnings: {len(result['warnings'])}")

            total_embeddings += result["actual_count"]
            total_size_mb += result["file_size_mb"]
            total_errors += len(result["errors"])
            total_warnings += len(result["warnings"])

        print("\n" + "="*80)
        print(f"Total embeddings: {total_embeddings:,}")
        print(f"Total size: {total_size_mb:.2f} MB ({total_size_mb/1024:.2f} GB)")
        print(f"Total errors: {total_errors}")
        print(f"Total warnings: {total_warnings}")

        if all_passed:
            print("\n🎉 ALL VALIDATIONS PASSED!")
            print("Embeddings are ready for database insertion.")
        else:
            print("\n❌ VALIDATION FAILED!")
            print("Please review errors above and regenerate embeddings.")

        print("="*80 + "\n")

    def write_report(self):
        """Write detailed validation report to JSON."""

        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "expected_dimension": self.EXPECTED_DIM,
            "normalization_tolerance": self.NORM_TOLERANCE,
            "results": self.validation_results
        }

        report_file = self.data_dir / "validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📝 Validation report written to: {report_file}")


def main():
    """Main execution function."""

    # Set random seed for reproducible sampling
    random.seed(42)

    validator = EmbeddingValidator()
    all_passed = validator.validate_all()

    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
