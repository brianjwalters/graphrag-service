-- Migration: Create graph.entities Table
-- Purpose: Single source of truth for entity management with deduplication tracking
-- Date: 2025-10-10
-- Author: GraphRAG Service Team
-- Applied Version: 20251010074538 (create_graph_entities_table_v3)
-- Status: SUCCESSFULLY APPLIED
-- NOTE: Vector dimension reduced to 2000 (from 2048) due to pgvector 0.8.0 indexed limit

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create update timestamp function if it doesn't exist
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create graph.entities table
CREATE TABLE IF NOT EXISTS graph.entities (
    -- Primary Keys
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id TEXT UNIQUE NOT NULL,  -- MD5 hash-based identifier (deterministic)

    -- Entity Core Fields
    entity_text TEXT NOT NULL,       -- Canonical entity text (e.g., "Supreme Court of the United States")
    entity_type TEXT NOT NULL,       -- Entity type (COURT, CASE_CITATION, STATUTE, etc.)
    description TEXT,                 -- Contextual description (e.g., "Judicial body" - NO " entity" suffix)

    -- Confidence & Quality Metrics
    confidence REAL DEFAULT 0.95 CHECK (confidence BETWEEN 0.0 AND 1.0),
    extraction_method TEXT DEFAULT 'AI_MULTIPASS',  -- AI_MULTIPASS, REGEX, HYBRID, MANUAL

    -- Multi-Tenant Isolation (dedicated indexed columns)
    client_id UUID,                   -- NULL = public law documents (e.g., federal statutes)
    case_id UUID,                     -- NULL = not case-specific (e.g., general legal concepts)

    -- Cross-Document Tracking
    first_seen_document_id TEXT NOT NULL,  -- Document where entity was first extracted
    document_count INTEGER DEFAULT 1 CHECK (document_count >= 1),  -- Number of documents containing this entity
    document_ids TEXT[] DEFAULT ARRAY[]::TEXT[],  -- Array of all document IDs containing this entity

    -- Semantic Embedding (2000-dim for deduplication - pgvector 0.8.0 indexed limit)
    embedding VECTOR(2000),           -- Used for similarity matching (threshold: 0.85)

    -- Attributes & Metadata
    attributes JSONB DEFAULT '{}'::jsonb,   -- Entity-specific attributes (e.g., {"jurisdiction": "federal", "level": "supreme"})
    metadata JSONB DEFAULT '{}'::jsonb,     -- Extraction metadata (e.g., pass_number, chunk_id, position)

    -- Temporal Tracking
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    last_seen_at TIMESTAMPTZ DEFAULT NOW() NOT NULL, -- Last time entity appeared in a document

    -- Foreign Key Constraints
    CONSTRAINT fk_entities_case FOREIGN KEY (case_id)
        REFERENCES client.cases(case_id)
        ON DELETE CASCADE
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_entities_entity_type
    ON graph.entities(entity_type);

CREATE INDEX IF NOT EXISTS idx_entities_entity_text
    ON graph.entities(entity_text);

CREATE INDEX IF NOT EXISTS idx_entities_client_id
    ON graph.entities(client_id)
    WHERE client_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_entities_case_id
    ON graph.entities(case_id)
    WHERE case_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_entities_first_seen
    ON graph.entities(first_seen_document_id);

CREATE INDEX IF NOT EXISTS idx_entities_confidence
    ON graph.entities(confidence DESC)
    WHERE confidence >= 0.7;  -- Partial index for high-confidence entities only

CREATE INDEX IF NOT EXISTS idx_entities_document_count
    ON graph.entities(document_count DESC);

CREATE INDEX IF NOT EXISTS idx_entities_created_at
    ON graph.entities(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_entities_last_seen_at
    ON graph.entities(last_seen_at DESC);

-- HNSW Index for Vector Similarity Search (cosine distance)
CREATE INDEX IF NOT EXISTS idx_entities_embedding_hnsw
    ON graph.entities
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-Text Search Index
CREATE INDEX IF NOT EXISTS idx_entities_text_search
    ON graph.entities
    USING gin(to_tsvector('english', entity_text));

-- Composite Indexes for Common Query Patterns
CREATE INDEX IF NOT EXISTS idx_entities_type_client
    ON graph.entities(entity_type, client_id);

CREATE INDEX IF NOT EXISTS idx_entities_type_confidence
    ON graph.entities(entity_type, confidence DESC);

-- Trigger for automatic updated_at timestamp
DROP TRIGGER IF EXISTS update_entities_timestamp ON graph.entities;
CREATE TRIGGER update_entities_timestamp
    BEFORE UPDATE ON graph.entities
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- Add table comment for documentation
COMMENT ON TABLE graph.entities IS
'Single source of truth for entity management with cross-document deduplication tracking.
Stores canonical entity records with metadata, embeddings, and multi-tenant isolation.
Used by Entity Extraction Service for entity upsert operations and deduplication.';

-- Column comments for clarity
COMMENT ON COLUMN graph.entities.entity_id IS 'Deterministic MD5 hash: md5(entity_type:entity_text.lower().strip())[:16]';
COMMENT ON COLUMN graph.entities.entity_text IS 'Canonical entity text as extracted (e.g., "Supreme Court of the United States")';
COMMENT ON COLUMN graph.entities.entity_type IS 'Entity type from 31 legal entity types (COURT, CASE_CITATION, STATUTE, etc.)';
COMMENT ON COLUMN graph.entities.description IS 'Human-readable contextual description without " entity" suffix (e.g., "Judicial body")';
COMMENT ON COLUMN graph.entities.confidence IS 'Extraction confidence score (0.0-1.0) - combined from multiple extractions if entity appears in multiple chunks';
COMMENT ON COLUMN graph.entities.extraction_method IS 'How entity was extracted: AI_MULTIPASS (8-pass LLM), REGEX (pattern matching), HYBRID (both), MANUAL (user-added)';
COMMENT ON COLUMN graph.entities.client_id IS 'Client tenant identifier (UUID) - NULL for public law documents like federal statutes';
COMMENT ON COLUMN graph.entities.case_id IS 'Case identifier (UUID) for case-specific entities - NULL for general legal concepts';
COMMENT ON COLUMN graph.entities.first_seen_document_id IS 'Document ID where this entity was first extracted - enables provenance tracking';
COMMENT ON COLUMN graph.entities.document_count IS 'Number of documents containing this entity - measures cross-document importance';
COMMENT ON COLUMN graph.entities.document_ids IS 'Array of all document IDs containing this entity - enables document-to-entity reverse lookup';
COMMENT ON COLUMN graph.entities.embedding IS '2000-dimensional vector for semantic similarity matching (deduplication threshold: 0.85) - pgvector 0.8.0 indexed limit';
COMMENT ON COLUMN graph.entities.attributes IS 'Entity-specific attributes in JSONB format (e.g., {"jurisdiction": "federal", "court_level": "supreme"})';
COMMENT ON COLUMN graph.entities.metadata IS 'Extraction metadata in JSONB format (e.g., {"pass_number": 1, "chunk_id": "chunk_001", "position": 123})';
COMMENT ON COLUMN graph.entities.last_seen_at IS 'Timestamp of last document containing this entity - enables staleness detection';

-- Grant permissions (adjust based on your security model)
GRANT SELECT, INSERT, UPDATE ON graph.entities TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON graph.entities TO service_role;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully: graph.entities table created with 13 indexes';
    RAISE NOTICE 'Table supports: entity upsert, semantic deduplication, multi-tenant isolation, cross-document tracking';
END $$;
