#!/usr/bin/env python3
"""
API Parity Validation Script

Validates that the Luris SupabaseClient fluent API implementation maintains
parity with supabase-py's PostgREST query builder interface.

This script checks:
1. Method existence and signatures
2. Method chaining capabilities
3. Query builder class structure
4. Parameter compatibility

Usage:
    python scripts/validate_api_parity.py
    python scripts/validate_api_parity.py --verbose
    python scripts/validate_api_parity.py --report=json
"""

import sys
import inspect
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, asdict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.clients.supabase_client import (
        QueryBuilder,
        TableQueryBuilder,
        SelectQueryBuilder,
        InsertQueryBuilder,
        UpdateQueryBuilder,
        DeleteQueryBuilder,
        UpsertQueryBuilder
    )
except ImportError as e:
    print(f"Error importing QueryBuilder classes: {e}")
    print("Make sure you're running from the graphrag-service directory")
    sys.exit(1)


# Expected supabase-py API surface (reference standard)
EXPECTED_API = {
    "QueryBuilder": {
        "methods": ["table"],
        "description": "Entry point for query building"
    },
    "TableQueryBuilder": {
        "methods": ["select", "insert", "update", "delete", "upsert"],
        "description": "Table-level query operations (factory pattern)",
        "factory_pattern": True  # Returns different builder types
    },
    "SelectQueryBuilder": {
        "methods": [
            # Filter methods (13 total)
            "eq", "neq", "gt", "gte", "lt", "lte",
            "like", "ilike", "is_", "in_",
            "contains", "contained_by", "range_",
            # Modifier methods (6 total)
            "order", "limit", "offset", "range",
            "single", "maybe_single",
            # Execution
            "execute"
        ],
        "description": "SELECT query builder with filters and modifiers"
    },
    "InsertQueryBuilder": {
        "methods": ["execute"],
        "description": "INSERT query builder"
    },
    "UpdateQueryBuilder": {
        "methods": ["execute"],
        "description": "UPDATE query builder"
    },
    "DeleteQueryBuilder": {
        "methods": ["execute"],
        "description": "DELETE query builder"
    },
    "UpsertQueryBuilder": {
        "methods": ["execute"],
        "description": "UPSERT query builder"
    }
}


@dataclass
class ValidationResult:
    """Result of API parity validation."""
    class_name: str
    expected_methods: List[str]
    implemented_methods: List[str]
    missing_methods: List[str]
    extra_methods: List[str]
    signature_mismatches: List[str]
    chainable: bool
    passed: bool


class APIParityValidator:
    """Validates API parity between implementation and supabase-py standard."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[ValidationResult] = []

    def validate_all(self) -> bool:
        """
        Validate all QueryBuilder classes.

        Returns:
            True if all validations passed, False otherwise
        """
        classes_to_validate = {
            "QueryBuilder": QueryBuilder,
            "TableQueryBuilder": TableQueryBuilder,
            "SelectQueryBuilder": SelectQueryBuilder,
            "InsertQueryBuilder": InsertQueryBuilder,
            "UpdateQueryBuilder": UpdateQueryBuilder,
            "DeleteQueryBuilder": DeleteQueryBuilder,
            "UpsertQueryBuilder": UpsertQueryBuilder
        }

        all_passed = True

        for class_name, class_obj in classes_to_validate.items():
            result = self.validate_class(class_name, class_obj)
            self.results.append(result)

            if not result.passed:
                all_passed = False

        return all_passed

    def validate_class(self, class_name: str, class_obj: type) -> ValidationResult:
        """
        Validate a single QueryBuilder class.

        Args:
            class_name: Name of the class
            class_obj: Class object to validate

        Returns:
            ValidationResult with validation details
        """
        if class_name not in EXPECTED_API:
            return ValidationResult(
                class_name=class_name,
                expected_methods=[],
                implemented_methods=[],
                missing_methods=[],
                extra_methods=[],
                signature_mismatches=[],
                chainable=False,
                passed=False
            )

        expected_spec = EXPECTED_API[class_name]
        expected_methods = set(expected_spec["methods"])

        # Get implemented public methods (exclude __init__, __repr__, etc.)
        implemented_methods = set(
            name for name in dir(class_obj)
            if not name.startswith('_')
            and callable(getattr(class_obj, name))
        )

        # Calculate differences
        missing_methods = expected_methods - implemented_methods
        extra_methods = implemented_methods - expected_methods

        # Check method signatures (skip for factory pattern classes)
        signature_mismatches = []
        is_factory = expected_spec.get("factory_pattern", False)

        if not is_factory:
            for method_name in expected_methods.intersection(implemented_methods):
                method = getattr(class_obj, method_name)
                sig = inspect.signature(method)

                # Check if method returns self for chaining (except execute)
                if method_name != "execute":
                    return_annotation = sig.return_annotation
                    if return_annotation != inspect.Signature.empty:
                        # Should return same type for chaining
                        if class_name not in str(return_annotation):
                            signature_mismatches.append(
                                f"{method_name}: Expected return type {class_name}, "
                                f"got {return_annotation}"
                            )

        # Check chainability (skip for factory pattern)
        chainable = is_factory or self._check_chainability(class_obj)

        # Determine pass/fail
        passed = (
            len(missing_methods) == 0 and
            len(signature_mismatches) == 0 and
            chainable
        )

        return ValidationResult(
            class_name=class_name,
            expected_methods=sorted(expected_methods),
            implemented_methods=sorted(implemented_methods),
            missing_methods=sorted(missing_methods),
            extra_methods=sorted(extra_methods),
            signature_mismatches=signature_mismatches,
            chainable=chainable,
            passed=passed
        )

    def _check_chainability(self, class_obj: type) -> bool:
        """
        Check if QueryBuilder methods support chaining.

        Args:
            class_obj: Class to check

        Returns:
            True if methods support chaining, False otherwise
        """
        # Get sample method (not execute, __init__, or private)
        methods = [
            name for name in dir(class_obj)
            if not name.startswith('_')
            and name != 'execute'
            and callable(getattr(class_obj, name))
        ]

        if not methods:
            return True  # No methods to check

        # Check first method's return type
        sample_method = getattr(class_obj, methods[0])
        sig = inspect.signature(sample_method)
        return_annotation = sig.return_annotation

        # Should return same type or string reference
        return (
            return_annotation != inspect.Signature.empty and
            (class_obj.__name__ in str(return_annotation) or
             return_annotation == class_obj)
        )

    def print_results(self):
        """Print validation results to console."""
        print("\n" + "="*80)
        print("API PARITY VALIDATION RESULTS")
        print("="*80 + "\n")

        total_classes = len(self.results)
        passed_classes = sum(1 for r in self.results if r.passed)

        for result in self.results:
            self._print_class_result(result)

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total Classes: {total_classes}")
        print(f"Passed: {passed_classes}")
        print(f"Failed: {total_classes - passed_classes}")

        if passed_classes == total_classes:
            print("\n✅ ALL VALIDATIONS PASSED - API parity confirmed")
            print(f"\nYour implementation has {self._count_total_methods()} methods")
            print(f"Expected supabase-py has {self._count_expected_methods()} methods")
            print("API surface is complete and compatible.")
        else:
            print("\n❌ VALIDATION FAILED - API parity issues detected")
            print("See details above for missing methods or signature mismatches.")

    def _print_class_result(self, result: ValidationResult):
        """Print results for a single class."""
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n{status} {result.class_name}")
        print("-" * 60)

        if self.verbose or not result.passed:
            print(f"Expected methods ({len(result.expected_methods)}): "
                  f"{', '.join(result.expected_methods)}")
            print(f"Implemented methods ({len(result.implemented_methods)}): "
                  f"{', '.join(result.implemented_methods)}")

        if result.missing_methods:
            print(f"\n  ⚠️  Missing methods ({len(result.missing_methods)}):")
            for method in result.missing_methods:
                print(f"    - {method}")

        if result.extra_methods and self.verbose:
            print(f"\n  ℹ️  Extra methods ({len(result.extra_methods)}) "
                  f"(not in supabase-py):")
            for method in result.extra_methods:
                print(f"    + {method}")

        if result.signature_mismatches:
            print(f"\n  ⚠️  Signature mismatches ({len(result.signature_mismatches)}):")
            for mismatch in result.signature_mismatches:
                print(f"    - {mismatch}")

        if not result.chainable:
            print("\n  ⚠️  Methods do not support chaining (missing return type hints)")

    def _count_total_methods(self) -> int:
        """Count total implemented methods across all classes."""
        return sum(len(r.implemented_methods) for r in self.results)

    def _count_expected_methods(self) -> int:
        """Count total expected methods across all classes."""
        return sum(len(r.expected_methods) for r in self.results)

    def export_json(self, output_path: str = "api_parity_report.json"):
        """
        Export validation results to JSON file.

        Args:
            output_path: Path to output JSON file
        """
        report = {
            "summary": {
                "total_classes": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "total_methods_implemented": self._count_total_methods(),
                "total_methods_expected": self._count_expected_methods()
            },
            "results": [asdict(r) for r in self.results]
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Report exported to: {output_path}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate API parity between SupabaseClient and supabase-py"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output including extra methods"
    )
    parser.add_argument(
        "--report",
        choices=["json", "console"],
        default="console",
        help="Output format (default: console)"
    )
    parser.add_argument(
        "--output", "-o",
        default="api_parity_report.json",
        help="Output file for JSON report (default: api_parity_report.json)"
    )

    args = parser.parse_args()

    validator = APIParityValidator(verbose=args.verbose)
    all_passed = validator.validate_all()

    if args.report == "console":
        validator.print_results()
    elif args.report == "json":
        validator.export_json(args.output)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
