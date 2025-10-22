"""
Entity Upsert API Routes
Intelligent entity deduplication and upsert operations for graph.nodes table
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, List, Optional
import time
import hashlib
import asyncio
from datetime import datetime

from ...models.entity_models import (
    EntityUpsertRequest,
    EntityUpsertResponse,
    BatchEntityUpsertRequest,
    BatchEntityUpsertResponse,
    EntitySearchRequest,
    EntitySearchResponse,
    EntityCheckRequest,
    EntityCheckResponse
)


router = APIRouter()


def generate_entity_id(entity_text: str, entity_type: str) -> str:
    """
    Generate MD5-based entity ID from text and type.

    This creates a deterministic identifier that enables exact match detection.
    Same text + type = same entity_id = deduplication.

    Args:
        entity_text: Entity text (normalized to lowercase)
        entity_type: Entity type (normalized to uppercase)

    Returns:
        Entity ID in format: entity_{md5_hash}

    Example:
        generate_entity_id("Supreme Court", "COURT")
        → "entity_a1b2c3d4e5f6"
    """
    # Normalize inputs for consistent hashing
    normalized_text = entity_text.lower().strip()
    normalized_type = entity_type.upper().strip()

    # Create combined string for hashing
    combined = f"{normalized_type}:{normalized_text}"

    # Generate MD5 hash (first 16 characters for brevity)
    hash_value = hashlib.md5(combined.encode()).hexdigest()[:16]

    return f"entity_{hash_value}"


def get_entity_description(entity_type: str, entity_text: str) -> str:
    """
    Get contextual description for entity based on type.

    Reuses the description logic from graph_constructor for consistency.

    Args:
        entity_type: Entity type (e.g., "COURT", "PERSON")
        entity_text: Entity text for fallback

    Returns:
        Human-readable entity description
    """
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
        "LEGAL_MARKER": "Legal indicator or reference",
        "PERSON": "Individual",
        "ORGANIZATION": "Legal entity or organization",
        "LOCATION": "Geographic location",
        "UNKNOWN": "Entity"
    }

    return descriptions.get(entity_type, entity_type.replace("_", " ").title())


async def semantic_similarity_search(
    supabase_client,
    embedding: List[float],
    entity_type: str,
    threshold: float = 0.85,
    client_id: Optional[str] = None,
    case_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Search for semantically similar entities using vector similarity.

    Uses cosine similarity with Jina Embeddings v4 (2048-dim vectors).

    Args:
        supabase_client: SupabaseClient instance
        embedding: Query embedding vector (2048-dim)
        entity_type: Entity type for filtering
        threshold: Similarity threshold (default: 0.85)
        client_id: Optional client ID for tenant filtering
        case_id: Optional case ID for filtering

    Returns:
        Most similar entity dict or None if no match above threshold
    """
    if not embedding or len(embedding) == 0:
        return None

    try:
        # Build RPC params for vector similarity search
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": 5,  # Get top 5 for entity_type filtering
            "entity_type_filter": entity_type  # Filter by same type only
        }

        # Add tenant filters if provided
        if client_id:
            rpc_params["client_id_filter"] = client_id
        if case_id:
            rpc_params["case_id_filter"] = case_id

        # Call database function for vector similarity search
        # This assumes existence of a `search_similar_entities` function
        try:
            results = await supabase_client.rpc(
                "search_similar_entities",
                rpc_params,
                admin_operation=True
            )

            if results and len(results) > 0:
                # Return the most similar entity
                return results[0]
        except Exception as rpc_error:
            # RPC function might not exist - fallback to manual search
            print(f"[INFO] RPC search_similar_entities not available: {rpc_error}")
            return None

    except Exception as e:
        print(f"[ERROR] Semantic similarity search failed: {e}")
        return None

    return None


async def merge_entities(
    supabase_client,
    canonical_node: Dict[str, Any],
    new_entity: EntityUpsertRequest,
    similarity_score: float
) -> Dict[str, Any]:
    """
    Merge new entity data with existing canonical entity.

    Updates:
    - Document tracking (add new document_ids)
    - Metadata enrichment
    - Confidence adjustment

    Args:
        supabase_client: SupabaseClient instance
        canonical_node: Existing canonical entity (node) from database
        new_entity: New entity data to merge
        similarity_score: Semantic similarity score

    Returns:
        Updated node data after merge
    """
    node_id = canonical_node["node_id"]

    # Extract existing metadata
    existing_metadata = canonical_node.get("metadata", {})

    # Track document IDs (merge without duplicates)
    existing_doc_ids = existing_metadata.get("document_ids", [])
    new_doc_ids = new_entity.document_ids or []
    merged_doc_ids = list(set(existing_doc_ids + new_doc_ids))

    # Update metadata with merge information
    updated_metadata = {
        **existing_metadata,
        "document_ids": merged_doc_ids,
        "last_merge_date": datetime.utcnow().isoformat(),
        "merge_count": existing_metadata.get("merge_count", 0) + 1,
        "last_merge_similarity": similarity_score,
        "last_merge_source": new_entity.source_chunk_id
    }

    # Merge attributes (new attributes augment existing)
    if new_entity.attributes:
        existing_attrs = existing_metadata.get("attributes", {})
        updated_metadata["attributes"] = {**existing_attrs, **new_entity.attributes}

    # Update confidence (take maximum)
    existing_confidence = existing_metadata.get("confidence", 0.95)
    new_confidence = new_entity.confidence or 0.95
    updated_metadata["confidence"] = max(existing_confidence, new_confidence)

    # Update node in database
    update_data = {
        "metadata": updated_metadata,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Update the node
    result = await supabase_client.update(
        "graph.nodes",
        update_data,
        {"node_id": node_id},
        admin_operation=True
    )

    if result and len(result) > 0:
        return result[0]
    else:
        # Return original with updates applied
        return {**canonical_node, **update_data}


@router.post("/upsert", response_model=EntityUpsertResponse)
async def upsert_entity(
    req: Request,
    entity: EntityUpsertRequest
) -> EntityUpsertResponse:
    """
    Intelligent entity upsert with automatic deduplication.

    **Deduplication Strategy:**
    1. **Exact Match**: Check for existing entity with same entity_id (MD5 hash)
    2. **Semantic Match**: If no exact match, search for similar entities using embedding
    3. **Create New**: If no matches found, create new entity

    **Entity Merging:**
    - When similar entity found (similarity >= 0.85), merge with canonical entity
    - Document tracking updated to include all documents
    - Metadata and attributes merged

    **Response Actions:**
    - `created`: New entity created
    - `updated`: Existing entity updated (exact match)
    - `merged`: Entity merged with similar existing entity (semantic match)

    **Performance:**
    - Exact match: < 50ms
    - Semantic match: < 150ms (with embedding)
    - Creation: < 100ms
    """
    start_time = time.time()

    try:
        supabase_client = req.app.state.graph_constructor.supabase_client

        # Step 1: Generate entity_id (MD5 hash)
        entity_id = generate_entity_id(entity.entity_text, entity.entity_type)

        # Step 2: Check for exact match by entity_id
        existing_nodes = await supabase_client.get(
            "graph.nodes",
            filters={"node_id": entity_id},
            limit=1,
            admin_operation=True
        )

        # If exact match found, update and return
        if existing_nodes and len(existing_nodes) > 0:
            existing_node = existing_nodes[0]

            # Update document tracking
            existing_metadata = existing_node.get("metadata", {})
            existing_doc_ids = existing_metadata.get("document_ids", [])
            new_doc_ids = entity.document_ids or []
            merged_doc_ids = list(set(existing_doc_ids + new_doc_ids))

            # Update metadata
            updated_metadata = {
                **existing_metadata,
                "document_ids": merged_doc_ids,
                "last_updated": datetime.utcnow().isoformat()
            }

            if entity.attributes:
                existing_attrs = existing_metadata.get("attributes", {})
                updated_metadata["attributes"] = {**existing_attrs, **entity.attributes}

            # Update node
            update_data = {
                "metadata": updated_metadata,
                "updated_at": datetime.utcnow().isoformat()
            }

            result = await supabase_client.update(
                "graph.nodes",
                update_data,
                {"node_id": entity_id},
                admin_operation=True
            )

            updated_node = result[0] if result and len(result) > 0 else {**existing_node, **update_data}

            processing_time = (time.time() - start_time) * 1000

            return EntityUpsertResponse(
                success=True,
                action="updated",
                node_id=entity_id,
                entity_text=entity.entity_text,
                entity_type=entity.entity_type,
                merged_with=None,
                similarity_score=None,
                document_ids=merged_doc_ids,
                document_count=len(merged_doc_ids),
                node_data=updated_node,
                processing_time_ms=round(processing_time, 2),
                warnings=[]
            )

        # Step 3: No exact match - check semantic similarity (if embedding provided)
        similar_entity = None
        similarity_score = None

        if entity.embedding and len(entity.embedding) > 0:
            similar_entity = await semantic_similarity_search(
                supabase_client,
                entity.embedding,
                entity.entity_type,
                threshold=0.85,
                client_id=entity.client_id,
                case_id=entity.case_id
            )

            if similar_entity:
                similarity_score = similar_entity.get("similarity", 0.85)

        # Step 4: If similar entity found, merge
        if similar_entity:
            merged_node = await merge_entities(
                supabase_client,
                similar_entity,
                entity,
                similarity_score
            )

            merged_metadata = merged_node.get("metadata", {})
            merged_doc_ids = merged_metadata.get("document_ids", [])

            processing_time = (time.time() - start_time) * 1000

            return EntityUpsertResponse(
                success=True,
                action="merged",
                node_id=merged_node["node_id"],
                entity_text=entity.entity_text,
                entity_type=entity.entity_type,
                merged_with=similar_entity["node_id"],
                similarity_score=round(similarity_score, 4),
                document_ids=merged_doc_ids,
                document_count=len(merged_doc_ids),
                node_data=merged_node,
                processing_time_ms=round(processing_time, 2),
                warnings=[f"Merged with similar entity (similarity: {round(similarity_score, 2)})"]
            )

        # Step 5: No matches found - create new entity
        new_node_data = {
            "node_id": entity_id,
            "node_type": "entity",
            "title": entity.entity_text,
            "description": get_entity_description(entity.entity_type, entity.entity_text),
            "source_id": entity.document_ids[0] if entity.document_ids else None,
            "source_type": "document",
            "metadata": {
                "entity_type": entity.entity_type,
                "confidence": entity.confidence or 0.95,
                "attributes": entity.attributes or {},
                "document_ids": entity.document_ids or [],
                "source_chunk_id": entity.source_chunk_id,
                "client_id": entity.client_id,
                "case_id": entity.case_id,
                "created_date": datetime.utcnow().isoformat(),
                **(entity.metadata or {})
            }
        }

        # Add embedding if provided
        if entity.embedding and len(entity.embedding) > 0:
            new_node_data["embedding"] = entity.embedding

        # Insert new node
        result = await supabase_client.insert(
            "graph.nodes",
            new_node_data,
            admin_operation=True
        )

        created_node = result[0] if result and len(result) > 0 else new_node_data

        processing_time = (time.time() - start_time) * 1000

        return EntityUpsertResponse(
            success=True,
            action="created",
            node_id=entity_id,
            entity_text=entity.entity_text,
            entity_type=entity.entity_type,
            merged_with=None,
            similarity_score=None,
            document_ids=entity.document_ids or [],
            document_count=len(entity.document_ids or []),
            node_data=created_node,
            processing_time_ms=round(processing_time, 2),
            warnings=[]
        )

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        raise HTTPException(
            status_code=500,
            detail=f"Entity upsert failed: {str(e)} (processing_time: {round(processing_time, 2)}ms)"
        )


@router.get("/{entity_id}", response_model=Dict[str, Any])
async def get_entity(
    req: Request,
    entity_id: str
) -> Dict[str, Any]:
    """
    Retrieve entity details by entity_id (node_id).

    Returns complete node record including:
    - Entity text and type
    - Document tracking information
    - Metadata and attributes
    - Relationships (if requested)
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client

        # Get entity node
        nodes = await supabase_client.get(
            "graph.nodes",
            filters={"node_id": entity_id},
            limit=1,
            admin_operation=True
        )

        if not nodes or len(nodes) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Entity {entity_id} not found"
            )

        node = nodes[0]

        # Enrich with document count
        metadata = node.get("metadata", {})
        document_ids = metadata.get("document_ids", [])

        return {
            "success": True,
            "entity": node,
            "document_count": len(document_ids),
            "document_ids": document_ids
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve entity: {str(e)}"
        )


@router.post("/search", response_model=EntitySearchResponse)
async def search_entities(
    req: Request,
    search_req: EntitySearchRequest
) -> EntitySearchResponse:
    """
    Search entities by text query with tenant filtering.

    **Search Modes:**
    - **Fuzzy Search** (default): Partial text matching in entity title
    - **Exact Match**: Exact text matching (case-insensitive)

    **Filtering:**
    - Entity types (e.g., ["COURT", "JUDGE"])
    - Client ID (tenant isolation)
    - Case ID (case-specific entities)
    - Public entities (client_id is NULL)

    **Pagination:**
    - Supports limit/offset for large result sets
    - Returns `has_more` indicator
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client

        # Build filters
        filters = {"node_type": "entity"}

        # Tenant filtering
        if search_req.client_id:
            filters["client_id"] = search_req.client_id
        if search_req.case_id:
            filters["case_id"] = search_req.case_id

        # Get all matching nodes (we'll filter by text afterward)
        all_nodes = await supabase_client.get(
            "graph.nodes",
            filters=filters,
            limit=1000,  # Get large batch for text filtering
            admin_operation=True
        )

        if not all_nodes:
            return EntitySearchResponse(
                success=True,
                query=search_req.query,
                results=[],
                count=0,
                total_count=0,
                has_more=False,
                offset=search_req.offset,
                limit=search_req.limit
            )

        # Filter by entity types if specified
        if search_req.entity_types:
            all_nodes = [
                node for node in all_nodes
                if node.get("metadata", {}).get("entity_type") in search_req.entity_types
            ]

        # Text search filtering
        query_lower = search_req.query.lower()
        matching_nodes = []

        for node in all_nodes:
            title = node.get("title", "").lower()
            description = node.get("description", "").lower()

            if search_req.exact_match:
                if title == query_lower:
                    matching_nodes.append(node)
            else:
                if query_lower in title or query_lower in description:
                    matching_nodes.append(node)

        # Apply pagination
        total_count = len(matching_nodes)
        start_idx = search_req.offset
        end_idx = start_idx + search_req.limit
        paginated_results = matching_nodes[start_idx:end_idx]

        return EntitySearchResponse(
            success=True,
            query=search_req.query,
            results=paginated_results,
            count=len(paginated_results),
            total_count=total_count,
            has_more=end_idx < total_count,
            offset=search_req.offset,
            limit=search_req.limit
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Entity search failed: {str(e)}"
        )


@router.post("/check", response_model=EntityCheckResponse)
async def check_entities(
    req: Request,
    check_req: EntityCheckRequest
) -> EntityCheckResponse:
    """
    Batch check entity existence.

    Efficiently check if multiple entities exist in the database
    without creating them. Useful for:
    - Pre-validation before batch upsert
    - Deduplication checks
    - Entity resolution

    **Returns:**
    - Entities that exist (with node_id and complete data)
    - Entities that don't exist (with computed entity_id for reference)
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client

        exists_list = []
        missing_list = []

        # Check each entity
        for entity_data in check_req.entities:
            entity_text = entity_data.get("entity_text")
            entity_type = entity_data.get("entity_type")

            if not entity_text or not entity_type:
                continue

            # Generate entity_id
            entity_id = generate_entity_id(entity_text, entity_type)

            # Check if exists
            nodes = await supabase_client.get(
                "graph.nodes",
                filters={"node_id": entity_id},
                limit=1,
                admin_operation=True
            )

            if nodes and len(nodes) > 0:
                node = nodes[0]
                exists_list.append({
                    "entity_text": entity_text,
                    "entity_type": entity_type,
                    "node_id": entity_id,
                    "exists": True,
                    "node_data": node
                })
            else:
                missing_list.append({
                    "entity_text": entity_text,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "exists": False
                })

        return EntityCheckResponse(
            success=True,
            total_checked=len(check_req.entities),
            exists=exists_list,
            missing=missing_list,
            exists_count=len(exists_list),
            missing_count=len(missing_list)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Entity check failed: {str(e)}"
        )


@router.post("/batch-upsert", response_model=BatchEntityUpsertResponse)
async def batch_upsert_entities(
    req: Request,
    batch_req: BatchEntityUpsertRequest
) -> BatchEntityUpsertResponse:
    """
    Batch entity upsert with within-batch deduplication.

    Efficiently upsert multiple entities with:
    - Within-batch deduplication (optional)
    - Concurrent processing (configurable)
    - Detailed per-entity results

    **Performance:**
    - Processes up to 100 entities per batch
    - Concurrent processing (default: 10 concurrent operations)
    - Total time scales with batch size and deduplication complexity
    """
    start_time = time.time()

    try:
        # Deduplicate within batch if requested
        entities_to_process = batch_req.entities
        within_batch_duplicates = 0

        if batch_req.deduplicate_within_batch:
            # Use entity_id as deduplication key
            seen_entity_ids = set()
            deduplicated_entities = []

            for entity in batch_req.entities:
                entity_id = generate_entity_id(entity.entity_text, entity.entity_type)
                if entity_id not in seen_entity_ids:
                    seen_entity_ids.add(entity_id)
                    deduplicated_entities.append(entity)
                else:
                    within_batch_duplicates += 1

            entities_to_process = deduplicated_entities

        # Process entities concurrently with limit
        semaphore = asyncio.Semaphore(batch_req.max_concurrent)

        async def process_entity(entity: EntityUpsertRequest) -> EntityUpsertResponse:
            async with semaphore:
                return await upsert_entity(req, entity)

        # Create tasks
        tasks = [process_entity(entity) for entity in entities_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Categorize results
        successful_results = []
        errors = []
        created_count = 0
        updated_count = 0
        merged_count = 0
        failed_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                errors.append({
                    "entity_index": i,
                    "entity_text": entities_to_process[i].entity_text,
                    "error": str(result)
                })
            else:
                successful_results.append(result)
                if result.action == "created":
                    created_count += 1
                elif result.action == "updated":
                    updated_count += 1
                elif result.action == "merged":
                    merged_count += 1

        total_processing_time = (time.time() - start_time) * 1000

        return BatchEntityUpsertResponse(
            success=failed_count == 0,
            total_entities=len(batch_req.entities),
            created_count=created_count,
            updated_count=updated_count,
            merged_count=merged_count,
            failed_count=failed_count,
            results=successful_results,
            errors=errors,
            total_processing_time_ms=round(total_processing_time, 2),
            within_batch_duplicates=within_batch_duplicates
        )

    except Exception as e:
        total_processing_time = (time.time() - start_time) * 1000
        raise HTTPException(
            status_code=500,
            detail=f"Batch upsert failed: {str(e)} (processing_time: {round(total_processing_time, 2)}ms)"
        )
