# GraphRAG Database Schema Documentation

**Version:** 2.1
**Last Updated:** 2025-01-21
**Purpose:** Complete reference for the Luris GraphRAG database architecture implementing Microsoft GraphRAG methodology with legal document specialization

**Note:** Updated with live schema verification via Supabase MCP integration

---

## 1. Overview

### Three-Schema Architecture

The Luris GraphRAG implementation uses a sophisticated three-schema separation strategy to isolate concerns, optimize queries, and enforce data governance:

```
┌─────────────────────┐
│    law schema       │  ← Immutable legal reference materials
│  (Public Content)   │     Case law, statutes, regulations
└─────────────────────┘
           │
           ├─── Raw Extraction ───→ law.entities (pre-deduplication)
           │
┌─────────────────────┐
│   client schema     │  ← Multi-tenant client documents
│ (Private Content)   │     Contracts, briefs, client-specific docs
└─────────────────────┘
           │
           ├─── Raw Extraction ───→ client.entities (pre-deduplication)
           │
           ↓
┌─────────────────────┐
│   graph schema      │  ← **Knowledge Graph Intelligence Layer**
│  (Unified KG)       │     Deduplicated entities, relationships, communities
└─────────────────────┘
```

### Design Philosophy

**Raw Extraction → Domain Storage → Knowledge Graph**

1. **Law & Client Schemas**: Store raw, unprocessed extraction results from legal documents
   - **Purpose**: Immutable audit trail of entity extraction
   - **Scope**: Document-scoped entities before deduplication
   - **Preservation**: Maintains original extraction confidence, context, position data

2. **Graph Schema**: Unified knowledge graph across all content
   - **Purpose**: Canonical, deduplicated representation of legal knowledge
   - **Scope**: Cross-document entities after Microsoft GraphRAG deduplication
   - **Intelligence**: Community detection, relationship discovery, precedent analysis

### Multi-Tenancy Strategy

**Tenant Isolation Approach**: Metadata-based with dedicated columns for performance

- **Primary Mechanism**: `client_id` and `case_id` columns in `graph.nodes`, `graph.communities`
- **Fallback**: JSONB `metadata` column for additional tenant context
- **RLS Policies**: Row Level Security policies enforce tenant isolation (enabled but policies pending implementation)
- **Public Content**: `client_id = NULL` indicates publicly accessible legal materials (law schema)

### Scalability Considerations

**Current Design**: Handles 10,000+ documents with 100,000+ entities efficiently

**Future Scaling Strategies**:
1. **Table Partitioning**:
   - `graph.nodes`: HASH partitioning by `client_id` (multi-tenant isolation)
   - `graph.edges`: RANGE partitioning by `created_at` (time-series optimization)

2. **Hot/Warm/Cold Data Archiving**:
   - **Hot**: Active cases and recent legal research (< 90 days)
   - **Warm**: Closed cases and historical precedents (90 days - 2 years)
   - **Cold**: Long-term archive (> 2 years) with compressed storage

3. **Vector Index Optimization**:
   - HNSW indexes with configurable `m` and `ef_construction` parameters
   - Separate indexes per tenant for large multi-tenant deployments
   - Periodic REINDEX CONCURRENTLY for optimal performance

---

## 2. Schema Architecture Diagram

### Data Flow Visualization

```
┌────────────────────────────────────────────────────────────────┐
│                    DOCUMENT UPLOAD (Port 8008)                  │
│                       PDF/DOCX/TXT/MD                           │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────┐
│            ENTITY EXTRACTION SERVICE (Port 8007)                │
│      31 Legal Entity Types | Multi-mode Extraction             │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ├─────────────────┬─────────────────┐
                 ▼                 ▼                 ▼
        ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
        │law.entities │   │law.citations │   │law.entity_   │
        │             │   │              │   │relationships │
        └─────────────┘   └──────────────┘   └──────────────┘
     OR  ┌──────────────┐
         │client.entities│
         └──────────────┘
                 │
                 │  Document-scoped, pre-deduplication
                 │  Audit trail with extraction metadata
                 │
                 ▼
┌────────────────────────────────────────────────────────────────┐
│              GRAPHRAG SERVICE (Port 8010)                       │
│       Microsoft GraphRAG | Deduplication | Leiden              │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ├─── Deduplication (0.85 similarity) ───┐
                 │                                         │
                 ▼                                         ▼
        ┌─────────────┐                          ┌──────────────┐
        │graph.nodes  │ ← CANONICAL ENTITIES     │graph.edges   │
        │             │   (deduplicated)          │              │
        └──────┬──────┘                          └──────────────┘
               │
               │  Community Detection (Leiden algorithm)
               │
               ▼
        ┌──────────────────┐
        │graph.communities │  ← AI-Generated Summaries
        │                  │    Hierarchical structure
        └──────────────────┘
```

### Table Relationships

```
graph.document_registry (Central Catalog)
    │
    ├──→ graph.chunks (Basic Chunks) ✅ ACTIVE
    │       └──→ chunk.content_embedding (2048-dim vector)
    │
    ├──→ graph.enhanced_contextual_chunks (Anthropic-style) ✅ ACTIVE
    │       └──→ enhanced.vector (2048-dim vector)
    │
    ├──→ graph.nodes (Canonical Entities) ✅ ACTIVE
    │       ├──→ node.embedding (2048-dim vector)
    │       └──→ graph.node_communities (Many-to-Many junction table) ⚠️ EMPTY
    │               └──→ graph.communities ✅ ACTIVE
    │                       └──→ community.summary_embedding (2048-dim)
    │
    └──→ graph.edges (Relationships) ✅ ACTIVE
```

### Schema Separation Rationale

**Why Three Schemas?**

1. **Governance**: Separate RLS policies for public law vs. private client data
2. **Performance**: Optimized indexes per schema, no cross-schema JOIN penalties
3. **Auditability**: Clear separation of raw extraction vs. processed knowledge graph
4. **Scalability**: Independent partitioning strategies per schema
5. **Security**: Client data physically isolated from public legal materials

---

## 3. Law Schema (Legal Reference Materials)

### law.documents

**Purpose**: Store immutable legal reference documents (case law, statutes, regulations, constitutional provisions)

**Status**: ✅ ACTIVE (15,001 rows in production)

**Table Definition**:
```sql
CREATE TABLE law.documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,  -- opinion, statute, regulation, case_law, constitutional
    content TEXT NOT NULL,
    markdown_content TEXT,

    -- Classification
    jurisdiction TEXT,  -- federal, state, local
    court TEXT,         -- e.g., "Supreme Court of the United States"
    citation TEXT,      -- Bluebook citation

    -- Temporal
    decision_date TIMESTAMP WITH TIME ZONE,
    filing_date TIMESTAMP WITH TIME ZONE,

    -- Metadata
    precedential_value TEXT,  -- binding, persuasive, non_precedential
    importance_score REAL DEFAULT 0.5,
    metadata JSONB DEFAULT '{}',

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_law_documents_type ON law.documents(document_type);
CREATE INDEX idx_law_documents_jurisdiction ON law.documents(jurisdiction);
CREATE INDEX idx_law_documents_court ON law.documents(court);
CREATE INDEX idx_law_documents_decision_date ON law.documents(decision_date DESC);
```

**Key Fields**:
- `document_id`: Unique identifier (e.g., `rahimi_v_us_2024`)
- `document_type`: Legal document classification
- `precedential_value`: Indicates binding vs. persuasive authority
- `importance_score`: Calculated based on citation frequency, court level, recency

**Example Use Cases**:
```sql
-- Find all Supreme Court opinions from 2024
SELECT document_id, title, citation
FROM law.documents
WHERE court = 'Supreme Court of the United States'
  AND EXTRACT(YEAR FROM decision_date) = 2024
  AND document_type = 'opinion'
ORDER BY decision_date DESC;

-- Get highly cited constitutional law cases
SELECT d.title, d.citation, d.importance_score
FROM law.documents d
WHERE d.metadata->>'subject_area' = 'constitutional_law'
  AND d.importance_score >= 0.8
ORDER BY d.importance_score DESC
LIMIT 20;
```

### law.entities

**Purpose**: Raw entity extraction results from legal documents (pre-deduplication audit trail)

**Status**: ✅ ACTIVE (59,919 rows in production)

**Table Definition**:
```sql
CREATE TABLE law.entities (
    entity_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES law.documents(document_id),
    entity_text TEXT NOT NULL,
    entity_type TEXT NOT NULL,  -- COURT, CASE_CITATION, STATUTE_CITATION, etc.

    -- Extraction Metadata
    confidence REAL DEFAULT 0.95,
    extraction_method TEXT,  -- ai_enhanced, regex, hybrid
    start_position INTEGER,
    end_position INTEGER,
    context TEXT,  -- Surrounding text

    -- Entity Attributes
    attributes JSONB DEFAULT '{}',  -- Type-specific attributes
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_law_entities_document ON law.entities(document_id);
CREATE INDEX idx_law_entities_type ON law.entities(entity_type);
CREATE INDEX idx_law_entities_text ON law.entities USING gin(to_tsvector('english', entity_text));
```

**Why Separate from graph.nodes?**

1. **Document-Scoped**: Entities are tied to specific source documents with position data
2. **Extraction Metadata**: Preserves confidence scores, extraction method, and context
3. **Audit Trail**: Immutable record of what was extracted before deduplication
4. **Performance**: No deduplication overhead for read-heavy legal research queries

**Entity Types Supported** (31 total):
- **Citations** (9): CASE_CITATION, STATUTE_CITATION, REGULATION_CITATION, CONSTITUTIONAL_CITATION, etc.
- **Legal Entities** (7): COURT, JUDGE, ATTORNEY, PARTY, LAW_FIRM, GOVERNMENT_ENTITY, JURISDICTION
- **Legal Concepts** (9): LEGAL_DOCTRINE, PROCEDURAL_TERM, CLAIM_TYPE, MOTION_TYPE, LEGAL_STANDARD, REMEDY, etc.
- **Document Elements** (6): MONETARY_AMOUNT, DATE, DOCKET_NUMBER, EXHIBIT, DEPOSITION, INTERROGATORY

**Example Queries**:
```sql
-- Get all COURT entities from Rahimi opinion
SELECT entity_text, confidence, context
FROM law.entities
WHERE document_id = 'rahimi_v_us_2024'
  AND entity_type = 'COURT'
ORDER BY confidence DESC;

-- Find high-confidence CASE_CITATION entities across all opinions
SELECT e.entity_text, e.document_id, d.title, e.confidence
FROM law.entities e
JOIN law.documents d ON e.document_id = d.document_id
WHERE e.entity_type = 'CASE_CITATION'
  AND e.confidence >= 0.9
ORDER BY e.confidence DESC
LIMIT 50;
```

### law.entity_relationships

**Purpose**: Document-scoped relationships before graph deduplication

**Status**: ✅ ACTIVE (29,835 rows in production)

**Table Definition**:
```sql
CREATE TABLE law.entity_relationships (
    relationship_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES law.documents(document_id),
    source_entity_id TEXT NOT NULL REFERENCES law.entities(entity_id),
    target_entity_id TEXT NOT NULL REFERENCES law.entities(entity_id),
    relationship_type TEXT NOT NULL,  -- CITES, OVERRULES, FOLLOWS, DISTINGUISHES, etc.

    -- Relationship Metadata
    confidence REAL DEFAULT 0.85,
    evidence TEXT,  -- Text supporting this relationship
    bidirectional BOOLEAN DEFAULT FALSE,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_law_rel_document ON law.entity_relationships(document_id);
CREATE INDEX idx_law_rel_source ON law.entity_relationships(source_entity_id);
CREATE INDEX idx_law_rel_target ON law.entity_relationships(target_entity_id);
CREATE INDEX idx_law_rel_type ON law.entity_relationships(relationship_type);
```

**Difference from graph.edges**:

| Feature | law.entity_relationships | graph.edges |
|---------|-------------------------|-------------|
| Scope | Single document | Cross-document |
| Deduplication | No | Yes (canonical entities) |
| Purpose | Extraction audit trail | Knowledge graph |
| Entities | Document-specific IDs | Canonical deduplicated IDs |

**Example Use Cases**:
```sql
-- Find all cases cited by Rahimi
SELECT e.entity_text, r.relationship_type, r.confidence
FROM law.entity_relationships r
JOIN law.entities e ON r.target_entity_id = e.entity_id
WHERE r.document_id = 'rahimi_v_us_2024'
  AND r.relationship_type = 'CITES'
  AND e.entity_type = 'CASE_CITATION'
ORDER BY r.confidence DESC;
```

---

## 4. Client Schema (Multi-Tenant Client Data)

### client.cases

**Purpose**: Case management and client matter tracking

**Status**: ✅ ACTIVE (50 rows in production)

**Table Definition**:
```sql
CREATE TABLE client.cases (
    case_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,  -- Multi-tenant identifier

    -- Case Information
    case_name TEXT NOT NULL,
    case_number TEXT,
    case_type TEXT,  -- contract_dispute, personal_injury, criminal, etc.

    -- Status
    status TEXT DEFAULT 'active',  -- active, settled, dismissed, completed
    filed_date TIMESTAMP WITH TIME ZONE,
    closed_date TIMESTAMP WITH TIME ZONE,

    -- Jurisdiction
    jurisdiction TEXT,
    court TEXT,
    judge TEXT,

    -- Financial
    amount_in_controversy DECIMAL,
    settlement_amount DECIMAL,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_client_cases_client ON client.cases(client_id);
CREATE INDEX idx_client_cases_status ON client.cases(status) WHERE status != 'completed';
CREATE INDEX idx_client_cases_court ON client.cases(court);
```

### client.documents

**Purpose**: Client-specific documents (contracts, briefs, memos, discovery materials)

**Table Definition**:
```sql
CREATE TABLE client.documents (
    document_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    case_id TEXT REFERENCES client.cases(case_id),

    -- Document Info
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,  -- contract, brief, memo, discovery, correspondence
    content TEXT,
    markdown_content TEXT,

    -- Classification
    confidentiality_level TEXT DEFAULT 'client_confidential',  -- public, attorney_eyes_only, client_confidential
    privilege_status TEXT,  -- attorney_client, work_product, none

    -- Workflow
    status TEXT DEFAULT 'draft',  -- draft, review, final, filed
    author TEXT,
    reviewer TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_client_documents_client ON client.documents(client_id);
CREATE INDEX idx_client_documents_case ON client.documents(case_id);
CREATE INDEX idx_client_documents_type ON client.documents(document_type);
CREATE INDEX idx_client_documents_status ON client.documents(status);
```

**Confidentiality Levels**:
- `public`: Can be shared publicly
- `client_confidential`: Only accessible to client and law firm
- `attorney_eyes_only`: Restricted to attorneys (not staff or client)

### client.entities

**Purpose**: Raw extraction from client documents

**Table Definition**:
```sql
CREATE TABLE client.entities (
    entity_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES client.documents(document_id),
    client_id TEXT NOT NULL,  -- Multi-tenant isolation
    case_id TEXT REFERENCES client.cases(case_id),

    entity_text TEXT NOT NULL,
    entity_type TEXT NOT NULL,

    -- Extraction
    confidence REAL DEFAULT 0.95,
    extraction_method TEXT,
    start_position INTEGER,
    end_position INTEGER,
    context TEXT,

    attributes JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_client_entities_document ON client.entities(document_id);
CREATE INDEX idx_client_entities_client ON client.entities(client_id);
CREATE INDEX idx_client_entities_case ON client.entities(case_id);
CREATE INDEX idx_client_entities_type ON client.entities(entity_type);
```

**NOTE: Future Migration to VIEW**

Consider migrating `client.entities` to a materialized VIEW over `graph.nodes` with client_id filtering:

```sql
-- Future approach (after migration):
CREATE MATERIALIZED VIEW client.entities AS
SELECT
    node_id AS entity_id,
    metadata->>'document_id' AS document_id,
    client_id,
    metadata->>'case_id' AS case_id,
    title AS entity_text,
    node_type AS entity_type,
    metadata->>'confidence' AS confidence,
    metadata
FROM graph.nodes
WHERE client_id IS NOT NULL
  AND node_type = 'entity';

CREATE UNIQUE INDEX ON client.entities(entity_id);
REFRESH MATERIALIZED VIEW CONCURRENTLY client.entities;
```

**Benefits of VIEW approach**:
- Single source of truth (graph.nodes)
- Automatic deduplication
- Reduced storage overhead
- Simplified maintenance

**Current approach advantages**:
- Complete extraction audit trail
- No dependency on deduplication service
- Faster document-scoped queries

### client.clients

**Purpose**: Client intake and management

**Status**: ✅ ACTIVE (6 rows in production)

**Table Definition**:
```sql
CREATE TABLE client.clients (
    client_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Client Information
    name TEXT NOT NULL,
    client_type TEXT,  -- individual, corporation, llc, partnership, government

    -- Contact Information
    email TEXT,
    phone TEXT,
    address TEXT,

    -- Business Details
    industry TEXT,
    company_size TEXT,  -- small, medium, large, enterprise

    -- Relationship
    status TEXT DEFAULT 'active',  -- active, inactive, prospective
    intake_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    primary_attorney TEXT,
    billing_contact TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_client_clients_status ON client.clients(status);
CREATE INDEX idx_client_clients_type ON client.clients(client_type);
CREATE INDEX idx_client_clients_attorney ON client.clients(primary_attorney);
```

**Use Cases**:
```sql
-- Get all active clients for attorney
SELECT client_id, name, intake_date
FROM client.clients
WHERE primary_attorney = 'attorney_id_here'
  AND status = 'active'
ORDER BY intake_date DESC;
```

### client.chats

**Purpose**: Chat/conversation tracking for client communications

**Status**: ⚠️ EMPTY (0 rows - table defined but not yet used)

**Table Definition**:
```sql
CREATE TABLE client.chats (
    chat_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    case_id TEXT REFERENCES client.cases(case_id),

    -- Chat Metadata
    chat_title TEXT,
    chat_type TEXT,  -- consultation, case_discussion, document_review

    -- Participants
    participants JSONB DEFAULT '[]',  -- Array of user IDs

    -- Status
    status TEXT DEFAULT 'active',  -- active, archived, closed
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_client_chats_client ON client.chats(client_id);
CREATE INDEX idx_client_chats_case ON client.chats(case_id);
CREATE INDEX idx_client_chats_status ON client.chats(status);
```

### client.messages

**Purpose**: Individual messages within chats

**Status**: ⚠️ EMPTY (0 rows - table defined but not yet used)

**Table Definition**:
```sql
CREATE TABLE client.messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL REFERENCES client.chats(chat_id) ON DELETE CASCADE,

    -- Message Content
    sender_id TEXT NOT NULL,
    sender_type TEXT,  -- attorney, client, system, ai_assistant
    message_content TEXT NOT NULL,

    -- Message Metadata
    message_type TEXT DEFAULT 'text',  -- text, file, system, ai_response
    attachments JSONB DEFAULT '[]',

    -- AI Context
    ai_generated BOOLEAN DEFAULT FALSE,
    prompt_id TEXT,  -- Reference to prompt template if AI-generated
    confidence REAL,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    edited_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_client_messages_chat ON client.messages(chat_id);
CREATE INDEX idx_client_messages_sender ON client.messages(sender_id);
CREATE INDEX idx_client_messages_created ON client.messages(created_at DESC);
```

### client.tasks

**Purpose**: Task management and workflow tracking

**Status**: ⚠️ EMPTY (0 rows - table defined but not yet used)

**Table Definition**:
```sql
CREATE TABLE client.tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id TEXT NOT NULL,
    case_id TEXT REFERENCES client.cases(case_id),

    -- Task Information
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT,  -- research, filing, discovery, client_communication

    -- Assignment
    assigned_to TEXT,
    assigned_by TEXT,

    -- Status & Priority
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, cancelled
    priority TEXT DEFAULT 'medium',  -- low, medium, high, urgent

    -- Deadlines
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_client_tasks_client ON client.tasks(client_id);
CREATE INDEX idx_client_tasks_case ON client.tasks(case_id);
CREATE INDEX idx_client_tasks_assigned ON client.tasks(assigned_to);
CREATE INDEX idx_client_tasks_status ON client.tasks(status);
CREATE INDEX idx_client_tasks_due ON client.tasks(due_date);
```

### client.user_case_client_mapping

**Purpose**: User access control mapping for multi-tenant security

**Status**: ⚠️ EMPTY (0 rows - table defined but not yet used)

**Table Definition**:
```sql
CREATE TABLE client.user_case_client_mapping (
    mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    client_id TEXT,
    case_id TEXT REFERENCES client.cases(case_id),

    -- Access Control
    access_level TEXT NOT NULL,  -- read, write, admin, owner
    permissions JSONB DEFAULT '{}',  -- Granular permissions

    -- Scope
    scope TEXT NOT NULL,  -- client_wide, case_specific, document_specific

    -- Status
    status TEXT DEFAULT 'active',  -- active, suspended, revoked
    granted_by TEXT,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_case_client_mapping_user ON client.user_case_client_mapping(user_id);
CREATE INDEX idx_user_case_client_mapping_client ON client.user_case_client_mapping(client_id);
CREATE INDEX idx_user_case_client_mapping_case ON client.user_case_client_mapping(case_id);
CREATE INDEX idx_user_case_client_mapping_status ON client.user_case_client_mapping(status);
```

**Access Level Hierarchy**:
- `read`: View-only access to documents and data
- `write`: Read + create/edit documents and entities
- `admin`: Write + manage tasks, users, and settings
- `owner`: Admin + billing, client management, full control

---

## 5. Graph Schema (Knowledge Graph Intelligence Layer)

### graph.document_registry

**Purpose**: Central document catalog across all schemas (law + client)

**Status**: ✅ ACTIVE (1,030 rows in production)

**Table Definition**:
```sql
CREATE TABLE graph.document_registry (
    document_id TEXT PRIMARY KEY,
    client_id UUID,  -- NULL for public law documents
    case_id UUID,    -- NULL for non-case documents

    -- Document Info
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    source_schema TEXT NOT NULL,  -- 'law' or 'client'

    -- Processing Status
    processing_status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    pipeline_stage TEXT,  -- upload, extraction, chunking, graphrag

    -- Metadata
    file_path TEXT,
    file_size_bytes BIGINT,
    page_count INTEGER,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_document_registry_client ON graph.document_registry(client_id);
CREATE INDEX idx_document_registry_case ON graph.document_registry(case_id);
CREATE INDEX idx_document_registry_status ON graph.document_registry(processing_status);
CREATE INDEX idx_document_registry_schema ON graph.document_registry(source_schema);
```

**Cross-Schema Document Tracking**:
```sql
-- Get all documents (both law and client) for a specific case
SELECT dr.document_id, dr.title, dr.source_schema, dr.processing_status
FROM graph.document_registry dr
WHERE dr.case_id = 'case_12345'
ORDER BY dr.created_at DESC;

-- Find unprocessed documents across all schemas
SELECT document_id, title, source_schema
FROM graph.document_registry
WHERE processing_status IN ('pending', 'failed')
ORDER BY created_at ASC;
```

### graph.nodes

**Purpose**: **CANONICAL deduplicated entities** - the single source of truth for all entities across documents

**Status**: ✅ ACTIVE (140,953 rows in production)

**Table Definition**:
```sql
CREATE TABLE graph.nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,  -- entity, document, concept, community

    -- Node Content
    title TEXT NOT NULL,  -- Entity name/label (NEW: replaced 'label')
    description TEXT,

    -- Source Tracking
    source_id TEXT,   -- Original source document/entity ID
    source_type TEXT, -- document, extraction, manual

    -- Multi-Tenancy (Dedicated Columns for Performance)
    client_id UUID,   -- NULL = public content (law schema)
    case_id UUID,     -- NULL = not case-specific

    -- Graph Metrics
    degree INTEGER DEFAULT 0,              -- Number of connections
    centrality REAL DEFAULT 0.0,           -- Betweenness centrality
    importance_score REAL DEFAULT 0.5,     -- Computed importance (0-1)

    -- Community Membership
    community_id TEXT,  -- Primary community assignment

    -- Vector Search
    embedding vector(2048),  -- Jina v4 embeddings for semantic search

    -- Metadata
    metadata JSONB DEFAULT '{}',  -- Extensible: entity_type, confidence, attributes

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX idx_nodes_type ON graph.nodes(node_type);
CREATE INDEX idx_nodes_client ON graph.nodes(client_id) WHERE client_id IS NOT NULL;
CREATE INDEX idx_nodes_case ON graph.nodes(case_id) WHERE case_id IS NOT NULL;
CREATE INDEX idx_nodes_community ON graph.nodes(community_id) WHERE community_id IS NOT NULL;
CREATE INDEX idx_nodes_importance ON graph.nodes(importance_score DESC) WHERE importance_score >= 0.7;

-- Vector Search Index (HNSW for fast ANN)
CREATE INDEX idx_nodes_embedding
ON graph.nodes USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-Text Search
CREATE INDEX idx_nodes_title_fts ON graph.nodes USING gin(to_tsvector('english', title));

-- Metadata Search
CREATE INDEX idx_nodes_metadata_gin ON graph.nodes USING gin(metadata);
```

**Why This is Different from law.entities and client.entities**:

| Aspect | graph.nodes | law.entities / client.entities |
|--------|-------------|-------------------------------|
| **Scope** | Cross-document canonical | Single document |
| **Deduplication** | Yes (0.85 similarity threshold) | No |
| **Purpose** | Knowledge graph source of truth | Extraction audit trail |
| **Entity IDs** | Canonical merged IDs | Original extraction IDs |
| **Relationships** | Cross-document via graph.edges | Document-scoped |
| **Graph Metrics** | Degree, centrality, importance | N/A |
| **Community Detection** | Leiden algorithm assignment | N/A |

**Node Types**:
- `entity`: Legal entities (courts, cases, parties, concepts)
- `document`: Document nodes for graph visualization
- `concept`: Abstract legal concepts (doctrines, standards)
- `community`: Community summary nodes

**Multi-Tenancy Support**:
```sql
-- Get all entities for a specific client
SELECT node_id, title, node_type, importance_score
FROM graph.nodes
WHERE client_id = 'client_uuid_123'
  AND node_type = 'entity'
ORDER BY importance_score DESC;

-- Get all PUBLIC legal entities (law schema)
SELECT node_id, title, metadata->>'entity_type' AS entity_type
FROM graph.nodes
WHERE client_id IS NULL
  AND node_type = 'entity'
ORDER BY degree DESC  -- Most connected entities
LIMIT 100;
```

**Graph Properties**:
- `degree`: Calculated from graph.edges (in-degree + out-degree)
- `centrality`: Betweenness centrality (measures bridging importance)
- `importance_score`: Composite metric: 0.4×centrality + 0.3×degree + 0.3×citation_count

**Example Queries**:
```sql
-- Find most important entities in constitutional law
SELECT n.title, n.importance_score, n.degree, n.centrality
FROM graph.nodes n
WHERE n.metadata->>'entity_type' IN ('CASE_CITATION', 'LEGAL_DOCTRINE')
  AND n.metadata->>'subject_area' = 'constitutional_law'
  AND n.importance_score >= 0.8
ORDER BY n.importance_score DESC
LIMIT 20;

-- Get canonical form of entity across documents
SELECT n.node_id, n.title, n.source_id, n.degree,
       COUNT(DISTINCT n.metadata->>'document_id') AS document_count
FROM graph.nodes n
WHERE n.title ILIKE '%Bruen%'
  AND n.node_type = 'entity'
GROUP BY n.node_id, n.title, n.source_id, n.degree;
```

### graph.edges

**Purpose**: Cross-document relationships after deduplication

**Status**: ✅ ACTIVE (81,974 rows in production)

**Table Definition**:
```sql
CREATE TABLE graph.edges (
    edge_id TEXT PRIMARY KEY,
    source_node_id TEXT NOT NULL REFERENCES graph.nodes(node_id) ON DELETE CASCADE,
    target_node_id TEXT NOT NULL REFERENCES graph.nodes(node_id) ON DELETE CASCADE,

    -- Edge Type and Semantics
    edge_type TEXT NOT NULL,           -- Relationship type
    relationship_type TEXT NOT NULL,   -- Alias for compatibility

    -- Edge Strength
    weight REAL DEFAULT 1.0,           -- Edge weight for graph algorithms
    confidence_score REAL DEFAULT 0.8, -- Extraction confidence

    -- Evidence
    evidence TEXT,  -- Supporting text or citation

    -- Metadata
    metadata JSONB DEFAULT '{}',  -- client_id, case_id, document_id, graph_id

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX idx_edges_source ON graph.edges(source_node_id);
CREATE INDEX idx_edges_target ON graph.edges(target_node_id);
CREATE INDEX idx_edges_type ON graph.edges(edge_type);
CREATE INDEX idx_edges_bidirectional ON graph.edges(target_node_id, source_node_id);
CREATE INDEX idx_edges_metadata_gin ON graph.edges USING gin(metadata);

-- Prevent duplicate edges
CREATE UNIQUE INDEX idx_edges_unique
ON graph.edges(source_node_id, target_node_id, edge_type);
```

**Edge Types and Semantics**:

| Edge Type | Description | Example | Bidirectional |
|-----------|-------------|---------|---------------|
| `CITES` | Source cites target | Rahimi CITES Bruen | No |
| `CITED_BY` | Reverse citation | Bruen CITED_BY Rahimi | No |
| `OVERRULES` | Source overrules target | Dobbs OVERRULES Roe | No |
| `FOLLOWS` | Source follows precedent | Rahimi FOLLOWS Heller | No |
| `DISTINGUISHES` | Source distinguishes from target | Case A DISTINGUISHES Case B | No |
| `SIMILAR_TO` | Semantic similarity | Concept A SIMILAR_TO Concept B | Yes |
| `PART_OF` | Hierarchical relationship | Regulation PART_OF Statute | No |
| `REFERS_TO` | General reference | Brief REFERS_TO Case | No |
| `DECIDED_CASE` | Court decided case | SCOTUS DECIDED_CASE Rahimi | No |

**Weight vs. Confidence Score**:
- `weight`: Used for graph algorithms (PageRank, community detection) - higher = stronger connection
- `confidence_score`: Extraction confidence from Entity Extraction Service - reliability of relationship

**Example Queries**:
```sql
-- Find all cases cited by Rahimi v. United States
SELECT
    e.edge_type,
    target_node.title AS cited_case,
    e.confidence_score,
    e.evidence
FROM graph.edges e
JOIN graph.nodes source_node ON e.source_node_id = source_node.node_id
JOIN graph.nodes target_node ON e.target_node_id = target_node.node_id
WHERE source_node.title ILIKE '%Rahimi%'
  AND e.edge_type = 'CITES'
ORDER BY e.confidence_score DESC;

-- Graph traversal: Find all cases within 2 hops of Heller
WITH RECURSIVE case_network AS (
    -- Base case: Heller itself
    SELECT node_id, title, 0 AS hop_distance
    FROM graph.nodes
    WHERE title ILIKE '%Heller%' AND node_type = 'entity'

    UNION

    -- Recursive case: expand network
    SELECT n.node_id, n.title, cn.hop_distance + 1
    FROM case_network cn
    JOIN graph.edges e ON (cn.node_id = e.source_node_id OR cn.node_id = e.target_node_id)
    JOIN graph.nodes n ON (
        CASE
            WHEN cn.node_id = e.source_node_id THEN n.node_id = e.target_node_id
            ELSE n.node_id = e.source_node_id
        END
    )
    WHERE cn.hop_distance < 2
)
SELECT DISTINCT title, hop_distance
FROM case_network
ORDER BY hop_distance, title;
```

### graph.communities

**Purpose**: Leiden algorithm community detection results with AI-generated summaries

**Status**: ✅ ACTIVE (1,000 rows in production)

**Table Definition**:
```sql
CREATE TABLE graph.communities (
    community_id TEXT PRIMARY KEY,

    -- Community Info
    title TEXT NOT NULL,
    summary TEXT,  -- AI-generated summary of community
    level INTEGER DEFAULT 0,  -- Hierarchical community level

    -- Size Metrics
    node_count INTEGER DEFAULT 0,
    edge_count INTEGER DEFAULT 0,

    -- Quality Metrics
    coherence_score REAL DEFAULT 0.0,  -- Intra-community connection density
    modularity REAL DEFAULT 0.0,       -- Community modularity score

    -- Multi-Tenancy
    client_id UUID,
    case_id UUID,

    -- Vector Search
    summary_embedding vector(2048),  -- Jina v4 embedding of AI summary

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX idx_communities_level ON graph.communities(level, node_count DESC);
CREATE INDEX idx_communities_client ON graph.communities(client_id) WHERE client_id IS NOT NULL;
CREATE INDEX idx_communities_case ON graph.communities(case_id) WHERE case_id IS NOT NULL;
CREATE INDEX idx_communities_coherence ON graph.communities(coherence_score DESC);

-- Vector Search Index
CREATE INDEX idx_communities_summary_embedding
ON graph.communities USING hnsw (summary_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Hierarchical Structure**:
- `level = 0`: Base communities (most granular)
- `level = 1`: Meta-communities (groups of level 0 communities)
- `level = 2`: Super-communities (highest abstraction)

**AI-Generated Summaries**:

Communities receive AI-generated summaries via Prompt Service (Port 8003):

**Example Prompt**:
```
Summarize this legal entity community in 2-3 sentences:

Community Type: Second Amendment Doctrine
Central Entities: Bruen v. NYC, Heller v. DC, McDonald v. Chicago
Community Members (12 total):
- New York State Rifle & Pistol Association, Inc. v. Bruen (CASE_CITATION)
- District of Columbia v. Heller (CASE_CITATION)
- McDonald v. City of Chicago (CASE_CITATION)
- Second Amendment (LEGAL_DOCTRINE)
- Historical Tradition Test (LEGAL_STANDARD)
...

Focus on the legal relationships and significance. Be concise and specific.
```

**Example Summary**:
> "This community centers around landmark Second Amendment cases establishing the individual right to bear arms. The key precedents (Heller, McDonald, Bruen) apply a historical tradition test to evaluate firearm regulations, requiring government to demonstrate consistency with historical restrictions at the nation's founding."

**Example Queries**:
```sql
-- Find communities related to Second Amendment
SELECT
    community_id,
    title,
    summary,
    node_count,
    coherence_score
FROM graph.communities
WHERE title ILIKE '%Second Amendment%'
   OR summary ILIKE '%firearm%'
   OR summary ILIKE '%gun rights%'
ORDER BY coherence_score DESC;

-- Get all communities for a specific case
SELECT c.title, c.summary, c.node_count, c.coherence_score
FROM graph.communities c
WHERE c.case_id = 'case_uuid_123'
ORDER BY c.node_count DESC;
```

### graph.node_communities

**Purpose**: Many-to-many junction table for node-community membership

**Status**: ⚠️ EMPTY (0 rows - table defined for future multi-community membership)

**Table Definition**:
```sql
CREATE TABLE graph.node_communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id TEXT NOT NULL REFERENCES graph.nodes(node_id) ON DELETE CASCADE,
    community_id TEXT NOT NULL REFERENCES graph.communities(community_id) ON DELETE CASCADE,
    membership_strength REAL DEFAULT 1.0,  -- 0.0-1.0 strength of membership

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(node_id, community_id)
);

CREATE INDEX idx_node_communities_node ON graph.node_communities(node_id);
CREATE INDEX idx_node_communities_community ON graph.node_communities(community_id);
```

**Note**: Currently, node-community membership is tracked via `graph.nodes.community_id` (single community per node). This junction table supports future enhancement where nodes can belong to multiple communities with varying membership strengths.

**Future Use Case**:
```sql
-- Get all communities a node belongs to (multi-membership)
SELECT c.community_id, c.title, nc.membership_strength
FROM graph.node_communities nc
JOIN graph.communities c ON nc.community_id = c.community_id
WHERE nc.node_id = 'node_123'
ORDER BY nc.membership_strength DESC;
```

### graph.chunks

**Purpose**: Basic document chunks from Chunking Service (Port 8009)

**Status**: ✅ ACTIVE (30,000 rows in production)

**Table Definition**:
```sql
CREATE TABLE graph.chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,

    -- Chunk Content
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,  -- Position in document (0-based)

    -- Chunking Strategy
    start_position INTEGER,
    end_position INTEGER,
    token_count INTEGER,

    -- Vector Search
    content_embedding vector(2048),  -- Jina v4 embedding

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON graph.chunks(document_id, chunk_index);

-- Vector Search Index
CREATE INDEX idx_chunks_content_embedding
ON graph.chunks USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
WHERE content_embedding IS NOT NULL;
```

**Chunking Strategy**:
- **Sliding window**: 512 tokens with 128-token overlap
- **Sentence-aware**: Respects sentence boundaries
- **Legal-aware**: Avoids splitting citations, numbered lists, legal citations

**Example Query**:
```sql
-- Get all chunks for a document in order
SELECT chunk_id, chunk_index, LEFT(content, 100) AS preview, token_count
FROM graph.chunks
WHERE document_id = 'rahimi_v_us_2024'
ORDER BY chunk_index;
```

### graph.enhanced_contextual_chunks

**Purpose**: Anthropic-style contextual retrieval chunks with enhanced context

**Status**: ✅ ACTIVE (30,000 rows in production)

**Table Definition**:
```sql
CREATE TABLE graph.enhanced_contextual_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,

    -- Content Layers
    content TEXT NOT NULL,                    -- Original chunk content
    contextualized_content TEXT NOT NULL,     -- Enhanced with document context
    situational_context TEXT,                 -- Document title, section, topic

    -- Position
    chunk_index INTEGER NOT NULL,
    start_position INTEGER,
    end_position INTEGER,

    -- Quality
    quality_score REAL DEFAULT 0.0,  -- Contextual enhancement quality (0-1)

    -- Vector Search (2048-dim for contextual embeddings)
    vector vector(2048),  -- Jina v4 embedding of contextualized_content

    -- Full-Text Search
    search_vector tsvector,  -- For hybrid search (text + vector)

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_enhanced_chunks_document ON graph.enhanced_contextual_chunks(document_id, chunk_index);
CREATE INDEX idx_enhanced_chunks_quality ON graph.enhanced_contextual_chunks(quality_score DESC)
    WHERE quality_score >= 0.7;

-- Vector Search Index (2048-dim)
CREATE INDEX idx_enhanced_chunks_vector_hnsw
ON graph.enhanced_contextual_chunks USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
WHERE vector IS NOT NULL;

-- Full-Text Search Index
CREATE INDEX idx_enhanced_chunks_search_gin
ON graph.enhanced_contextual_chunks USING gin(search_vector);

-- Metadata Search
CREATE INDEX idx_enhanced_chunks_metadata_gin
ON graph.enhanced_contextual_chunks USING gin(metadata);
```

**Contextual Enhancement Layers**:

1. **Original Content**: Raw chunk text
   ```
   "The Court held that the Second Amendment protects an individual right to keep and bear arms."
   ```

2. **Situational Context**: Document metadata injection
   ```
   "Document: Rahimi v. United States (2024)
   Topic: Second Amendment Disarmament
   Section: Constitutional Analysis
   Court: Supreme Court of the United States"
   ```

3. **Contextualized Content**: Combined for embedding
   ```
   "In Rahimi v. United States (2024), a Supreme Court Second Amendment case, the Court held that the Second Amendment protects an individual right to keep and bear arms. This holding appears in the constitutional analysis section discussing Second Amendment disarmament."
   ```

**Benefits**:
- **15-20% better retrieval accuracy** vs. plain text embeddings
- **Better semantic understanding** of legal context
- **Improved cross-document connections**

**Example Queries**:
```sql
-- High-quality contextual chunks for a document
SELECT
    chunk_id,
    LEFT(content, 100) AS original_preview,
    LEFT(situational_context, 100) AS context_preview,
    quality_score
FROM graph.enhanced_contextual_chunks
WHERE document_id = 'rahimi_v_us_2024'
  AND quality_score >= 0.8
ORDER BY quality_score DESC;
```

### graph.text_units

**Purpose**: Microsoft GraphRAG intermediate extraction layer linking entities to chunks

**Table Definition**:
```sql
CREATE TABLE graph.text_units (
    text_unit_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_id TEXT REFERENCES graph.chunks(chunk_id),

    -- Content
    content TEXT NOT NULL,
    tokens INTEGER DEFAULT 0,

    -- Entity Links (Array Fields)
    entity_ids TEXT[] DEFAULT '{}',          -- Array of node_ids
    relationship_ids TEXT[] DEFAULT '{}',    -- Array of edge_ids

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_text_units_document ON graph.text_units(document_id);
CREATE INDEX idx_text_units_chunk ON graph.text_units(chunk_id);
CREATE INDEX idx_text_units_entities_gin ON graph.text_units USING gin(entity_ids);
CREATE INDEX idx_text_units_rels_gin ON graph.text_units USING gin(relationship_ids);
```

**Purpose in Microsoft GraphRAG**:
- **Intermediate layer**: Links raw text to extracted entities
- **Provenance tracking**: Which text produced which entities
- **Relationship attribution**: Evidence for relationships

**Example Query**:
```sql
-- Find all text units containing a specific entity
SELECT tu.text_unit_id, tu.content, array_length(tu.entity_ids, 1) AS entity_count
FROM graph.text_units tu
WHERE 'node_entity_bruen_001' = ANY(tu.entity_ids)
ORDER BY created_at DESC;
```

### graph.reports

**Purpose**: AI-generated summaries (expensive, optional in LazyGraphRAG)

**Status**: ⚠️ EMPTY (0 rows - LazyGraphRAG generates on-demand)

**Table Definition**:
```sql
CREATE TABLE graph.reports (
    report_id TEXT PRIMARY KEY,
    report_type TEXT NOT NULL,  -- global, community, node

    -- Report Content
    title TEXT NOT NULL,
    summary TEXT NOT NULL,  -- AI-generated summary

    -- Scope
    community_id TEXT REFERENCES graph.communities(community_id),
    node_id TEXT REFERENCES graph.nodes(node_id),

    -- Quality
    relevance_score REAL DEFAULT 0.0,  -- 0-1 relevance for query answering

    -- Vector Search
    report_embedding vector(2048),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_reports_type ON graph.reports(report_type);
CREATE INDEX idx_reports_community ON graph.reports(community_id) WHERE community_id IS NOT NULL;
CREATE INDEX idx_reports_node ON graph.reports(node_id) WHERE node_id IS NOT NULL;
CREATE INDEX idx_reports_relevance ON graph.reports(relevance_score DESC)
    WHERE relevance_score >= 0.7;

-- Vector Search Index
CREATE INDEX idx_reports_report_embedding
ON graph.reports USING hnsw (report_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
WHERE report_embedding IS NOT NULL;
```

**Report Types**:

1. **Global Reports**: Entire knowledge graph summary
   - **Use Case**: High-level overview questions
   - **Example**: "What are the main themes in constitutional law?"

2. **Community Reports**: Community-level summaries
   - **Use Case**: Topic-specific queries
   - **Example**: "Summarize Second Amendment precedents"

3. **Node Reports**: Individual entity deep-dives
   - **Use Case**: Specific entity analysis
   - **Example**: "Explain the Bruen decision"

**LazyGraphRAG Optimization**:

Reports are **expensive to generate** (LLM calls), so LazyGraphRAG only creates them when:
- `relevance_score >= 0.7` (high-value content)
- User explicitly requests summary
- Community is frequently queried (caching benefit)

**Cost Comparison**:
- **FULL_GRAPHRAG**: Generate all reports upfront (~$50-100 per 1000 documents)
- **LAZY_GRAPHRAG**: Generate on-demand (99.9% cost reduction, ~$0.05-0.10 per 1000 documents)

---

## 6. Removed Tables (and Why)

### law.citations - **REMOVED** ❌

**Migration Date**: 2025-09-01
**Reason**: Redundant with citation entity types in unified graph.nodes

**Old Approach**:
```sql
-- DEPRECATED
CREATE TABLE law.citations (
    citation_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    citation_text TEXT NOT NULL,
    citation_type TEXT,  -- CASE_LAW, STATUTE, REGULATION
    ...
);
```

**New Approach**:
Citations now exist **only** in `graph.nodes` with entity types:
- `CASE_CITATION`
- `STATUTE_CITATION`
- `REGULATION_CITATION`
- `CONSTITUTIONAL_CITATION`
- etc.

**Migration Path**:
```sql
-- Migrate law.citations to graph.nodes
INSERT INTO graph.nodes (node_id, node_type, title, metadata)
SELECT
    citation_id AS node_id,
    'entity' AS node_type,
    citation_text AS title,
    jsonb_build_object(
        'entity_type', citation_type,
        'source_table', 'law.citations',
        'document_id', document_id
    ) AS metadata
FROM law.citations;

-- Drop old table
DROP TABLE law.citations CASCADE;
```

**Benefits**:
- Unified citation representation across all documents
- Automatic deduplication (same citation across multiple documents)
- Graph algorithms include citation relationships
- Simplified querying (single table instead of JOIN)

### graph.entities - 🔻 **DEPRECATED** (not removed, but empty)

**Status**: ⚠️ Table exists but empty (0 rows) - marked for future removal

**Deprecation Date**: 2025-09-01
**Reason**: Replaced by graph.nodes for all entity storage

**Current State**:
The `graph.entities` table still exists in the database but contains 0 rows. It uses a different vector dimension (2000-dim) than the current standard (2048-dim Jina v4).

**Old Approach**:
```sql
-- DEPRECATED - Table exists but not used
CREATE TABLE graph.entities (
    entity_id TEXT PRIMARY KEY,
    entity_text TEXT NOT NULL,
    entity_type TEXT,
    embedding vector(2000),  -- Old dimension, incompatible with current system
    ...
);
```

**New Approach**:
All entities stored in `graph.nodes` with `node_type = 'entity'` and 2048-dim embeddings

**Migration Status**:
- ✅ All production code migrated to graph.nodes
- ✅ No active writes to graph.entities
- ⚠️ Table schema preserved for historical reference
- 📋 **Future**: Remove table entirely after audit period

**Confusion Point**:
The old `graph.entities` table was a **duplicate** created early in development. All GraphRAG code was already using `graph.nodes`. The table remains empty as a placeholder but can be safely dropped.

### graph.covariates - **REMOVED** ❌

**Migration Date**: 2025-09-01
**Reason**: Unused legacy from Microsoft GraphRAG reference implementation

**Old Approach**:
```sql
-- DEPRECATED (from Microsoft GraphRAG)
CREATE TABLE graph.covariates (
    covariate_id TEXT PRIMARY KEY,
    covariate_type TEXT,
    subject_id TEXT,
    object_id TEXT,
    ...
);
```

**Original Purpose** (Microsoft GraphRAG):
Covariates capture **claims** and **extracted knowledge** about entities that don't fit into simple relationships.

**Example Covariate**:
- **Subject**: "Supreme Court"
- **Covariate**: "has_jurisdiction"
- **Object**: "Federal constitutional law"

**Why Removed**:
- **Metadata Approach**: We use JSONB `metadata` columns instead for flexibility
- **Relationship Modeling**: Complex claims represented as `graph.edges` with rich metadata
- **Simpler Schema**: One less table to maintain

**Migration Path**:
```sql
-- Convert covariates to metadata in graph.nodes
UPDATE graph.nodes n
SET metadata = metadata || jsonb_build_object(
    'covariates', (
        SELECT jsonb_agg(
            jsonb_build_object(
                'type', c.covariate_type,
                'value', c.object_id
            )
        )
        FROM graph.covariates c
        WHERE c.subject_id = n.node_id
    )
)
WHERE EXISTS (
    SELECT 1 FROM graph.covariates c WHERE c.subject_id = n.node_id
);

-- Drop old table
DROP TABLE graph.covariates CASCADE;
```

### graph.embeddings - **REMOVED** ❌

**Migration Date**: 2025-10-02
**Reason**: Centralized storage created performance bottleneck

**Old Approach** (Centralized Embeddings Table):
```sql
-- DEPRECATED
CREATE TABLE graph.embeddings (
    embedding_id UUID PRIMARY KEY,
    source_id TEXT NOT NULL,       -- References chunk_id, node_id, etc.
    source_type TEXT NOT NULL,     -- 'chunk', 'entity', 'community'
    embedding_type TEXT NOT NULL,  -- 'jina_v4_contextual', 'jina_v4_entity'
    vector vector(2048) NOT NULL,
    model_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Required JOIN for every search
SELECT cc.*, 1 - (e.vector <=> query_vector) AS similarity
FROM graph.enhanced_contextual_chunks cc
JOIN graph.embeddings e ON e.source_id = cc.chunk_id  -- Performance bottleneck!
WHERE e.source_type = 'chunk'
ORDER BY e.vector <=> query_vector
LIMIT 10;
```

**New Approach** (Distributed Embeddings):
Embeddings stored **directly** in source tables:

```sql
-- No JOIN required! Much faster
SELECT
    chunk_id,
    content,
    1 - (vector <=> query_vector) AS similarity
FROM graph.enhanced_contextual_chunks
WHERE vector IS NOT NULL
ORDER BY vector <=> query_vector
LIMIT 10;
```

**Performance Impact**:
- **Query Speed**: 5-10x faster (no JOIN overhead)
- **Index Efficiency**: Dedicated HNSW index per table
- **Parallelization**: Better query parallelization
- **Cache Locality**: Better CPU cache performance

**Storage Trade-off**:
- **Old**: One centralized table (easier to manage)
- **New**: Multiple vector columns (better performance, slightly more storage)

**Migration Script** (from migration 011 - updated to 2048-dim):
```sql
-- Add vector columns to tables (ALL using 2048-dim Jina v4)
ALTER TABLE graph.nodes ADD COLUMN embedding vector(2048);
ALTER TABLE graph.communities ADD COLUMN summary_embedding vector(2048);
ALTER TABLE graph.chunks ADD COLUMN content_embedding vector(2048);
ALTER TABLE graph.enhanced_contextual_chunks ADD COLUMN vector vector(2048);
ALTER TABLE graph.reports ADD COLUMN report_embedding vector(2048);

-- Migrate data
UPDATE graph.nodes n
SET embedding = e.vector
FROM graph.embeddings e
WHERE e.source_id = n.node_id AND e.source_type = 'entity';

UPDATE graph.communities c
SET summary_embedding = e.vector
FROM graph.embeddings e
WHERE e.source_id = c.community_id AND e.source_type = 'community';

-- ... (similar for other tables)

-- Create HNSW indexes
CREATE INDEX idx_nodes_embedding
ON graph.nodes USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Drop old table
DROP TABLE graph.embeddings CASCADE;
```

---

## 7. Public Schema (Configuration and Utilities)

### public.vector_search_config

**Purpose**: Global configuration for vector search parameters and optimization

**Status**: ✅ ACTIVE (1 row - singleton configuration)

**Table Definition**:
```sql
CREATE TABLE public.vector_search_config (
    id SERIAL PRIMARY KEY,

    -- Search Parameters
    default_similarity_threshold REAL DEFAULT 0.7,  -- Minimum similarity score
    default_limit INTEGER DEFAULT 10,               -- Default result count

    -- HNSW Index Parameters
    hnsw_m INTEGER DEFAULT 16,                      -- Max connections per layer
    hnsw_ef_construction INTEGER DEFAULT 64,        -- Index build quality
    hnsw_ef_search INTEGER DEFAULT 40,              -- Search quality

    -- Model Configuration
    embedding_model TEXT DEFAULT 'jina-embeddings-v4',
    embedding_dimension INTEGER DEFAULT 2048,

    -- Performance Tuning
    enable_approximate_search BOOLEAN DEFAULT TRUE,
    max_concurrent_searches INTEGER DEFAULT 10,

    -- Metadata
    config_version TEXT DEFAULT '1.0',
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by TEXT
);

-- Singleton constraint (only one config row allowed)
CREATE UNIQUE INDEX idx_vector_search_config_singleton ON public.vector_search_config((id IS NOT NULL));
```

**Configuration Values** (Current Production):
```sql
SELECT * FROM public.vector_search_config;

-- Expected output:
{
    "id": 1,
    "default_similarity_threshold": 0.7,
    "default_limit": 10,
    "hnsw_m": 16,
    "hnsw_ef_construction": 64,
    "hnsw_ef_search": 40,
    "embedding_model": "jina-embeddings-v4",
    "embedding_dimension": 2048,
    "enable_approximate_search": true,
    "max_concurrent_searches": 10,
    "config_version": "1.0",
    "last_updated": "2025-01-21T..."
}
```

**Usage in Application Code**:
```python
# GraphRAG Service fetches config on startup
from shared.clients.supabase_client import create_supabase_client

client = create_supabase_client("graphrag-service")
config = client.get("public.vector_search_config", limit=1)[0]

# Use config for vector search
similarity_threshold = config["default_similarity_threshold"]
search_limit = config["default_limit"]

# Query with configured parameters
results = client.execute_sql(f"""
    SELECT chunk_id, content,
           1 - (vector <=> :query_vector) AS similarity
    FROM graph.enhanced_contextual_chunks
    WHERE (1 - (vector <=> :query_vector)) >= {similarity_threshold}
    ORDER BY vector <=> :query_vector
    LIMIT {search_limit}
""")
```

**Updating Configuration**:
```sql
-- Update search parameters (requires admin privileges)
UPDATE public.vector_search_config
SET
    default_similarity_threshold = 0.75,
    hnsw_ef_search = 50,
    last_updated = NOW(),
    updated_by = 'system_admin'
WHERE id = 1;
```

**Design Rationale**:
- **Singleton Pattern**: Only one configuration row prevents configuration drift
- **Centralized Management**: All vector search settings in one place
- **Dynamic Updates**: Change search parameters without code deployment
- **Performance Tuning**: Adjust HNSW parameters based on production metrics
- **Model Versioning**: Track embedding model changes for migration planning

---

## 8. Embedding/Vector Storage Strategy

### Distributed Embedding Architecture

**Design Decision**: Store embeddings **directly in source tables** instead of centralized table

**Motivation**:
1. **Query Performance**: Eliminates JOIN overhead for vector similarity search
2. **Index Optimization**: Dedicated HNSW index per table with tuned parameters
3. **Parallel Queries**: Better query parallelization across tables
4. **Cache Efficiency**: Improved CPU cache locality for similarity calculations

**Vector Dimensions**:
- **2048 dimensions**: ✅ **STANDARD** - All active tables use Jina v4 2048-dim embeddings
  - graph.nodes.embedding
  - graph.communities.summary_embedding
  - graph.chunks.content_embedding
  - graph.enhanced_contextual_chunks.vector
  - graph.reports.report_embedding
- **2000 dimensions**: 🔻 **DEPRECATED** - Only in empty graph.entities table (marked for removal)

### Distributed Embedding Tables

#### graph.chunks.content_embedding (Jina v4, 2048-dim)
```sql
ALTER TABLE graph.chunks ADD COLUMN content_embedding vector(2048);

CREATE INDEX idx_chunks_content_embedding
ON graph.chunks USING hnsw (content_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
WHERE content_embedding IS NOT NULL;
```

**Use Case**: Basic semantic search over document chunks

**Example Query**:
```sql
-- Find similar chunks (no JOIN required!)
SELECT chunk_id, content,
       1 - (content_embedding <=> :query_embedding) AS similarity
FROM graph.chunks
WHERE content_embedding IS NOT NULL
  AND (1 - (content_embedding <=> :query_embedding)) >= 0.7
ORDER BY content_embedding <=> :query_embedding
LIMIT 10;
```

#### graph.enhanced_contextual_chunks.vector (Jina v4, 2048-dim)
```sql
ALTER TABLE graph.enhanced_contextual_chunks ADD COLUMN vector vector(2048);

CREATE INDEX idx_enhanced_chunks_vector_hnsw
ON graph.enhanced_contextual_chunks USING hnsw (vector vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
WHERE vector IS NOT NULL;
```

**Use Case**: **Primary search target** - Anthropic-style contextual retrieval

**Performance Characteristics**:
- 15-20% better retrieval accuracy vs. plain chunks
- Consistent 2048-dim standard across all embeddings
- Best for legal research and precedent discovery

#### graph.nodes.embedding (Jina v4, 2048-dim)
```sql
ALTER TABLE graph.nodes ADD COLUMN embedding vector(2048);

CREATE INDEX idx_nodes_embedding
ON graph.nodes USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
WHERE embedding IS NOT NULL;
```

**Use Case**: Entity deduplication and entity-centric search

**Deduplication Process**:
1. Extract entities from document
2. Generate embeddings for each entity text
3. Calculate cosine similarity against existing entities
4. If similarity >= 0.85 → **Merge** (same canonical entity)
5. If similarity < 0.85 → **New entity**

**Example Query**:
```sql
-- Find similar entities for deduplication
SELECT node_id, title,
       1 - (embedding <=> :entity_embedding) AS similarity
FROM graph.nodes
WHERE node_type = 'entity'
  AND embedding IS NOT NULL
  AND (1 - (embedding <=> :entity_embedding)) >= 0.85
ORDER BY embedding <=> :entity_embedding
LIMIT 1;
```

#### graph.communities.summary_embedding (Jina v4, 2048-dim)
```sql
ALTER TABLE graph.communities ADD COLUMN summary_embedding vector(2048);

CREATE INDEX idx_communities_summary_embedding
ON graph.communities USING hnsw (summary_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
WHERE summary_embedding IS NOT NULL;
```

**Use Case**: Global search across knowledge graph communities

**Community Summary Embedding Process**:
1. Detect communities using Leiden algorithm
2. Generate AI summary of community (via Prompt Service)
3. Embed summary text using Jina v4
4. Store embedding in `summary_embedding` column

**Example Query**:
```sql
-- Find relevant communities for broad query
SELECT community_id, title, summary,
       1 - (summary_embedding <=> :query_embedding) AS similarity
FROM graph.communities
WHERE summary_embedding IS NOT NULL
  AND (1 - (summary_embedding <=> :query_embedding)) >= 0.6
ORDER BY summary_embedding <=> :query_embedding
LIMIT 5;
```

### pgvector Indexes

**Index Type**: HNSW (Hierarchical Navigable Small World)

**Why HNSW?**
- **Fast approximate nearest neighbor (ANN) search**
- **High recall** (>95% at default settings)
- **Scales to millions of vectors**
- **Better than IVFFlat** for most use cases

**HNSW Parameters**:
```sql
CREATE INDEX ON table_name
USING hnsw (vector_column vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `m` | 16 | Maximum connections per layer (16 = balanced speed/recall) |
| `ef_construction` | 64 | Size of dynamic candidate list during index build (64 = good quality) |
| `vector_cosine_ops` | - | Use cosine distance operator (<=> for similarity: 1 - distance) |

**Index Performance**:

| Vector Count | Index Size | Build Time | Query Time |
|--------------|------------|-----------|------------|
| 1,000 | 2 MB | 5 sec | 2-5 ms |
| 10,000 | 20 MB | 30 sec | 5-15 ms |
| 100,000 | 200 MB | 5 min | 15-50 ms |
| 1,000,000 | 2 GB | 30 min | 50-150 ms |

**Query Operators**:
- `<=>`: Cosine distance (used for similarity: `1 - (vec1 <=> vec2)`)
- `<->`: L2 distance (Euclidean)
- `<#>`: Inner product

**Similarity Calculation**:
```sql
-- Cosine similarity (0 = dissimilar, 1 = identical)
SELECT 1 - (vector1 <=> vector2) AS cosine_similarity;

-- Distance (0 = identical, 2 = opposite)
SELECT vector1 <=> vector2 AS cosine_distance;
```

**Query Tuning** (Runtime):
```sql
-- Increase search quality (slower but more accurate)
SET hnsw.ef_search = 100;  -- Default: 40

-- Maintenance work memory (for index creation)
SET maintenance_work_mem = '2GB';  -- Default: 64MB
```

### Performance Characteristics

**Embedding Generation Speed** (vLLM Embeddings Service, GPU 1):
- Single chunk: ~15-25ms
- Batch (10 chunks): ~80-120ms
- Batch (100 chunks): ~600-900ms

**Search Performance** (with HNSW indexes):
- Semantic search (1,000 chunks): ~5-15ms
- Hybrid search (1,000 chunks): ~20-40ms
- Local search (community of 50 nodes): ~3-8ms
- Global search (5 communities): ~30-60ms

**Scaling Recommendations**:
- **10,000 chunks**: Default settings work well (~20-50ms queries)
- **100,000 chunks**: Increase `ef_search` to 80 (~50-150ms queries)
- **1,000,000 chunks**: Consider partitioning by `client_id` or `case_id`

### Scaling Considerations

**Partitioning Strategy** (for 1M+ vectors):

```sql
-- Partition graph.enhanced_contextual_chunks by client_id
CREATE TABLE graph.enhanced_contextual_chunks_template (
    LIKE graph.enhanced_contextual_chunks INCLUDING ALL
) PARTITION BY HASH (metadata->>'client_id');

-- Create partitions (e.g., 16 partitions for large deployments)
CREATE TABLE graph.chunks_p0 PARTITION OF graph.enhanced_contextual_chunks_template
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE graph.chunks_p1 PARTITION OF graph.enhanced_contextual_chunks_template
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
-- ... (create remaining partitions)

-- Separate HNSW index per partition
CREATE INDEX ON graph.chunks_p0 USING hnsw (vector vector_cosine_ops);
CREATE INDEX ON graph.chunks_p1 USING hnsw (vector vector_cosine_ops);
-- ... (create indexes for remaining partitions)
```

**Benefits of Partitioning**:
- Smaller indexes per partition (faster builds, better query performance)
- Parallel query execution across partitions
- Easier index maintenance (REINDEX per partition)
- Tenant isolation (one partition per large client)

---

## 9. Data Flow Through System

### Complete Pipeline Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. DOCUMENT UPLOAD                            │
│                  Document Upload Service (Port 8008)             │
│                                                                  │
│  PDF/DOCX/TXT/MD → Markdown Conversion → S3/Local Storage       │
│                                                                  │
│  Outputs: markdown_content, document_metadata                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  2. ENTITY EXTRACTION                            │
│              Entity Extraction Service (Port 8007)               │
│                                                                  │
│  Modes: AI_ENHANCED (vLLM) | REGEX (Pattern-based) | HYBRID     │
│  Extracts: 31 Legal Entity Types + Citations + Relationships    │
│                                                                  │
│  Outputs:                                                        │
│    - entities[] (with confidence, position, context)             │
│    - citations[] (case law, statutes, regulations)               │
│    - relationships[] (entity-entity connections)                 │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ├─────────────────────┬─────────────────────┐
                 │                     │                     │
                 ▼                     ▼                     ▼
        ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
        │law.entities │      │law.citations │      │law.entity_   │
        │             │      │ (DEPRECATED) │      │relationships │
        │ (audit)     │      └──────────────┘      │ (audit)      │
        └─────────────┘                            └──────────────┘
     OR
        ┌──────────────┐
        │client.entities│
        │ (audit)       │
        └──────────────┘
                 │
                 │  RAW EXTRACTION STORAGE
                 │  (Document-scoped, pre-deduplication)
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   3. DOCUMENT CHUNKING                           │
│                 Chunking Service (Port 8009)                     │
│                                                                  │
│  Strategies:                                                     │
│    - Basic: 512 tokens, 128 overlap, sentence-aware             │
│    - Contextual: Anthropic-style enhancement with metadata      │
│                                                                  │
│  Outputs:                                                        │
│    - chunks[] (basic chunks)                                     │
│    - enhanced_chunks[] (with situational context)                │
│    - embeddings[] (2048-dim Jina v4 vectors)                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ├─────────────────────┬─────────────────────┐
                 ▼                     ▼                     ▼
        ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
        │graph.chunks │      │graph.enhanced│      │graph.text_   │
        │             │      │_contextual_  │      │units         │
        │ +embedding  │      │chunks        │      │              │
        │ (2048-dim)  │      │ +vector      │      │ (MS GraphRAG)│
        │             │      │ (2048-dim)   │      │              │
        └─────────────┘      └──────────────┘      └──────────────┘
                 │
                 │  CHUNK STORAGE
                 │  (Vector embeddings included)
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  4. GRAPHRAG PROCESSING                          │
│                 GraphRAG Service (Port 8010)                     │
│              Microsoft GraphRAG Implementation                   │
│                                                                  │
│  Step 1: Entity Deduplication (0.85 similarity threshold)       │
│    - Compare entity embeddings                                  │
│    - Merge duplicates → Canonical entities                      │
│    - Map: original_id → canonical_id                            │
│                                                                  │
│  Step 2: Relationship Discovery                                 │
│    - Citation analysis                                           │
│    - Co-occurrence patterns                                      │
│    - Cross-document linking                                      │
│                                                                  │
│  Step 3: Community Detection (Leiden Algorithm)                 │
│    - Resolution: 1.0 (configurable)                             │
│    - Min community size: 3 entities                             │
│    - Hierarchical: levels 0, 1, 2                               │
│                                                                  │
│  Step 4: AI Summary Generation                                  │
│    - Prompt Service integration                                  │
│    - Community summaries (2-3 sentences)                         │
│    - Embed summaries (2048-dim vectors)                         │
│                                                                  │
│  Step 5: Graph Analytics                                        │
│    - Centrality calculation                                      │
│    - Importance scoring                                          │
│    - Quality metrics                                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ├─────────────────────┬──────────────────────┐
                 ▼                     ▼                      ▼
        ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
        │graph.nodes  │      │graph.edges   │      │graph.communities│
        │             │      │              │      │              │
        │ CANONICAL   │      │ DEDUPLICATED │      │ AI SUMMARIES │
        │ ENTITIES    │      │ RELATIONSHIPS│      │ + EMBEDDINGS │
        │             │      │              │      │              │
        │ +embedding  │      │ +confidence  │      │ +summary_    │
        │ (2048-dim)  │      │  +weight     │      │  embedding   │
        │             │      │              │      │ (2048-dim)   │
        └──────┬──────┘      └──────────────┘      └──────────────┘
               │
               └─────→ graph.node_communities (Many-to-Many junction table)
```

### Processing Stages Detail

#### Stage 1: Document Upload
```
Input:  PDF/DOCX/TXT file
Output: markdown_content, document_metadata
Time:   0.5-2 seconds per document
```

#### Stage 2: Entity Extraction
```
Input:  markdown_content
Output: entities[], citations[], relationships[]
Time:   2-10 seconds per document (AI_ENHANCED mode)
        0.5-2 seconds per document (REGEX mode)
```

**Entity Extraction Output Example**:
```json
{
  "entities": [
    {
      "entity_id": "ent_rahimi_scotus_001",
      "entity_text": "Supreme Court of the United States",
      "entity_type": "COURT",
      "confidence": 0.97,
      "start_position": 145,
      "end_position": 180,
      "context": "In the Supreme Court case of...",
      "attributes": {
        "jurisdiction": "federal",
        "level": "supreme"
      }
    }
  ],
  "citations": [
    {
      "citation_id": "cite_bruen_001",
      "citation_text": "New York State Rifle & Pistol Association, Inc. v. Bruen, 597 U.S. 1 (2022)",
      "citation_type": "CASE_CITATION",
      "confidence": 0.98
    }
  ],
  "relationships": [
    {
      "relationship_id": "rel_001",
      "source_entity": "ent_rahimi_scotus_001",
      "target_entity": "cite_bruen_001",
      "relationship_type": "CITES",
      "confidence": 0.92
    }
  ]
}
```

#### Stage 3: Document Chunking
```
Input:  markdown_content, entities[]
Output: chunks[], enhanced_chunks[], embeddings[]
Time:   1-5 seconds per document (chunking + embedding)
```

**Enhanced Chunk Output Example**:
```json
{
  "enhanced_chunks": [
    {
      "chunk_id": "chunk_rahimi_001",
      "content": "The Court held that the Second Amendment protects...",
      "contextualized_content": "Document: Rahimi v. United States (2024). Topic: Second Amendment. The Court held that the Second Amendment protects...",
      "situational_context": "Rahimi v. US | Constitutional Analysis | SCOTUS",
      "quality_score": 0.92,
      "vector": [0.123, -0.456, 0.789, ...]  // 2048 dimensions
    }
  ]
}
```

#### Stage 4: GraphRAG Processing
```
Input:  entities[], citations[], relationships[], enhanced_chunks[]
Output: graph.nodes, graph.edges, graph.communities
Time:   5-20 seconds per document (depends on entity count)
```

**GraphRAG Output Example**:
```json
{
  "success": true,
  "graph_id": "graph_rahimi_1735689600",
  "graph_summary": {
    "nodes_created": 37,
    "edges_created": 23,
    "communities_detected": 4,
    "deduplication_rate": 0.18,
    "processing_time_seconds": 8.5
  },
  "communities": [
    {
      "community_id": "comm_2a_doctrine_001",
      "title": "Second Amendment Doctrine",
      "ai_summary": "This community centers around landmark Second Amendment cases...",
      "node_count": 12,
      "coherence_score": 0.91
    }
  ]
}
```

### Error Handling and Recovery

**Failed Processing Stages**:
```sql
-- Track processing status in document_registry
UPDATE graph.document_registry
SET processing_status = 'failed',
    pipeline_stage = 'entity_extraction',
    metadata = metadata || jsonb_build_object(
        'error_message', 'Extraction timeout',
        'failed_at', NOW()
    )
WHERE document_id = :failed_document_id;

-- Query failed documents for retry
SELECT document_id, pipeline_stage, metadata->>'error_message'
FROM graph.document_registry
WHERE processing_status = 'failed'
ORDER BY created_at DESC;
```

**Retry Strategy**:
1. **Transient Failures** (timeouts, rate limits): Retry 3x with exponential backoff
2. **Persistent Failures** (invalid format, corruption): Mark as failed, require manual intervention
3. **Partial Failures** (some entities extracted): Store partial results, mark stage as completed with warnings

---

## 10. Key Design Patterns

### Entity Lifecycle

```
┌───────────────────────────────────────────────────────────┐
│                  ENTITY LIFECYCLE                          │
└───────────────────────────────────────────────────────────┘

1. RAW EXTRACTION (Document-Scoped)
   ┌──────────────────────────────────────┐
   │ Entity Extraction Service            │
   │ - Text: "Supreme Court"              │
   │ - Type: COURT                        │
   │ - Confidence: 0.95                   │
   │ - Position: char 145-160             │
   │ - Context: "In the Supreme Court..." │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ law.entities OR client.entities      │
   │ - entity_id: ent_doc001_court_001    │
   │ - document_id: rahimi_v_us_2024      │
   │ - entity_text: "Supreme Court"       │
   │ - extraction_method: ai_enhanced     │
   └────────────┬─────────────────────────┘
                │
                │ IMMUTABLE AUDIT TRAIL
                │ (preserved for compliance)
                │
                ▼

2. DOMAIN STORAGE (Pre-Deduplication)
   ┌──────────────────────────────────────┐
   │ Multiple documents extract same entity:│
   │                                       │
   │ doc_001: "Supreme Court" (0.97)      │
   │ doc_002: "U.S. Supreme Court" (0.94) │
   │ doc_003: "SCOTUS" (0.89)             │
   │ doc_004: "Supreme Court of US" (0.92)│
   └────────────┬─────────────────────────┘
                │
                │ ALL STORED SEPARATELY
                │ (document-scoped IDs)
                │
                ▼

3. DEDUPLICATION (GraphRAG Service)
   ┌──────────────────────────────────────┐
   │ Entity Deduplicator                  │
   │ - Generate embeddings                │
   │ - Calculate cosine similarity        │
   │ - Threshold: 0.85                    │
   │ - Legal entity type boost: +0.05     │
   └────────────┬─────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────┐
   │ Similarity Matrix:                   │
   │                                      │
   │ "Supreme Court" ↔ "U.S. Supreme Court" = 0.92 ✓ MERGE│
   │ "Supreme Court" ↔ "SCOTUS" = 0.78 ✗ SEPARATE         │
   │ "Supreme Court" ↔ "Supreme Court of US" = 0.88 ✓ MERGE│
   └────────────┬─────────────────────────┘
                │
                ▼

4. CANONICAL REPRESENTATION (graph.nodes)
   ┌──────────────────────────────────────┐
   │ graph.nodes (Canonical Entities)     │
   │                                      │
   │ Node 1:                              │
   │  - node_id: node_scotus_canonical_001│
   │  - title: "Supreme Court of the      │
   │             United States"           │
   │  - source_ids: [ent_doc001_court_001,│
   │                 ent_doc002_court_003,│
   │                 ent_doc004_court_002]│
   │  - degree: 45 (connections)          │
   │  - importance_score: 0.95            │
   │  - embedding: [vector...]            │
   │                                      │
   │ Node 2:                              │
   │  - node_id: node_scotus_acronym_001  │
   │  - title: "SCOTUS"                   │
   │  - source_ids: [ent_doc003_court_001]│
   │  - degree: 12                        │
   │  - importance_score: 0.72            │
   └────────────┬─────────────────────────┘
                │
                │ SINGLE SOURCE OF TRUTH
                │ (deduplicated, canonical)
                │
                ▼

5. GRAPH INTEGRATION
   ┌──────────────────────────────────────┐
   │ graph.edges (Relationships)          │
   │                                      │
   │ - node_scotus_canonical_001 →        │
   │   node_case_rahimi_001               │
   │   (DECIDED_CASE, weight: 1.0)        │
   │                                      │
   │ - node_scotus_canonical_001 →        │
   │   node_scotus_acronym_001            │
   │   (ALIAS_OF, weight: 0.85)           │
   └──────────────────────────────────────┘
```

**Key Takeaways**:
1. **Raw → Domain → Graph**: Three-stage entity lifecycle prevents data loss
2. **Audit Trail**: Original extractions preserved in law/client schemas
3. **Deduplication**: Semantic similarity (0.85 threshold) with legal type awareness
4. **Canonical IDs**: graph.nodes contains merged, deduplicated entities
5. **Relationship Mapping**: Original entity IDs mapped to canonical IDs for graph.edges

### Multi-Tenancy Enforcement

**Strategy**: Dedicated columns (`client_id`, `case_id`) with JSONB metadata fallback

```sql
-- EFFICIENT: Direct column filtering
SELECT node_id, title, importance_score
FROM graph.nodes
WHERE client_id = 'client_uuid_123'  -- Indexed column
  AND node_type = 'entity'
ORDER BY importance_score DESC;

-- FALLBACK: JSONB metadata filtering (slower)
SELECT chunk_id, content
FROM graph.enhanced_contextual_chunks
WHERE metadata->>'client_id' = 'client_uuid_123'  -- GIN index
ORDER BY created_at DESC;
```

**RLS Policies** (Enabled but Pending Implementation):

```sql
-- Enable RLS on graph tables
ALTER TABLE graph.nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph.edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph.communities ENABLE ROW LEVEL SECURITY;

-- Future RLS policy for client isolation
CREATE POLICY client_isolation ON graph.nodes
FOR ALL
USING (
    client_id IS NULL  -- Public content (law schema)
    OR client_id = current_setting('app.current_client_id', true)::UUID
);

-- Future RLS policy for service_role (bypass)
CREATE POLICY service_role_all_access ON graph.nodes
FOR ALL
TO service_role
USING (true);
```

**Current Enforcement**:
- **Application-Level**: GraphRAG Service validates `client_id` on all operations
- **Database-Level**: RLS enabled but permissive (allows all with service_role)
- **Future**: Implement JWT-based RLS policies for production multi-tenancy

### Scalability Patterns

#### Partitioning Strategy for graph.nodes (HASH by client_id)

**Trigger**: When `client_id` count > 100 OR total nodes > 1,000,000

```sql
-- Create partitioned table
CREATE TABLE graph.nodes_partitioned (
    LIKE graph.nodes INCLUDING ALL
) PARTITION BY HASH (client_id);

-- Create partitions (16 for large deployments)
CREATE TABLE graph.nodes_p0 PARTITION OF graph.nodes_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE graph.nodes_p1 PARTITION OF graph.nodes_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
-- ... (create p2-p15)

-- Migrate data
INSERT INTO graph.nodes_partitioned SELECT * FROM graph.nodes;

-- Swap tables
ALTER TABLE graph.nodes RENAME TO graph.nodes_old;
ALTER TABLE graph.nodes_partitioned RENAME TO graph.nodes;

-- Create indexes per partition
CREATE INDEX idx_nodes_p0_type ON graph.nodes_p0(node_type);
CREATE INDEX idx_nodes_p0_embedding
ON graph.nodes_p0 USING hnsw (embedding vector_cosine_ops);
-- ... (repeat for all partitions)
```

**Benefits**:
- **Parallel Queries**: PostgreSQL queries partitions in parallel
- **Smaller Indexes**: 16x smaller indexes → faster builds and queries
- **Maintenance**: REINDEX per partition instead of entire table
- **Tenant Isolation**: Large clients get dedicated partitions

#### Partitioning Strategy for graph.edges (RANGE by created_at)

**Trigger**: When edges > 10,000,000 OR query performance degrades

```sql
-- Create partitioned table
CREATE TABLE graph.edges_partitioned (
    LIKE graph.edges INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create monthly partitions (time-series optimization)
CREATE TABLE graph.edges_2024_01 PARTITION OF graph.edges_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE graph.edges_2024_02 PARTITION OF graph.edges_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... (create ongoing partitions)

-- Default partition for future data
CREATE TABLE graph.edges_default PARTITION OF graph.edges_partitioned DEFAULT;

-- Migrate data
INSERT INTO graph.edges_partitioned SELECT * FROM graph.edges;

-- Swap tables
ALTER TABLE graph.edges RENAME TO graph.edges_old;
ALTER TABLE graph.edges_partitioned RENAME TO graph.edges;
```

**Benefits**:
- **Partition Pruning**: Queries with `WHERE created_at > ...` only scan relevant partitions
- **Archiving**: Older partitions can be moved to cold storage or compressed
- **Maintenance**: DROP old partitions instead of DELETE (faster, no vacuuming)

#### Hot/Warm/Cold Data Archiving

**Data Lifecycle**:
- **Hot** (< 90 days): Active cases, recent research → SSD storage, full indexing
- **Warm** (90 days - 2 years): Closed cases, historical precedents → SSD/HDD, selective indexing
- **Cold** (> 2 years): Long-term archive → Compressed HDD/S3, minimal indexing

**Implementation**:
```sql
-- Create archive schema for cold data
CREATE SCHEMA archive;

-- Move old data to archive
CREATE TABLE archive.nodes_2023 AS
SELECT * FROM graph.nodes
WHERE created_at < '2023-01-01';

CREATE TABLE archive.edges_2023 AS
SELECT * FROM graph.edges
WHERE created_at < '2023-01-01';

-- Compress archive tables
ALTER TABLE archive.nodes_2023 SET (fillfactor = 100);
VACUUM FULL archive.nodes_2023;

-- Create minimal indexes (only for occasional queries)
CREATE INDEX ON archive.nodes_2023(node_id);
CREATE INDEX ON archive.edges_2023(source_node_id, target_node_id);

-- Remove from hot storage
DELETE FROM graph.nodes WHERE created_at < '2023-01-01';
DELETE FROM graph.edges WHERE created_at < '2023-01-01';
VACUUM FULL graph.nodes;
VACUUM FULL graph.edges;
```

**Query Pattern for Archived Data**:
```sql
-- Create VIEW spanning hot + warm + cold
CREATE VIEW graph.nodes_all AS
SELECT * FROM graph.nodes           -- Hot
UNION ALL
SELECT * FROM graph.nodes_2024      -- Warm
UNION ALL
SELECT * FROM archive.nodes_2023;   -- Cold

-- Applications query VIEW instead of table
SELECT node_id, title FROM graph.nodes_all
WHERE title ILIKE '%Bruen%';
```

---

## 11. Common Query Patterns

### Entity-Centric Queries

#### Find all documents mentioning entity X

```sql
-- Find entity across all documents via metadata
SELECT node_id, title, metadata->>'document_id' AS document_id
FROM graph.nodes
WHERE metadata @> '{"entity_text": "Bruen"}'
  AND node_type = 'entity'
ORDER BY importance_score DESC;

-- Alternative: Find all chunks referencing the entity
SELECT cc.chunk_id, cc.content, cc.document_id
FROM graph.enhanced_contextual_chunks cc
WHERE cc.content ILIKE '%Bruen%'
  OR cc.contextualized_content ILIKE '%Bruen%'
ORDER BY cc.quality_score DESC;
```

#### Get canonical form of entity across documents

```sql
-- Find merged entity with all source documents
SELECT
    n.node_id,
    n.title AS canonical_name,
    n.degree,
    n.importance_score,
    COUNT(DISTINCT n.metadata->>'document_id') AS document_count,
    ARRAY_AGG(DISTINCT n.metadata->>'document_id') AS documents
FROM graph.nodes n
WHERE n.title ILIKE '%Bruen%'
  AND n.node_type = 'entity'
GROUP BY n.node_id, n.title, n.degree, n.importance_score
ORDER BY n.importance_score DESC;
```

### Graph Traversal Queries

#### Find all entities connected to X within 2 hops

```sql
WITH RECURSIVE entity_network AS (
    -- Base case: Starting entity
    SELECT
        n.node_id,
        n.title,
        0 AS hop_distance,
        ARRAY[n.node_id] AS path
    FROM graph.nodes n
    WHERE n.title ILIKE '%Second Amendment%'
      AND n.node_type = 'entity'

    UNION

    -- Recursive case: Expand network
    SELECT
        n2.node_id,
        n2.title,
        en.hop_distance + 1,
        en.path || n2.node_id
    FROM entity_network en
    JOIN graph.edges e ON (en.node_id = e.source_node_id OR en.node_id = e.target_node_id)
    JOIN graph.nodes n2 ON (
        CASE
            WHEN en.node_id = e.source_node_id THEN n2.node_id = e.target_node_id
            ELSE n2.node_id = e.source_node_id
        END
    )
    WHERE en.hop_distance < 2
      AND NOT (n2.node_id = ANY(en.path))  -- Prevent cycles
)
SELECT DISTINCT
    node_id,
    title,
    hop_distance,
    path
FROM entity_network
ORDER BY hop_distance, title;
```

#### Get community members for entity X

```sql
-- Find entity's community and all members
SELECT
    n.node_id,
    n.title,
    n.node_type,
    n.importance_score,
    c.title AS community_name,
    c.summary AS community_summary,
    nc.membership_strength
FROM graph.nodes n
JOIN graph.node_communities nc ON n.node_id = nc.node_id
JOIN graph.communities c ON nc.community_id = c.community_id
WHERE c.community_id = (
    -- Subquery: Find entity's primary community
    SELECT community_id
    FROM graph.nodes
    WHERE title ILIKE '%Bruen%'
      AND node_type = 'entity'
    LIMIT 1
)
ORDER BY nc.membership_strength DESC, n.importance_score DESC;
```

### Cross-Document Queries

#### Find all documents citing case Y

```sql
-- Method 1: Via edges (fastest, requires deduplication)
SELECT DISTINCT
    source_doc.document_id,
    source_doc.title,
    e.edge_type,
    e.confidence_score
FROM graph.edges e
JOIN graph.nodes target_node ON e.target_node_id = target_node.node_id
JOIN graph.nodes source_node ON e.source_node_id = source_node.node_id
JOIN graph.document_registry source_doc
    ON source_doc.document_id = source_node.metadata->>'document_id'
WHERE target_node.title ILIKE '%Bruen%'
  AND target_node.metadata->>'entity_type' = 'CASE_CITATION'
  AND e.edge_type = 'CITES'
ORDER BY e.confidence_score DESC;

-- Method 2: Via chunk content search (citation text-based)
SELECT DISTINCT
    cc.document_id,
    dr.title AS document_title,
    cc.quality_score
FROM graph.enhanced_contextual_chunks cc
JOIN graph.document_registry dr
    ON cc.document_id = dr.document_id
WHERE (cc.content ILIKE '%Bruen%' OR cc.contextualized_content ILIKE '%Bruen%')
  AND cc.quality_score >= 0.7
ORDER BY cc.quality_score DESC;
```

#### Discover related documents via entity overlap

```sql
-- Find documents sharing entities with target document
WITH target_entities AS (
    -- Get entities from target document
    SELECT DISTINCT node_id, title
    FROM graph.nodes
    WHERE metadata->>'document_id' = 'rahimi_v_us_2024'
      AND node_type = 'entity'
),
related_documents AS (
    -- Find documents sharing these entities
    SELECT
        n.metadata->>'document_id' AS document_id,
        COUNT(DISTINCT n.node_id) AS shared_entity_count,
        ARRAY_AGG(DISTINCT n.title) AS shared_entities
    FROM graph.nodes n
    WHERE n.node_id IN (SELECT node_id FROM target_entities)
      AND n.metadata->>'document_id' != 'rahimi_v_us_2024'
    GROUP BY n.metadata->>'document_id'
    HAVING COUNT(DISTINCT n.node_id) >= 3  -- At least 3 shared entities
)
SELECT
    rd.document_id,
    dr.title,
    rd.shared_entity_count,
    rd.shared_entities
FROM related_documents rd
JOIN graph.document_registry dr ON rd.document_id = dr.document_id
ORDER BY rd.shared_entity_count DESC;
```

---

## 12. Migration Notes

### Removed Tables Migration (2025-09-01)

**Migration Script**: `sql-scripts/003_migrate_existing_data.sql`

**Tables Removed**:
1. `law.citations` → Migrated to `graph.nodes` with `entity_type = 'CASE_CITATION'`
2. `graph.entities` → Consolidated into `graph.nodes`
3. `graph.covariates` → Metadata moved to `graph.nodes.metadata`
4. `graph.embeddings` → Distributed to source tables (nodes, chunks, communities)

**Rollback Procedure**:

If migration causes issues, rollback is available:

```sql
BEGIN;

-- Restore law.citations from graph.nodes
CREATE TABLE law.citations AS
SELECT
    node_id AS citation_id,
    metadata->>'document_id' AS document_id,
    title AS citation_text,
    metadata->>'entity_type' AS citation_type,
    (metadata->>'confidence')::REAL AS confidence,
    created_at
FROM graph.nodes
WHERE metadata->>'source_table' = 'law.citations';

-- Restore graph.embeddings from distributed vectors
CREATE TABLE graph.embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    vector vector(2048),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO graph.embeddings (source_id, source_type, vector)
SELECT node_id, 'entity', embedding::vector(2048)
FROM graph.nodes WHERE embedding IS NOT NULL
UNION ALL
SELECT chunk_id, 'chunk', vector
FROM graph.enhanced_contextual_chunks WHERE vector IS NOT NULL
UNION ALL
SELECT community_id, 'community', summary_embedding::vector(2048)
FROM graph.communities WHERE summary_embedding IS NOT NULL;

COMMIT;
```

### Embedding Architecture Migration (2025-10-02)

**Migration Script**: `sql-scripts/011_add_vector_columns_to_graph_tables.sql`

**Changes**:
- **Before**: Centralized `graph.embeddings` table with JOINs
- **After**: Distributed vector columns in source tables

**Performance Impact**:
- **Query Speed**: 5-10x faster (no JOIN overhead)
- **Index Size**: +20% total storage (separate indexes per table)
- **Maintenance**: Easier index rebuilds (per-table instead of monolithic)

**Verification Queries**:

```sql
-- Check vector migration status
SELECT * FROM graph.count_vectors();

-- Expected output:
-- table_name | total_rows | vectors_populated | vectors_null | percentage_populated
-- nodes      | 1250       | 1200              | 50           | 96.00
-- communities| 45         | 42                | 3            | 93.33
-- chunks     | 3400       | 3350              | 50           | 98.53
-- reports    | 120        | 115               | 5            | 95.83

-- Test vector search performance
EXPLAIN ANALYZE
SELECT chunk_id, 1 - (vector <=> '[0.1, 0.2, ...]'::vector(2048)) AS similarity
FROM graph.enhanced_contextual_chunks
WHERE vector IS NOT NULL
ORDER BY vector <=> '[0.1, 0.2, ...]'::vector(2048)
LIMIT 10;

-- Should use index scan with HNSW
-- Execution time should be < 50ms for 10,000 chunks
```

---

## 13. Future Enhancements

### 1. Implement RLS Policies for Production

**Status**: Enabled but permissive (allows all via service_role)

**Implementation Plan**:

```sql
-- Phase 1: JWT-based tenant isolation
CREATE POLICY client_jwt_isolation ON graph.nodes
FOR ALL
USING (
    client_id IS NULL  -- Public content
    OR client_id = (current_setting('request.jwt.claims', true)::json->>'client_id')::UUID
);

CREATE POLICY case_jwt_isolation ON graph.nodes
FOR ALL
USING (
    case_id IS NULL  -- Not case-specific
    OR case_id = (current_setting('request.jwt.claims', true)::json->>'case_id')::UUID
    OR client_id = (current_setting('request.jwt.claims', true)::json->>'client_id')::UUID  -- Client can see all their cases
);

-- Phase 2: Service role bypass
CREATE POLICY service_role_bypass ON graph.nodes
FOR ALL
TO service_role
USING (true);

-- Phase 3: Enable policies
ALTER TABLE graph.nodes FORCE ROW LEVEL SECURITY;
ALTER TABLE graph.edges FORCE ROW LEVEL SECURITY;
ALTER TABLE graph.communities FORCE ROW LEVEL SECURITY;
```

**Testing Plan**:
1. Create test users with different `client_id` values
2. Verify isolation: User A cannot see User B's data
3. Verify public access: All users can see `client_id = NULL` data
4. Load testing: Ensure RLS doesn't degrade performance > 10%

### 2. Add Table Partitioning When Hitting Thresholds

**Trigger Thresholds**:
- `graph.nodes`: > 1,000,000 rows OR > 100 clients
- `graph.edges`: > 10,000,000 rows OR query latency > 500ms
- `graph.enhanced_contextual_chunks`: > 5,000,000 rows

**Partitioning Strategy**:

| Table | Partitioning Key | Partitioning Type | Partition Count |
|-------|------------------|-------------------|-----------------|
| graph.nodes | client_id | HASH | 16 |
| graph.edges | created_at | RANGE | Monthly |
| graph.enhanced_contextual_chunks | client_id | HASH | 16 |
| graph.communities | client_id | HASH | 8 |

**Implementation Roadmap**:
1. **Month 1**: Design partitioning strategy, test on staging
2. **Month 2**: Migrate graph.nodes to partitioned table (zero-downtime migration)
3. **Month 3**: Migrate graph.edges to partitioned table
4. **Month 4**: Monitor performance, adjust partition count if needed

### 3. Consider client.entities → VIEW Migration

**Current Approach**: Separate `client.entities` table with raw extraction data

**Proposed Approach**: Materialized VIEW over `graph.nodes`

```sql
-- Phase 1: Create materialized view
CREATE MATERIALIZED VIEW client.entities_mv AS
SELECT
    node_id AS entity_id,
    metadata->>'document_id' AS document_id,
    client_id,
    metadata->>'case_id' AS case_id,
    title AS entity_text,
    metadata->>'entity_type' AS entity_type,
    (metadata->>'confidence')::REAL AS confidence,
    (metadata->>'start_position')::INTEGER AS start_position,
    (metadata->>'end_position')::INTEGER AS end_position,
    metadata->>'context' AS context,
    metadata->>'extraction_method' AS extraction_method,
    metadata AS attributes,
    created_at
FROM graph.nodes
WHERE client_id IS NOT NULL
  AND node_type = 'entity';

-- Phase 2: Create indexes
CREATE UNIQUE INDEX ON client.entities_mv(entity_id);
CREATE INDEX ON client.entities_mv(document_id);
CREATE INDEX ON client.entities_mv(client_id);
CREATE INDEX ON client.entities_mv(entity_type);

-- Phase 3: Set up auto-refresh (hourly)
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
    'refresh-client-entities',
    '0 * * * *',  -- Every hour
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY client.entities_mv$$
);

-- Phase 4: Swap tables
ALTER TABLE client.entities RENAME TO client.entities_old;
ALTER MATERIALIZED VIEW client.entities_mv RENAME TO client.entities;

-- Phase 5: Update application code to use VIEW
-- (No code changes needed if using same column names)

-- Phase 6: After validation, drop old table
DROP TABLE client.entities_old CASCADE;
```

**Benefits**:
- **Single Source of Truth**: `graph.nodes` is canonical
- **Automatic Deduplication**: No duplicate entities
- **Reduced Storage**: ~50% storage savings (no duplicate data)
- **Easier Maintenance**: One table to maintain instead of two

**Tradeoffs**:
- **Refresh Latency**: Entities appear in VIEW after refresh (max 1 hour delay)
- **Audit Trail**: Lose original extraction timestamps (mitigated by metadata)
- **Query Performance**: Materialized VIEW is fast (similar to table)

**Decision Criteria**:
- Implement VIEW approach if audit trail is **not critical** for client documents
- Keep separate table if **real-time extraction tracking** is required
- Hybrid: Keep `client.entities` for 90 days, then migrate to VIEW for archiving

---

## 14. Conclusion

The Luris GraphRAG database schema implements a sophisticated three-tier architecture (law → client → graph) that balances **auditability**, **performance**, and **multi-tenancy**.

**Key Design Principles**:
1. **Raw Extraction Preservation**: law/client schemas maintain immutable audit trails
2. **Canonical Knowledge Graph**: graph schema provides deduplicated source of truth
3. **Distributed Embeddings**: Vector search optimized with per-table HNSW indexes
4. **Multi-Tenant Isolation**: Dedicated columns with RLS policy enforcement
5. **Scalability**: Partitioning strategies ready for production deployment

**Migration History**:
- **2025-09-01**: Removed redundant tables (law.citations, graph.entities, graph.covariates)
- **2025-10-02**: Migrated from centralized graph.embeddings to distributed vectors

This documentation serves as the **complete technical reference** for understanding, querying, and extending the Luris GraphRAG database architecture.

---

**For Questions or Issues**:
- GraphRAG Service: Port 8010
- Database Admin: Supabase Dashboard
- Migration Scripts: `/srv/luris/be/sql-scripts/`
- API Documentation: `/srv/luris/be/graphrag-service/api.md`

---

## 15. Common Schema Issues and Solutions

### Issue: PostgreSQL Views Not Updating with Schema Changes

**Problem**: When using `SELECT *` in view definitions, PostgreSQL captures the column list at view creation time. If columns are added to the base table later, the view will not automatically include them.

**Example Scenario**:
```sql
-- Step 1: Create base table
CREATE TABLE graph.document_registry (
    id UUID PRIMARY KEY,
    document_id TEXT,
    title TEXT,
    status TEXT
);

-- Step 2: Create view with SELECT *
CREATE VIEW public.graph_document_registry AS 
SELECT * FROM graph.document_registry;

-- Step 3: Add new column to base table
ALTER TABLE graph.document_registry ADD COLUMN processing_status TEXT;

-- Problem: View still only shows original 4 columns, not processing_status!
SELECT * FROM public.graph_document_registry;
-- Returns: id, document_id, title, status (missing processing_status)
```

**Solution**: Recreate the view after schema changes:
```sql
DROP VIEW IF EXISTS public.graph_document_registry;
CREATE OR REPLACE VIEW public.graph_document_registry AS 
SELECT * FROM graph.document_registry;
```

**Prevention Strategies**:

1. **Explicit Column Lists** (Recommended):
```sql
-- Instead of SELECT *, use explicit columns
CREATE VIEW public.graph_document_registry AS
SELECT 
    id,
    document_id,
    title,
    status,
    processing_status,
    metadata,
    created_at,
    updated_at
FROM graph.document_registry;
```

2. **View Recreation in Migrations**:
```sql
-- In the same migration that adds columns
BEGIN;

-- Add column
ALTER TABLE graph.document_registry ADD COLUMN processing_status TEXT;

-- Recreate view to include new column
CREATE OR REPLACE VIEW public.graph_document_registry AS
SELECT * FROM graph.document_registry;

COMMIT;
```

3. **Automated Testing**:
```python
def test_view_includes_all_columns():
    """Verify public view includes all base table columns"""
    from supabase import create_client
    
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get columns from view
    view_result = client.table('graph_document_registry').select('*').limit(1).execute()
    view_columns = set(view_result.data[0].keys()) if view_result.data else set()
    
    # Expected columns (must match base table)
    expected_columns = {
        'id', 'document_id', 'title', 'document_type', 
        'source_schema', 'status', 'processing_status', 
        'metadata', 'created_at', 'updated_at'
    }
    
    assert expected_columns.issubset(view_columns), \
        f"View missing columns: {expected_columns - view_columns}"
```

**Historical Example**:

On October 18, 2025, the GraphRAG service experienced a 20% failure rate due to `public.graph_document_registry` view missing the `processing_status` column that was added in migration `001_fix_schema_mismatches.sql`. The view was created before the migration, so it didn't include the new column.

**Fix Applied**: Migration `recreate_graph_document_registry_view` recreated the view to include all columns.

**Monitoring**: Add automated tests to verify view column completeness after every schema migration.

---
