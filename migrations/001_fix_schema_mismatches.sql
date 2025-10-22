-- ============================================================================
-- GraphRAG Schema Fix Migration
-- Purpose: Align database schema with GraphRAG service expectations
-- Date: 2025-08-30
-- Issue: Service expects different column names than what exists in database
-- ============================================================================

BEGIN;

-- 1. Fix graph.document_registry table
-- Current issue: Code expects 'processing_status' but table has 'status'
ALTER TABLE graph.document_registry 
ADD COLUMN IF NOT EXISTS processing_status TEXT;

-- Migrate existing status values to processing_status
UPDATE graph.document_registry 
SET processing_status = CASE
    WHEN status = 'completed' THEN 'graph_completed'
    WHEN status = 'processing' THEN 'graph_processing'
    WHEN status = 'failed' THEN 'graph_failed'
    WHEN status = 'pending' THEN 'graph_pending'
    ELSE status
END
WHERE processing_status IS NULL;

-- 2. Fix graph.nodes table
-- Current issue: Code uses 'title' but table has 'label'
-- Current issue: Code expects 'source_id' and 'source_type' columns
ALTER TABLE graph.nodes
ADD COLUMN IF NOT EXISTS title TEXT,
ADD COLUMN IF NOT EXISTS source_id TEXT,
ADD COLUMN IF NOT EXISTS source_type TEXT;

-- Migrate existing label data to title
UPDATE graph.nodes SET title = label WHERE title IS NULL AND label IS NOT NULL;

-- 3. Fix graph.edges table
-- Current issue: Code expects 'edge_id', 'relationship_type', 'confidence_score'
-- Current issue: Table has 'edge_type' not 'relationship_type'
ALTER TABLE graph.edges
ADD COLUMN IF NOT EXISTS edge_id TEXT,
ADD COLUMN IF NOT EXISTS relationship_type TEXT,
ADD COLUMN IF NOT EXISTS confidence_score REAL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0);

-- Migrate edge_type to relationship_type
UPDATE graph.edges SET relationship_type = edge_type WHERE relationship_type IS NULL AND edge_type IS NOT NULL;

-- Generate edge_id for existing edges if they don't have one
UPDATE graph.edges 
SET edge_id = 'edge_' || generate_random_uuid()::text 
WHERE edge_id IS NULL;

-- 4. Fix graph.communities table
-- Current issue: Code expects 'title', 'node_count', 'edge_count'
-- Current issue: Table has 'size_nodes' not 'node_count'
ALTER TABLE graph.communities
ADD COLUMN IF NOT EXISTS title TEXT,
ADD COLUMN IF NOT EXISTS node_count INTEGER,
ADD COLUMN IF NOT EXISTS edge_count INTEGER;

-- Migrate size_nodes to node_count
UPDATE graph.communities SET node_count = size_nodes WHERE node_count IS NULL AND size_nodes IS NOT NULL;

-- Set default edge_count to 0 for existing communities
UPDATE graph.communities SET edge_count = 0 WHERE edge_count IS NULL;

-- Generate titles for communities that don't have them
UPDATE graph.communities 
SET title = 'Community ' || id::text 
WHERE title IS NULL;

-- 5. Add performance indexes for new columns
CREATE INDEX IF NOT EXISTS idx_graph_document_registry_processing_status 
ON graph.document_registry(processing_status);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_title 
ON graph.nodes USING gin(to_tsvector('english', title)) 
WHERE title IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_graph_nodes_source 
ON graph.nodes(source_id, source_type) 
WHERE source_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_graph_edges_edge_id 
ON graph.edges(edge_id) 
WHERE edge_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_graph_edges_relationship_type 
ON graph.edges(relationship_type) 
WHERE relationship_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_graph_edges_confidence 
ON graph.edges(confidence_score) 
WHERE confidence_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_graph_communities_title 
ON graph.communities USING gin(to_tsvector('english', title)) 
WHERE title IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_graph_communities_node_count 
ON graph.communities(node_count) 
WHERE node_count IS NOT NULL;

-- 6. Add constraints to ensure data integrity
ALTER TABLE graph.edges 
ADD CONSTRAINT unique_edge_id UNIQUE (edge_id) DEFERRABLE INITIALLY DEFERRED;

-- 7. Update any views that might be affected (if they exist)
-- Note: This will need to be customized based on actual views in the system

COMMIT;

-- ============================================================================
-- Post-migration verification queries
-- Run these to verify the migration worked correctly:
-- ============================================================================

-- Verify document_registry has processing_status
-- SELECT COUNT(*) as docs_with_processing_status FROM graph.document_registry WHERE processing_status IS NOT NULL;

-- Verify nodes have title column
-- SELECT COUNT(*) as nodes_with_title FROM graph.nodes WHERE title IS NOT NULL;

-- Verify edges have new columns
-- SELECT COUNT(*) as edges_with_relationship_type FROM graph.edges WHERE relationship_type IS NOT NULL;
-- SELECT COUNT(*) as edges_with_edge_id FROM graph.edges WHERE edge_id IS NOT NULL;

-- Verify communities have new columns
-- SELECT COUNT(*) as communities_with_title FROM graph.communities WHERE title IS NOT NULL;
-- SELECT COUNT(*) as communities_with_node_count FROM graph.communities WHERE node_count IS NOT NULL;