"""
Main Graph Constructor Module
Orchestrates the complete GraphRAG pipeline following Microsoft methodology
"""

import asyncio
import time
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import httpx
import traceback

from ..core.entity_deduplicator import EntityDeduplicator
from ..core.community_detector import CommunityDetector
from ..core.relationship_discoverer import RelationshipDiscoverer
from ..core.graph_analytics import GraphAnalytics
from ..core.config import GraphRAGSettings


class GraphConstructor:
    """
    Main orchestrator for GraphRAG knowledge graph construction.
    Implements the complete Microsoft GraphRAG pipeline with legal specialization.
    """
    
    def __init__(self, settings: GraphRAGSettings):
        """
        Initialize graph constructor with all components.
        
        Args:
            settings: GraphRAG configuration settings
        """
        self.settings = settings
        
        # Initialize components
        self.entity_deduplicator = EntityDeduplicator(
            default_threshold=settings.entity_similarity_threshold,
            legal_entity_boost=settings.legal_entity_boost
        )
        
        self.community_detector = CommunityDetector(
            resolution=settings.leiden_resolution,
            min_community_size=settings.min_community_size,
            max_community_size=settings.max_community_size,
            coherence_threshold=settings.community_coherence_threshold
        )
        
        self.relationship_discoverer = RelationshipDiscoverer(
            min_confidence=settings.min_relationship_confidence,
            citation_weight=settings.citation_relationship_weight,
            cross_doc_boost=1.5
        )
        
        self.graph_analytics = GraphAnalytics()
        
        # Initialize clients
        self.supabase_client = None
        self.prompt_client = None
        self.log_client = None
        self.http_client = None
        
    async def initialize_clients(self):
        """Initialize service clients."""
        # Import here to avoid circular dependencies
        from ..clients.supabase_client import create_admin_supabase_client
        from ..clients.prompt_client import PromptClient
        
        # Initialize Supabase client
        self.supabase_client = create_admin_supabase_client("graphrag-service")
        
        # Initialize Prompt client if URL is configured
        if self.settings.prompt_service_url:
            self.prompt_client = PromptClient(
                base_url=self.settings.prompt_service_url,
                timeout=30.0
            )
        
        # Initialize HTTP client for other service communication
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def construct_graph(self,
                            document_id: str,
                            markdown_content: str,
                            entities: List[Dict[str, Any]],
                            citations: List[Dict[str, Any]],
                            relationships: List[Dict[str, Any]],
                            enhanced_chunks: List[Dict[str, Any]],
                            graph_options: Dict[str, Any],
                            metadata: Optional[Dict[str, Any]] = None,
                            client_id: Optional[str] = None,
                            case_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Construct knowledge graph from document data with multi-tenant support.
        
        Args:
            document_id: Document identifier
            markdown_content: Document content
            entities: Extracted entities
            citations: Extracted citations
            relationships: Initial relationships
            enhanced_chunks: Document chunks with context
            graph_options: Graph construction options
            metadata: Additional document metadata
            client_id: Client identifier for multi-tenant isolation
            case_id: Case identifier for case-specific data
            
        Returns:
            Complete graph construction results with tenant context
        """
        start_time = time.time()
        graph_id = f"graph_{document_id}_{int(time.time())}"
        
        # Add tenant context to metadata
        if metadata is None:
            metadata = {}
        metadata["client_id"] = client_id
        metadata["case_id"] = case_id
        metadata["is_public"] = client_id is None
        
        try:
            # Initialize clients if not already done
            if not self.supabase_client:
                await self.initialize_clients()
            
            # Step 1: Entity Deduplication
            if graph_options.get("enable_deduplication", True):
                deduplicated_entities, dedup_metadata = await self.entity_deduplicator.deduplicate_entities(
                    entities, document_id
                )
                await self._log_step("Entity deduplication", dedup_metadata)
            else:
                deduplicated_entities = entities
                # Provide complete deduplication metadata even when disabled
                dedup_metadata = {
                    "original_count": len(entities),
                    "deduplicated_count": len(entities),
                    "merge_operations": 0,
                    "merged_entities": [],
                    "canonical_mappings": {},
                    "deduplication_rate": 0
                }
            
            # Step 2: Relationship Discovery
            if graph_options.get("enable_cross_document_linking", True):
                enhanced_relationships, rel_metadata = await self.relationship_discoverer.discover_relationships(
                    deduplicated_entities,
                    relationships,
                    citations,
                    enhanced_chunks
                )
                await self._log_step("Relationship discovery", rel_metadata)
            else:
                enhanced_relationships = relationships
                rel_metadata = {"discovered_relationships": 0}
            
            # Step 3: Community Detection
            communities = []
            community_metadata = {}
            if graph_options.get("enable_community_detection", True) and len(deduplicated_entities) >= 3:
                communities, community_metadata = await self.community_detector.detect_communities(
                    deduplicated_entities,
                    enhanced_relationships,
                    citations
                )
                await self._log_step("Community detection", community_metadata)
                
                # Generate AI summaries for communities if requested
                if graph_options.get("use_ai_summaries", True) and communities:
                    communities = await self._generate_community_summaries(communities, deduplicated_entities)
            
            # Step 4: Graph Analytics
            analytics = None
            if graph_options.get("enable_analytics", True):
                analytics = await self.graph_analytics.analyze_graph(
                    deduplicated_entities,
                    enhanced_relationships,
                    communities
                )
                await self._log_step("Graph analytics", analytics.get("basic_metrics", {}))
            
            # Step 5: Store in Database with tenant columns
            storage_info = await self._store_graph_data(
                graph_id,
                document_id,
                deduplicated_entities,
                enhanced_relationships,
                communities,
                metadata,
                client_id,
                case_id,
                enhanced_chunks,
                citations
            )
            
            # Step 6: Cross-document linking (if applicable)
            cross_doc_links = []
            if graph_options.get("enable_cross_document_linking", True):
                cross_doc_links = await self._find_cross_document_links(
                    document_id,
                    deduplicated_entities,
                    enhanced_relationships,
                    client_id
                )
                if cross_doc_links:
                    await self._store_cross_document_links(cross_doc_links)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Build comprehensive response
            return {
                "success": True,
                "graph_id": graph_id,
                "document_id": document_id,
                "client_id": client_id,
                "case_id": case_id,
                "graph_summary": {
                    "nodes_created": len(deduplicated_entities),
                    "edges_created": len(enhanced_relationships),
                    "communities_detected": len(communities),
                    "deduplication_rate": dedup_metadata.get("deduplication_rate", 0),
                    "graph_density": analytics.get("basic_metrics", {}).get("density", 0) if analytics else 0,
                    "processing_time_seconds": processing_time
                },
                "quality_metrics": self._calculate_quality_metrics(
                    deduplicated_entities,
                    enhanced_relationships,
                    communities,
                    analytics
                ),
                "communities": communities,
                "analytics": self._format_analytics(analytics) if analytics else None,
                "deduplication": dedup_metadata,
                "storage_info": storage_info,
                "cross_document_links": len(cross_doc_links),
                "processing_metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "processing_time": processing_time,
                    "options_used": graph_options
                }
            }
            
        except Exception as e:
            error_msg = f"Graph construction failed: {str(e)}"
            # Print to console for debugging
            print(f"ERROR in graph_constructor: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            await self._log_error(error_msg, traceback.format_exc())
            
            return {
                "success": False,
                "error": error_msg,
                "graph_id": graph_id,
                "document_id": document_id,
                "processing_time": time.time() - start_time
            }
    
    async def _generate_community_summaries(self,
                                           communities: List[Dict[str, Any]],
                                           entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate AI summaries for communities using Prompt Service."""
        if not self.prompt_client:
            return communities
        
        entity_map = {e["entity_id"]: e for e in entities}
        
        for community in communities:
            try:
                # Get entity details for this community
                community_entities = []
                for entity_id in community.get("entity_ids", []):
                    if entity_id in entity_map:
                        entity = entity_map[entity_id]
                        community_entities.append({
                            "text": entity.get("entity_text", ""),
                            "type": entity.get("entity_type", "")
                        })
                
                # Generate summary via Prompt Service
                prompt = self._build_community_summary_prompt(
                    community_entities,
                    community.get("community_type", ""),
                    community.get("central_entities", []),
                    entity_map
                )
                
                # Use the PromptClient for chat completion
                response = await self.prompt_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.3
                )
                
                if response and "choices" in response and len(response["choices"]) > 0:
                    community["ai_summary"] = response["choices"][0]["message"]["content"]
                    
            except Exception as e:
                # Don't fail the whole process if summary generation fails
                await self._log_error(f"Failed to generate summary for community: {e}")
                continue
        
        return communities
    
    def _build_community_summary_prompt(self,
                                       entities: List[Dict[str, Any]],
                                       community_type: str,
                                       central_entities: List[str],
                                       entity_map: Dict[str, Any]) -> str:
        """Build prompt for community summary generation."""
        entity_list = "\n".join([f"- {e['text']} ({e['type']})" for e in entities[:20]])
        
        central_names = []
        for entity_id in central_entities[:3]:
            if entity_id in entity_map:
                central_names.append(entity_map[entity_id].get("entity_text", ""))
        
        return f"""Summarize this legal entity community in 2-3 sentences:

Community Type: {community_type}
Central Entities: {', '.join(central_names)}
Community Members ({len(entities)} total):
{entity_list}

Focus on the legal relationships and significance. Be concise and specific."""
    
    def _generate_entity_id(self, entity_text: str, entity_type: str) -> str:
        """Generate a unique entity ID from text and type."""
        import hashlib

        # Create a unique identifier based on entity text and type
        combined = f"{entity_type}:{entity_text}".lower().strip()
        entity_id = hashlib.md5(combined.encode()).hexdigest()[:16]
        return f"entity_{entity_id}"

    def _get_entity_description(self, entity_type: str, entity_text: str) -> str:
        """Get contextual description for entity without ' entity' suffix."""

        # Contextual descriptions by type
        descriptions = {
            "COURT": "Judicial body",
            "JUDGE": "Judicial officer",
            "GOVERNMENT_ENTITY": "Government department or agency",
            "LAW_FIRM": "Legal practice organization",
            "ATTORNEY": "Legal counsel",
            "PLAINTIFF": "Party bringing legal action",
            "DEFENDANT": "Party defending legal action",
            "APPELLANT": "Party appealing decision",
            "APPELLEE": "Party responding to appeal",
            "CASE_CITATION": "Legal case reference",
            "STATUTE": "Legislative enactment",
            "STATUTE_CITATION": "Statutory reference",
            "REGULATION": "Administrative rule",
            "REGULATION_CITATION": "Regulatory reference",
            "FILING_DATE": "Document filing date",
            "DECISION_DATE": "Judicial decision date",
            "HEARING_DATE": "Court hearing date",
            "DEADLINE": "Legal deadline",
            "DATE": "Temporal reference",
            "MONETARY_AMOUNT": "Financial value",
            "CONTRACT": "Legal agreement",
            "MOTION": "Legal request to court",
            "BRIEF": "Legal argument document",
            "COMPLAINT": "Initial legal filing",
            "PARTY": "Litigation participant",
            "FEDERAL_AGENCY": "Federal government agency",
            "STATE_AGENCY": "State government agency",
            "JURISDICTION": "Legal authority area",
            "VENUE": "Legal proceeding location",
            "DISTRICT": "Judicial district",
            "CIRCUIT": "Appellate circuit",
            "SETTLEMENT": "Legal dispute resolution",
            "DAMAGES": "Legal compensation",
            "LEGAL_CONCEPT": "Legal principle or doctrine",
            "LEGAL_MARKER": "Legal indicator or reference"
        }

        # Return description or fallback to simple entity type
        return descriptions.get(entity_type, entity_type.replace("_", " ").title())

    async def _store_graph_data(self,
                               graph_id: str,
                               document_id: str,
                               entities: List[Dict[str, Any]],
                               relationships: List[Dict[str, Any]],
                               communities: List[Dict[str, Any]],
                               metadata: Optional[Dict[str, Any]],
                               client_id: Optional[str] = None,
                               case_id: Optional[str] = None,
                               enhanced_chunks: Optional[List[Dict[str, Any]]] = None,
                               citations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Store graph data in Supabase database with tenant columns."""
        storage_info = {
            "nodes_created": 0,
            "edges_created": 0,
            "communities_detected": 0,
            "errors": []
        }

        # CRITICAL FIX: Removed outer try-except to allow exceptions to propagate
        # The old pattern was catching ALL exceptions and continuing silently

        # Store entities in graph.nodes with tenant info in metadata
        if entities:
            # CRITICAL FIX: Fail-safe deduplication by entity_id before database insert
            # This prevents duplicate key errors if the upstream deduplication somehow failed
            seen_entity_ids = set()
            unique_entities = []
            duplicate_count = 0

            for entity in entities:
                entity_id = entity.get("entity_id")
                if entity_id and entity_id not in seen_entity_ids:
                    seen_entity_ids.add(entity_id)
                    unique_entities.append(entity)
                else:
                    duplicate_count += 1

            if duplicate_count > 0:
                await self._log_step("fail_safe_deduplication", {
                    "duplicates_removed": duplicate_count,
                    "original_count": len(entities),
                    "unique_count": len(unique_entities)
                })

            # Use unique entities for node creation
            node_records = []
            for entity in unique_entities:
                # Create base node record
                node_record = {
                    "node_id": entity["entity_id"],
                    "node_type": "entity",
                    "description": self._get_entity_description(
                        entity.get('entity_type', 'UNKNOWN'),
                        entity.get('entity_text', '')
                    ),
                }

                # Set title field from entity text
                entity_text = entity.get("entity_text", "")
                node_record["title"] = entity_text  # Use title column (not label)

                # Add source fields if they exist in schema
                if "source_id" in entity:
                    node_record["source_id"] = entity["source_id"]
                else:
                    node_record["source_id"] = document_id

                if "source_type" in entity:
                    node_record["source_type"] = entity["source_type"]
                else:
                    node_record["source_type"] = "document"

                # Add metadata
                node_record["metadata"] = {
                    "entity_type": entity.get("entity_type"),
                    "confidence": entity.get("confidence", 0.95),
                    "attributes": entity.get("attributes", {}),
                    "document_id": document_id,
                    "graph_id": graph_id,
                    "client_id": client_id,  # Store tenant info in metadata
                    "case_id": case_id       # Store tenant info in metadata
                }

                node_records.append(node_record)

            # Batch upsert nodes with validation (idempotent for re-runs)
            await self._log_step("upserting_nodes", {"count": len(node_records)})
            result = await self.supabase_client.upsert(
                "graph.nodes",
                node_records,
                on_conflict="node_id",
                admin_operation=True
            )

            # CRITICAL FIX: Validate result and fail fast if insert failed
            if result is None:
                raise Exception(f"Failed to insert {len(node_records)} nodes: Supabase returned None")
            elif len(result) == 0:
                raise Exception(f"Failed to insert {len(node_records)} nodes: Supabase returned empty result")
            elif len(result) != len(node_records):
                raise Exception(f"Partial insert failure: Expected {len(node_records)} nodes, got {len(result)}")

            storage_info["nodes_created"] = len(result)
            await self._log_step("nodes_inserted", {"count": len(result)})
            
        # Store relationships in graph.edges with tenant info in metadata
        if relationships:
            edge_records = []
            for i, rel in enumerate(relationships):
                # Handle both Pass 8 AI-extracted and co-occurrence relationships
                # Pass 8 relationships have specific fields from relationship extraction
                is_ai_extracted = "source_entity_text" in rel and "target_entity_text" in rel

                if is_ai_extracted:
                    # AI-extracted relationship from Pass 8
                    relationship_type_val = rel.get("relationship_type", "UNKNOWN")
                    confidence_val = rel.get("confidence", 0.9)  # Higher default for AI

                    # Map entity texts to entity IDs
                    source_id = rel.get("source_entity")
                    target_id = rel.get("target_entity")

                    # If we don't have entity IDs, generate them from text
                    if not source_id:
                        source_id = self._generate_entity_id(
                            rel.get("source_entity_text", ""),
                            rel.get("source_entity_type", "")
                        )
                    if not target_id:
                        target_id = self._generate_entity_id(
                            rel.get("target_entity_text", ""),
                            rel.get("target_entity_type", "")
                        )

                    extraction_method = "AI_MULTIPASS_RELATIONSHIPS"
                    evidence = rel.get("evidence_text", "") or str(rel.get("evidence", ""))
                else:
                    # Co-occurrence or other relationship types
                    relationship_type_val = rel.get("relationship_type", "UNKNOWN")
                    confidence_val = rel.get("confidence", 0.7)  # Lower default for co-occurrence
                    source_id = rel["source_entity"]
                    target_id = rel["target_entity"]
                    extraction_method = rel.get("discovery_method", "COOCCURRENCE_INFERENCE")
                    evidence = str(rel.get("evidence", ""))

                edge_record = {
                    "source_node_id": source_id,
                    "target_node_id": target_id,
                    "weight": confidence_val,
                    "evidence": evidence,
                    "metadata": {
                        "client_id": client_id,  # Store tenant info in metadata
                        "case_id": case_id,      # Store tenant info in metadata
                        "document_id": document_id,
                        "graph_id": graph_id,
                        "extraction_method": extraction_method
                    }
                }

                # Add required fields for graph.edges table
                edge_record["edge_id"] = f"{graph_id}_edge_{i:04d}"
                edge_record["relationship_type"] = relationship_type_val
                edge_record["confidence_score"] = confidence_val

                edge_records.append(edge_record)

            # Batch upsert edges with validation (idempotent for re-runs)
            await self._log_step("upserting_edges", {"count": len(edge_records)})
            result = await self.supabase_client.upsert(
                "graph.edges",
                edge_records,
                on_conflict="edge_id",
                admin_operation=True
            )

            # CRITICAL FIX: Validate result and fail fast
            if result is None:
                raise Exception(f"Failed to insert {len(edge_records)} edges: Supabase returned None")
            elif len(result) == 0:
                raise Exception(f"Failed to insert {len(edge_records)} edges: Supabase returned empty result")
            elif len(result) != len(edge_records):
                raise Exception(f"Partial insert failure: Expected {len(edge_records)} edges, got {len(result)}")

            storage_info["edges_created"] = len(result)
            await self._log_step("edges_inserted", {"count": len(result)})
            
        # Store communities in graph.communities with tenant info in metadata
        if communities:
            community_records = []
            for community in communities:
                community_records.append({
                    "community_id": community["community_id"],
                    "title": community.get("title", f"Community {community['community_id']}"),
                    "summary": community.get("ai_summary", community.get("description", "")),
                    "level": 0,
                    "node_count": len(community.get("entity_ids", [])),
                    "edge_count": 0,  # Will be updated later if needed
                    "coherence_score": community.get("coherence_score", 0),
                    "metadata": {
                        "client_id": client_id,  # Store tenant info in metadata
                        "case_id": case_id,      # Store tenant info in metadata
                        "document_id": document_id,
                        "graph_id": graph_id
                    }
                })

            # Batch upsert communities with validation (idempotent for re-runs)
            await self._log_step("upserting_communities", {"count": len(community_records)})
            result = await self.supabase_client.upsert(
                "graph.communities",
                community_records,
                on_conflict="community_id",
                admin_operation=True
            )

            # CRITICAL FIX: Validate result and fail fast
            if result is None:
                raise Exception(f"Failed to insert {len(community_records)} communities: Supabase returned None")
            elif len(result) == 0:
                raise Exception(f"Failed to insert {len(community_records)} communities: Supabase returned empty result")
            elif len(result) != len(community_records):
                raise Exception(f"Partial insert failure: Expected {len(community_records)} communities, got {len(result)}")

            storage_info["communities_detected"] = len(result)
            await self._log_step("communities_inserted", {"count": len(result)})

            # Store node-community memberships
            membership_records = []
            for community in communities:
                for entity_id in community.get("entity_ids", []):
                    membership_records.append({
                        "node_id": entity_id,
                        "community_id": community["community_id"],
                        "membership_strength": 1.0
                    })

            if membership_records:
                await self._log_step("inserting_memberships", {"count": len(membership_records)})
                try:
                    membership_result = await self.supabase_client.insert(
                        "graph.node_communities",
                        membership_records,
                        admin_operation=True
                    )

                    # Validate membership inserts
                    if membership_result is None or len(membership_result) == 0:
                        await self._log_error(f"WARNING: Failed to insert {len(membership_records)} community memberships - table may not be exposed via REST API")
                        storage_info["membership_warning"] = "Failed to insert community memberships"
                    else:
                        await self._log_step("memberships_inserted", {"count": len(membership_result)})
                except Exception as e:
                    # Don't fail entire graph construction if membership table has issues
                    await self._log_error(f"WARNING: Community membership insert failed (non-critical): {str(e)}")
                    storage_info["membership_warning"] = f"Membership insert failed: {str(e)}"

            # Store chunk-entity connections with relevance scoring
            if enhanced_chunks:
                chunk_connections_stored = await self._create_chunk_entity_connections(
                    enhanced_chunks,
                    entities,
                    document_id
                )
                storage_info["chunk_connections_stored"] = chunk_connections_stored
            else:
                storage_info["chunk_connections_stored"] = 0

            # Store chunk cross-references (citations and semantic similarity)
            chunk_cross_refs_stored = await self._create_chunk_cross_references(
                enhanced_chunks,
                entities,
                citations,
                document_id
            )
            storage_info["chunk_cross_references_stored"] = chunk_cross_refs_stored

        # Update document registry with backward compatibility
        try:
            # Try new column name first
            await self.supabase_client.update(
                "graph.document_registry",
                {"processing_status": "graph_completed", "updated_at": datetime.utcnow().isoformat()},
                {"document_id": document_id},
                admin_operation=True
            )
        except Exception as e:
            # Fallback to old column name if processing_status doesn't exist
            if "processing_status" in str(e):
                await self.supabase_client.update(
                    "graph.document_registry",
                    {"status": "completed", "updated_at": datetime.utcnow().isoformat()},
                    {"document_id": document_id},
                    admin_operation=True
                )
            else:
                raise

        # CRITICAL FIX: Removed outer try-except that was swallowing ALL exceptions
        # Old code had try-except wrapping the entire method, catching errors but
        # still returning storage_info with success = True
        # Now exceptions propagate properly to construct_graph() which handles them correctly

        return storage_info

    async def _create_chunk_entity_connections(self,
                                              chunks: List[Dict[str, Any]],
                                              entities: List[Dict[str, Any]],
                                              document_id: str) -> int:
        """
        Create bidirectional chunk-entity connections with relevance scoring.

        This method links chunks to entities based on entity occurrences within chunk content,
        calculating relevance scores based on frequency, position, and confidence.

        Args:
            chunks: List of enhanced chunk dictionaries with content and metadata
            entities: List of entity dictionaries with entity_id, entity_text, and confidence
            document_id: Document identifier for logging

        Returns:
            Number of connections created

        Relevance Score Calculation:
            - Entity frequency in chunk (weight: 0.5)
            - Position in chunk - earlier mentions score higher (weight: 0.3)
            - Entity confidence score (weight: 0.2)

        Only creates connections where relevance_score >= 0.5
        """
        if not chunks or not entities:
            await self._log_step(
                "chunk_entity_connections",
                {"status": "skipped", "reason": "no_chunks_or_entities"}
            )
            return 0

        try:
            connection_records = []

            # Create entity lookup map for efficient access
            entity_map = {e["entity_id"]: e for e in entities}

            # Process each chunk
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id")
                chunk_content = chunk.get("content", "").lower()
                chunk_length = len(chunk_content)

                if not chunk_id or not chunk_content:
                    continue

                # Track entities found in this chunk
                chunk_entities = {}

                # Find all entities mentioned in this chunk
                for entity in entities:
                    entity_id = entity["entity_id"]
                    entity_text = entity.get("entity_text", "").lower()
                    entity_confidence = entity.get("confidence", 0.95)

                    if not entity_text:
                        continue

                    # Find all occurrences of entity in chunk
                    occurrences = []
                    start_pos = 0

                    while True:
                        pos = chunk_content.find(entity_text, start_pos)
                        if pos == -1:
                            break
                        occurrences.append(pos)
                        start_pos = pos + 1

                    # If entity found in chunk, calculate relevance
                    if occurrences:
                        # Calculate frequency score (0-1 scale)
                        # Normalize by chunk length and cap at reasonable maximum
                        frequency_count = len(occurrences)
                        max_expected_frequency = 10  # Reasonable cap for normalization
                        frequency_score = min(frequency_count / max_expected_frequency, 1.0)

                        # Calculate position score (earlier = higher)
                        # Use first occurrence position, normalize by chunk length
                        first_position = occurrences[0]
                        if chunk_length > 0:
                            position_score = 1.0 - (first_position / chunk_length)
                        else:
                            position_score = 1.0

                        # Calculate weighted relevance score
                        relevance_score = (
                            (frequency_score * 0.5) +      # Frequency weight: 0.5
                            (position_score * 0.3) +        # Position weight: 0.3
                            (entity_confidence * 0.2)       # Confidence weight: 0.2
                        )

                        # Only create connection if relevance meets threshold
                        if relevance_score >= 0.5:
                            chunk_entities[entity_id] = {
                                "relevance_score": round(relevance_score, 4),
                                "position_in_chunk": first_position,
                                "frequency": frequency_count
                            }

                # Create connection records for this chunk
                for entity_id, metrics in chunk_entities.items():
                    connection_records.append({
                        "chunk_id": chunk_id,
                        "entity_id": entity_id,
                        "relevance_score": metrics["relevance_score"],
                        "position_in_chunk": metrics["position_in_chunk"]
                    })

            # Batch insert all connections
            if connection_records:
                result = await self.supabase_client.insert(
                    "graph.chunk_entity_connections",
                    connection_records,
                    admin_operation=True
                )

                connections_created = len(result) if result else 0

                await self._log_step(
                    "chunk_entity_connections",
                    {
                        "connections_created": connections_created,
                        "chunks_processed": len(chunks),
                        "entities_processed": len(entities),
                        "avg_connections_per_chunk": round(connections_created / len(chunks), 2) if chunks else 0
                    }
                )

                return connections_created
            else:
                await self._log_step(
                    "chunk_entity_connections",
                    {
                        "status": "no_connections",
                        "reason": "no_entities_met_relevance_threshold",
                        "chunks_processed": len(chunks),
                        "entities_processed": len(entities)
                    }
                )
                return 0

        except Exception as e:
            error_msg = f"Failed to create chunk-entity connections: {str(e)}"
            await self._log_error(error_msg, traceback.format_exc())
            # Don't fail the entire graph construction
            return 0

    async def _create_chunk_cross_references(self,
                                            chunks: List[Dict[str, Any]],
                                            entities: List[Dict[str, Any]],
                                            citations: List[Dict[str, Any]],
                                            document_id: str) -> int:
        """
        Create chunk cross-references in graph.chunk_cross_references table.

        Implements two detection strategies:
        1. Citation Detection: If chunk A contains citation text matching entity in chunk B
        2. Semantic Similarity: If chunks have embeddings with cosine similarity >= 0.85

        Args:
            chunks: List of enhanced chunks with content and embeddings
            entities: List of extracted entities
            citations: List of extracted citations
            document_id: Document identifier

        Returns:
            Number of cross-references created
        """
        if not chunks or len(chunks) < 2:
            await self._log_step(
                "chunk_cross_references",
                {"status": "skipped", "reason": "insufficient_chunks", "chunk_count": len(chunks) if chunks else 0}
            )
            return 0

        try:
            import numpy as np
            from numpy.linalg import norm

            reference_records = []

            # Build entity-to-chunks mapping for citation detection
            entity_to_chunks = {}
            for entity in entities:
                entity_id = entity.get("entity_id")
                entity_text = entity.get("entity_text", "").lower()

                if not entity_id or not entity_text:
                    continue

                # Find which chunks contain this entity
                for chunk in chunks:
                    chunk_content = chunk.get("content", "").lower()
                    if entity_text in chunk_content:
                        if entity_id not in entity_to_chunks:
                            entity_to_chunks[entity_id] = []
                        entity_to_chunks[entity_id].append(chunk.get("chunk_id"))

            # Strategy 1: Citation-based cross-references
            citation_refs_count = 0
            for citation in citations:
                citation_text = citation.get("citation_text", "").lower()
                citation_entity_id = citation.get("entity_id")

                if not citation_text or not citation_entity_id:
                    continue

                # Find chunks containing this citation text
                source_chunks = []
                for chunk in chunks:
                    chunk_content = chunk.get("content", "").lower()
                    if citation_text in chunk_content:
                        source_chunks.append(chunk.get("chunk_id"))

                # Find chunks containing the cited entity
                target_chunks = entity_to_chunks.get(citation_entity_id, [])

                # Create cross-references between source and target chunks
                for source_chunk_id in source_chunks:
                    for target_chunk_id in target_chunks:
                        if source_chunk_id != target_chunk_id:
                            # Calculate confidence based on citation quality
                            confidence = citation.get("confidence", 0.85)

                            reference_records.append({
                                "source_chunk_id": source_chunk_id,
                                "target_chunk_id": target_chunk_id,
                                "reference_type": "citation",
                                "confidence_score": round(confidence, 3)
                            })
                            citation_refs_count += 1

            # Strategy 2: Semantic similarity-based cross-references
            # Extract chunks with embeddings
            chunks_with_embeddings = []
            for chunk in chunks:
                embedding = chunk.get("embedding")
                if embedding and isinstance(embedding, list) and len(embedding) > 0:
                    chunks_with_embeddings.append({
                        "chunk_id": chunk.get("chunk_id"),
                        "embedding": np.array(embedding, dtype=float)
                    })

            # Calculate pairwise similarities
            similarity_threshold = 0.85
            similarity_refs_count = 0

            for i, chunk_a in enumerate(chunks_with_embeddings):
                for chunk_b in chunks_with_embeddings[i+1:]:
                    try:
                        # Cosine similarity
                        vec_a = chunk_a["embedding"]
                        vec_b = chunk_b["embedding"]

                        # Handle potential zero vectors
                        norm_a = norm(vec_a)
                        norm_b = norm(vec_b)

                        if norm_a > 0 and norm_b > 0:
                            similarity = np.dot(vec_a, vec_b) / (norm_a * norm_b)

                            if similarity >= similarity_threshold:
                                reference_records.append({
                                    "source_chunk_id": chunk_a["chunk_id"],
                                    "target_chunk_id": chunk_b["chunk_id"],
                                    "reference_type": "similar_topic",
                                    "confidence_score": round(float(similarity), 3)
                                })
                                similarity_refs_count += 1
                    except Exception as e:
                        # Skip this pair if there's an issue with similarity calculation
                        await self._log_error(f"Similarity calculation failed for chunks: {e}")
                        continue

            # Remove duplicates (same source-target-type combination)
            unique_references = {}
            for record in reference_records:
                key = f"{record['source_chunk_id']}_{record['target_chunk_id']}_{record['reference_type']}"
                if key not in unique_references:
                    unique_references[key] = record
                else:
                    # Keep the one with higher confidence
                    if record['confidence_score'] > unique_references[key]['confidence_score']:
                        unique_references[key] = record

            final_records = list(unique_references.values())

            # Batch insert cross-references
            if final_records:
                # Insert in batches to avoid overwhelming database
                batch_size = 100
                total_inserted = 0

                for i in range(0, len(final_records), batch_size):
                    batch = final_records[i:i + batch_size]
                    result = await self.supabase_client.insert(
                        "graph.chunk_cross_references",
                        batch,
                        admin_operation=True
                    )
                    total_inserted += len(result) if result else 0

                await self._log_step(
                    "chunk_cross_references",
                    {
                        "references_created": total_inserted,
                        "citation_refs": citation_refs_count,
                        "similarity_refs": similarity_refs_count,
                        "chunks_with_embeddings": len(chunks_with_embeddings),
                        "total_chunks": len(chunks)
                    }
                )

                return total_inserted
            else:
                await self._log_step(
                    "chunk_cross_references",
                    {
                        "status": "no_references",
                        "reason": "no_citations_or_similar_chunks",
                        "chunks_processed": len(chunks),
                        "citations_processed": len(citations) if citations else 0
                    }
                )
                return 0

        except ImportError as e:
            error_msg = f"Failed to import numpy for similarity calculation: {e}"
            await self._log_error(error_msg, traceback.format_exc())
            return 0
        except Exception as e:
            error_msg = f"Failed to create chunk cross-references: {str(e)}"
            await self._log_error(error_msg, traceback.format_exc())
            # Don't fail the entire graph construction
            return 0

    async def _find_cross_document_links(self,
                                        document_id: str,
                                        entities: List[Dict[str, Any]],
                                        relationships: List[Dict[str, Any]],
                                        client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find links to other documents in the graph database."""
        cross_doc_links = []
        
        try:
            # Get all entities from database to find cross-document connections
            # Uses dedicated client_id column for efficient tenant filtering
            # Build filters for efficient database query
            filters = {"node_type": "entity"}  # Only get entity nodes
            if client_id:
                filters["client_id"] = client_id  # Use dedicated column for tenant filtering

            all_entities = await self.supabase_client.get(
                "graph.nodes",
                filters=filters,
                limit=1000,
                admin_operation=True
            )
            
            if all_entities:
                # Find cross-document entities
                cross_doc_entities = await self.entity_deduplicator.find_cross_document_entities(
                    all_entities
                )
                
                # Identify cross-document links
                documents = await self.supabase_client.get(
                    "graph.document_registry",
                    limit=100,
                    admin_operation=True
                )
                
                if documents:
                    cross_doc_links = await self.relationship_discoverer.identify_cross_document_links(
                        documents,
                        all_entities,
                        relationships
                    )
            
        except Exception as e:
            await self._log_error(f"Failed to find cross-document links: {e}")
        
        return cross_doc_links
    
    async def _store_cross_document_links(self, links: List[Dict[str, Any]]):
        """Store cross-document links in database."""
        if not links:
            return
        
        try:
            link_records = []
            for link in links:
                link_records.append({
                    "source_document_id": link["source_document_id"],
                    "target_document_id": link["target_document_id"],
                    "link_type": link.get("link_type", "GENERAL_REFERENCE"),
                    "shared_entities": link.get("shared_entities", []),
                    "metadata": {
                        "strength": link.get("strength", 0),
                        "created_at": datetime.utcnow().isoformat()
                    }
                })
            
            await self.supabase_client.insert(
                "graph.cross_document_links",
                link_records,
                admin_operation=True
            )
            
        except Exception as e:
            await self._log_error(f"Failed to store cross-document links: {e}")
    
    def _calculate_quality_metrics(self,
                                  entities: List[Dict[str, Any]],
                                  relationships: List[Dict[str, Any]],
                                  communities: List[Dict[str, Any]],
                                  analytics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics."""
        quality = analytics.get("quality_assessment", {}) if analytics else {}
        
        # Add additional quality metrics
        if not quality.get("graph_completeness"):
            if entities and len(entities) > 1:
                max_edges = len(entities) * (len(entities) - 1) / 2
                # Avoid division by zero and set reasonable minimum
                if max_edges > 0:
                    quality["graph_completeness"] = min(len(relationships) / (max_edges * 0.1), 1.0)
                else:
                    quality["graph_completeness"] = 1.0 if len(relationships) == 0 else 0
            elif entities and len(entities) == 1:
                # Single entity with no possible edges - mark as complete
                quality["graph_completeness"] = 1.0
            else:
                quality["graph_completeness"] = 0
        
        if not quality.get("community_coherence"):
            if communities:
                coherences = [c.get("coherence_score", 0) for c in communities]
                quality["community_coherence"] = sum(coherences) / len(coherences) if coherences else 0
            else:
                quality["community_coherence"] = 0
        
        if not quality.get("entity_confidence_avg"):
            confidences = [e.get("confidence", 0.95) for e in entities]
            quality["entity_confidence_avg"] = sum(confidences) / len(confidences) if confidences else 0
        
        if not quality.get("relationship_confidence_avg"):
            rel_confidences = [r.get("confidence", 0.8) for r in relationships]
            quality["relationship_confidence_avg"] = sum(rel_confidences) / len(rel_confidences) if rel_confidences else 0
        
        if not quality.get("coverage_score"):
            if communities and entities:
                covered = set()
                for community in communities:
                    covered.update(community.get("entity_ids", []))
                quality["coverage_score"] = len(covered) / len(entities)
            else:
                quality["coverage_score"] = 0
        
        return quality
    
    def _format_analytics(self, analytics: Dict[str, Any]) -> Dict[str, Any]:
        """Format analytics for response."""
        if not analytics:
            return {}
        
        return {
            "top_entities": analytics.get("top_entities", [])[:10],
            "relationship_types": analytics.get("legal_metrics", {}).get("relationship_type_distribution", {}),
            "cross_document_connections": analytics.get("legal_metrics", {}).get("cross_document_relationships", 0),
            "entity_type_distribution": analytics.get("legal_metrics", {}).get("entity_type_distribution", {}),
            "graph_metrics": analytics.get("basic_metrics", {}),
            "quality_assessment": analytics.get("quality_assessment", {})
        }
    
    async def _log_step(self, step_name: str, metadata: Dict[str, Any]):
        """Log processing step."""
        if self.settings.log_service_url:
            try:
                await self.http_client.post(
                    f"{self.settings.log_service_url}/api/v1/log",
                    json={
                        "service": "graphrag-service",
                        "level": "info",
                        "message": f"GraphRAG step completed: {step_name}",
                        "metadata": metadata
                    }
                )
            except:
                pass  # Don't fail on logging errors
    
    async def _log_error(self, message: str, details: str = ""):
        """Log error message."""
        if self.settings.log_service_url:
            try:
                await self.http_client.post(
                    f"{self.settings.log_service_url}/api/v1/log",
                    json={
                        "service": "graphrag-service",
                        "level": "error",
                        "message": message,
                        "details": details
                    }
                )
            except:
                pass  # Don't fail on logging errors
    
    async def close(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()
        if self.supabase_client:
            await self.supabase_client.close()