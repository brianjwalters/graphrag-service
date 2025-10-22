"""
RAG Orchestrator - Combines Context Engine and GraphRAG
Provides unified retrieval-augmented generation for legal documents
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from .config import GraphRAGSettings
from .vector_search_service import VectorSearchService, SearchQuery, SearchType, SearchScope, GraphRAGSearchResult
from ..clients.supabase_client import SupabaseClient

logger = structlog.get_logger(__name__)


class RAGMode(Enum):
    """RAG operation mode."""
    CONTEXT_FIRST = "context_first"  # Get context first, then retrieve
    RETRIEVE_FIRST = "retrieve_first"  # Retrieve first, then contextualize
    PARALLEL = "parallel"  # Run both in parallel
    ADAPTIVE = "adaptive"  # Choose based on query analysis


class QueryIntent(Enum):
    """Query intent classification."""
    CASE_SPECIFIC = "case_specific"  # Query about specific case
    GENERAL_LEGAL = "general_legal"  # General legal knowledge
    PROCEDURAL = "procedural"  # Court procedures, deadlines
    PRECEDENT = "precedent"  # Case law and precedents
    CONTEXTUAL = "contextual"  # Needs situational context


@dataclass
class RAGQuery:
    """RAG query parameters."""
    query_text: str
    client_id: str
    case_id: Optional[str] = None
    mode: RAGMode = RAGMode.ADAPTIVE
    max_results: int = 10
    include_context: bool = True
    include_reasoning: bool = True
    quality_threshold: float = 0.7
    context_depth: int = 3
    search_types: List[SearchType] = None
    
    def __post_init__(self):
        if self.search_types is None:
            self.search_types = [SearchType.SEMANTIC, SearchType.HYBRID]


@dataclass
class RAGResult:
    """Unified RAG result combining context and retrieval."""
    query: str
    intent: QueryIntent
    mode_used: RAGMode
    
    # Context Engine results
    context_data: Optional[Dict[str, Any]] = None
    context_quality: float = 0.0
    
    # GraphRAG results
    retrieval_results: Optional[GraphRAGSearchResult] = None
    retrieval_quality: float = 0.0
    
    # Combined results
    synthesized_response: Optional[str] = None
    evidence_chain: List[Dict[str, Any]] = None
    confidence_score: float = 0.0
    
    # Performance metrics
    total_time_ms: float = 0.0
    context_time_ms: float = 0.0
    retrieval_time_ms: float = 0.0
    synthesis_time_ms: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.evidence_chain is None:
            self.evidence_chain = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class RAGOrchestrator:
    """
    RAG Orchestrator for Legal Document Intelligence.
    
    Combines Context Engine (situational awareness) and GraphRAG (knowledge retrieval)
    to provide comprehensive legal document analysis and question answering.
    
    Features:
    - Query intent classification
    - Adaptive execution strategies
    - Context-aware retrieval
    - Evidence synthesis
    - Multi-modal reasoning chains
    """

    def __init__(self, settings: GraphRAGSettings):
        self.settings = settings
        self.vector_search_service: Optional[VectorSearchService] = None
        self.supabase_client: Optional[SupabaseClient] = None
        self.is_initialized = False
        
        # Performance tracking
        self.total_queries = 0
        self.avg_response_time = 0.0
        self.success_rate = 0.0
        self.intent_distribution = {intent.value: 0 for intent in QueryIntent}
        
        # Service URLs for Context Engine integration
        self.context_engine_url = "http://localhost:8015"
        
        logger.info("RAGOrchestrator initialized")

    async def initialize(
        self,
        supabase_client: SupabaseClient,
        vector_search_service: VectorSearchService
    ) -> None:
        """Initialize the RAG Orchestrator."""
        try:
            logger.info("🎯 Initializing RAG Orchestrator")
            
            self.supabase_client = supabase_client
            self.vector_search_service = vector_search_service
            
            # Verify Context Engine availability
            await self._verify_context_engine()
            
            self.is_initialized = True
            logger.info("✅ RAG Orchestrator initialized successfully")
            
        except Exception as e:
            logger.error("❌ RAG Orchestrator initialization failed", error=str(e))
            raise

    async def process_query(self, query: RAGQuery) -> RAGResult:
        """
        Process a RAG query using the appropriate strategy.
        
        Args:
            query: RAG query parameters
            
        Returns:
            RAGResult with combined context and retrieval data
        """
        start_time = time.time()
        
        try:
            logger.info("🎯 Processing RAG query",
                       query_text=query.query_text[:100],
                       client_id=query.client_id,
                       case_id=query.case_id,
                       mode=query.mode.value)
            
            # Classify query intent
            intent = await self._classify_query_intent(query)
            self.intent_distribution[intent.value] += 1
            
            # Determine execution mode
            execution_mode = await self._determine_execution_mode(query, intent)
            
            # Execute based on mode
            if execution_mode == RAGMode.CONTEXT_FIRST:
                result = await self._execute_context_first(query, intent)
            elif execution_mode == RAGMode.RETRIEVE_FIRST:
                result = await self._execute_retrieve_first(query, intent)
            elif execution_mode == RAGMode.PARALLEL:
                result = await self._execute_parallel(query, intent)
            else:  # ADAPTIVE
                result = await self._execute_adaptive(query, intent)
            
            # Synthesize final response
            if query.include_reasoning and result.context_data and result.retrieval_results:
                synthesis_start = time.time()
                result.synthesized_response = await self._synthesize_response(result)
                result.synthesis_time_ms = (time.time() - synthesis_start) * 1000
            
            # Calculate overall confidence
            result.confidence_score = self._calculate_confidence_score(result)
            
            # Update metadata
            result.total_time_ms = (time.time() - start_time) * 1000
            result.mode_used = execution_mode
            result.intent = intent
            result.metadata.update({
                "orchestrator_version": "1.0.0",
                "services_used": self._get_services_used(result),
                "query_complexity": self._assess_query_complexity(query)
            })
            
            self._update_metrics(start_time, success=True)
            self.total_queries += 1
            
            logger.info("✅ RAG query processed successfully",
                       intent=intent.value,
                       mode=execution_mode.value,
                       confidence=result.confidence_score,
                       total_time_ms=result.total_time_ms)
            
            return result
            
        except Exception as e:
            logger.error("❌ RAG query processing failed",
                        query_text=query.query_text[:100],
                        client_id=query.client_id,
                        error=str(e))
            
            self._update_metrics(start_time, success=False)
            raise

    async def get_contextual_retrieval(
        self,
        client_id: str,
        query_text: str,
        case_id: Optional[str] = None,
        max_results: int = 10
    ) -> RAGResult:
        """
        Convenience method for contextual retrieval.
        
        Args:
            client_id: Client identifier
            query_text: Query text
            case_id: Optional case context
            max_results: Maximum results to return
            
        Returns:
            RAGResult with contextual search results
        """
        query = RAGQuery(
            query_text=query_text,
            client_id=client_id,
            case_id=case_id,
            mode=RAGMode.CONTEXT_FIRST,
            max_results=max_results,
            include_context=True,
            include_reasoning=True
        )
        
        return await self.process_query(query)

    async def get_precedent_analysis(
        self,
        client_id: str,
        query_text: str,
        jurisdiction: Optional[str] = None,
        case_type: Optional[str] = None
    ) -> RAGResult:
        """
        Get precedent analysis with legal context.
        
        Args:
            client_id: Client identifier
            query_text: Legal query
            jurisdiction: Jurisdiction filter
            case_type: Case type filter
            
        Returns:
            RAGResult with precedent analysis
        """
        query = RAGQuery(
            query_text=query_text,
            client_id=client_id,
            mode=RAGMode.PARALLEL,
            max_results=15,
            include_context=True,
            include_reasoning=True,
            search_types=[SearchType.SEMANTIC, SearchType.GLOBAL]
        )
        
        # Add jurisdiction and case type to metadata for filtering
        query.metadata = {
            "jurisdiction": jurisdiction,
            "case_type": case_type,
            "analysis_type": "precedent"
        }
        
        return await self.process_query(query)

    # Private execution methods
    
    async def _execute_context_first(self, query: RAGQuery, intent: QueryIntent) -> RAGResult:
        """Execute context-first strategy."""
        result = RAGResult(query=query.query_text, intent=intent, mode_used=RAGMode.CONTEXT_FIRST)
        
        # Get context first
        context_start = time.time()
        result.context_data = await self._get_context_data(query)
        result.context_time_ms = (time.time() - context_start) * 1000
        result.context_quality = self._assess_context_quality(result.context_data)
        
        # Use context to enhance retrieval
        retrieval_start = time.time()
        enhanced_query = self._enhance_query_with_context(query, result.context_data)
        result.retrieval_results = await self._get_retrieval_results(enhanced_query)
        result.retrieval_time_ms = (time.time() - retrieval_start) * 1000
        result.retrieval_quality = result.retrieval_results.quality_score if result.retrieval_results else 0.0
        
        return result
    
    async def _execute_retrieve_first(self, query: RAGQuery, intent: QueryIntent) -> RAGResult:
        """Execute retrieve-first strategy."""
        result = RAGResult(query=query.query_text, intent=intent, mode_used=RAGMode.RETRIEVE_FIRST)
        
        # Retrieve first
        retrieval_start = time.time()
        result.retrieval_results = await self._get_retrieval_results(query)
        result.retrieval_time_ms = (time.time() - retrieval_start) * 1000
        result.retrieval_quality = result.retrieval_results.quality_score if result.retrieval_results else 0.0
        
        # Get context based on retrieval results
        context_start = time.time()
        result.context_data = await self._get_context_for_results(query, result.retrieval_results)
        result.context_time_ms = (time.time() - context_start) * 1000
        result.context_quality = self._assess_context_quality(result.context_data)
        
        return result
    
    async def _execute_parallel(self, query: RAGQuery, intent: QueryIntent) -> RAGResult:
        """Execute parallel strategy."""
        result = RAGResult(query=query.query_text, intent=intent, mode_used=RAGMode.PARALLEL)
        
        # Run both in parallel
        context_task = self._get_context_data(query)
        retrieval_task = self._get_retrieval_results(query)
        
        context_start = time.time()
        retrieval_start = time.time()
        
        result.context_data, result.retrieval_results = await asyncio.gather(
            context_task, retrieval_task, return_exceptions=False
        )
        
        result.context_time_ms = (time.time() - context_start) * 1000
        result.retrieval_time_ms = (time.time() - retrieval_start) * 1000
        
        result.context_quality = self._assess_context_quality(result.context_data)
        result.retrieval_quality = result.retrieval_results.quality_score if result.retrieval_results else 0.0
        
        return result
    
    async def _execute_adaptive(self, query: RAGQuery, intent: QueryIntent) -> RAGResult:
        """Execute adaptive strategy based on query analysis."""
        # Choose strategy based on intent
        if intent in [QueryIntent.CASE_SPECIFIC, QueryIntent.CONTEXTUAL]:
            return await self._execute_context_first(query, intent)
        elif intent in [QueryIntent.PRECEDENT, QueryIntent.GENERAL_LEGAL]:
            return await self._execute_retrieve_first(query, intent)
        else:  # PROCEDURAL or unclear
            return await self._execute_parallel(query, intent)
    
    # Private helper methods
    
    async def _classify_query_intent(self, query: RAGQuery) -> QueryIntent:
        """Classify query intent based on content analysis."""
        query_lower = query.query_text.lower()
        
        # Case-specific indicators
        case_indicators = ["this case", "our case", "case number", "plaintiff", "defendant"]
        if any(indicator in query_lower for indicator in case_indicators) or query.case_id:
            return QueryIntent.CASE_SPECIFIC
        
        # Precedent indicators
        precedent_indicators = ["precedent", "case law", "similar cases", "court held", "ruling"]
        if any(indicator in query_lower for indicator in precedent_indicators):
            return QueryIntent.PRECEDENT
        
        # Procedural indicators
        procedural_indicators = ["deadline", "filing", "procedure", "court rules", "when to"]
        if any(indicator in query_lower for indicator in procedural_indicators):
            return QueryIntent.PROCEDURAL
        
        # Contextual indicators
        contextual_indicators = ["who", "what", "where", "when", "parties involved"]
        if any(indicator in query_lower for indicator in contextual_indicators):
            return QueryIntent.CONTEXTUAL
        
        # Default to general legal
        return QueryIntent.GENERAL_LEGAL
    
    async def _determine_execution_mode(self, query: RAGQuery, intent: QueryIntent) -> RAGMode:
        """Determine the best execution mode."""
        if query.mode != RAGMode.ADAPTIVE:
            return query.mode
        
        # Adaptive logic based on intent
        if intent == QueryIntent.CASE_SPECIFIC:
            return RAGMode.CONTEXT_FIRST
        elif intent == QueryIntent.PRECEDENT:
            return RAGMode.RETRIEVE_FIRST
        elif intent in [QueryIntent.GENERAL_LEGAL, QueryIntent.PROCEDURAL]:
            return RAGMode.PARALLEL
        else:
            return RAGMode.CONTEXT_FIRST
    
    async def _get_context_data(self, query: RAGQuery) -> Dict[str, Any]:
        """Get context data from Context Engine service."""
        try:
            import httpx
            
            # Build context request
            context_params = {
                "client_id": query.client_id,
                "case_id": query.case_id,
                "context_type": "composite",
                "scope": "standard",
                "include_precedents": True,
                "include_deadlines": True,
                "max_depth": query.context_depth
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.context_engine_url}/api/v1/context/retrieve",
                    params=context_params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning("Context Engine request failed",
                                 status_code=response.status_code,
                                 response=response.text)
                    return {}
                    
        except Exception as e:
            logger.warning("Context data retrieval failed", error=str(e))
            return {}
    
    async def _get_retrieval_results(self, query: RAGQuery) -> Optional[GraphRAGSearchResult]:
        """Get retrieval results from Vector Search Service."""
        if not self.vector_search_service:
            logger.warning("Vector search service not available")
            return None
        
        try:
            # Use the first search type from the query
            search_type = query.search_types[0] if query.search_types else SearchType.SEMANTIC
            
            search_query = SearchQuery(
                query_text=query.query_text,
                client_id=query.client_id,
                search_type=search_type,
                search_scope=SearchScope.CHUNKS,
                limit=query.max_results,
                similarity_threshold=query.quality_threshold,
                include_metadata=True,
                rerank=True
            )
            
            return await self.vector_search_service.search(search_query)
            
        except Exception as e:
            logger.warning("Retrieval failed", error=str(e))
            return None
    
    async def _get_context_for_results(
        self,
        query: RAGQuery,
        retrieval_results: Optional[GraphRAGSearchResult]
    ) -> Dict[str, Any]:
        """Get context based on retrieval results."""
        if not retrieval_results or not retrieval_results.entity_matches:
            return await self._get_context_data(query)
        
        # Enhance context query with entities found in retrieval
        entities = retrieval_results.entity_matches[:3]  # Top 3 entities
        entity_context = {
            "entity_insights": entities,
            "communities": retrieval_results.communities_involved
        }
        
        base_context = await self._get_context_data(query)
        base_context.update({"retrieval_context": entity_context})
        
        return base_context
    
    def _enhance_query_with_context(self, query: RAGQuery, context_data: Dict[str, Any]) -> RAGQuery:
        """Enhance query using context information."""
        enhanced_query = RAGQuery(
            query_text=query.query_text,
            client_id=query.client_id,
            case_id=query.case_id,
            mode=query.mode,
            max_results=query.max_results,
            include_context=query.include_context,
            include_reasoning=query.include_reasoning,
            quality_threshold=query.quality_threshold,
            context_depth=query.context_depth,
            search_types=query.search_types
        )
        
        # Add context-based filters
        if context_data.get("case_context", {}).get("case", {}).get("jurisdiction"):
            jurisdiction = context_data["case_context"]["case"]["jurisdiction"]
            enhanced_query.metadata = {"jurisdiction_filter": jurisdiction}
        
        return enhanced_query
    
    async def _synthesize_response(self, result: RAGResult) -> str:
        """Synthesize a response combining context and retrieval results."""
        synthesis_parts = []
        
        # Context summary
        if result.context_data:
            context_summary = self._summarize_context(result.context_data)
            synthesis_parts.append(f"Context: {context_summary}")
        
        # Retrieval summary
        if result.retrieval_results and result.retrieval_results.results:
            retrieval_summary = self._summarize_retrieval(result.retrieval_results)
            synthesis_parts.append(f"Evidence: {retrieval_summary}")
        
        # Reasoning chain
        if result.retrieval_results and result.retrieval_results.reasoning_chain:
            reasoning = " -> ".join(result.retrieval_results.reasoning_chain)
            synthesis_parts.append(f"Reasoning: {reasoning}")
        
        return " | ".join(synthesis_parts)
    
    def _summarize_context(self, context_data: Dict[str, Any]) -> str:
        """Create a summary of context data."""
        summaries = []
        
        if context_data.get("case_context"):
            case = context_data["case_context"].get("case", {})
            if case:
                summaries.append(f"Case: {case.get('case_title', 'Unknown')}")
        
        if context_data.get("party_context"):
            parties = context_data["party_context"].get("parties", [])
            if parties:
                summaries.append(f"Parties: {len(parties)} involved")
        
        if context_data.get("temporal_context"):
            deadlines = context_data["temporal_context"].get("upcoming_deadlines", [])
            if deadlines:
                summaries.append(f"Deadlines: {len(deadlines)} upcoming")
        
        return "; ".join(summaries) if summaries else "No specific context"
    
    def _summarize_retrieval(self, retrieval_result: GraphRAGSearchResult) -> str:
        """Create a summary of retrieval results."""
        if not retrieval_result.results:
            return "No relevant results found"
        
        top_result = retrieval_result.results[0]
        summary_parts = [
            f"{len(retrieval_result.results)} results found",
            f"Top relevance: {top_result.score:.3f}",
            f"Communities: {len(retrieval_result.communities_involved)}"
        ]
        
        return "; ".join(summary_parts)
    
    def _assess_context_quality(self, context_data: Dict[str, Any]) -> float:
        """Assess quality of context data."""
        if not context_data:
            return 0.0
        
        quality_factors = []
        
        # Case context completeness
        if context_data.get("case_context"):
            case = context_data["case_context"].get("case")
            if case:
                required_fields = ["case_number", "case_title", "case_type", "jurisdiction"]
                completeness = sum(1 for field in required_fields if case.get(field)) / len(required_fields)
                quality_factors.append(completeness)
        
        # Party information
        if context_data.get("party_context", {}).get("parties"):
            quality_factors.append(0.8)  # Having party info is good
        
        # Temporal context
        if context_data.get("temporal_context"):
            quality_factors.append(0.7)  # Having deadlines is helpful
        
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
    
    def _calculate_confidence_score(self, result: RAGResult) -> float:
        """Calculate overall confidence score."""
        factors = []
        
        # Context confidence
        if result.context_quality > 0:
            factors.append(result.context_quality * 0.3)
        
        # Retrieval confidence
        if result.retrieval_quality > 0:
            factors.append(result.retrieval_quality * 0.5)
        
        # Intent match confidence (simple heuristic)
        intent_confidence = 0.8  # Default confidence in intent classification
        factors.append(intent_confidence * 0.2)
        
        return sum(factors) if factors else 0.0
    
    def _get_services_used(self, result: RAGResult) -> List[str]:
        """Get list of services used in processing."""
        services = []
        
        if result.context_data:
            services.append("context_engine")
        
        if result.retrieval_results:
            services.append("vector_search")
            services.append("graphrag")
        
        return services
    
    def _assess_query_complexity(self, query: RAGQuery) -> str:
        """Assess query complexity."""
        text_length = len(query.query_text.split())
        
        if text_length > 30:
            return "high"
        elif text_length > 10:
            return "medium"
        else:
            return "low"
    
    async def _verify_context_engine(self) -> None:
        """Verify Context Engine service availability."""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.context_engine_url}/api/v1/health/ping",
                    timeout=5.0
                )
                
                if response.status_code != 200:
                    logger.warning("Context Engine not available",
                                 status_code=response.status_code)
                else:
                    logger.info("✅ Context Engine verified")
                    
        except Exception as e:
            logger.warning("Context Engine verification failed", error=str(e))
    
    def _update_metrics(self, start_time: float, success: bool) -> None:
        """Update performance metrics."""
        response_time = time.time() - start_time
        
        # Update rolling averages
        self.avg_response_time = (self.avg_response_time * 0.9) + (response_time * 1000 * 0.1)
        
        if success:
            self.success_rate = (self.success_rate * 0.9) + (1.0 * 0.1)
        else:
            self.success_rate = (self.success_rate * 0.9) + (0.0 * 0.1)

    @property
    def performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "total_queries": self.total_queries,
            "avg_response_time_ms": self.avg_response_time,
            "success_rate": self.success_rate,
            "intent_distribution": self.intent_distribution.copy(),
            "is_initialized": self.is_initialized
        }