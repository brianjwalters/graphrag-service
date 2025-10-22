"""
Tests for StorageQueryBuilder fluent API.

Tests the storage() method and StorageQueryBuilder class for file operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.clients.supabase_client import (
    SupabaseClient,
    StorageQueryBuilder,
    SupabaseSettings
)


@pytest.fixture
def mock_settings():
    """Create mock SupabaseSettings with required attributes"""
    settings = Mock(spec=SupabaseSettings)
    settings.max_connections = 30
    settings.circuit_breaker_enabled = True
    settings.enable_slow_query_log = False
    settings.slow_query_threshold = 5.0
    settings.environment = "test"
    settings.service_name = "test-service"
    return settings


@pytest.fixture
def mock_supabase_client(mock_settings):
    """Create mock SupabaseClient with storage support"""
    with patch.object(SupabaseClient, '_create_clients'):
        client = SupabaseClient(
            settings=mock_settings,
            service_name="test-service"
        )

        # Mock the underlying Supabase client
        client.service_client = Mock()
        client.anon_client = Mock()

        # Mock storage operations
        storage_mock = Mock()
        storage_from_mock = Mock()
        storage_mock.from_ = Mock(return_value=storage_from_mock)
        client.service_client.storage = storage_mock
        client.anon_client.storage = storage_mock

        yield client


class TestStorageQueryBuilder:
    """Test StorageQueryBuilder class"""

    def test_storage_method_returns_builder(self, mock_supabase_client):
        """Test that storage() method returns StorageQueryBuilder"""
        builder = mock_supabase_client.storage('documents')

        assert isinstance(builder, StorageQueryBuilder)
        assert builder._bucket == 'documents'
        assert builder._admin_operation == True  # Default for storage

    def test_storage_method_with_admin_flag(self, mock_supabase_client):
        """Test storage() with explicit admin_operation flag"""
        builder = mock_supabase_client.storage('documents', admin_operation=False)

        assert isinstance(builder, StorageQueryBuilder)
        assert builder._admin_operation == False

    def test_upload_method_sets_operation(self, mock_supabase_client):
        """Test that upload() method configures upload operation"""
        file_data = b"Test file content"

        builder = mock_supabase_client.storage('documents') \
            .upload('test/file.pdf', file_data, content_type='application/pdf')

        assert builder._operation == 'upload'
        assert builder._path == 'test/file.pdf'
        assert builder._file_data == file_data
        assert builder._file_options['content_type'] == 'application/pdf'

    def test_download_method_sets_operation(self, mock_supabase_client):
        """Test that download() method configures download operation"""
        builder = mock_supabase_client.storage('documents') \
            .download('test/file.pdf')

        assert builder._operation == 'download'
        assert builder._path == 'test/file.pdf'

    def test_list_method_sets_operation(self, mock_supabase_client):
        """Test that list() method configures list operation"""
        builder = mock_supabase_client.storage('documents') \
            .list('client-123/', limit=50, sort_by='updated_at')

        assert builder._operation == 'list'
        assert builder._path == 'client-123/'
        assert builder._list_options['limit'] == 50
        assert 'sortBy' in builder._list_options

    def test_remove_single_file(self, mock_supabase_client):
        """Test remove() with single file path"""
        builder = mock_supabase_client.storage('documents') \
            .remove('test/file.pdf')

        assert builder._operation == 'remove'
        assert builder._paths == ['test/file.pdf']

    def test_remove_multiple_files(self, mock_supabase_client):
        """Test remove() with multiple file paths"""
        paths = ['file1.pdf', 'file2.pdf', 'file3.pdf']
        builder = mock_supabase_client.storage('documents') \
            .remove(paths)

        assert builder._operation == 'remove'
        assert builder._paths == paths

    def test_get_public_url_synchronous(self, mock_supabase_client):
        """Test get_public_url() returns URL synchronously"""
        # Mock get_public_url to return a URL
        mock_supabase_client.service_client.storage.from_().get_public_url.return_value = \
            "https://supabase.co/storage/v1/object/public/documents/test.pdf"

        url = mock_supabase_client.storage('documents') \
            .get_public_url('test.pdf')

        assert 'https://' in url
        assert 'test.pdf' in url

    def test_create_signed_url_method(self, mock_supabase_client):
        """Test create_signed_url() method configuration"""
        builder = mock_supabase_client.storage('private-docs') \
            .create_signed_url('confidential.pdf', expires_in=1800)

        assert builder._operation == 'create_signed_url'
        assert builder._path == 'confidential.pdf'
        assert builder._file_options['expires_in'] == 1800

    @pytest.mark.asyncio
    async def test_execute_without_operation_raises_error(self, mock_supabase_client):
        """Test that execute() without operation raises ValueError"""
        builder = mock_supabase_client.storage('documents')

        with pytest.raises(ValueError, match="No storage operation specified"):
            await builder.execute()

    def test_method_chaining(self, mock_supabase_client):
        """Test that methods support fluent chaining"""
        file_data = b"Test content"

        builder = mock_supabase_client.storage('documents') \
            .upload('test.pdf', file_data)

        # Verify builder is returned for chaining
        assert isinstance(builder, StorageQueryBuilder)
        assert builder._operation == 'upload'


class TestStorageIntegration:
    """Integration tests for storage operations"""

    @pytest.mark.asyncio
    async def test_upload_workflow(self, mock_supabase_client):
        """Test complete upload workflow"""
        file_data = b"Sample PDF content"

        # Mock _execute to simulate successful upload
        async def mock_execute(operation, func, admin_op):
            return {
                "path": "client-123/document.pdf",
                "bucket": "documents",
                "url": "https://example.com/documents/client-123/document.pdf",
                "size": len(file_data)
            }

        mock_supabase_client._execute = mock_execute

        # Execute upload
        result = await mock_supabase_client.storage('documents') \
            .upload('client-123/document.pdf', file_data, content_type='application/pdf') \
            .execute()

        assert result['path'] == 'client-123/document.pdf'
        assert result['bucket'] == 'documents'
        assert 'url' in result
        assert result['size'] == len(file_data)

    @pytest.mark.asyncio
    async def test_download_workflow(self, mock_supabase_client):
        """Test complete download workflow"""
        expected_data = b"Downloaded file content"

        # Mock _execute to simulate successful download
        async def mock_execute(operation, func, admin_op):
            return expected_data

        mock_supabase_client._execute = mock_execute

        # Execute download
        result = await mock_supabase_client.storage('documents') \
            .download('client-123/document.pdf') \
            .execute()

        assert result == expected_data

    @pytest.mark.asyncio
    async def test_list_workflow(self, mock_supabase_client):
        """Test complete list workflow"""
        expected_files = [
            {"name": "file1.pdf", "size": 1024},
            {"name": "file2.pdf", "size": 2048}
        ]

        # Mock _execute to simulate successful list
        async def mock_execute(operation, func, admin_op):
            return expected_files

        mock_supabase_client._execute = mock_execute

        # Execute list
        result = await mock_supabase_client.storage('documents') \
            .list('client-123/', limit=10) \
            .execute()

        assert len(result) == 2
        assert result[0]['name'] == 'file1.pdf'

    @pytest.mark.asyncio
    async def test_remove_workflow(self, mock_supabase_client):
        """Test complete remove workflow"""
        paths_to_remove = ['file1.pdf', 'file2.pdf']

        # Mock _execute to simulate successful remove
        async def mock_execute(operation, func, admin_op):
            return {
                "success": True,
                "paths": paths_to_remove,
                "bucket": "documents",
                "count": len(paths_to_remove)
            }

        mock_supabase_client._execute = mock_execute

        # Execute remove
        result = await mock_supabase_client.storage('documents') \
            .remove(paths_to_remove) \
            .execute()

        assert result['success'] == True
        assert result['count'] == 2
        assert result['paths'] == paths_to_remove


class TestStorageAPIConsistency:
    """Test consistency with database query API"""

    def test_storage_api_mirrors_schema_api(self, mock_supabase_client):
        """Test that storage API has similar structure to schema API"""
        # Both should return builder objects
        schema_builder = mock_supabase_client.schema('graph')
        storage_builder = mock_supabase_client.storage('documents')

        assert hasattr(schema_builder, 'table')  # Factory method for table ops
        assert hasattr(storage_builder, 'upload')  # Direct operation methods

    def test_both_apis_support_admin_operation(self, mock_supabase_client):
        """Test that both APIs support admin_operation flag"""
        # Schema API with admin flag
        schema_builder = mock_supabase_client.schema('graph', admin_operation=True)
        assert schema_builder._admin_operation == True

        # Storage API with admin flag
        storage_builder = mock_supabase_client.storage('documents', admin_operation=False)
        assert storage_builder._admin_operation == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
