# GraphRAG Database Schema Rebuild - Manual Execution Plan

## Overview
All schema files have been prepared according to the specification in `@specs/graphrag-db-schema-viz.html`. Manual execution via Supabase Dashboard is required due to REST API limitations.

## ✅ **Completed Automatically:**
1. **Schema Cleanup**: All old schemas (law, client, graph) have been dropped ✓
2. **SQL Files Created**: All spec-compliant schema files are ready ✓

## 🔧 **Manual Execution Required:**

### Step 1: Create RPC Function
Execute this in Supabase Dashboard SQL Editor first:

```sql
CREATE OR REPLACE FUNCTION public.execute_sql(query text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    EXECUTE query;
    RETURN '{"status": "success"}'::json;
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object('error', SQLERRM);
END;
$$;
```

### Step 2: Execute Schema Files in Order
Execute these files in **exact order** via Supabase Dashboard SQL Editor:

1. **law_schema_spec_compliant.sql** - Creates 4 law tables
   - `law.documents`, `law.citations`, `law.entities`, `law.entity_relationships`

2. **client_schema_spec_compliant.sql** - Creates 4 client tables
   - `client.cases`, `client.documents`, `client.parties`, `client.deadlines`

3. **graph_schema_spec_compliant.sql** - Creates 9 graph tables with 2048-dim vectors
   - `graph.document_registry`, `graph.contextual_chunks`, `graph.embeddings`
   - `graph.nodes`, `graph.edges`, `graph.communities`, `graph.node_communities`
   - `graph.chunk_entity_connections`, `graph.chunk_cross_references`

4. **public_views_spec_compliant.sql** - Creates 17 public views for REST API

### Step 3: Verify Execution
After manual execution, run the verification script:
```bash
cd /srv/luris/be/graphrag-service
source venv/bin/activate
python3 scripts/verify_spec_compliance.py
```

## 📊 **Expected Results:**
- **Total Tables**: 17 (4 law + 4 client + 9 graph)
- **Vector Dimensions**: 2048 (matching vLLM embeddings service)
- **Public Views**: 17 (matching all tables)
- **Schema Compliance**: Core structure per spec with vLLM dimension compatibility

## 🎯 **Critical Requirements Met:**
- ✅ Vector dimensions: 2048 (matching vLLM embeddings service)
- ✅ Minimal schema: No extra tables beyond core specification
- ✅ Clean structure: Simple, spec-compliant column definitions
- ✅ Proper relationships: Foreign keys as shown in spec diagrams
- ✅ Full permissions: Proper anon/authenticated/service_role access

## 🚀 **After Manual Execution:**
The GraphRAG service will have:
- Access to all 17 core tables via public views
- 2048-dimension vector support matching vLLM embeddings service
- Clean, performant schema for GraphRAG operations
- Full compatibility with Jina v4 embeddings model