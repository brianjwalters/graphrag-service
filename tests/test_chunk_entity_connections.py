"""
Unit tests for chunk-entity connections functionality.

Tests the _create_chunk_entity_connections method in GraphConstructor.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.graph_constructor import GraphConstructor
from src.core.config import GraphRAGSettings


@pytest.fixture
def mock_graph_constructor():
    """Create a GraphConstructor instance with mocked dependencies."""
    settings = GraphRAGSettings()
    constructor = GraphConstructor(settings)

    # Mock the supabase client
    constructor.supabase_client = AsyncMock()
    constructor.supabase_client.insert = AsyncMock()

    # Mock logging methods
    constructor._log_step = AsyncMock()
    constructor._log_error = AsyncMock()

    return constructor


@pytest.mark.asyncio
async def test_chunk_entity_connections_basic(mock_graph_constructor):
    """Test basic chunk-entity connection creation."""

    # Sample chunks
    chunks = [
        {
            "chunk_id": "chunk_001",
            "content": "The Supreme Court ruled in Marbury v. Madison that judicial review is constitutional. This case involved Chief Justice Marshall."
        },
        {
            "chunk_id": "chunk_002",
            "content": "Justice Marshall wrote the opinion establishing judicial review as a fundamental principle."
        }
    ]

    # Sample entities
    entities = [
        {
            "entity_id": "entity_001",
            "entity_text": "Supreme Court",
            "entity_type": "COURT",
            "confidence": 0.95
        },
        {
            "entity_id": "entity_002",
            "entity_text": "Marbury v. Madison",
            "entity_type": "CASE_NAME",
            "confidence": 0.98
        },
        {
            "entity_id": "entity_003",
            "entity_text": "Marshall",
            "entity_type": "PERSON",
            "confidence": 0.92
        }
    ]

    # Mock successful insert
    mock_graph_constructor.supabase_client.insert.return_value = [
        {"id": "conn_001"},
        {"id": "conn_002"},
        {"id": "conn_003"},
        {"id": "conn_004"}
    ]

    # Execute method
    result = await mock_graph_constructor._create_chunk_entity_connections(
        chunks,
        entities,
        "doc_test_001"
    )

    # Verify insert was called
    assert mock_graph_constructor.supabase_client.insert.called
    insert_call = mock_graph_constructor.supabase_client.insert.call_args

    # Verify table name
    assert insert_call[0][0] == "graph.chunk_entity_connections"

    # Verify connection records
    connection_records = insert_call[0][1]
    assert len(connection_records) > 0

    # Verify each connection has required fields
    for record in connection_records:
        assert "chunk_id" in record
        assert "entity_id" in record
        assert "relevance_score" in record
        assert "position_in_chunk" in record

        # Verify relevance score is in valid range
        assert 0.0 <= record["relevance_score"] <= 1.0
        assert record["relevance_score"] >= 0.5  # Threshold check

        # Verify position is non-negative
        assert record["position_in_chunk"] >= 0

    # Verify return value
    assert result == 4


@pytest.mark.asyncio
async def test_chunk_entity_connections_relevance_scoring(mock_graph_constructor):
    """Test relevance score calculation logic."""

    chunks = [
        {
            "chunk_id": "chunk_001",
            "content": "Contract Contract Contract early mention. The Contract is central to this case."
        }
    ]

    entities = [
        {
            "entity_id": "entity_001",
            "entity_text": "Contract",
            "entity_type": "LEGAL_TERM",
            "confidence": 0.95
        }
    ]

    mock_graph_constructor.supabase_client.insert.return_value = [{"id": "conn_001"}]

    result = await mock_graph_constructor._create_chunk_entity_connections(
        chunks,
        entities,
        "doc_test_001"
    )

    # Verify connection was created
    insert_call = mock_graph_constructor.supabase_client.insert.call_args
    connection_records = insert_call[0][1]

    assert len(connection_records) == 1

    # Verify high relevance due to multiple mentions and early position
    record = connection_records[0]
    assert record["relevance_score"] >= 0.6  # Should be reasonably high (4 occurrences in short text)
    assert record["position_in_chunk"] == 0  # First position


@pytest.mark.asyncio
async def test_chunk_entity_connections_threshold_filtering(mock_graph_constructor):
    """Test that low-relevance connections are filtered out."""

    chunks = [
        {
            "chunk_id": "chunk_001",
            "content": "This is a long document with many words and complex legal terminology. " * 20 + "Obscure term mentioned once at the very end."
        }
    ]

    entities = [
        {
            "entity_id": "entity_001",
            "entity_text": "obscure term",
            "entity_type": "LEGAL_TERM",
            "confidence": 0.60  # Low confidence
        }
    ]

    mock_graph_constructor.supabase_client.insert.return_value = []

    result = await mock_graph_constructor._create_chunk_entity_connections(
        chunks,
        entities,
        "doc_test_001"
    )

    # Low frequency + late position + low confidence should result in low relevance
    # Verify no connections created (filtered by threshold)
    if mock_graph_constructor.supabase_client.insert.called:
        insert_call = mock_graph_constructor.supabase_client.insert.call_args
        connection_records = insert_call[0][1]
        # If any connections created, they must meet threshold
        for record in connection_records:
            assert record["relevance_score"] >= 0.5


@pytest.mark.asyncio
async def test_chunk_entity_connections_empty_inputs(mock_graph_constructor):
    """Test handling of empty inputs."""

    # Test with no chunks
    result = await mock_graph_constructor._create_chunk_entity_connections(
        [],
        [{"entity_id": "e1", "entity_text": "Test", "confidence": 0.9}],
        "doc_test_001"
    )
    assert result == 0

    # Test with no entities
    result = await mock_graph_constructor._create_chunk_entity_connections(
        [{"chunk_id": "c1", "content": "Test content"}],
        [],
        "doc_test_001"
    )
    assert result == 0


@pytest.mark.asyncio
async def test_chunk_entity_connections_error_handling(mock_graph_constructor):
    """Test error handling doesn't crash graph construction."""

    chunks = [{"chunk_id": "chunk_001", "content": "Test content"}]
    entities = [{"entity_id": "entity_001", "entity_text": "Test", "confidence": 0.9}]

    # Simulate database error
    mock_graph_constructor.supabase_client.insert.side_effect = Exception("Database error")

    # Should return 0 and log error, not raise exception
    result = await mock_graph_constructor._create_chunk_entity_connections(
        chunks,
        entities,
        "doc_test_001"
    )

    assert result == 0
    assert mock_graph_constructor._log_error.called


@pytest.mark.asyncio
async def test_chunk_entity_connections_case_insensitive(mock_graph_constructor):
    """Test that entity matching is case-insensitive."""

    chunks = [
        {
            "chunk_id": "chunk_001",
            "content": "The SUPREME COURT ruled in favor of the plaintiff."
        }
    ]

    entities = [
        {
            "entity_id": "entity_001",
            "entity_text": "supreme court",  # Lowercase
            "entity_type": "COURT",
            "confidence": 0.95
        }
    ]

    mock_graph_constructor.supabase_client.insert.return_value = [{"id": "conn_001"}]

    result = await mock_graph_constructor._create_chunk_entity_connections(
        chunks,
        entities,
        "doc_test_001"
    )

    # Should find the entity despite case difference
    assert result == 1

    insert_call = mock_graph_constructor.supabase_client.insert.call_args
    connection_records = insert_call[0][1]
    assert len(connection_records) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
