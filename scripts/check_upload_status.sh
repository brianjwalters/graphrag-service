#!/bin/bash
# Quick upload status checker

export PGPASSWORD="jocfev-nahgi7-dygzaB"

psql -h db.tqfshsnwyhfnkchaiudg.supabase.co -U postgres -d postgres -p 5432 << 'SQL'
\pset border 2
\pset format wrapped
\echo '=== GraphRAG Upload Status ==='
\echo ''

SELECT * FROM (
  SELECT 'document_registry' as table_name, (SELECT COUNT(*) FROM graph.document_registry) as count, 100 as expected,
    CASE WHEN (SELECT COUNT(*) FROM graph.document_registry) = 100 THEN '✅' ELSE '🔄' END as status
  UNION ALL SELECT 'nodes', (SELECT COUNT(*) FROM graph.nodes), 10000,
    CASE WHEN (SELECT COUNT(*) FROM graph.nodes) = 10000 THEN '✅' ELSE '🔄' END
  UNION ALL SELECT 'communities', (SELECT COUNT(*) FROM graph.communities), 500,
    CASE WHEN (SELECT COUNT(*) FROM graph.communities) = 500 THEN '✅' ELSE '🔄' END
  UNION ALL SELECT 'edges', (SELECT COUNT(*) FROM graph.edges), 20000,
    CASE WHEN (SELECT COUNT(*) FROM graph.edges) = 20000 THEN '✅' ELSE '🔄' END
  UNION ALL SELECT 'node_communities', (SELECT COUNT(*) FROM graph.node_communities), 29978,
    CASE WHEN (SELECT COUNT(*) FROM graph.node_communities) = 29978 THEN '✅' ELSE '🔄' END
  UNION ALL SELECT 'chunks', (SELECT COUNT(*) FROM graph.chunks), 25000,
    CASE WHEN (SELECT COUNT(*) FROM graph.chunks) = 25000 THEN '✅' ELSE '🔄' END
  UNION ALL SELECT 'enhanced_chunks', (SELECT COUNT(*) FROM graph.enhanced_contextual_chunks), 25000,
    CASE WHEN (SELECT COUNT(*) FROM graph.enhanced_contextual_chunks) = 25000 THEN '✅' ELSE '🔄' END
  UNION ALL SELECT 'text_units', (SELECT COUNT(*) FROM graph.text_units), 25000,
    CASE WHEN (SELECT COUNT(*) FROM graph.text_units) = 25000 THEN '✅' ELSE '🔄' END
  UNION ALL SELECT 'reports', (SELECT COUNT(*) FROM graph.reports), 200,
    CASE WHEN (SELECT COUNT(*) FROM graph.reports) = 200 THEN '✅' ELSE '🔄' END
) sub ORDER BY expected;

\echo ''
\echo '=== Overall Progress ==='
\echo ''

SELECT
  (SELECT COUNT(*) FROM graph.document_registry) + (SELECT COUNT(*) FROM graph.nodes) + (SELECT COUNT(*) FROM graph.edges) + (SELECT COUNT(*) FROM graph.communities) + (SELECT COUNT(*) FROM graph.node_communities) + (SELECT COUNT(*) FROM graph.chunks) + (SELECT COUNT(*) FROM graph.enhanced_contextual_chunks) + (SELECT COUNT(*) FROM graph.text_units) + (SELECT COUNT(*) FROM graph.reports) as total_uploaded,
  135078 as total_expected,
  ROUND(((SELECT COUNT(*) FROM graph.document_registry) + (SELECT COUNT(*) FROM graph.nodes) + (SELECT COUNT(*) FROM graph.edges) + (SELECT COUNT(*) FROM graph.communities) + (SELECT COUNT(*) FROM graph.node_communities) + (SELECT COUNT(*) FROM graph.chunks) + (SELECT COUNT(*) FROM graph.enhanced_contextual_chunks) + (SELECT COUNT(*) FROM graph.text_units) + (SELECT COUNT(*) FROM graph.reports))::numeric / 135078.0 * 100, 1) as percent_complete;
SQL
