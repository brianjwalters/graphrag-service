"""
Edge (Relationship) API Routes
Direct CRUD operations for graph edges with tenant isolation
"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Dict, Any, List, Optional
from datetime import datetime


router = APIRouter()


@router.get("/")
async def list_edges(
    req: Request,
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    edge_type: Optional[str] = Query(None, description="Filter by edge type"),
    source_node_id: Optional[str] = Query(None, description="Filter by source node"),
    target_node_id: Optional[str] = Query(None, description="Filter by target node"),
    min_weight: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    List edges with optional filtering.
    
    Supports tenant isolation and various filters.
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
        if edge_type:
            filters["edge_type"] = edge_type
        if source_node_id:
            filters["source_node_id"] = source_node_id
        if target_node_id:
            filters["target_node_id"] = target_node_id
            
        # Query edges
        edges = await supabase_client.get(
            "graph.edges",
            filters=filters,
            limit=limit,
            offset=offset,
            admin_operation=True
        )
        
        # Filter by weight if specified
        if min_weight is not None and edges:
            edges = [e for e in edges if e.get("weight", 0) >= min_weight]
        
        return {
            "success": True,
            "count": len(edges) if edges else 0,
            "edges": edges or [],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(edges) == limit if edges else False
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list edges: {str(e)}")


@router.get("/{edge_id}")
async def get_edge(
    req: Request,
    edge_id: str,
    include_nodes: bool = Query(False, description="Include connected node details")
) -> Dict[str, Any]:
    """
    Get a specific edge by ID.
    
    Optionally includes details of connected nodes.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Get the edge
        edges = await supabase_client.get(
            "graph.edges",
            filters={"id": edge_id},
            limit=1,
            admin_operation=True
        )
        
        if not edges:
            raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found")
        
        edge = edges[0]
        result = {"edge": edge}
        
        # Include node details if requested
        if include_nodes:
            # Get source node
            source_nodes = await supabase_client.get(
                "graph.nodes",
                filters={"node_id": edge["source_node_id"]},
                limit=1,
                admin_operation=True
            )
            
            # Get target node
            target_nodes = await supabase_client.get(
                "graph.nodes",
                filters={"node_id": edge["target_node_id"]},
                limit=1,
                admin_operation=True
            )
            
            result["nodes"] = {
                "source": source_nodes[0] if source_nodes else None,
                "target": target_nodes[0] if target_nodes else None
            }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get edge: {str(e)}")


@router.post("/")
async def create_edge(
    req: Request,
    edge_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new edge between two nodes.
    
    Requires source_node_id and target_node_id.
    Validates that both nodes exist.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Validate required fields
        if not edge_data.get("source_node_id"):
            raise HTTPException(status_code=400, detail="source_node_id is required")
        if not edge_data.get("target_node_id"):
            raise HTTPException(status_code=400, detail="target_node_id is required")
        
        # Verify nodes exist
        source_nodes = await supabase_client.get(
            "graph.nodes",
            filters={"node_id": edge_data["source_node_id"]},
            limit=1,
            admin_operation=True
        )
        
        if not source_nodes:
            raise HTTPException(status_code=404, detail=f"Source node {edge_data['source_node_id']} not found")
        
        target_nodes = await supabase_client.get(
            "graph.nodes",
            filters={"node_id": edge_data["target_node_id"]},
            limit=1,
            admin_operation=True
        )
        
        if not target_nodes:
            raise HTTPException(status_code=404, detail=f"Target node {edge_data['target_node_id']} not found")
        
        # Inherit tenant context from source node if not provided
        if not edge_data.get("client_id"):
            edge_data["client_id"] = source_nodes[0].get("client_id")
        if not edge_data.get("case_id"):
            edge_data["case_id"] = source_nodes[0].get("case_id")
        
        # Set defaults
        edge_data.setdefault("edge_type", "RELATED_TO")
        edge_data.setdefault("weight", 0.5)
        edge_data.setdefault("evidence", "")
        
        # Insert edge
        result = await supabase_client.insert(
            "graph.edges",
            edge_data,
            admin_operation=True
        )
        
        return {
            "success": True,
            "edge": result[0] if result else edge_data,
            "message": f"Edge created between {edge_data['source_node_id']} and {edge_data['target_node_id']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create edge: {str(e)}")


@router.put("/{edge_id}")
async def update_edge(
    req: Request,
    edge_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing edge.
    
    Can update weight, type, evidence, etc.
    Cannot change source or target nodes.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Check if edge exists
        existing = await supabase_client.get(
            "graph.edges",
            filters={"id": edge_id},
            limit=1,
            admin_operation=True
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found")
        
        # Don't allow changing source/target nodes
        updates.pop("source_node_id", None)
        updates.pop("target_node_id", None)
        
        # Update edge
        result = await supabase_client.update(
            "graph.edges",
            updates,
            {"id": edge_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "edge": result[0] if result else updates,
            "message": f"Edge {edge_id} updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update edge: {str(e)}")


@router.delete("/{edge_id}")
async def delete_edge(
    req: Request,
    edge_id: str
) -> Dict[str, Any]:
    """
    Delete an edge.
    
    Does not affect connected nodes.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Check if edge exists
        existing = await supabase_client.get(
            "graph.edges",
            filters={"id": edge_id},
            limit=1,
            admin_operation=True
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found")
        
        # Delete the edge
        await supabase_client.delete(
            "graph.edges",
            {"id": edge_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "message": f"Edge {edge_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete edge: {str(e)}")


@router.post("/batch")
async def batch_create_edges(
    req: Request,
    edges: List[Dict[str, Any]],
    validate_nodes: bool = Query(True, description="Validate that all nodes exist")
) -> Dict[str, Any]:
    """
    Create multiple edges in a single operation.
    
    More efficient than individual creates.
    Supports up to 1000 edges per batch.
    """
    try:
        if len(edges) > 1000:
            raise HTTPException(status_code=400, detail="Maximum 1000 edges per batch")
        
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Validate nodes if requested
        if validate_nodes:
            # Collect all unique node IDs
            node_ids = set()
            for edge in edges:
                node_ids.add(edge.get("source_node_id"))
                node_ids.add(edge.get("target_node_id"))
            
            # Query all nodes at once
            existing_nodes = await supabase_client.get(
                "graph.nodes",
                limit=len(node_ids) * 2,  # Some buffer
                admin_operation=True
            )
            
            existing_node_ids = set(n["node_id"] for n in (existing_nodes or []))
            
            # Check for missing nodes
            missing = node_ids - existing_node_ids
            if missing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Nodes not found: {', '.join(missing)}"
                )
        
        # Prepare edges
        for edge in edges:
            edge.setdefault("edge_type", "RELATED_TO")
            edge.setdefault("weight", 0.5)
            edge.setdefault("evidence", "")
        
        # Batch insert
        result = await supabase_client.insert(
            "graph.edges",
            edges,
            admin_operation=True
        )
        
        return {
            "success": True,
            "created": len(result) if result else 0,
            "edges": result or edges,
            "message": f"Created {len(result) if result else 0} edges"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to batch create edges: {str(e)}")


@router.get("/between/{source_node_id}/{target_node_id}")
async def get_edges_between_nodes(
    req: Request,
    source_node_id: str,
    target_node_id: str,
    bidirectional: bool = Query(False, description="Check both directions")
) -> Dict[str, Any]:
    """
    Get all edges between two specific nodes.
    
    If bidirectional=true, checks edges in both directions.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Get edges from source to target
        forward_edges = await supabase_client.get(
            "graph.edges",
            filters={
                "source_node_id": source_node_id,
                "target_node_id": target_node_id
            },
            admin_operation=True
        )
        
        edges = forward_edges or []
        
        # Check reverse direction if requested
        if bidirectional:
            reverse_edges = await supabase_client.get(
                "graph.edges",
                filters={
                    "source_node_id": target_node_id,
                    "target_node_id": source_node_id
                },
                admin_operation=True
            )
            
            if reverse_edges:
                edges.extend(reverse_edges)
        
        return {
            "success": True,
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "edges": edges,
            "count": len(edges),
            "bidirectional": bidirectional
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get edges between nodes: {str(e)}")


@router.get("/node/{node_id}")
async def get_node_edges(
    req: Request,
    node_id: str,
    direction: str = Query("both", regex="^(incoming|outgoing|both)$"),
    edge_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Get all edges connected to a specific node.
    
    Direction can be: incoming, outgoing, or both.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        edges = []
        
        # Get outgoing edges
        if direction in ["outgoing", "both"]:
            filters = {"source_node_id": node_id}
            if edge_type:
                filters["edge_type"] = edge_type
            
            outgoing = await supabase_client.get(
                "graph.edges",
                filters=filters,
                limit=limit,
                admin_operation=True
            )
            
            if outgoing:
                for edge in outgoing:
                    edge["direction"] = "outgoing"
                edges.extend(outgoing)
        
        # Get incoming edges
        if direction in ["incoming", "both"]:
            filters = {"target_node_id": node_id}
            if edge_type:
                filters["edge_type"] = edge_type
            
            incoming = await supabase_client.get(
                "graph.edges",
                filters=filters,
                limit=limit,
                admin_operation=True
            )
            
            if incoming:
                for edge in incoming:
                    edge["direction"] = "incoming"
                edges.extend(incoming)
        
        # Limit total results
        edges = edges[:limit]
        
        return {
            "success": True,
            "node_id": node_id,
            "edges": edges,
            "count": len(edges),
            "direction": direction,
            "edge_type": edge_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node edges: {str(e)}")