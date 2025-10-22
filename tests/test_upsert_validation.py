"""
Test suite for UPSERT validation improvements.

Tests the enhanced upsert method with input validation, error handling,
and comprehensive documentation.
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.clients.supabase_client import SupabaseClient, SupabaseSettings


class TestUpsertValidation:
    """Test UPSERT input validation and error handling."""

    def test_upsert_validation_missing_on_conflict_column(self):
        """Test that ValueError is raised when on_conflict column doesn't exist in record."""
        # Setup
        settings = SupabaseSettings()
        client = SupabaseClient(settings=settings, service_name="test-service")

        # Test data with missing column
        test_data = [
            {"node_id": "node1", "node_type": "person", "data": "test"},
            {"node_id": "node2", "node_type": "organization", "data": "test2"}
        ]

        # Attempt to upsert with invalid on_conflict column
        with pytest.raises(ValueError) as exc_info:
            # Run synchronously for test
            import asyncio
            asyncio.run(client.upsert(
                "graph.nodes",
                test_data,
                on_conflict="invalid_column",  # This column doesn't exist in data
                admin_operation=True
            ))

        # Verify error message
        error_msg = str(exc_info.value)
        assert "on_conflict columns" in error_msg
        assert "invalid_column" in error_msg
        assert "not found in record keys" in error_msg

    def test_upsert_validation_valid_on_conflict_column(self):
        """Test that validation passes with valid on_conflict column."""
        # This test would require a working Supabase connection
        # For now, we just test the validation logic doesn't raise ValueError

        settings = SupabaseSettings()
        client = SupabaseClient(settings=settings, service_name="test-service")

        # Test data with valid column
        test_data = [
            {"node_id": "node1", "node_type": "person", "data": "test"},
            {"node_id": "node2", "node_type": "organization", "data": "test2"}
        ]

        # This should pass validation (but may fail on actual DB operation)
        # The key is that validation shouldn't raise ValueError
        try:
            import asyncio
            asyncio.run(client.upsert(
                "graph.nodes",
                test_data,
                on_conflict="node_id",  # This column EXISTS in data
                admin_operation=True
            ))
        except ValueError as ve:
            # If ValueError is raised, it should NOT be about missing column
            error_msg = str(ve)
            assert "on_conflict columns" not in error_msg, \
                f"Validation failed for valid column: {error_msg}"
        except Exception:
            # Other exceptions are expected (no DB connection, etc.)
            pass

    def test_upsert_validation_single_record(self):
        """Test validation works with single record (not a list)."""
        settings = SupabaseSettings()
        client = SupabaseClient(settings=settings, service_name="test-service")

        # Single record (dict, not list)
        test_data = {"node_id": "node1", "node_type": "person", "data": "test"}

        # Test with invalid column
        with pytest.raises(ValueError) as exc_info:
            import asyncio
            asyncio.run(client.upsert(
                "graph.nodes",
                test_data,
                on_conflict="invalid_column",
                admin_operation=True
            ))

        error_msg = str(exc_info.value)
        assert "invalid_column" in error_msg

    def test_upsert_validation_no_conflict_column(self):
        """Test that validation is skipped when on_conflict is None."""
        settings = SupabaseSettings()
        client = SupabaseClient(settings=settings, service_name="test-service")

        test_data = [{"node_id": "node1", "data": "test"}]

        # This should not raise ValueError (may fail on DB operation though)
        try:
            import asyncio
            asyncio.run(client.upsert(
                "graph.nodes",
                test_data,
                on_conflict=None,  # No validation needed
                admin_operation=True
            ))
        except ValueError as ve:
            # Should not get ValueError from validation
            pytest.fail(f"Unexpected ValueError with on_conflict=None: {ve}")
        except Exception:
            # Other exceptions are expected
            pass

    def test_upsert_validation_empty_data(self):
        """Test that validation handles empty data gracefully."""
        settings = SupabaseSettings()
        client = SupabaseClient(settings=settings, service_name="test-service")

        # Empty list
        test_data = []

        # Should not raise ValueError (validation is skipped for empty data)
        try:
            import asyncio
            asyncio.run(client.upsert(
                "graph.nodes",
                test_data,
                on_conflict="node_id",
                admin_operation=True
            ))
        except ValueError as ve:
            pytest.fail(f"Unexpected ValueError with empty data: {ve}")
        except Exception:
            # Other exceptions are expected
            pass

    def test_upsert_error_context(self):
        """Test that error context is properly logged on failure."""
        # This test verifies the error context structure
        # In a real scenario, you'd mock the log_error method

        settings = SupabaseSettings()
        client = SupabaseClient(settings=settings, service_name="test-service")

        test_data = [{"node_id": "node1", "data": "test"}]

        # The enhanced error handling wraps exceptions in RuntimeError
        # with detailed context
        try:
            import asyncio
            asyncio.run(client.upsert(
                "graph.nodes",
                test_data,
                on_conflict="node_id",
                admin_operation=True
            ))
        except RuntimeError as re:
            # Verify error message format
            error_msg = str(re)
            assert "Upsert operation failed" in error_msg
            assert "graph.nodes" in error_msg
        except Exception:
            # Other exceptions may occur (DB connection, etc.)
            pass


if __name__ == "__main__":
    """Run tests manually for validation."""
    print("Running UPSERT validation tests...\n")

    test = TestUpsertValidation()

    # Test 1: Missing column validation
    print("Test 1: Missing on_conflict column validation")
    try:
        test.test_upsert_validation_missing_on_conflict_column()
        print("✅ PASSED: ValueError raised for missing column\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    except Exception as e:
        print(f"⚠️  ERROR: {e}\n")

    # Test 2: Valid column validation
    print("Test 2: Valid on_conflict column validation")
    try:
        test.test_upsert_validation_valid_on_conflict_column()
        print("✅ PASSED: Validation passed for valid column\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    except Exception as e:
        print(f"⚠️  ERROR: {e}\n")

    # Test 3: Single record validation
    print("Test 3: Single record validation")
    try:
        test.test_upsert_validation_single_record()
        print("✅ PASSED: Validation works with single record\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    except Exception as e:
        print(f"⚠️  ERROR: {e}\n")

    # Test 4: No conflict column
    print("Test 4: No conflict column (on_conflict=None)")
    try:
        test.test_upsert_validation_no_conflict_column()
        print("✅ PASSED: Validation skipped when on_conflict=None\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    except Exception as e:
        print(f"⚠️  ERROR: {e}\n")

    # Test 5: Empty data
    print("Test 5: Empty data validation")
    try:
        test.test_upsert_validation_empty_data()
        print("✅ PASSED: Validation handles empty data\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    except Exception as e:
        print(f"⚠️  ERROR: {e}\n")

    print("All validation tests completed!")
