"""
Entity Client for GraphRAG Service

This client interfaces with the Entity Extraction Service to fetch entity types
and perform entity-related operations. This avoids duplicating the 275+ entity
types and maintains proper service boundaries.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EntityTypeInfo(BaseModel):
    """Information about a specific entity type."""
    type: str
    name: str
    category: str
    description: str
    regex_supported: bool
    ai_enhanced: bool


class CitationTypeInfo(BaseModel):
    """Information about a specific citation type."""
    type: str
    name: str
    category: str
    description: str
    regex_supported: bool
    examples: List[str] = Field(default_factory=list)


class EntityTypesResponse(BaseModel):
    """Response containing all available entity and citation types."""
    entity_types: List[EntityTypeInfo]
    citation_types: List[CitationTypeInfo]
    total_entity_types: int
    total_citation_types: int
    categories: Dict[str, List[str]]
    metadata: Dict[str, Any]


class EntityClient:
    """
    Client for interacting with the Entity Extraction Service.
    
    This client provides methods to:
    - Fetch available entity and citation types
    - Get entity type categories
    - Get details about specific entity types
    - Cache entity type information for performance
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8007",
        timeout: float = 30.0,
        enable_caching: bool = True,
        cache_ttl: int = 3600  # 1 hour cache TTL
    ):
        """
        Initialize the Entity Client.
        
        Args:
            base_url: Base URL of the Entity Extraction Service
            timeout: Request timeout in seconds
            enable_caching: Whether to cache entity type information
            cache_ttl: Cache time-to-live in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        
        # Initialize cache
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(f"Entity Client initialized with base URL: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cached data is still valid.
        
        Args:
            cache_key: The cache key to check
            
        Returns:
            bool: True if cache is valid, False otherwise
        """
        if not self.enable_caching:
            return False
        
        if cache_key not in self._cache:
            return False
        
        timestamp = self._cache_timestamps.get(cache_key, 0)
        current_time = asyncio.get_event_loop().time()
        
        return (current_time - timestamp) < self.cache_ttl
    
    def _set_cache(self, cache_key: str, data: Any):
        """
        Set cache data.
        
        Args:
            cache_key: The cache key
            data: The data to cache
        """
        if self.enable_caching:
            self._cache[cache_key] = data
            self._cache_timestamps[cache_key] = asyncio.get_event_loop().time()
    
    async def get_entity_types(
        self,
        include_descriptions: bool = True,
        include_examples: bool = False,
        use_cache: bool = True
    ) -> EntityTypesResponse:
        """
        Get all available entity and citation types.
        
        Args:
            include_descriptions: Whether to include descriptions
            include_examples: Whether to include example citations
            use_cache: Whether to use cached data if available
            
        Returns:
            EntityTypesResponse: Complete list of entity and citation types
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        cache_key = f"entity_types_{include_descriptions}_{include_examples}"
        
        # Check cache
        if use_cache and self._is_cache_valid(cache_key):
            logger.debug(f"Using cached entity types (key: {cache_key})")
            return EntityTypesResponse(**self._cache[cache_key])
        
        try:
            # Make request to Entity Extraction Service
            response = await self.client.get(
                "/api/v1/entity-types",
                params={
                    "include_descriptions": include_descriptions,
                    "include_examples": include_examples
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the response
            self._set_cache(cache_key, data)
            
            logger.info(
                f"Fetched {data['total_entity_types']} entity types and "
                f"{data['total_citation_types']} citation types"
            )
            
            return EntityTypesResponse(**data)
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch entity types: {e}")
            raise
    
    async def get_entity_categories(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get a summary of entity type categories.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            Dict: Categories with counts and information
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        cache_key = "entity_categories"
        
        # Check cache
        if use_cache and self._is_cache_valid(cache_key):
            logger.debug("Using cached entity categories")
            return self._cache[cache_key]
        
        try:
            response = await self.client.get("/api/v1/entity-types/categories")
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the response
            self._set_cache(cache_key, data)
            
            logger.info(
                f"Fetched {data['total_entity_categories']} entity categories "
                f"and {data['total_citation_categories']} citation categories"
            )
            
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch entity categories: {e}")
            raise
    
    async def get_entity_type_details(
        self,
        entity_type: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific entity or citation type.
        
        Args:
            entity_type: The entity or citation type to get details for
            use_cache: Whether to use cached data if available
            
        Returns:
            Dict: Detailed information about the entity type
            
        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If the entity type is not found
        """
        cache_key = f"entity_details_{entity_type}"
        
        # Check cache
        if use_cache and self._is_cache_valid(cache_key):
            logger.debug(f"Using cached details for entity type: {entity_type}")
            return self._cache[cache_key]
        
        try:
            response = await self.client.get(f"/api/v1/entity-types/{entity_type}")
            
            if response.status_code == 404:
                raise ValueError(f"Entity type '{entity_type}' not found")
            
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the response
            self._set_cache(cache_key, data)
            
            logger.info(f"Fetched details for entity type: {entity_type}")
            
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch entity type details: {e}")
            raise
    
    async def get_all_entity_type_names(self) -> List[str]:
        """
        Get a simple list of all entity type names (both entities and citations).
        
        Returns:
            List[str]: List of all entity and citation type names
        """
        entity_types = await self.get_entity_types(
            include_descriptions=False,
            include_examples=False
        )
        
        all_types = []
        
        # Add entity types
        for entity in entity_types.entity_types:
            all_types.append(entity.type)
        
        # Add citation types
        for citation in entity_types.citation_types:
            all_types.append(citation.type)
        
        return sorted(all_types)
    
    async def get_entity_types_by_category(
        self,
        category: str
    ) -> List[str]:
        """
        Get all entity types in a specific category.
        
        Args:
            category: The category name
            
        Returns:
            List[str]: List of entity type names in the category
        """
        entity_types = await self.get_entity_types()
        
        category_types = []
        
        # Check entity types
        for entity in entity_types.entity_types:
            if entity.category == category:
                category_types.append(entity.type)
        
        # Check citation types (category might be prefixed with "Citation: ")
        citation_category = category.replace("Citation: ", "")
        for citation in entity_types.citation_types:
            if citation.category == citation_category or citation.category == category:
                category_types.append(citation.type)
        
        return sorted(category_types)
    
    async def validate_entity_types(
        self,
        entity_types: List[str]
    ) -> Dict[str, bool]:
        """
        Validate a list of entity type names.
        
        Args:
            entity_types: List of entity type names to validate
            
        Returns:
            Dict[str, bool]: Mapping of entity type to validity
        """
        valid_types = await self.get_all_entity_type_names()
        valid_set = set(valid_types)
        
        return {
            entity_type: entity_type in valid_set
            for entity_type in entity_types
        }
    
    async def health_check(self) -> bool:
        """
        Check if the Entity Extraction Service is healthy.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get("/api/v1/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Entity Extraction Service health check failed: {e}")
            return False
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("Entity client cache cleared")


# Example usage and testing
async def test_entity_client():
    """Test the Entity Client functionality."""
    async with EntityClient() as client:
        # Check health
        is_healthy = await client.health_check()
        print(f"Entity Extraction Service healthy: {is_healthy}")
        
        if is_healthy:
            # Get all entity types
            entity_types = await client.get_entity_types()
            print(f"\nTotal entity types: {entity_types.total_entity_types}")
            print(f"Total citation types: {entity_types.total_citation_types}")
            
            # Get categories
            categories = await client.get_entity_categories()
            print(f"\nEntity categories: {len(categories['entity_categories'])}")
            print(f"Citation categories: {len(categories['citation_categories'])}")
            
            # Get specific entity type details
            try:
                details = await client.get_entity_type_details("COURT")
                print(f"\nCOURT entity type details:")
                print(f"  Category: {details['category']}")
                print(f"  Description: {details['description']}")
                print(f"  AI Enhanced: {details['ai_enhanced']}")
            except ValueError as e:
                print(f"Error: {e}")
            
            # Validate entity types
            validation = await client.validate_entity_types([
                "COURT",
                "INVALID_TYPE",
                "ATTORNEY",
                "CASE_CITATION"
            ])
            print(f"\nEntity type validation:")
            for entity_type, is_valid in validation.items():
                print(f"  {entity_type}: {'✓' if is_valid else '✗'}")


if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_entity_client())