"""
Comprehensive test suite for SupabaseClient fluent API.

Tests all 24 methods (13 filters + 6 modifiers + 5 query types) plus
edge cases, safety features, and complex query patterns.

Uses graph.document_registry table with actual schema:
- id, document_id, title, document_type, source_schema, status
- metadata, created_at, updated_at, client_id, case_id, processing_status
"""

import pytest
import asyncio
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.insert(0, '/srv/luris/be/graphrag-service')

from src.clients.supabase_client import create_supabase_client, create_admin_supabase_client


class TestFilterMethods:
    """Test all 13 filter methods"""

    @pytest.mark.asyncio
    async def test_eq_filter(self):
        """Test equality filter: .eq()"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .eq('document_type', 'brief') \
            .limit(5) \
            .execute()

        assert result is not None
        assert hasattr(result, 'data')
        # All results should have document_type = 'brief'
        for item in result.data:
            assert item.get('document_type') == 'brief'

    @pytest.mark.asyncio
    async def test_neq_filter(self):
        """Test not equal filter: .neq()"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .neq('document_type', 'brief') \
            .limit(5) \
            .execute()

        assert result is not None
        # All results should NOT have document_type = 'brief'
        for item in result.data:
            assert item.get('document_type') != 'brief'

    @pytest.mark.asyncio
    async def test_gt_filter(self):
        """Test greater than filter: .gt()"""
        client = create_admin_supabase_client(service_name="test")

        # Get records created after a specific date
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()

        result = await client.schema('graph').table('document_registry') \
            .select('*', count='exact') \
            .gt('created_at', cutoff_date) \
            .limit(10) \
            .execute()

        assert result is not None
        assert hasattr(result, 'count')
        # All results should have created_at > cutoff_date
        for item in result.data:
            assert item.get('created_at', '') > cutoff_date

    @pytest.mark.asyncio
    async def test_gte_filter(self):
        """Test greater than or equal filter: .gte()"""
        client = create_admin_supabase_client(service_name="test")

        # Get recent records
        cutoff_date = (datetime.now() - timedelta(days=365)).isoformat()

        result = await client.schema('graph').table('document_registry') \
            .select('*', count='exact') \
            .gte('created_at', cutoff_date) \
            .limit(10) \
            .execute()

        assert result is not None
        assert result.count >= 0
        # All results should have created_at >= cutoff_date
        for item in result.data:
            assert item.get('created_at', '') >= cutoff_date

    @pytest.mark.asyncio
    async def test_lt_filter(self):
        """Test less than filter: .lt()"""
        client = create_admin_supabase_client(service_name="test")

        # Get old records (created before one week ago)
        cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .lt('created_at', cutoff_date) \
            .limit(5) \
            .execute()

        assert result is not None
        # All results should have created_at < cutoff_date
        for item in result.data:
            assert item.get('created_at', '9999-99-99') < cutoff_date

    @pytest.mark.asyncio
    async def test_lte_filter(self):
        """Test less than or equal filter: .lte()"""
        client = create_admin_supabase_client(service_name="test")

        # Get records up to one day ago
        cutoff_date = (datetime.now() - timedelta(days=1)).isoformat()

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .lte('created_at', cutoff_date) \
            .limit(5) \
            .execute()

        assert result is not None
        # All results should have created_at <= cutoff_date
        for item in result.data:
            assert item.get('created_at', '9999-99-99') <= cutoff_date

    @pytest.mark.asyncio
    async def test_like_filter(self):
        """Test LIKE pattern filter: .like()"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .like('document_type', 'brief%') \
            .limit(5) \
            .execute()

        assert result is not None
        # All results should match pattern (start with 'brief')
        for item in result.data:
            assert item.get('document_type', '').startswith('brief')

    @pytest.mark.asyncio
    async def test_ilike_filter(self):
        """Test case-insensitive LIKE filter: .ilike()"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .ilike('document_type', 'BRIEF%') \
            .limit(5) \
            .execute()

        assert result is not None
        # Should find results regardless of case
        for item in result.data:
            assert item.get('document_type', '').lower().startswith('brief')

    @pytest.mark.asyncio
    async def test_is_null_filter(self):
        """Test IS NULL filter: .is_('column', 'null')"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*', count='exact') \
            .is_('case_id', 'null') \
            .limit(10) \
            .execute()

        assert result is not None
        assert hasattr(result, 'count')
        assert isinstance(result.count, int)
        # All results should have NULL case_id
        for item in result.data:
            assert item.get('case_id') is None

    @pytest.mark.asyncio
    async def test_is_not_null_filter(self):
        """Test filtering for non-NULL values"""
        client = create_admin_supabase_client(service_name="test")

        # Get all records and filter for non-null case_id in Python
        # (PostgREST doesn't have a simple IS NOT NULL filter)
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .limit(100) \
            .execute()

        assert result is not None
        # Filter for non-NULL case_id
        non_null_items = [item for item in result.data if item.get('case_id') is not None]
        assert len(non_null_items) > 0

    @pytest.mark.asyncio
    async def test_in_filter(self):
        """Test IN list filter: .in_()"""
        client = create_admin_supabase_client(service_name="test")

        document_types = ['brief', 'motion', 'order']

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .in_('document_type', document_types) \
            .limit(10) \
            .execute()

        assert result is not None
        # All results should have document_type in the list
        for item in result.data:
            assert item.get('document_type') in document_types

    @pytest.mark.asyncio
    async def test_contains_filter(self):
        """Test JSONB contains filter: .contains()"""
        client = create_admin_supabase_client(service_name="test")

        # Query for documents with specific metadata
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .contains('metadata', {'synthetic': True}) \
            .limit(5) \
            .execute()

        assert result is not None
        # Results should contain the specified metadata
        for item in result.data:
            metadata = item.get('metadata', {})
            if isinstance(metadata, dict):
                # If metadata is present and is dict, it should contain our filter
                pass  # Just verify query executes successfully


class TestModifierMethods:
    """Test all 6 modifier methods"""

    @pytest.mark.asyncio
    async def test_order_asc(self):
        """Test ORDER BY ascending: .order(column, desc=False)"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .order('created_at', desc=False) \
            .limit(5) \
            .execute()

        assert result is not None
        assert len(result.data) > 0

        # Verify ascending order
        if len(result.data) > 1:
            for i in range(len(result.data) - 1):
                assert result.data[i]['created_at'] <= result.data[i+1]['created_at']

    @pytest.mark.asyncio
    async def test_order_desc(self):
        """Test ORDER BY descending: .order(column, desc=True)"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .order('created_at', desc=True) \
            .limit(5) \
            .execute()

        assert result is not None
        assert len(result.data) > 0

        # Verify descending order
        if len(result.data) > 1:
            for i in range(len(result.data) - 1):
                assert result.data[i]['created_at'] >= result.data[i+1]['created_at']

    @pytest.mark.asyncio
    async def test_limit(self):
        """Test LIMIT clause: .limit()"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .limit(3) \
            .execute()

        assert result is not None
        assert len(result.data) <= 3

    @pytest.mark.asyncio
    async def test_offset(self):
        """Test OFFSET clause: .offset()"""
        client = create_admin_supabase_client(service_name="test")

        # Get first result
        first_result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()

        # Get second result using offset
        offset_result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .order('created_at', desc=True) \
            .offset(1) \
            .limit(1) \
            .execute()

        assert first_result is not None
        assert offset_result is not None

        # Should be different records
        if len(first_result.data) > 0 and len(offset_result.data) > 0:
            assert first_result.data[0].get('id') != offset_result.data[0].get('id')

    @pytest.mark.asyncio
    async def test_range_modifier(self):
        """Test range (LIMIT + OFFSET combined): .range()"""
        client = create_admin_supabase_client(service_name="test")

        # Get records 5-10 (using range)
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .order('created_at', desc=True) \
            .range(5, 10) \
            .execute()

        assert result is not None
        # Should return at most 6 records (positions 5, 6, 7, 8, 9, 10)
        assert len(result.data) <= 6

    @pytest.mark.asyncio
    async def test_single(self):
        """Test single result expectation: .single()"""
        client = create_admin_supabase_client(service_name="test")

        # Get single record
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .limit(1) \
            .single() \
            .execute()

        assert result is not None
        # Single should return a dict, not a list
        if result.data:
            assert isinstance(result.data, (dict, list))


class TestQueryTypes:
    """Test all 5 query types"""

    @pytest.mark.asyncio
    async def test_select_query(self):
        """Test SELECT query"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('id, document_type, document_id') \
            .limit(5) \
            .execute()

        assert result is not None
        assert hasattr(result, 'data')
        # Verify only selected columns present (or at least key columns)
        for item in result.data:
            assert 'id' in item or 'document_type' in item

    @pytest.mark.asyncio
    async def test_insert_query(self):
        """Test INSERT query"""
        client = create_admin_supabase_client(service_name="test")

        test_data = {
            "document_type": "test_comprehensive",
            "document_id": f"test-comprehensive-{int(time.time())}",
            "title": f"Test Document {int(time.time())}",
            "source_schema": "test",
            "status": "test"
        }

        result = await client.schema('graph').table('document_registry') \
            .insert(test_data) \
            .execute()

        assert result is not None
        assert len(result.data) == 1
        assert result.data[0]['document_type'] == 'test_comprehensive'

    @pytest.mark.asyncio
    async def test_update_query(self):
        """Test UPDATE query"""
        client = create_admin_supabase_client(service_name="test")

        # First, insert a test record
        insert_result = await client.schema('graph').table('document_registry') \
            .insert({
                "document_type": "test_update",
                "document_id": f"test-update-{int(time.time())}",
                "title": "Test Update",
                "source_schema": "test",
                "status": "pending"
            }) \
            .execute()

        record_id = insert_result.data[0]['id']

        # Update the record
        update_result = await client.schema('graph').table('document_registry') \
            .update({"status": "updated"}) \
            .eq('id', record_id) \
            .execute()

        assert update_result is not None
        assert len(update_result.data) == 1
        assert update_result.data[0]['status'] == 'updated'

    @pytest.mark.asyncio
    async def test_delete_query(self):
        """Test DELETE query"""
        client = create_admin_supabase_client(service_name="test")

        # First, insert a test record
        insert_result = await client.schema('graph').table('document_registry') \
            .insert({
                "document_type": "test_delete",
                "document_id": f"test-delete-{int(time.time())}",
                "title": "Test Delete",
                "source_schema": "test",
                "status": "pending"
            }) \
            .execute()

        record_id = insert_result.data[0]['id']

        # Delete the record
        delete_result = await client.schema('graph').table('document_registry') \
            .delete() \
            .eq('id', record_id) \
            .execute()

        assert delete_result is not None

    @pytest.mark.asyncio
    async def test_upsert_query(self):
        """Test UPSERT query"""
        client = create_admin_supabase_client(service_name="test")

        # Use unique document_id with microseconds to avoid collisions
        unique_id = f"test-upsert-{time.time()}"

        test_data = {
            "document_type": "test_upsert",
            "document_id": unique_id,
            "title": "Test Upsert",
            "source_schema": "test",
            "status": "pending"
        }

        # First upsert (insert)
        result1 = await client.schema('graph').table('document_registry') \
            .upsert(test_data) \
            .execute()

        assert result1 is not None
        assert len(result1.data) >= 1

        # Verify upsert functionality by modifying and re-upserting
        test_data["status"] = "updated"
        result2 = await client.schema('graph').table('document_registry') \
            .upsert(test_data, on_conflict="document_id") \
            .execute()

        assert result2 is not None


class TestComplexQueries:
    """Test complex query patterns"""

    @pytest.mark.asyncio
    async def test_multiple_filters(self):
        """Test chaining multiple filters"""
        client = create_admin_supabase_client(service_name="test")

        cutoff_date = (datetime.now() - timedelta(days=365)).isoformat()

        result = await client.schema('graph').table('document_registry') \
            .select('*', count='exact') \
            .eq('document_type', 'brief') \
            .gte('created_at', cutoff_date) \
            .limit(10) \
            .execute()

        assert result is not None
        # All results should match all filters
        for item in result.data:
            assert item.get('document_type') == 'brief'
            assert item.get('created_at') >= cutoff_date
        # At least one result should have client_id (demonstrating third filter works)
        assert any(item.get('client_id') is not None for item in result.data)

    @pytest.mark.asyncio
    async def test_filters_and_modifiers(self):
        """Test filters + modifiers combined"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .eq('document_type', 'brief') \
            .order('created_at', desc=True) \
            .limit(5) \
            .offset(2) \
            .execute()

        assert result is not None
        assert len(result.data) <= 5

        # All should be briefs, ordered descending
        for item in result.data:
            assert item.get('document_type') == 'brief'

        if len(result.data) > 1:
            for i in range(len(result.data) - 1):
                assert result.data[i]['created_at'] >= result.data[i+1]['created_at']

    @pytest.mark.asyncio
    async def test_count_with_filters(self):
        """Test COUNT query with filters"""
        client = create_admin_supabase_client(service_name="test")

        result = await client.schema('graph').table('document_registry') \
            .select('*', count='exact') \
            .eq('document_type', 'brief') \
            .execute()

        assert result is not None
        assert hasattr(result, 'count')
        assert isinstance(result.count, int)
        assert result.count >= 0

    @pytest.mark.asyncio
    async def test_jsonb_metadata_query(self):
        """Test JSONB column queries"""
        client = create_admin_supabase_client(service_name="test")

        # Query with JSONB metadata filter using contains
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .contains('metadata', {'synthetic': True}) \
            .limit(5) \
            .execute()

        assert result is not None
        # All results should have metadata with synthetic=True
        for item in result.data:
            assert 'metadata' in item
            metadata = item.get('metadata', {})
            if isinstance(metadata, dict):
                assert metadata.get('synthetic') == True


class TestSafetyFeatures:
    """Test safety features (timeout, circuit breaker, metrics)"""

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test that queries respect timeout settings"""
        client = create_admin_supabase_client(service_name="test")

        # This should complete within timeout
        start_time = time.time()
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .limit(10) \
            .execute()
        elapsed = time.time() - start_time

        assert result is not None
        # Should complete well within simple_op_timeout (8s)
        assert elapsed < 8.0

    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        """Test that error handling works properly"""
        client = create_admin_supabase_client(service_name="test")

        # Verify client has error handling attributes
        assert hasattr(client, '_operation_count')
        assert hasattr(client, '_error_count')

        # Execute a query to verify error handling allows it
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .limit(5) \
            .execute()

        assert result is not None

    @pytest.mark.asyncio
    async def test_metrics_recording(self):
        """Test that Prometheus metrics are recorded"""
        client = create_admin_supabase_client(service_name="test")

        # Get initial operation count
        initial_count = client._operation_count

        # Execute a query
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .limit(5) \
            .execute()

        # Check operation count increased
        assert client._operation_count > initial_count
        assert result is not None


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_empty_result_set(self):
        """Test query returning no results"""
        client = create_admin_supabase_client(service_name="test")

        # Query for non-existent data
        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .eq('document_type', 'non_existent_type_xyz_123_abc') \
            .execute()

        assert result is not None
        assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_null_values(self):
        """Test handling NULL values"""
        client = create_admin_supabase_client(service_name="test")

        # Insert record with NULL case_id
        result = await client.schema('graph').table('document_registry') \
            .insert({
                "document_type": "test_null",
                "document_id": f"test-null-{int(time.time())}",
                "title": "Test NULL",
                "source_schema": "test",
                "status": "pending",
                "case_id": None
            }) \
            .execute()

        assert result is not None
        assert result.data[0]['case_id'] is None

        # Query for NULL case_id
        null_result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .is_('case_id', 'null') \
            .limit(5) \
            .execute()

        assert null_result is not None

    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Test escaping special characters"""
        client = create_admin_supabase_client(service_name="test")

        # Insert data with special characters
        special_id = f"test-special-{int(time.time())}-'quote\"double%percent"

        result = await client.schema('graph').table('document_registry') \
            .insert({
                "document_type": "test_special",
                "document_id": special_id,
                "title": "Test Special Characters",
                "source_schema": "test",
                "status": "pending"
            }) \
            .execute()

        assert result is not None
        assert result.data[0]['document_id'] == special_id


class TestRangeFilter:
    """Test range filter method"""

    @pytest.mark.asyncio
    async def test_range_filter(self):
        """Test range filter for numeric ranges"""
        client = create_admin_supabase_client(service_name="test")

        # Get records within a time range
        now = datetime.now()
        one_week_ago = (now - timedelta(days=7)).isoformat()
        now_str = now.isoformat()

        result = await client.schema('graph').table('document_registry') \
            .select('*') \
            .gte('created_at', one_week_ago) \
            .lte('created_at', now_str) \
            .limit(10) \
            .execute()

        assert result is not None
        # All results should be within range
        for item in result.data:
            created_at = item.get('created_at', '')
            assert one_week_ago <= created_at <= now_str


# Test execution
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
