"""
API Parity Error Handling Tests for GraphRAG Service

Validates that GraphRAG QueryBuilder error handling matches supabase-py behavior
for all error scenarios including invalid inputs, network failures, and edge cases.

Author: Senior Code Reviewer
Created: 2025-10-20
"""

import pytest
import asyncio
from typing import Dict, Any

# Absolute imports from project root
from src.clients.graphrag_client import GraphRAGClient
from shared.clients.supabase_client import create_supabase_client


class TestErrorHandling:
    """Test error handling parity between GraphRAG and supabase-py"""

    @pytest.mark.asyncio
    async def test_invalid_table_name(self, graphrag_client, supabase_client):
        """
        Verify error handling for non-existent table access.
        Both clients should raise similar exceptions.
        """
        invalid_table = "nonexistent_table_xyz_12345"

        # GraphRAG error capture
        graphrag_error = None
        try:
            result = await graphrag_client.table(invalid_table).select("*").execute()
        except Exception as e:
            graphrag_error = str(e)

        # Supabase error capture
        supabase_error = None
        try:
            result = await supabase_client.table(invalid_table).select("*").execute()
        except Exception as e:
            supabase_error = str(e)

        # Verify both raised errors
        assert graphrag_error is not None, "GraphRAG should raise error for invalid table"
        assert supabase_error is not None, "Supabase should raise error for invalid table"

        # Verify error messages are similar (both mention table/relation)
        assert any(keyword in graphrag_error.lower() for keyword in ["table", "relation", "not found"])
        assert any(keyword in supabase_error.lower() for keyword in ["table", "relation", "not found"])

    @pytest.mark.asyncio
    async def test_invalid_column_name(self, graphrag_client, supabase_client):
        """
        Verify error handling for selecting non-existent columns.
        PostgreSQL should return error for invalid column names.
        """
        invalid_column = "invalid_column_xyz_99999"

        graphrag_error = None
        try:
            result = await (
                graphrag_client.table("law.us_code")
                .select(invalid_column)
                .limit(1)
                .execute()
            )
        except Exception as e:
            graphrag_error = str(e)

        supabase_error = None
        try:
            result = await (
                supabase_client.table("law.us_code")
                .select(invalid_column)
                .limit(1)
                .execute()
            )
        except Exception as e:
            supabase_error = str(e)

        # Verify both raised errors
        assert graphrag_error is not None
        assert supabase_error is not None

        # Verify error mentions column
        assert "column" in graphrag_error.lower()

    @pytest.mark.asyncio
    async def test_type_mismatch_in_filter(self, graphrag_client, supabase_client):
        """
        Verify error handling for type mismatches in filter operations.
        Example: Filtering integer column with incompatible string.
        """
        # Attempt to filter integer column with invalid type
        graphrag_error = None
        try:
            result = await (
                graphrag_client.table("client.entities")
                .select("*")
                .eq("confidence", "not_a_number")  # confidence is float, passing string
                .limit(1)
                .execute()
            )
        except Exception as e:
            graphrag_error = str(e)

        # Note: PostgreSQL may coerce types, so this might not always error
        # Test validates behavior matches supabase-py

        supabase_error = None
        try:
            result = await (
                supabase_client.table("client.entities")
                .select("*")
                .eq("confidence", "not_a_number")
                .limit(1)
                .execute()
            )
        except Exception as e:
            supabase_error = str(e)

        # Verify error parity (both succeed or both fail)
        assert (graphrag_error is None) == (supabase_error is None), \
            "Type mismatch handling should match between clients"

    @pytest.mark.asyncio
    async def test_empty_result_set(self, graphrag_client, supabase_client):
        """
        Verify handling of queries that return zero rows.
        Should return empty data array, not raise error.
        """
        # Query with filter guaranteed to return no results
        graphrag_result = await (
            graphrag_client.table("law.us_code")
            .select("*")
            .eq("section", "GUARANTEED_NONEXISTENT_999999")
            .execute()
        )

        supabase_result = await (
            supabase_client.table("law.us_code")
            .select("*")
            .eq("section", "GUARANTEED_NONEXISTENT_999999")
            .execute()
        )

        # Verify both return empty arrays (not None, not error)
        assert isinstance(graphrag_result.data, list)
        assert len(graphrag_result.data) == 0
        assert isinstance(supabase_result.data, list)
        assert len(supabase_result.data) == 0

    @pytest.mark.asyncio
    async def test_null_value_filtering(self, graphrag_client, supabase_client):
        """
        Verify NULL value filtering behavior matches supabase-py.
        Tests both is_(null) and not_.is_(null) operations.
        """
        # Test IS NULL filter
        graphrag_null_result = await (
            graphrag_client.table("client.entities")
            .select("id, metadata")
            .is_("subtype", "null")  # Find entities where subtype is NULL
            .limit(5)
            .execute()
        )

        supabase_null_result = await (
            supabase_client.table("client.entities")
            .select("id, metadata")
            .is_("subtype", "null")
            .limit(5)
            .execute()
        )

        # Verify both handle NULL filtering
        assert isinstance(graphrag_null_result.data, list)
        assert isinstance(supabase_null_result.data, list)

        # If results exist, verify subtype is actually NULL
        if len(graphrag_null_result.data) > 0:
            for entity in graphrag_null_result.data:
                assert entity.get("subtype") is None or entity.get("subtype") == ""

        # Test IS NOT NULL filter
        graphrag_not_null_result = await (
            graphrag_client.table("client.entities")
            .select("id, subtype")
            .not_.is_("subtype", "null")
            .limit(5)
            .execute()
        )

        # Verify all results have non-NULL subtype
        if len(graphrag_not_null_result.data) > 0:
            for entity in graphrag_not_null_result.data:
                assert entity.get("subtype") is not None

    @pytest.mark.asyncio
    async def test_malformed_json_in_metadata(self, graphrag_client):
        """
        Verify handling of malformed JSON in JSONB columns.
        PostgreSQL should handle this gracefully.
        """
        # Query entities and verify metadata is valid JSON
        result = await (
            graphrag_client.table("client.entities")
            .select("id, metadata")
            .limit(10)
            .execute()
        )

        assert len(result.data) > 0

        # Verify all metadata is valid JSON (dict type)
        for entity in result.data:
            metadata = entity.get("metadata")
            assert isinstance(metadata, (dict, type(None))), \
                f"Metadata should be dict or None, got {type(metadata)}"

    @pytest.mark.asyncio
    async def test_query_timeout_handling(self, graphrag_client):
        """
        Verify query timeout handling for potentially long-running queries.
        Note: This test may be slow, uses large LIMIT to stress test.
        """
        import time

        start_time = time.time()

        try:
            # Query with large limit (but still bounded)
            result = await (
                graphrag_client.table("client.entities")
                .select("*")
                .limit(10000)  # Large but not unbounded
                .execute()
            )

            elapsed = time.time() - start_time

            # Verify query completed within reasonable time (30 seconds)
            assert elapsed < 30.0, f"Query took too long: {elapsed:.2f}s"

            # Verify results returned
            assert len(result.data) > 0

        except asyncio.TimeoutError:
            pytest.fail("Query timed out - timeout handling may need adjustment")

    @pytest.mark.asyncio
    async def test_concurrent_query_safety(self, graphrag_client):
        """
        Verify multiple concurrent queries don't interfere with each other.
        Tests connection pool and thread safety.
        """
        # Define 5 concurrent queries
        queries = [
            graphrag_client.table("law.us_code").select("*").limit(10).execute(),
            graphrag_client.table("client.entities").select("*").limit(10).execute(),
            graphrag_client.table("graph.nodes").select("*").limit(10).execute(),
            graphrag_client.table("law.us_code").select("id, section").limit(5).execute(),
            graphrag_client.table("client.entities").select("id, entity_type").limit(5).execute(),
        ]

        # Execute all queries concurrently
        results = await asyncio.gather(*queries, return_exceptions=True)

        # Verify all completed successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), \
                f"Query {i} failed: {result}"
            assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_special_characters_in_filter(self, graphrag_client, supabase_client):
        """
        Verify handling of special characters in string filters.
        Tests SQL injection prevention and proper escaping.
        """
        # Test with special characters that could cause SQL issues
        special_strings = [
            "'; DROP TABLE law.us_code; --",  # SQL injection attempt
            "\" OR 1=1 --",  # Another injection pattern
            "\\n\\r\\t",  # Whitespace characters
            "100% correct",  # Percent sign
            "test_value",  # Underscore (SQL wildcard)
        ]

        for test_string in special_strings:
            graphrag_result = await (
                graphrag_client.table("law.us_code")
                .select("*")
                .eq("section", test_string)
                .limit(1)
                .execute()
            )

            supabase_result = await (
                supabase_client.table("law.us_code")
                .select("*")
                .eq("section", test_string)
                .limit(1)
                .execute()
            )

            # Verify both handle special characters safely (no SQL injection)
            assert isinstance(graphrag_result.data, list)
            assert isinstance(supabase_result.data, list)
            # Both should return empty (no match) but not error

    @pytest.mark.asyncio
    async def test_invalid_schema_access(self, graphrag_client):
        """
        Verify error handling for accessing non-existent schema.
        """
        invalid_error = None
        try:
            result = await (
                graphrag_client.table("nonexistent_schema.some_table")
                .select("*")
                .execute()
            )
        except Exception as e:
            invalid_error = str(e)

        assert invalid_error is not None
        assert any(keyword in invalid_error.lower() for keyword in ["schema", "relation", "not found"])

    @pytest.mark.asyncio
    async def test_order_by_invalid_column(self, graphrag_client, supabase_client):
        """
        Verify error handling when ordering by non-existent column.
        """
        invalid_column = "nonexistent_order_column_xyz"

        graphrag_error = None
        try:
            result = await (
                graphrag_client.table("law.us_code")
                .select("*")
                .order(invalid_column)
                .limit(5)
                .execute()
            )
        except Exception as e:
            graphrag_error = str(e)

        supabase_error = None
        try:
            result = await (
                supabase_client.table("law.us_code")
                .select("*")
                .order(invalid_column)
                .limit(5)
                .execute()
            )
        except Exception as e:
            supabase_error = str(e)

        # Verify error parity
        assert (graphrag_error is None) == (supabase_error is None)

    @pytest.mark.asyncio
    async def test_range_out_of_bounds(self, graphrag_client, supabase_client):
        """
        Verify range() behavior when requesting beyond available data.
        Should return available data, not error.
        """
        # Request range far beyond available data
        graphrag_result = await (
            graphrag_client.table("law.us_code")
            .select("*")
            .range(1000000, 1000010)  # Way beyond data size
            .execute()
        )

        supabase_result = await (
            supabase_client.table("law.us_code")
            .select("*")
            .range(1000000, 1000010)
            .execute()
        )

        # Both should return empty arrays, not error
        assert isinstance(graphrag_result.data, list)
        assert isinstance(supabase_result.data, list)
        assert len(graphrag_result.data) == len(supabase_result.data)


# Fixtures
@pytest.fixture(scope="module")
async def graphrag_client():
    """Create GraphRAG client for testing"""
    from src.clients.graphrag_client import GraphRAGClient
    client = GraphRAGClient(base_url="http://localhost:8010")
    yield client
    await client.close()


@pytest.fixture(scope="module")
async def supabase_client():
    """Create Supabase client for comparison testing"""
    from shared.clients.supabase_client import create_supabase_client
    client = await create_supabase_client()
    yield client
    await client.close()
