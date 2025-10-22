"""
Community API Routes
Direct CRUD operations for graph communities with tenant isolation
"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


router = APIRouter()


@router.get("/")
async def list_communities(
    req: Request,
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    min_size: Optional[int] = Query(None, ge=1, description="Minimum community size"),
    max_size: Optional[int] = Query(None, ge=1, description="Maximum community size"),
    min_cohesion: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum cohesion score"),
    level: Optional[int] = Query(None, ge=0, description="Community level"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    List communities with optional filtering.
    
    Supports tenant isolation and quality filters.
    Returns paginated results ordered by size.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Build filters
        filters = {}
        if client_id:
            filters["client_id"] = client_id
        if case_id:
            filters["case_id"] = case_id
        if level is not None:
            filters["level"] = level
            
        # Query communities
        communities = await supabase_client.get(
            "graph.communities",
            filters=filters,
            limit=limit * 2,  # Get extra for filtering
            offset=offset,
            admin_operation=True
        )
        
        if communities:
            # Apply size and cohesion filters
            if min_size:
                communities = [c for c in communities if c.get("size_nodes", 0) >= min_size]
            if max_size:
                communities = [c for c in communities if c.get("size_nodes", 0) <= max_size]
            if min_cohesion:
                communities = [c for c in communities if c.get("cohesion_score", 0) >= min_cohesion]
            
            # Sort by size (largest first)
            communities.sort(key=lambda c: c.get("size_nodes", 0), reverse=True)
            
            # Apply limit
            communities = communities[:limit]
        
        return {
            "success": True,
            "count": len(communities) if communities else 0,
            "communities": communities or [],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(communities) == limit if communities else False
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list communities: {str(e)}")


@router.get("/{community_id}")
async def get_community(
    req: Request,
    community_id: str,
    include_members: bool = Query(False, description="Include member nodes"),
    include_summary: bool = Query(True, description="Include AI summary if available")
) -> Dict[str, Any]:
    """
    Get a specific community by ID.
    
    Optionally includes member nodes and AI-generated summary.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Get the community
        communities = await supabase_client.get(
            "graph.communities",
            filters={"community_id": community_id},
            limit=1,
            admin_operation=True
        )
        
        if not communities:
            raise HTTPException(status_code=404, detail=f"Community {community_id} not found")
        
        community = communities[0]
        result = {"community": community}
        
        # Include member nodes if requested
        if include_members:
            # Get node memberships
            memberships = await supabase_client.get(
                "graph.node_communities",
                filters={"community_id": community_id},
                admin_operation=True
            )
            
            if memberships:
                # Get node details for all members
                node_ids = [m["node_id"] for m in memberships]
                nodes = []
                
                for node_id in node_ids:
                    node_results = await supabase_client.get(
                        "graph.nodes",
                        filters={"node_id": node_id},
                        limit=1,
                        admin_operation=True
                    )
                    if node_results:
                        nodes.append(node_results[0])
                
                # Add membership strength to nodes
                for node in nodes:
                    for membership in memberships:
                        if membership["node_id"] == node["node_id"]:
                            node["membership_strength"] = membership.get("membership_strength", 1.0)
                            break
                
                result["members"] = nodes
                result["member_count"] = len(nodes)
        
        # Remove summary if not requested
        if not include_summary and "summary" in community:
            del community["summary"]
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get community: {str(e)}")


@router.post("/")
async def create_community(
    req: Request,
    community_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new community.
    
    Optionally specify initial member nodes.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Generate community ID if not provided
        if not community_data.get("community_id"):
            community_data["community_id"] = f"community_{uuid.uuid4().hex[:8]}"
        
        # Extract member nodes if provided
        member_nodes = community_data.pop("member_nodes", [])
        
        # Set defaults
        community_data.setdefault("level", 0)
        community_data.setdefault("size_nodes", len(member_nodes))
        community_data.setdefault("cohesion_score", 0.5)
        community_data.setdefault("summary", "")
        
        # Insert community
        result = await supabase_client.insert(
            "graph.communities",
            community_data,
            admin_operation=True
        )
        
        if result and member_nodes:
            # Add node memberships
            memberships = []
            for node_id in member_nodes:
                memberships.append({
                    "node_id": node_id,
                    "community_id": community_data["community_id"],
                    "membership_strength": 1.0
                })
            
            if memberships:
                await supabase_client.insert(
                    "graph.node_communities",
                    memberships,
                    admin_operation=True
                )
        
        return {
            "success": True,
            "community": result[0] if result else community_data,
            "members_added": len(member_nodes),
            "message": f"Community {community_data['community_id']} created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create community: {str(e)}")


@router.put("/{community_id}")
async def update_community(
    req: Request,
    community_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing community.
    
    Can update summary, cohesion score, level, etc.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Check if community exists
        existing = await supabase_client.get(
            "graph.communities",
            filters={"community_id": community_id},
            limit=1,
            admin_operation=True
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Community {community_id} not found")
        
        # Update community
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        result = await supabase_client.update(
            "graph.communities",
            updates,
            {"community_id": community_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "community": result[0] if result else updates,
            "message": f"Community {community_id} updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update community: {str(e)}")


@router.delete("/{community_id}")
async def delete_community(
    req: Request,
    community_id: str,
    cascade: bool = Query(False, description="Delete member associations")
) -> Dict[str, Any]:
    """
    Delete a community.
    
    If cascade=true, also deletes node membership records.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Check if community exists
        existing = await supabase_client.get(
            "graph.communities",
            filters={"community_id": community_id},
            limit=1,
            admin_operation=True
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Community {community_id} not found")
        
        deleted_items = {"community": 1, "memberships": 0}
        
        if cascade:
            # Delete memberships
            memberships = await supabase_client.delete(
                "graph.node_communities",
                {"community_id": community_id},
                admin_operation=True
            )
            
            deleted_items["memberships"] = len(memberships or [])
        
        # Delete the community
        await supabase_client.delete(
            "graph.communities",
            {"community_id": community_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "message": f"Community {community_id} deleted successfully",
            "deleted": deleted_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete community: {str(e)}")


@router.post("/{community_id}/members")
async def add_community_members(
    req: Request,
    community_id: str,
    node_ids: List[str],
    membership_strength: float = Query(1.0, ge=0.0, le=1.0)
) -> Dict[str, Any]:
    """
    Add nodes to a community.
    
    Creates node_communities membership records.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Check if community exists
        existing = await supabase_client.get(
            "graph.communities",
            filters={"community_id": community_id},
            limit=1,
            admin_operation=True
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Community {community_id} not found")
        
        # Verify nodes exist
        existing_nodes = await supabase_client.get(
            "graph.nodes",
            limit=len(node_ids) * 2,
            admin_operation=True
        )
        
        existing_node_ids = set(n["node_id"] for n in (existing_nodes or []))
        missing = set(node_ids) - existing_node_ids
        
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Nodes not found: {', '.join(missing)}"
            )
        
        # Create memberships
        memberships = []
        for node_id in node_ids:
            memberships.append({
                "node_id": node_id,
                "community_id": community_id,
                "membership_strength": membership_strength
            })
        
        result = await supabase_client.insert(
            "graph.node_communities",
            memberships,
            admin_operation=True
        )
        
        # Update community size
        new_size = existing[0].get("size_nodes", 0) + len(node_ids)
        await supabase_client.update(
            "graph.communities",
            {"size_nodes": new_size},
            {"community_id": community_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "members_added": len(result) if result else 0,
            "community_id": community_id,
            "new_size": new_size,
            "message": f"Added {len(node_ids)} members to community {community_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add community members: {str(e)}")


@router.delete("/{community_id}/members")
async def remove_community_members(
    req: Request,
    community_id: str,
    node_ids: List[str]
) -> Dict[str, Any]:
    """
    Remove nodes from a community.
    
    Deletes node_communities membership records.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        
        # Check if community exists
        existing = await supabase_client.get(
            "graph.communities",
            filters={"community_id": community_id},
            limit=1,
            admin_operation=True
        )
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Community {community_id} not found")
        
        # Delete memberships
        removed = 0
        for node_id in node_ids:
            result = await supabase_client.delete(
                "graph.node_communities",
                {
                    "node_id": node_id,
                    "community_id": community_id
                },
                admin_operation=True
            )
            if result:
                removed += len(result)
        
        # Update community size
        new_size = max(0, existing[0].get("size_nodes", 0) - removed)
        await supabase_client.update(
            "graph.communities",
            {"size_nodes": new_size},
            {"community_id": community_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "members_removed": removed,
            "community_id": community_id,
            "new_size": new_size,
            "message": f"Removed {removed} members from community {community_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove community members: {str(e)}")


@router.post("/{community_id}/recalculate")
async def recalculate_community_metrics(
    req: Request,
    community_id: str,
    generate_summary: bool = Query(False, description="Generate AI summary")
) -> Dict[str, Any]:
    """
    Recalculate community metrics.
    
    Updates size, cohesion score, and optionally generates AI summary.
    """
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        graph_constructor = req.app.state.graph_constructor
        
        # Get community
        communities = await supabase_client.get(
            "graph.communities",
            filters={"community_id": community_id},
            limit=1,
            admin_operation=True
        )
        
        if not communities:
            raise HTTPException(status_code=404, detail=f"Community {community_id} not found")
        
        community = communities[0]
        
        # Get memberships
        memberships = await supabase_client.get(
            "graph.node_communities",
            filters={"community_id": community_id},
            admin_operation=True
        )
        
        # Calculate new size
        new_size = len(memberships) if memberships else 0
        
        # Calculate cohesion (simplified - ratio of internal edges)
        cohesion_score = 0.5  # Default
        
        if memberships and len(memberships) > 1:
            node_ids = [m["node_id"] for m in memberships]
            
            # Count edges between community members
            internal_edges = 0
            for source_id in node_ids:
                edges = await supabase_client.get(
                    "graph.edges",
                    filters={"source_node_id": source_id},
                    admin_operation=True
                )
                
                if edges:
                    for edge in edges:
                        if edge["target_node_id"] in node_ids:
                            internal_edges += 1
            
            # Calculate cohesion as ratio of actual to possible edges
            max_edges = len(node_ids) * (len(node_ids) - 1)
            if max_edges > 0:
                cohesion_score = min(1.0, internal_edges / (max_edges * 0.5))
        
        # Update metrics
        updates = {
            "size_nodes": new_size,
            "cohesion_score": cohesion_score,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Generate AI summary if requested
        if generate_summary and graph_constructor.settings.prompt_service_url:
            # Get node details
            nodes = []
            for membership in (memberships or []):
                node_results = await supabase_client.get(
                    "graph.nodes",
                    filters={"node_id": membership["node_id"]},
                    limit=1,
                    admin_operation=True
                )
                if node_results:
                    nodes.append(node_results[0])
            
            if nodes:
                # This would call the prompt service
                # For now, just create a basic summary
                node_labels = [n.get("label", "") for n in nodes[:10]]
                updates["summary"] = f"Community of {new_size} entities including: {', '.join(node_labels[:5])}"
        
        # Update community
        result = await supabase_client.update(
            "graph.communities",
            updates,
            {"community_id": community_id},
            admin_operation=True
        )
        
        return {
            "success": True,
            "community": result[0] if result else updates,
            "metrics": {
                "size": new_size,
                "cohesion": cohesion_score
            },
            "message": f"Community {community_id} metrics recalculated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to recalculate community metrics: {str(e)}")