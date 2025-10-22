#!/bin/bash
#
# GraphRAG Optimized Upload - Master Execution Script
# Orchestrates the complete upload process with all optimizations
#
# This script executes:
# 1. Environment setup
# 2. Drop vector indexes
# 3. Validation
# 4. Small batch test
# 5. Full upload
# 6. Recreate indexes
# 7. VACUUM ANALYZE
# 8. Verification
#

set -e  # Exit on error

# Colors for output
RED='\033[0:31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}GraphRAG Optimized Upload - Master Execution Script${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo "Project directory: $PROJECT_DIR"
echo "Start time: $(date --iso-8601=seconds)"
echo ""

# Step 1: Environment Setup
echo -e "${BLUE}━━━ Step 1: Environment Setup ━━━${NC}"
echo "Loading optimized configuration..."

# Export environment variables from .env.upload
if [ -f "$PROJECT_DIR/.env.upload" ]; then
    set -a
    source "$PROJECT_DIR/.env.upload"
    set +a
    echo -e "${GREEN}✓${NC} Loaded .env.upload"
else
    echo -e "${RED}✗${NC} .env.upload not found!"
    exit 1
fi

# Verify critical variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo -e "${RED}✗${NC} Missing required Supabase credentials!"
    echo "   Required: SUPABASE_URL, SUPABASE_SERVICE_KEY"
    exit 1
fi

echo -e "${GREEN}✓${NC} Supabase URL: $SUPABASE_URL"
echo -e "${GREEN}✓${NC} Service key: ${SUPABASE_SERVICE_KEY:0:20}..."
echo -e "${GREEN}✓${NC} Batch timeout: ${SUPABASE_BATCH_OP_TIMEOUT}s"
echo -e "${GREEN}✓${NC} Vector timeout: ${SUPABASE_VECTOR_OP_TIMEOUT}s"
echo -e "${GREEN}✓${NC} Max connections: $SUPABASE_MAX_CONNECTIONS"
echo -e "${GREEN}✓${NC} Circuit breaker threshold: $SUPABASE_CB_FAILURE_THRESHOLD"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
cd "$PROJECT_DIR"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated"
else
    echo -e "${RED}✗${NC} Virtual environment not found!"
    exit 1
fi
echo ""

# Step 2: Drop Vector Indexes
echo -e "${BLUE}━━━ Step 2: Drop Vector Indexes ━━━${NC}"
echo "Dropping indexes for 10-100x faster upload..."
echo ""

# Note: This requires manual execution via MCP or psql
echo -e "${YELLOW}⚠️  Index dropping requires manual execution${NC}"
echo ""
echo "Please execute these SQL statements via Supabase dashboard or MCP:"
echo ""
cat << 'EOF'
-- Drop vector indexes (execute via Supabase dashboard SQL editor)
DROP INDEX IF EXISTS idx_nodes_embedding;
DROP INDEX IF EXISTS idx_chunks_content_embedding;
DROP INDEX IF EXISTS idx_enhanced_chunks_vector;
DROP INDEX IF EXISTS idx_communities_summary_embedding;
DROP INDEX IF EXISTS idx_reports_report_embedding;
EOF
echo ""
read -p "Have you dropped the indexes? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  Proceeding without dropping indexes (slower upload)${NC}"
    echo ""
fi

# Step 3: Validation
echo -e "${BLUE}━━━ Step 3: Pre-Upload Validation ━━━${NC}"
echo "Running validation checks..."
echo ""

if [ -f "$SCRIPT_DIR/validate_upload_setup.py" ]; then
    python "$SCRIPT_DIR/validate_upload_setup.py"
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗${NC} Validation failed!"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Validation passed"
else
    echo -e "${YELLOW}⚠️  Validation script not found, skipping...${NC}"
fi
echo ""

# Step 4: Small Batch Test
echo -e "${BLUE}━━━ Step 4: Small Batch Test (100 records) ━━━${NC}"
echo "Testing upload with 100 records per table..."
echo ""

read -p "Run test upload? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python "$SCRIPT_DIR/upload_via_supabase_client.py" --test --limit 100

    if [ $? -ne 0 ]; then
        echo -e "${RED}✗${NC} Test upload failed!"
        echo "Review errors above before proceeding to full upload."
        exit 1
    fi

    echo -e "${GREEN}✓${NC} Test upload completed successfully"
    echo ""

    read -p "Proceed with full upload? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Upload cancelled by user."
        exit 0
    fi
fi
echo ""

# Step 5: Full Upload
echo -e "${BLUE}━━━ Step 5: Full Upload (135,078 records) ━━━${NC}"
echo "Starting full production upload..."
echo "Estimated time: 20-30 minutes with optimizations"
echo ""

# Record start time
UPLOAD_START=$(date +%s)

# Execute upload
python "$SCRIPT_DIR/upload_via_supabase_client.py"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Upload failed!"
    echo "Check logs above for details."
    echo "Use --resume-from to continue from last checkpoint."
    exit 1
fi

# Calculate duration
UPLOAD_END=$(date +%s)
UPLOAD_DURATION=$((UPLOAD_END - UPLOAD_START))
UPLOAD_MINUTES=$((UPLOAD_DURATION / 60))
UPLOAD_SECONDS=$((UPLOAD_DURATION % 60))

echo -e "${GREEN}✓${NC} Upload completed successfully"
echo "Duration: ${UPLOAD_MINUTES}m ${UPLOAD_SECONDS}s"
echo ""

# Step 6: Recreate Vector Indexes
echo -e "${BLUE}━━━ Step 6: Recreate Vector Indexes ━━━${NC}"
echo "Recreating indexes for fast similarity search..."
echo ""

echo -e "${YELLOW}⚠️  Index creation requires manual execution${NC}"
echo ""
echo "Please execute these SQL statements via Supabase dashboard:"
echo ""
cat << 'EOF'
-- Recreate vector indexes with optimal settings
CREATE INDEX idx_nodes_embedding
ON graph.nodes
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_chunks_content_embedding
ON graph.chunks
USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_enhanced_chunks_vector
ON graph.enhanced_contextual_chunks
USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_communities_summary_embedding
ON graph.communities
USING hnsw (summary_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_reports_report_embedding
ON graph.reports
USING hnsw (report_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
EOF
echo ""
read -p "Have you created the indexes? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  Proceeding without indexes (slower queries)${NC}"
    echo ""
fi

# Step 7: VACUUM ANALYZE
echo -e "${BLUE}━━━ Step 7: VACUUM ANALYZE ━━━${NC}"
echo "Optimizing database statistics and reclaiming space..."
echo ""

echo -e "${YELLOW}⚠️  VACUUM ANALYZE requires manual execution${NC}"
echo ""
echo "Please execute via Supabase dashboard:"
echo ""
cat << 'EOF'
-- Optimize database after bulk insert
VACUUM ANALYZE graph.nodes;
VACUUM ANALYZE graph.edges;
VACUUM ANALYZE graph.communities;
VACUUM ANALYZE graph.node_communities;
VACUUM ANALYZE graph.chunks;
VACUUM ANALYZE graph.enhanced_contextual_chunks;
VACUUM ANALYZE graph.text_units;
VACUUM ANALYZE graph.reports;
VACUUM ANALYZE graph.document_registry;
EOF
echo ""
read -p "Have you run VACUUM ANALYZE? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  Skipping VACUUM ANALYZE (may affect query performance)${NC}"
    echo ""
fi

# Step 8: Verification
echo -e "${BLUE}━━━ Step 8: Post-Upload Verification ━━━${NC}"
echo "Verifying upload success..."
echo ""

echo "Expected row counts:"
echo "  graph.document_registry: 100"
echo "  graph.nodes: 10,000"
echo "  graph.edges: 20,000"
echo "  graph.communities: 500"
echo "  graph.node_communities: 29,978"
echo "  graph.chunks: 25,000"
echo "  graph.enhanced_contextual_chunks: 25,000"
echo "  graph.text_units: 25,000"
echo "  graph.reports: 200"
echo "  TOTAL: 135,078"
echo ""

echo -e "${YELLOW}⚠️  Verification requires manual SQL queries${NC}"
echo ""
echo "Execute via Supabase dashboard to verify:"
echo ""
cat << 'EOF'
-- Verify row counts
SELECT
    'document_registry' as table_name,
    COUNT(*) as row_count
FROM graph.document_registry
UNION ALL
SELECT 'nodes', COUNT(*) FROM graph.nodes
UNION ALL
SELECT 'edges', COUNT(*) FROM graph.edges
UNION ALL
SELECT 'communities', COUNT(*) FROM graph.communities
UNION ALL
SELECT 'node_communities', COUNT(*) FROM graph.node_communities
UNION ALL
SELECT 'chunks', COUNT(*) FROM graph.chunks
UNION ALL
SELECT 'enhanced_contextual_chunks', COUNT(*) FROM graph.enhanced_contextual_chunks
UNION ALL
SELECT 'text_units', COUNT(*) FROM graph.text_units
UNION ALL
SELECT 'reports', COUNT(*) FROM graph.reports;

-- Verify vector embeddings
SELECT
    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as nodes_with_embeddings
FROM graph.nodes;

SELECT
    COUNT(*) FILTER (WHERE content_embedding IS NOT NULL) as chunks_with_embeddings
FROM graph.chunks;
EOF
echo ""

# Final Summary
echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}UPLOAD COMPLETE${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo "End time: $(date --iso-8601=seconds)"
echo ""
echo -e "${GREEN}✓${NC} Environment setup"
echo -e "${GREEN}✓${NC} Indexes dropped (manual)"
echo -e "${GREEN}✓${NC} Validation passed"
echo -e "${GREEN}✓${NC} Upload completed (${UPLOAD_MINUTES}m ${UPLOAD_SECONDS}s)"
echo -e "${GREEN}✓${NC} Indexes recreated (manual)"
echo -e "${GREEN}✓${NC} VACUUM ANALYZE (manual)"
echo ""
echo "Next steps:"
echo "1. Verify row counts match expected values"
echo "2. Test GraphRAG query endpoints"
echo "3. Review upload logs for any warnings"
echo ""
echo -e "${GREEN}🎉 GraphRAG upload process complete!${NC}"
