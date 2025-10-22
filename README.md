# GraphRAG Service

**Port**: 8010  
**Version**: 1.0.0  
**Description**: Advanced Knowledge Graph Construction Service using Microsoft GraphRAG methodology optimized for legal document processing

## Overview

The GraphRAG Service implements Microsoft's Graph Retrieval-Augmented Generation (GraphRAG) methodology, specifically optimized for legal document processing. It constructs comprehensive knowledge graphs from legal documents, enabling advanced entity deduplication, community detection, and relationship discovery across complex legal corpora.

**Key Highlights:**
- 🔍 **Microsoft GraphRAG Implementation** - Complete pipeline with legal optimizations
- 🤖 **Intelligent Entity Deduplication** - 0.85 similarity threshold with type awareness
- 🌐 **Community Detection** - Leiden algorithm for optimal graph structure
- 🔗 **Cross-Document Linking** - Relationship discovery across document boundaries
- ⚖️ **Legal Specialization** - 31 entity types, court hierarchies, citation relationships
- 📊 **Quality Assessment** - Graph completeness, coherence, and coverage metrics
- 💰 **Cost-Optimized Modes** - FULL, LAZY (99.9% cost reduction), and HYBRID modes
- 🔎 **Multi-Modal Search** - LOCAL, GLOBAL, and HYBRID search capabilities

## Schema Architecture

### Multi-Tenant Isolation

All graph tables support multi-tenant isolation through `client_id` and `case_id` columns:

- **client_id**: Links to `client.cases.client_id` (tenant isolation)
- **case_id**: Links to `client.cases.case_id` (case-level isolation)

**Tables with Multi-Tenant Support**:
- graph.document_registry
- graph.nodes
- graph.edges
- graph.communities
- graph.chunks
- graph.text_units
- graph.enhanced_contextual_chunks

**Foreign Key Relationships**:
```
client.cases (50 rows)
├── graph.document_registry (25K) → case_id
├── graph.nodes (100K) → case_id
├── graph.edges (80K) → case_id
├── graph.communities (500) → case_id
├── graph.chunks (750K) → case_id
├── graph.text_units → case_id
└── graph.enhanced_contextual_chunks (750K) → case_id
```

**Indexes for Performance**:
All tables have indexes on:
- `client_id` (partial index WHERE client_id IS NOT NULL)
- `case_id` (partial index WHERE case_id IS NOT NULL)
- `(case_id, client_id)` (compound index)
- `(case_id, document_id)` (for document-based tables)

### Querying Graph Data by Case

**Get all nodes for a specific case:**
```python
nodes = await client.get(
    'graph.nodes',
    filters={'case_id': 'your-case-uuid'},
    limit=1000
)
```

**Get chunks for a specific document in a case:**
```python
chunks = await client.get(
    'graph.chunks',
    filters={
        'case_id': 'your-case-uuid',
        'document_id': 'your-doc-id'
    },
    order_by='chunk_index'
)
```

**Get all communities for a client:**
```python
communities = await client.get(
    'graph.communities',
    filters={'client_id': 'your-client-uuid'}
)
```

### Synthetic Data Generation

The graph schema contains 1.68M rows of synthetic legal data for testing:

| Table | Rows | Embeddings |
|-------|------|------------|
| document_registry | 25,000 | - |
| nodes | 100,000 | 2048-dim |
| edges | 80,000 | - |
| communities | 500 | 2048-dim |
| chunks | 750,000 | 2048-dim |
| enhanced_contextual_chunks | 750,000 | 2048-dim |

**Distribution**: Data distributed across 50 test cases (10 clients × 5 cases each)

**Embeddings**: All vectors are 2048-dimensional, normalized unit vectors

### Schema Relationships

```
┌─────────────────────┐
│   client.cases      │
│   (50 rows)         │
│                     │
│ PK: case_id         │
│     client_id       │
└──────────┬──────────┘
           │
           │ FK: case_id
           │
    ┌──────┴───────────────────────────────────────┐
    │                                              │
┌───▼──────────────┐                    ┌─────────▼────────┐
│ graph.document_  │                    │  graph.nodes     │
│   registry       │                    │  (100K rows)     │
│ (25K rows)       │                    │                  │
│                  │                    │  embedding:      │
│ FK: case_id      │                    │  vector(2048)    │
└────────┬─────────┘                    └─────────┬────────┘
         │                                        │
         │ FK: document_id                        │
         │                                        │
    ┌────▼───────────┐                      ┌────▼─────────┐
    │ graph.chunks   │                      │ graph.edges  │
    │ (750K rows)    │                      │ (80K rows)   │
    │                │                      │              │
    │ embedding:     │                      │ FK: source,  │
    │ vector(2048)   │                      │     target   │
    │                │                      │     case_id  │
    │ FK: case_id,   │                      └──────────────┘
    │     document_id│
    └────────┬───────┘
             │
             │ FK: chunk_id
             │
    ┌────────▼──────────────────┐
    │ graph.enhanced_contextual_│
    │        _chunks            │
    │ (750K rows)               │
    │                           │
    │ vector: vector(2048)      │
    │ FK: chunk_id, case_id     │
    └───────────────────────────┘
```

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GraphRAG Service (Port 8010)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   FastAPI    │  │   GraphRAG   │  │  Community   │         │
│  │   Routes     │──│     Core     │──│  Detection   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                 │                  │                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Entity     │  │ Relationship │  │   Quality    │         │
│  │ Deduplication│  │  Discovery   │  │  Assessment  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                 │                  │                  │
│  ┌───────────────────────────────────────────────────────┐      │
│  │            Supabase Graph Schema                       │      │
│  │  (nodes, edges, communities, node_communities, chunks) │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                    External Integrations
                               │
    ┌──────────────────────────┼──────────────────────────┐
    │                          │                           │
┌───────────┐         ┌────────────┐           ┌─────────────┐
│  Entity   │         │  Chunking  │           │   Prompt    │
│Extraction │         │  Service   │           │   Service   │
│  (8007)   │         │   (8009)   │           │   (8003)    │
└───────────┘         └────────────┘           └─────────────┘
```

### GPU Hardware Configuration

**CRITICAL**: The GraphRAG service relies on two separate GPU-accelerated services:

```
┌────────────────────────────────────────────────────────────┐
│                     GPU Assignment                          │
├────────────────────────────────────────────────────────────┤
│  GPU 0 (NVIDIA)                                             │
│  ├─ vLLM LLM Service (Port 8080)                           │
│  ├─ Model: IBM Granite 3.3 2B (128K context)               │
│  └─ Use: AI summaries, entity extraction, reasoning        │
│                                                             │
│  GPU 1 (NVIDIA)                                             │
│  ├─ vLLM Embeddings Service (Port 8081)                    │
│  ├─ Model: Jina Embeddings v4 (2048 dimensions)            │
│  └─ Use: Semantic search, entity deduplication             │
└────────────────────────────────────────────────────────────┘
```

**⚠️ Important**: Never run both services on the same GPU to avoid memory conflicts and OOM errors.

### Vector/Embedding Strategy

The GraphRAG service uses a **distributed embedding architecture** where vectors are stored directly in the tables they represent:

**Storage locations:**
```
- graph.chunks.content_embedding          → Basic chunk embeddings
- graph.enhanced_contextual_chunks.vector → Anthropic-style enhanced chunk embeddings
- graph.nodes.embedding                   → Entity embeddings for deduplication
- graph.communities.summary_embedding     → Community summary embeddings
```

**Three Embedding Types:**

1. **Contextual Chunk Embeddings** (Primary)
   - Generated from Anthropic-style enhanced chunks
   - 2048 dimensions (Jina Embeddings v4)
   - 15-20% better retrieval vs. plain text
   - Stored in: `graph.enhanced_contextual_chunks.vector`

2. **Entity Embeddings**
   - Generated from entity text + context
   - 2048 dimensions (Jina Embeddings v4)
   - Used for: Entity deduplication (0.85 threshold), entity search
   - Stored in: `graph.nodes.embedding`

3. **Community Summary Embeddings**
   - Generated from AI-generated community summaries
   - 2048 dimensions (Jina Embeddings v4)
   - Used for: Global search, topic clustering
   - Stored in: `graph.communities.summary_embedding`

**Benefits of Distributed Storage:**
- No JOINs required for retrieval queries
- Better index optimization per table
- Simpler query patterns (one table = one query)
- Localized vector searches don't scan unrelated embeddings

**Search Types**:
- **Semantic Search**: Pure vector similarity using pgvector (<=> cosine distance)
- **Hybrid Search**: Vector + BM25 keyword search with Reciprocal Rank Fusion (RRF)
- **Local Search**: Community-scoped semantic search (3-5x faster)
- **Global Search**: Cross-community search using community embeddings

**Performance**:
- Embedding generation: 15-25ms per chunk
- Semantic search (1K chunks): 5-15ms
- Hybrid search (1K chunks): 20-40ms
- Local search (50 nodes): 3-8ms
- Global search (5 communities): 30-60ms

See [api.md](./api.md#vectorembedding-strategy) for detailed embedding strategy documentation.

## Features

### Core GraphRAG Capabilities
- **Entity Deduplication**: Smart entity merging using 0.85 similarity threshold with legal entity type awareness
- **Community Detection**: Leiden algorithm for optimal community detection with hierarchical structure
- **Relationship Discovery**: Cross-document relationship identification and inference
- **Graph Analytics**: Comprehensive metrics including centrality, connectivity, and quality assessment

### Legal Specialization (31 Entity Types)

**Citation Types (9)**:
- CASE_CITATION, STATUTE_CITATION, REGULATION_CITATION
- CONSTITUTIONAL_CITATION, LAW_REVIEW_CITATION, BOOK_CITATION
- NEWSPAPER_CITATION, WEB_CITATION, PARALLEL_CITATION

**Legal Entities (7)**:
- COURT, JUDGE, ATTORNEY, PARTY
- LAW_FIRM, GOVERNMENT_ENTITY, JURISDICTION

**Legal Concepts (9)**:
- LEGAL_DOCTRINE, PROCEDURAL_TERM, CLAIM_TYPE
- MOTION_TYPE, LEGAL_STANDARD, REMEDY
- LEGAL_ISSUE, HOLDING, RULING

**Document Elements (6)**:
- MONETARY_AMOUNT, DATE, DOCKET_NUMBER
- EXHIBIT, DEPOSITION, INTERROGATORY

### Processing Modes

#### FULL_GRAPHRAG (Default)
- Complete Microsoft GraphRAG implementation
- AI-enhanced entity extraction
- Full deduplication with 0.85 threshold
- Leiden community detection
- AI-generated community summaries
- **Cost**: ~$0.10-0.20 per document
- **Use Case**: High-value legal documents, critical cases

#### LAZY_GRAPHRAG
- 99.9% cost reduction compared to FULL mode
- NLP-based extraction (SpaCy)
- On-demand summary generation (relevance > 0.7)
- Louvain community detection
- **Cost**: ~$0.0001-0.001 per document
- **Use Case**: Bulk document processing, initial analysis

#### HYBRID_MODE
- Intelligent mode selection based on document importance
- Automatic routing between FULL and LAZY modes
- Balances cost and quality
- **Use Case**: Production environments with mixed document types

### Quality Assurance
- Graph completeness scoring
- Community coherence validation
- Entity and relationship confidence tracking
- Coverage metrics
- AI-powered community summaries

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL="your-supabase-url"
export SUPABASE_API_KEY="your-supabase-anon-key"
export SUPABASE_SERVICE_KEY="your-supabase-service-key"
export PROMPT_SERVICE_URL="http://localhost:8003"
export LOG_SERVICE_URL="http://localhost:8001"
```

## Usage

### Start the Service

```bash
python run.py
```

The service will start on port 8010 by default.

### API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: http://localhost:8010/docs
- ReDoc: http://localhost:8010/redoc

## API Endpoints

### Graph Construction

#### POST /api/v1/graph/create
Create a knowledge graph from document entities and relationships.

**Request Body:**
```json
{
  "document_id": "doc_001",
  "markdown_content": "Document content...",
  "entities": [
    {
      "entity_id": "ent_001",
      "entity_text": "Supreme Court",
      "entity_type": "COURT",
      "confidence": 0.95
    }
  ],
  "citations": [...],
  "relationships": [...],
  "enhanced_chunks": [...],
  "graph_options": {
    "enable_deduplication": true,
    "enable_community_detection": true,
    "enable_cross_document_linking": true,
    "enable_analytics": true,
    "use_ai_summaries": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "graph_id": "graph_doc_001_1234567890",
  "storage_info": {
    "nodes_created": 45,
    "edges_created": 67,
    "communities_detected": 8,
    "chunks_with_embeddings": 12,
    "graph_schema_tables": ["graph.nodes", "graph.edges", "graph.communities", "graph.chunks", "graph.enhanced_contextual_chunks"]
  },
  "quality_metrics": {
    "graph_completeness": 0.92,
    "community_coherence": 0.87,
    "entity_confidence_avg": 0.89,
    "relationship_confidence_avg": 0.81
  },
  "communities": [...],
  "analytics": {...}
}
```

### Health Monitoring

The service provides standardized health check endpoints:

- `GET /api/v1/health` - Basic health status
- `GET /api/v1/health/ping` - Simple ping check for load balancers
- `GET /api/v1/health/ready` - Readiness check with dependency verification
- `GET /api/v1/health/detailed` - Comprehensive health information including metrics

Example:
```bash
# Check basic health
curl http://localhost:8010/api/v1/health

# Check readiness
curl http://localhost:8010/api/v1/health/ready

# Get detailed health info
curl http://localhost:8010/api/v1/health/detailed
```

### Advanced Monitoring

#### GET /api/v1/health/metrics
Detailed service metrics including resource usage and processing statistics.

## Configuration

Key configuration parameters in `src/core/config.py`:

- `entity_similarity_threshold`: 0.85 (threshold for entity deduplication)
- `leiden_resolution`: 1.0 (community detection resolution)
- `min_community_size`: 3 (minimum entities for valid community)
- `max_community_size`: 50 (maximum entities per community)
- `community_coherence_threshold`: 0.7 (minimum coherence score)

## Architecture

### Core Modules

1. **Entity Deduplicator** (`entity_deduplicator.py`)
   - TF-IDF and fuzzy matching for similarity
   - Legal entity type-aware deduplication
   - Canonical form resolution

2. **Community Detector** (`community_detector.py`)
   - Leiden algorithm implementation
   - Hierarchical community structure
   - Legal context-aware community typing

3. **Relationship Discoverer** (`relationship_discoverer.py`)
   - Citation-based relationships
   - Cross-document connections
   - Inference from entity types and context
   - Co-occurrence pattern detection

4. **Graph Analytics** (`graph_analytics.py`)
   - Centrality metrics (degree, betweenness, PageRank)
   - Connectivity analysis
   - Legal-specific metrics
   - Quality assessment

5. **Graph Constructor** (`graph_constructor.py`)
   - Main orchestrator
   - Pipeline coordination
   - Database storage
   - Service integration

## Database Schema

The service stores data in the `graph` schema:

### Core Graph Tables
- `graph.nodes`: **Canonical deduplicated entities** - Single source of truth for all entities across documents
- `graph.edges`: Cross-document relationships with deduplication
- `graph.communities`: Leiden algorithm community detection results
- `graph.node_communities`: **Many-to-many junction table** - Links nodes to communities with membership strength scores (0.0-1.0 indicating strength of community membership)
- `graph.document_registry`: Central document catalog across all schemas
- `graph.chunks`: Basic document chunks with embeddings (content_embedding field)
- `graph.enhanced_contextual_chunks`: Anthropic-style contextual chunks with embeddings (vector field)
- `graph.text_units`: Microsoft GraphRAG intermediate layer linking entities to chunks
- `graph.reports`: AI-generated summaries (optional, expensive in FULL_GRAPHRAG mode)

### Domain Storage Tables
- `law.documents`: Legal reference documents (statutes, case law, regulations)
- `law.entities`: Raw entity extraction from legal documents (pre-deduplication audit trail)
- `law.entity_relationships`: Document-scoped relationships before graph deduplication
- `client.documents`: Client-specific case documents
- `client.entities`: Raw entity extraction from client documents

**Key Design Philosophy:**
- **law.entities / client.entities**: Raw extraction results (document-scoped, pre-deduplication)
- **graph.nodes**: Deduplicated canonical entities (cross-document, post-deduplication)
- Embeddings stored in source tables (distributed strategy) for better query performance

### Removed Tables (Schema Consolidation)

The following tables have been removed to eliminate redundancy and improve performance:

#### graph.entities (Removed)
**Reason**: Redundant with `graph.nodes`
- Original intent: Store Microsoft GraphRAG entities
- **Reality**: Code actually uses `graph.nodes` directly
- **Migration**: No data to migrate (table was never used)

#### law.citations (Removed)
**Reason**: Citations are entity types, not separate entities
- Citations now stored in `graph.nodes` with types:
  - CASE_CITATION, STATUTE_CITATION, REGULATION_CITATION
  - CONSTITUTIONAL_CITATION, LAW_REVIEW_CITATION, etc. (9 citation types total)
- **Migration**: Citation data preserved in graph.nodes

#### graph.covariates (Removed)
**Reason**: Unused legacy from Microsoft GraphRAG
- Metadata now stored in JSONB columns on respective tables
- **Migration**: No data to migrate (table was unused)

#### graph.embeddings (Removed)
**Reason**: Centralized storage created performance bottleneck
- **New approach**: Distributed embeddings in source tables
- **Migration**: Embeddings moved to content_embedding/vector fields in source tables

### Advanced Cross-Reference Tables

#### graph.chunk_entity_connections
Bidirectional links between chunks and entities for enhanced retrieval:
- **Purpose**: Entity-centric retrieval, co-occurrence analysis, chunk quality scoring
- **Schema**: chunk_id, entity_id, relevance_score (0.0-1.0), position_in_chunk
- **Use Cases**:
  - Find all chunks mentioning a specific case/entity
  - Discover entities that commonly appear together
  - Identify information-rich chunks based on entity density
  - Priority ranking for retrieval

**Example Query**: Find all chunks that discuss "Bruen v. NYC"
```sql
SELECT cc.chunk_id, cc.original_content, cec.relevance_score
FROM graph.chunk_entity_connections cec
INNER JOIN graph.contextual_chunks cc ON cc.chunk_id = cec.chunk_id
WHERE cec.entity_id = 'entity_case_bruen_001'
    AND cec.relevance_score >= 0.7
ORDER BY cec.relevance_score DESC;
```

#### graph.chunk_cross_references
Semantic relationships between chunks for citation analysis:
- **Purpose**: Citation network traversal, precedent analysis, contradiction detection
- **Schema**: source_chunk_id, target_chunk_id, reference_type, confidence_score
- **Reference Types**: citation, follows, contradicts, supports, elaborates, summarizes, questions, references, similar_topic
- **Use Cases**:
  - Build citation networks showing which cases cite others
  - Find precedent chains (which later cases follow earlier reasoning)
  - Identify contradictory holdings across documents
  - Discover thematically similar content via semantic clustering

**Example Query**: Find all cases that Rahimi cites
```sql
SELECT target.document_id, ccr.confidence_score
FROM graph.chunk_cross_references ccr
INNER JOIN graph.contextual_chunks source ON source.chunk_id = ccr.source_chunk_id
INNER JOIN graph.contextual_chunks target ON target.chunk_id = ccr.target_chunk_id
WHERE source.document_id = 'rahimi_v_us_2024'
    AND ccr.reference_type = 'citation'
ORDER BY ccr.confidence_score DESC;
```

See [api.md](./api.md#chunk-cross-reference-tables) for comprehensive usage examples and query patterns.

#### graph.node_communities (Many-to-Many Junction Table)

The `graph.node_communities` junction table enables many-to-many relationships between nodes and communities, allowing sophisticated community membership analysis:

- **Purpose**: Link nodes to multiple communities with varying membership strengths
- **Schema**: node_id, community_id, membership_strength (0.0-1.0), created_at
- **Use Cases**:
  - Find all communities a specific entity belongs to
  - Get all entities within a community (with membership filtering)
  - Discover "bridge entities" that connect multiple thematic areas
  - Assess community cohesion via membership strength distribution

**Membership Strength Scoring:**
- **0.9-1.0**: Core member (central to community theme)
- **0.7-0.89**: Strong member (highly relevant)
- **0.5-0.69**: Moderate member (relevant but peripheral)
- **< 0.5**: Weak member (tangentially related)

**Example Query:** Find all communities for a specific node

```sql
SELECT c.community_id, c.title, nc.membership_strength
FROM graph.node_communities nc
INNER JOIN graph.communities c ON c.community_id = nc.community_id
WHERE nc.node_id = 'entity_case_bruen_001'
ORDER BY nc.membership_strength DESC;
```

**Example Query:** Find all nodes in a community

```sql
SELECT n.node_id, n.label, nc.membership_strength
FROM graph.node_communities nc
INNER JOIN graph.nodes n ON n.node_id = nc.node_id
WHERE nc.community_id = 'community_2A_doctrine_001'
    AND nc.membership_strength >= 0.7
ORDER BY nc.membership_strength DESC;
```

**Typical Performance:**
- Node→Communities lookup: 2-5ms
- Community→Nodes lookup: 3-8ms (depends on community size)
- Multi-community analysis: 10-30ms

See [api.md](./api.md#many-to-many-node-community-relationships) for comprehensive examples and advanced query patterns.

## Microsoft GraphRAG Methodology

This service implements the key principles from Microsoft's GraphRAG paper:

1. **Entity Resolution**: Deduplication using multiple similarity measures
2. **Hierarchical Communities**: Multi-level community detection
3. **Relationship Inference**: Discovering implicit connections
4. **Quality Metrics**: Comprehensive graph quality assessment
5. **Incremental Updates**: Efficient graph updates for new documents

## Performance

- Handles up to 1000 entities per document
- Community detection within 30 seconds
- Entity deduplication at 0.85 similarity threshold
- Graph construction within 2 minutes for typical legal documents

## Integration

The GraphRAG Service integrates with:

- **Document Service** (Port 8005): Receives processed documents
- **Entity Extraction Service** (Port 8004): Gets extracted entities
- **Prompt Service** (Port 8003): For AI-powered summaries
- **Supabase**: For graph data persistence

## Development

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Adding New Features

1. Extend entity types in `entity_deduplicator.py`
2. Add relationship patterns in `relationship_discoverer.py`
3. Implement new metrics in `graph_analytics.py`
4. Update API models in `src/models/`

## Troubleshooting

### Common Issues

1. **Slow Community Detection**: Adjust `leiden_resolution` parameter
2. **Too Many Small Communities**: Increase `min_community_size`
3. **Low Deduplication Rate**: Lower `entity_similarity_threshold`
4. **Missing Cross-Document Links**: Ensure `enable_cross_document_linking` is true

## License

© 2025 Luris Legal Technology. All rights reserved.