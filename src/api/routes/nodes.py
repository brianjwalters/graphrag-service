"""
Node (Entity) API Routes
Direct CRUD operations for graph nodes with tenant isolation
"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ...models.requests import EntityData


router = APIRouter()


@router.get("/")
async def list_nodes(
    req: Request,
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    List nodes with optional filtering.
    
    Supports tenant isolation and type filtering.
    Returns paginated results.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Build filters
        filters = {}
        if client_id:
            filters["client_id"] = client_id
        if case_id:
            filters["case_id"] = case_id
        if node_type:
            filters["node_type"] = node_type
            
        # Query nodes
        nodes = await supabase_client.get(
            "graph.nodes",
            filters=filters,
            limit=limit,
            offset=offset,
            admin_operation=True
        )
        
        # Filter by entity_type if specified (stored in attributes)
        if entity_type and nodes:
            nodes = [n for n in nodes if n.get("attributes", {}).get("entity_type") == entity_type]
        
        return {
            "success": True,
            "count": len(nodes) if nodes else 0,
            "nodes": nodes or [],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(nodes) == limit if nodes else False
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list nodes: {str(e)}")


@router.get("/{node_id}")
async def get_node(
    req: Request,
    node_id: str,
    include_edges: bool = Query(False, description="Include connected edges"),
    include_communities: bool = Query(False, description="Include community memberships")
) -> Dict[str, Any]:
    """
    Get a specific node by ID.
    
    Optionally includes connected edges and community memberships.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Get the node
        nodes = await supabase_client.get(
            "graph.nodes",
            filters={"node_id": node_id},
            limit=1,
            admin_operation=True
        )
        
        if not nodes:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        
        node = nodes[0]
        result = {"node": node}
        
        # Include edges if requested
        if include_edges:
            # Get edges where this node is source or target
            source_edges = await supabase_client.get(
                "graph.edges",
                filters={"source_node_id": node_id},
                admin_operation=True
            )
            
            target_edges = await supabase_client.get(
                "graph.edges",
                filters={"target_node_id": node_id},
                admin_operation=True
            )
            
            result["edges"] = {
                "outgoing": source_edges or [],
                "incoming": target_edges or [],
                "total": len(source_edges or []) + len(target_edges or [])
            }
        
        # Include community memberships if requested
        if include_communities:
            memberships = await supabase_client.get(
                "graph.node_communities",
                filters={"node_id": node_id},
                admin_operation=True
            )
            result["communities"] = memberships or []
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node: {str(e)}")


@router.post("/")
async def create_node(
    req: Request,
    node_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new node.
    
    Requires node_id, label, and node_type.
    Supports tenant isolation via client_id and case_id.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Validate required fields
        if not node_data.get("node_id"):
            node_data["node_id"] = f"node_{uuid.uuid4().hex[:8]}"
        
        if not node_data.get("label"):
            raise HTTPException(status_code=400, detail="Node label is required")
        
        # Set defaults
        node_data.setdefault("node_type", "entity")
        node_data.setdefault("importance_score", 0.5)
        node_data.setdefault("attributes", {})
        
        # Insert node
        result = await supabase_client.insert(
            "graph.nodes",
            node_data,
            admin_operation=True
        )
        
        return {
            "success": True,
            "node": result[0] if result else node_data,
            "message": f"Node {node_data['node_id']} created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create node: {str(e)}")


@router.put("/{node_id}")
async def update_node(
    req: Request,
    node_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing node.
    
    Partial updates supported - only provided fields are updated.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Check if node exists
        existing = await supabase_client.get(
            "graph.nodes",
            filters={"node_id": node_id},
            limit=1,
            admin_operation=True
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        
        # Update node
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        result = await supabase_client.update(
            "graph.nodes",
            updates,
            {"node_id": node_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "node": result[0] if result else updates,
            "message": f"Node {node_id} updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update node: {str(e)}")


@router.delete("/{node_id}")
async def delete_node(
    req: Request,
    node_id: str,
    cascade: bool = Query(False, description="Delete connected edges and memberships")
) -> Dict[str, Any]:
    """
    Delete a node.
    
    If cascade=true, also deletes connected edges and community memberships.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Check if node exists
        existing = await supabase_client.get(
            "graph.nodes",
            filters={"node_id": node_id},
            limit=1,
            admin_operation=True
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        
        deleted_items = {"node": 1, "edges": 0, "memberships": 0}
        
        if cascade:
            # Delete edges
            source_edges = await supabase_client.delete(
                "graph.edges",
                {"source_node_id": node_id},
                admin_operation=True
            )
            
            target_edges = await supabase_client.delete(
                "graph.edges",
                {"target_node_id": node_id},
                admin_operation=True
            )
            
            deleted_items["edges"] = len(source_edges or []) + len(target_edges or [])
            
            # Delete community memberships
            memberships = await supabase_client.delete(
                "graph.node_communities",
                {"node_id": node_id},
                admin_operation=True
            )
            
            deleted_items["memberships"] = len(memberships or [])
        
        # Delete the node
        await supabase_client.delete(
            "graph.nodes",
            {"node_id": node_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "message": f"Node {node_id} deleted successfully",
            "deleted": deleted_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete node: {str(e)}")


@router.post("/batch")
async def batch_create_nodes(
    req: Request,
    nodes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create multiple nodes in a single operation.
    
    More efficient than individual creates.
    Supports up to 1000 nodes per batch.
    """
    try:
        if len(nodes) > 1000:
            raise HTTPException(status_code=400, detail="Maximum 1000 nodes per batch")
        
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Prepare nodes
        for node in nodes:
            if not node.get("node_id"):
                node["node_id"] = f"node_{uuid.uuid4().hex[:8]}"
            node.setdefault("node_type", "entity")
            node.setdefault("importance_score", 0.5)
            node.setdefault("attributes", {})
        
        # Batch insert
        result = await supabase_client.insert(
            "graph.nodes",
            nodes,
            admin_operation=True
        )
        
        return {
            "success": True,
            "created": len(result) if result else 0,
            "nodes": result or nodes,
            "message": f"Created {len(result) if result else 0} nodes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to batch create nodes: {str(e)}")


@router.post("/search")
async def search_nodes(
    req: Request,
    query: str,
    client_id: Optional[str] = None,
    case_id: Optional[str] = None,
    search_fields: List[str] = Query(default=["label", "description"]),
    limit: int = Query(50, ge=1, le=500)
) -> Dict[str, Any]:
    """
    Search nodes by text query.
    
    Searches in label and description fields by default.
    Supports tenant filtering.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Build base filters for tenant isolation
        filters = {}
        if client_id:
            filters["client_id"] = client_id
        if case_id:
            filters["case_id"] = case_id
        
        # Get all nodes with filters
        all_nodes = await supabase_client.get(
            "graph.nodes",
            filters=filters,
            limit=1000,  # Get more for searching
            admin_operation=True
        )
        
        if not all_nodes:
            return {
                "success": True,
                "query": query,
                "results": [],
                "count": 0
            }
        
        # Search in specified fields
        query_lower = query.lower()
        results = []
        
        for node in all_nodes:
            match = False
            
            # Search in each specified field
            for field in search_fields:
                if field == "label" and query_lower in str(node.get("label", "")).lower():
                    match = True
                    break
                elif field == "description" and query_lower in str(node.get("description", "")).lower():
                    match = True
                    break
                elif field == "attributes":
                    # Search in attributes JSON
                    attr_str = str(node.get("attributes", {})).lower()
                    if query_lower in attr_str:
                        match = True
                        break
            
            if match:
                results.append(node)
            
            if len(results) >= limit:
                break
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
            "search_fields": search_fields
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search nodes: {str(e)}")