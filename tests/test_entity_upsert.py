"""
Unit Tests for Entity Upsert Endpoints
Tests for intelligent entity deduplication and upsert operations
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.routes.entity import (
    generate_entity_id,
    get_entity_description,
    semantic_similarity_search,
    merge_entities
)
from src.models.entity_models import EntityUpsertRequest


class TestEntityIdGeneration:
    """Test entity ID generation with MD5 hashing."""

    def test_generate_entity_id_basic(self):
        """Test basic entity ID generation."""
        entity_id = generate_entity_id("Supreme Court", "COURT")

        assert entity_id.startswith("entity_")
        assert len(entity_id) == 23  # "entity_" + 16 chars

    def test_generate_entity_id_deterministic(self):
        """Test that same inputs produce same entity_id."""
        id1 = generate_entity_id("Supreme Court", "COURT")
        id2 = generate_entity_id("Supreme Court", "COURT")

        assert id1 == id2

    def test_generate_entity_id_case_insensitive(self):
        """Test that entity_id is case-insensitive for text."""
        id1 = generate_entity_id("Supreme Court", "COURT")
        id2 = generate_entity_id("supreme court", "COURT")
        id3 = generate_entity_id("SUPREME COURT", "COURT")

        assert id1 == id2 == id3

    def test_generate_entity_id_type_sensitive(self):
        """Test that different types produce different entity_ids."""
        id_court = generate_entity_id("John Doe", "COURT")
        id_person = generate_entity_id("John Doe", "PERSON")

        assert id_court != id_person

    def test_generate_entity_id_whitespace_normalization(self):
        """Test that whitespace is normalized."""
        id1 = generate_entity_id("  Supreme Court  ", "COURT")
        id2 = generate_entity_id("Supreme Court", "COURT")

        assert id1 == id2


class TestEntityDescription:
    """Test entity description generation."""

    def test_get_entity_description_known_types(self):
        """Test descriptions for known entity types."""
        assert get_entity_description("COURT", "Supreme Court") == "Judicial body"
        assert get_entity_description("JUDGE", "John Roberts") == "Judicial officer"
        assert get_entity_description("PLAINTIFF", "ACME Corp") == "Party bringing legal action"

    def test_get_entity_description_unknown_type(self):
        """Test description for unknown entity type."""
        desc = get_entity_description("CUSTOM_TYPE", "Test Entity")

        assert desc == "Custom Type"  # Formatted title

    def test_get_entity_description_handles_underscores(self):
        """Test that underscores in types are converted to spaces."""
        desc = get_entity_description("LEGAL_CONCEPT", "Due Process")

        assert desc == "Legal principle or doctrine"


class TestSemanticSimilaritySearch:
    """Test semantic similarity search functionality."""

    @pytest.mark.asyncio
    async def test_semantic_search_no_embedding(self):
        """Test that None is returned when no embedding provided."""
        mock_client = AsyncMock()

        result = await semantic_similarity_search(
            mock_client,
            [],  # Empty embedding
            "COURT",
            threshold=0.85
        )

        assert result is None
        mock_client.rpc.assert_not_called()

    @pytest.mark.asyncio
    async def test_semantic_search_with_results(self):
        """Test semantic search with matching results."""
        mock_client = AsyncMock()
        mock_client.rpc.return_value = [
            {
                "node_id": "entity_abc123",
                "title": "Supreme Court of the United States",
                "similarity": 0.92
            }
        ]

        embedding = [0.1] * 2048  # Mock 2048-dim embedding

        result = await semantic_similarity_search(
            mock_client,
            embedding,
            "COURT",
            threshold=0.85
        )

        assert result is not None
        assert result["node_id"] == "entity_abc123"
        assert result["similarity"] == 0.92

        # Verify RPC was called with correct params
        mock_client.rpc.assert_called_once()
        call_args = mock_client.rpc.call_args
        assert call_args[0][0] == "search_similar_entities"

    @pytest.mark.asyncio
    async def test_semantic_search_rpc_not_available(self):
        """Test fallback when RPC function doesn't exist."""
        mock_client = AsyncMock()
        mock_client.rpc.side_effect = Exception("Function search_similar_entities does not exist")

        embedding = [0.1] * 2048

        result = await semantic_similarity_search(
            mock_client,
            embedding,
            "COURT",
            threshold=0.85
        )

        # Should return None when RPC fails
        assert result is None


class TestEntityMerging:
    """Test entity merging logic."""

    @pytest.mark.asyncio
    async def test_merge_entities_document_tracking(self):
        """Test that document IDs are merged correctly."""
        mock_client = AsyncMock()
        mock_client.update.return_value = [
            {
                "node_id": "entity_abc123",
                "metadata": {
                    "document_ids": ["doc_001", "doc_002", "doc_003"]
                }
            }
        ]

        canonical_node = {
            "node_id": "entity_abc123",
            "title": "Supreme Court",
            "metadata": {
                "document_ids": ["doc_001", "doc_002"]
            }
        }

        new_entity = EntityUpsertRequest(
            entity_text="Supreme Court",
            entity_type="COURT",
            document_ids=["doc_003"]
        )

        result = await merge_entities(
            mock_client,
            canonical_node,
            new_entity,
            similarity_score=0.92
        )

        # Verify update was called
        mock_client.update.assert_called_once()
        update_call = mock_client.update.call_args

        # Check that document_ids were merged
        updated_metadata = update_call[0][1]["metadata"]
        assert set(updated_metadata["document_ids"]) == {"doc_001", "doc_002", "doc_003"}

    @pytest.mark.asyncio
    async def test_merge_entities_confidence_max(self):
        """Test that confidence is set to maximum of existing and new."""
        mock_client = AsyncMock()
        mock_client.update.return_value = [{
            "node_id": "entity_abc123",
            "metadata": {"confidence": 0.98}
        }]

        canonical_node = {
            "node_id": "entity_abc123",
            "metadata": {
                "confidence": 0.95,
                "document_ids": []
            }
        }

        new_entity = EntityUpsertRequest(
            entity_text="Supreme Court",
            entity_type="COURT",
            confidence=0.98
        )

        await merge_entities(
            mock_client,
            canonical_node,
            new_entity,
            similarity_score=0.90
        )

        # Check that confidence was maximized
        update_call = mock_client.update.call_args
        updated_metadata = update_call[0][1]["metadata"]
        assert updated_metadata["confidence"] == 0.98

    @pytest.mark.asyncio
    async def test_merge_entities_attributes(self):
        """Test that attributes are merged correctly."""
        mock_client = AsyncMock()
        mock_client.update.return_value = [{
            "node_id": "entity_abc123",
            "metadata": {
                "attributes": {
                    "jurisdiction": "federal",
                    "court_level": "supreme"
                }
            }
        }]

        canonical_node = {
            "node_id": "entity_abc123",
            "metadata": {
                "attributes": {"jurisdiction": "federal"},
                "document_ids": []
            }
        }

        new_entity = EntityUpsertRequest(
            entity_text="Supreme Court",
            entity_type="COURT",
            attributes={"court_level": "supreme"}
        )

        await merge_entities(
            mock_client,
            canonical_node,
            new_entity,
            similarity_score=0.90
        )

        # Check attributes were merged
        update_call = mock_client.update.call_args
        updated_metadata = update_call[0][1]["metadata"]
        assert updated_metadata["attributes"]["jurisdiction"] == "federal"
        assert updated_metadata["attributes"]["court_level"] == "supreme"


class TestEntityUpsertModels:
    """Test Pydantic models for entity upsert."""

    def test_entity_upsert_request_basic(self):
        """Test basic EntityUpsertRequest creation."""
        request = EntityUpsertRequest(
            entity_text="Supreme Court",
            entity_type="COURT"
        )

        assert request.entity_text == "Supreme Court"
        assert request.entity_type == "COURT"
        assert request.confidence == 0.95  # Default
        assert request.embedding is None
        assert request.attributes is None

    def test_entity_upsert_request_with_embedding(self):
        """Test EntityUpsertRequest with embedding."""
        embedding = [0.1] * 2048

        request = EntityUpsertRequest(
            entity_text="Supreme Court",
            entity_type="COURT",
            embedding=embedding,
            confidence=0.98
        )

        assert len(request.embedding) == 2048
        assert request.confidence == 0.98

    def test_entity_upsert_request_with_tenant_context(self):
        """Test EntityUpsertRequest with tenant context."""
        request = EntityUpsertRequest(
            entity_text="Private Entity",
            entity_type="ORGANIZATION",
            client_id="client_123",
            case_id="case_456"
        )

        assert request.client_id == "client_123"
        assert request.case_id == "case_456"


# Integration test markers
@pytest.mark.integration
class TestEntityUpsertIntegration:
    """Integration tests requiring actual database connection."""

    @pytest.mark.asyncio
    async def test_entity_upsert_create_new(self):
        """Test creating a new entity via upsert endpoint."""
        # This test requires actual database connection
        # Run with: pytest -m integration
        pytest.skip("Requires database connection")

    @pytest.mark.asyncio
    async def test_entity_upsert_exact_match(self):
        """Test updating existing entity (exact match)."""
        pytest.skip("Requires database connection")

    @pytest.mark.asyncio
    async def test_entity_upsert_semantic_merge(self):
        """Test merging entities via semantic similarity."""
        pytest.skip("Requires database connection")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
