"""
Local PromptClient for GraphRAG Service

This client provides a lightweight wrapper around the Prompt Service API endpoints.
It's designed specifically for GraphRAG's needs (AI-generated community summaries)
without requiring imports from the prompt-service directory.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
import httpx
from pydantic import BaseModel, Field
import backoff
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Chat message for OpenAI-compatible API."""
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions."""
    model: str = Field(default="luris-legal-gpt", description="Model to use")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    temperature: float = Field(default=0.3, description="Sampling temperature")
    max_tokens: int = Field(default=150, description="Maximum tokens to generate")
    top_p: float = Field(default=0.9, description="Nucleus sampling probability")
    stream: bool = Field(default=False, description="Stream responses")
    thinking_trace: bool = Field(default=False, description="Include thinking trace")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completions."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
    thinking_trace: Optional[List[Dict[str, Any]]] = None
    pipeline_metadata: Optional[Dict[str, Any]] = None


class TemplateInfo(BaseModel):
    """Template information model."""
    id: str
    name: str
    category: str
    description: str
    variables: List[str]
    tags: List[str]


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    version: Optional[str] = None
    uptime: Optional[float] = None
    timestamp: Optional[str] = None
    checks: Optional[Dict[str, Any]] = None


class PromptClient:
    """
    Local client for interacting with the Prompt Service API.
    
    This client provides:
    - OpenAI-compatible chat completions for AI summaries
    - Template management capabilities
    - Health checking
    - Retry logic with exponential backoff
    - Circuit breaker pattern for resilience
    - Async operations with proper timeout handling
    
    Note: This is a standalone implementation that doesn't import from prompt-service.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8003",
        timeout: float = 30.0,
        max_retries: int = 3,
        enable_circuit_breaker: bool = True
    ):
        """
        Initialize the PromptClient.
        
        Args:
            base_url: Base URL for the Prompt Service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            enable_circuit_breaker: Enable circuit breaker pattern
        """
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_circuit_breaker = enable_circuit_breaker
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={"Content-Type": "application/json"}
        )
        
        # Circuit breaker state
        self._circuit_state = "closed"  # closed, open, half_open
        self._circuit_failures = 0
        self._circuit_last_failure = None
        self._circuit_threshold = 5
        self._circuit_recovery_timeout = 60  # seconds
        
        # Metrics
        self._request_count = 0
        self._error_count = 0
        self._total_latency = 0.0
        
        logger.info(f"PromptClient initialized with base_url: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info(f"PromptClient closed. Stats: requests={self._request_count}, errors={self._error_count}")
    
    def _check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker allows the request.
        
        Returns:
            True if request is allowed, False if circuit is open
        """
        if not self.enable_circuit_breaker:
            return True
        
        if self._circuit_state == "open":
            # Check if we should try half-open
            if self._circuit_last_failure:
                time_since_failure = (datetime.now() - self._circuit_last_failure).total_seconds()
                if time_since_failure > self._circuit_recovery_timeout:
                    self._circuit_state = "half_open"
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False
        
        return True
    
    def _record_success(self):
        """Record successful request for circuit breaker."""
        if self._circuit_state == "half_open":
            self._circuit_state = "closed"
            self._circuit_failures = 0
            logger.info("Circuit breaker closed after successful request")
    
    def _record_failure(self):
        """Record failed request for circuit breaker."""
        self._circuit_failures += 1
        self._circuit_last_failure = datetime.now()
        
        if self._circuit_failures >= self._circuit_threshold:
            self._circuit_state = "open"
            logger.warning(f"Circuit breaker opened after {self._circuit_failures} failures")
    
    @backoff.on_exception(
        backoff.expo,
        (httpx.TimeoutException, httpx.ConnectError),
        max_tries=3,
        max_time=60
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: JSON body for POST requests
            params: Query parameters
            
        Returns:
            Response data as dict or list
            
        Raises:
            Exception: If request fails after retries
        """
        if not self._check_circuit_breaker():
            raise Exception("Circuit breaker is open - Prompt Service unavailable")
        
        url = f"{self.api_base}{endpoint}"
        self._request_count += 1
        
        try:
            import time
            start_time = time.time()
            
            response = await self.client.request(
                method=method,
                url=url,
                json=json_data,
                params=params
            )
            
            response.raise_for_status()
            
            # Track latency
            latency = time.time() - start_time
            self._total_latency += latency
            
            # Record success
            self._record_success()
            
            # Return JSON response
            return response.json()
            
        except httpx.HTTPStatusError as e:
            self._error_count += 1
            self._record_failure()
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
            raise
        except Exception as e:
            self._error_count += 1
            self._record_failure()
            logger.error(f"Request failed for {url}: {str(e)}")
            raise
    
    # Core API Methods
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 150,
        model: str = "luris-legal-gpt",
        thinking_trace: bool = False,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Create a chat completion using the Prompt Service.
        
        This is the main method GraphRAG uses for generating AI summaries
        of detected communities.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            model: Model to use
            thinking_trace: Include thinking pipeline trace
            stream: Stream responses (not implemented)
            
        Returns:
            Chat completion response
            
        Example:
            response = await client.chat_completion(
                messages=[{"role": "user", "content": "Summarize this community"}],
                temperature=0.3,
                max_tokens=150
            )
            content = response["choices"][0]["message"]["content"]
        """
        if stream:
            raise NotImplementedError("Streaming not yet implemented in local client")
        
        request_data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "thinking_trace": thinking_trace,
            "stream": False
        }
        
        response = await self._make_request(
            method="POST",
            endpoint="/chat/completions",
            json_data=request_data
        )
        
        return response
    
    async def analyze_input(
        self,
        messages: List[Dict[str, str]],
        thinking_trace: bool = True,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze input without generating full completion.
        
        Useful for understanding intent and getting template recommendations.
        
        Args:
            messages: List of message dicts
            thinking_trace: Include thinking trace
            document_type: Type of document for context
            
        Returns:
            Analysis response with intent and recommendations
        """
        request_data = {
            "model": "luris-legal-gpt",
            "messages": messages,
            "thinking_trace": thinking_trace
        }
        
        if document_type:
            request_data["document_type"] = document_type
        
        response = await self._make_request(
            method="POST",
            endpoint="/chat/completions/analyze",
            json_data=request_data
        )
        
        return response
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of the Prompt Service.
        
        Returns:
            Health status information
        """
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health"
            )
            return response
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def ping(self) -> bool:
        """
        Simple ping check for the Prompt Service.
        
        Returns:
            True if service is responsive, False otherwise
        """
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health/ping"
            )
            return response.get("ping") == "pong"
        except:
            return False
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """
        List available templates from the Prompt Service.
        
        Returns:
            List of template information
        """
        response = await self._make_request(
            method="GET",
            endpoint="/chat/completions/templates"
        )
        
        return response.get("data", [])
    
    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """
        Get specific template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template details
        """
        response = await self._make_request(
            method="GET",
            endpoint=f"/chat/completions/templates/{template_id}"
        )
        
        return response
    
    async def render_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        strict: bool = False
    ) -> Dict[str, Any]:
        """
        Render a template with provided variables.
        
        Args:
            template_id: Template identifier
            variables: Variables to inject into template
            strict: Strict mode for validation
            
        Returns:
            Rendered template content
        """
        request_data = {
            "template_id": template_id,
            "variables": variables,
            "strict": strict
        }
        
        response = await self._make_request(
            method="POST",
            endpoint="/templates/render",
            json_data=request_data
        )
        
        return response
    
    # Utility Methods
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.
        
        Returns:
            Statistics about client usage
        """
        avg_latency = self._total_latency / max(self._request_count, 1)
        error_rate = self._error_count / max(self._request_count, 1)
        
        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": round(error_rate, 3),
            "average_latency": round(avg_latency, 3),
            "circuit_state": self._circuit_state,
            "circuit_failures": self._circuit_failures
        }
    
    async def test_connection(self) -> bool:
        """
        Test connection to Prompt Service.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = await self.ping()
            if result:
                logger.info("Prompt Service connection test successful")
            else:
                logger.warning("Prompt Service connection test failed")
            return result
        except Exception as e:
            logger.error(f"Prompt Service connection test error: {e}")
            return False


# Factory function for easy client creation
def create_prompt_client(
    base_url: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 3
) -> PromptClient:
    """
    Factory function to create a configured PromptClient.
    
    Args:
        base_url: Base URL for Prompt Service (defaults to localhost:8003)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        
    Returns:
        Configured PromptClient instance
        
    Example:
        async with create_prompt_client() as client:
            response = await client.chat_completion(messages=[...])
    """
    import os
    
    url = base_url or os.getenv("PROMPT_SERVICE_URL", "http://localhost:8003")
    
    return PromptClient(
        base_url=url,
        timeout=timeout,
        max_retries=max_retries
    )


# Example usage for testing
if __name__ == "__main__":
    async def test_client():
        """Test the PromptClient functionality."""
        async with create_prompt_client() as client:
            # Test ping
            print("Testing ping...")
            ping_result = await client.ping()
            print(f"Ping result: {ping_result}")
            
            # Test health check
            print("\nTesting health check...")
            health = await client.health_check()
            print(f"Health status: {health.get('status')}")
            
            # Test chat completion
            print("\nTesting chat completion...")
            try:
                response = await client.chat_completion(
                    messages=[
                        {"role": "user", "content": "What is a legal brief?"}
                    ],
                    temperature=0.3,
                    max_tokens=50
                )
                if response and "choices" in response:
                    content = response["choices"][0]["message"]["content"]
                    print(f"Response: {content[:100]}...")
            except Exception as e:
                print(f"Chat completion error: {e}")
            
            # Get stats
            print("\nClient statistics:")
            stats = client.get_stats()
            for key, value in stats.items():
                print(f"  {key}: {value}")
    
    # Run the test
    asyncio.run(test_client())