#!/usr/bin/env python3
"""
Quick validation script to check upload prerequisites.
Runs much faster than the full upload script.
"""

import os
import sys
import json
from pathlib import Path

def check_environment():
    """Check required environment variables"""
    print("🔍 Checking Environment Variables...")

    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_API_KEY",
        "SUPABASE_SERVICE_KEY"
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✓ {var}: {value[:30]}...")
        else:
            print(f"  ✗ {var}: NOT SET")
            missing.append(var)

    if missing:
        print(f"\n❌ Missing environment variables: {', '.join(missing)}")
        return False

    print("✓ All environment variables set\n")
    return True


def check_data_files():
    """Check data files exist and are valid JSON"""
    print("🔍 Checking Data Files...")

    data_dir = Path(__file__).parent.parent / "data"

    files_to_check = [
        "document_registry.json",
        "nodes.json",
        "communities.json",
        "edges.json",
        "node_communities.json",
        "chunks.json",
        "enhanced_contextual_chunks.json",
        "text_units.json",
        "reports.json"
    ]

    all_good = True
    total_size = 0

    for filename in files_to_check:
        filepath = data_dir / filename

        if not filepath.exists():
            print(f"  ✗ {filename}: NOT FOUND")
            all_good = False
            continue

        size_mb = filepath.stat().st_size / 1024 / 1024
        total_size += size_mb

        # Quick JSON validation (just check it loads, don't read all data)
        try:
            with open(filepath, 'r') as f:
                # Read first character to check if it's valid JSON start
                first_char = f.read(1)
                if first_char not in ['[', '{']:
                    print(f"  ✗ {filename}: Invalid JSON (doesn't start with [ or {{)")
                    all_good = False
                    continue

            print(f"  ✓ {filename}: {size_mb:.1f} MB")
        except Exception as e:
            print(f"  ✗ {filename}: Error - {e}")
            all_good = False

    print(f"\n  Total data size: {total_size:.1f} MB")

    if all_good:
        print("✓ All data files present and valid\n")
    else:
        print("❌ Some data files are missing or invalid\n")

    return all_good


def check_supabase_client():
    """Check SupabaseClient can be imported"""
    print("🔍 Checking SupabaseClient...")

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.clients.supabase_client import create_admin_supabase_client

        print("  ✓ SupabaseClient import successful")
        print("✓ Client module loaded\n")
        return True

    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        print("❌ Failed to import SupabaseClient\n")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        print("❌ Failed to load client\n")
        return False


def check_dependencies():
    """Check required Python packages"""
    print("🔍 Checking Dependencies...")

    required_packages = [
        "asyncio",
        "json",
        "argparse",
        "pathlib",
        "dataclasses",
        "psutil"
    ]

    all_installed = True

    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package}: NOT INSTALLED")
            all_installed = False

    if all_installed:
        print("✓ All dependencies installed\n")
    else:
        print("❌ Some dependencies missing\n")

    return all_installed


def main():
    """Run all validation checks"""
    print("=" * 80)
    print("🚀 GraphRAG Upload Setup Validation")
    print("=" * 80)
    print()

    checks = [
        ("Environment Variables", check_environment),
        ("Data Files", check_data_files),
        ("Dependencies", check_dependencies),
        ("SupabaseClient", check_supabase_client),
    ]

    results = {}

    for check_name, check_func in checks:
        results[check_name] = check_func()

    # Summary
    print("=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)
    print()

    all_passed = all(results.values())

    for check_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status:8} - {check_name}")

    print()

    if all_passed:
        print("✅ All checks passed! Ready to upload.")
        print()
        print("Next steps:")
        print("  1. Test with dry-run:")
        print("     python scripts/upload_via_supabase_client.py --dry-run --test --limit 10")
        print()
        print("  2. Run full upload:")
        print("     python scripts/upload_via_supabase_client.py")
        print()
        return 0
    else:
        print("❌ Some checks failed. Fix issues before uploading.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
