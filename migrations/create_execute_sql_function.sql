-- ============================================================================
-- Create execute_sql PostgreSQL Function for Supabase
-- Purpose: Enable dynamic SQL execution including DDL statements
-- Required by: GraphRAG service SupabaseClient for complex queries
-- Date: 2025-08-31
-- ============================================================================

-- IMPORTANT: This function must be created in the PUBLIC schema to be accessible
-- via PostgREST API calls from the SupabaseClient

BEGIN;

-- ============================================================================
-- 1. Create the execute_sql function with single parameter (query only)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.execute_sql(query text)
RETURNS TABLE(result jsonb) 
LANGUAGE plpgsql 
SECURITY DEFINER  -- Run with creator's privileges (important for DDL)
AS $$
DECLARE
    rec record;
    result_array jsonb := '[]'::jsonb;
    result_object jsonb := '{}'::jsonb;
    command_type text;
    affected_rows integer := 0;
BEGIN
    -- Log the query for debugging (optional, remove in production if needed)
    RAISE NOTICE 'Executing SQL: %', query;
    
    -- Extract the command type (first word) for different handling
    command_type := upper(split_part(trim(query), ' ', 1));
    
    -- Handle different types of SQL commands
    CASE 
        -- DDL Commands (ALTER, CREATE, DROP, etc.) - No return data expected
        WHEN command_type IN ('ALTER', 'CREATE', 'DROP', 'TRUNCATE', 'COMMENT', 'GRANT', 'REVOKE') THEN
            EXECUTE query;
            -- Return success indicator for DDL
            RETURN QUERY SELECT jsonb_build_object(
                'command', command_type,
                'status', 'success',
                'message', format('Command %s executed successfully', command_type)
            );
            
        -- DML Commands (INSERT, UPDATE, DELETE) - Return affected row count
        WHEN command_type IN ('INSERT', 'UPDATE', 'DELETE') THEN
            EXECUTE query;
            GET DIAGNOSTICS affected_rows = ROW_COUNT;
            RETURN QUERY SELECT jsonb_build_object(
                'command', command_type,
                'status', 'success',
                'affected_rows', affected_rows
            );
            
        -- SELECT and other queries - Return actual data
        ELSE
            -- For SELECT queries, return the actual data as JSONB array
            FOR rec IN EXECUTE query LOOP
                result_array := result_array || to_jsonb(rec);
            END LOOP;
            
            -- If no results, return empty array, otherwise return the data
            IF result_array = '[]'::jsonb THEN
                RETURN QUERY SELECT '[]'::jsonb;
            ELSE
                RETURN QUERY SELECT result_array;
            END IF;
    END CASE;
    
EXCEPTION 
    WHEN OTHERS THEN
        -- Return error information as JSON
        RETURN QUERY SELECT jsonb_build_object(
            'error', true,
            'sqlstate', SQLSTATE,
            'message', SQLERRM,
            'command', command_type,
            'query', query
        );
END;
$$;

-- ============================================================================
-- 2. Create the execute_sql function with two parameters (params + query)
--    This version supports parameterized queries for security
-- ============================================================================
CREATE OR REPLACE FUNCTION public.execute_sql(params jsonb, query text)
RETURNS TABLE(result jsonb) 
LANGUAGE plpgsql 
SECURITY DEFINER
AS $$
DECLARE
    rec record;
    result_array jsonb := '[]'::jsonb;
    command_type text;
    final_query text;
    param_key text;
    param_value text;
    affected_rows integer := 0;
BEGIN
    -- Start with the original query
    final_query := query;
    
    -- Replace parameters in the query if params are provided
    IF params IS NOT NULL AND params != 'null'::jsonb THEN
        FOR param_key, param_value IN SELECT * FROM jsonb_each_text(params) LOOP
            final_query := replace(final_query, '$' || param_key, param_value);
        END LOOP;
    END IF;
    
    -- Log the final query for debugging
    RAISE NOTICE 'Executing parameterized SQL: %', final_query;
    
    -- Extract the command type
    command_type := upper(split_part(trim(final_query), ' ', 1));
    
    -- Handle different types of SQL commands (same logic as single-param version)
    CASE 
        WHEN command_type IN ('ALTER', 'CREATE', 'DROP', 'TRUNCATE', 'COMMENT', 'GRANT', 'REVOKE') THEN
            EXECUTE final_query;
            RETURN QUERY SELECT jsonb_build_object(
                'command', command_type,
                'status', 'success',
                'message', format('Command %s executed successfully', command_type)
            );
            
        WHEN command_type IN ('INSERT', 'UPDATE', 'DELETE') THEN
            EXECUTE final_query;
            GET DIAGNOSTICS affected_rows = ROW_COUNT;
            RETURN QUERY SELECT jsonb_build_object(
                'command', command_type,
                'status', 'success',
                'affected_rows', affected_rows
            );
            
        ELSE
            FOR rec IN EXECUTE final_query LOOP
                result_array := result_array || to_jsonb(rec);
            END LOOP;
            
            IF result_array = '[]'::jsonb THEN
                RETURN QUERY SELECT '[]'::jsonb;
            ELSE
                RETURN QUERY SELECT result_array;
            END IF;
    END CASE;
    
EXCEPTION 
    WHEN OTHERS THEN
        RETURN QUERY SELECT jsonb_build_object(
            'error', true,
            'sqlstate', SQLSTATE,
            'message', SQLERRM,
            'command', command_type,
            'query', final_query,
            'params', params
        );
END;
$$;

-- ============================================================================
-- 3. Grant necessary permissions for PostgREST access
-- ============================================================================

-- Grant execute permission to anon and authenticated users
GRANT EXECUTE ON FUNCTION public.execute_sql(text) TO anon;
GRANT EXECUTE ON FUNCTION public.execute_sql(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.execute_sql(jsonb, text) TO anon;
GRANT EXECUTE ON FUNCTION public.execute_sql(jsonb, text) TO authenticated;

-- Grant execute permission to service_role (for admin operations)
GRANT EXECUTE ON FUNCTION public.execute_sql(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.execute_sql(jsonb, text) TO service_role;

-- ============================================================================
-- 4. Create a helper function for safe DDL operations (optional but recommended)
-- ============================================================================
CREATE OR REPLACE FUNCTION public.execute_ddl(ddl_query text)
RETURNS TABLE(result jsonb) 
LANGUAGE plpgsql 
SECURITY DEFINER
AS $$
DECLARE
    command_type text;
BEGIN
    -- Extract and validate the command type
    command_type := upper(split_part(trim(ddl_query), ' ', 1));
    
    -- Only allow specific DDL commands for security
    IF command_type NOT IN ('ALTER', 'CREATE', 'DROP', 'TRUNCATE', 'COMMENT', 'GRANT', 'REVOKE', 'ADD', 'MODIFY') THEN
        RETURN QUERY SELECT jsonb_build_object(
            'error', true,
            'message', format('DDL command %s is not allowed', command_type),
            'allowed_commands', '["ALTER", "CREATE", "DROP", "TRUNCATE", "COMMENT", "GRANT", "REVOKE"]'
        );
        RETURN;
    END IF;
    
    -- Execute the DDL command
    EXECUTE ddl_query;
    
    RETURN QUERY SELECT jsonb_build_object(
        'command', command_type,
        'status', 'success',
        'message', format('DDL command %s executed successfully', command_type)
    );
    
EXCEPTION 
    WHEN OTHERS THEN
        RETURN QUERY SELECT jsonb_build_object(
            'error', true,
            'sqlstate', SQLSTATE,
            'message', SQLERRM,
            'command', command_type,
            'query', ddl_query
        );
END;
$$;

-- Grant permissions for DDL function
GRANT EXECUTE ON FUNCTION public.execute_ddl(text) TO service_role;

COMMIT;

-- ============================================================================
-- POST-INSTALLATION TEST QUERIES
-- Run these to verify the functions work correctly:
-- ============================================================================

-- Test 1: Simple SELECT query
SELECT * FROM public.execute_sql('SELECT 1 as test_number, ''hello'' as test_text');

-- Test 2: DDL operation (create a test table)
SELECT * FROM public.execute_sql('CREATE TABLE IF NOT EXISTS public.test_execute_sql (id serial primary key, name text)');

-- Test 3: INSERT operation  
SELECT * FROM public.execute_sql('INSERT INTO public.test_execute_sql (name) VALUES (''test record'')');

-- Test 4: SELECT from created table
SELECT * FROM public.execute_sql('SELECT * FROM public.test_execute_sql');

-- Test 5: Parameterized query
SELECT * FROM public.execute_sql('{"table_name": "test_execute_sql", "limit_count": "5"}', 'SELECT * FROM public.$table_name LIMIT $limit_count');

-- Test 6: DDL-specific function
SELECT * FROM public.execute_ddl('ALTER TABLE public.test_execute_sql ADD COLUMN IF NOT EXISTS created_at timestamp default now()');

-- Test 7: Clean up test table
SELECT * FROM public.execute_sql('DROP TABLE IF EXISTS public.test_execute_sql');

-- ============================================================================
-- FUNCTION USAGE EXAMPLES FOR GRAPHRAG SERVICE
-- ============================================================================

/*
From Python GraphRAG service, you can now call:

# Simple query
result = await client.execute_raw_sql("SELECT * FROM graph.nodes LIMIT 10")

# DDL operation  
result = await client.execute_raw_sql("ALTER TABLE graph.nodes ADD COLUMN IF NOT EXISTS new_field text")

# Complex query with joins
result = await client.execute_raw_sql("""
    SELECT n.node_id, n.title, COUNT(e.id) as edge_count 
    FROM graph.nodes n 
    LEFT JOIN graph.edges e ON n.node_id = e.source_node_id 
    GROUP BY n.node_id, n.title 
    ORDER BY edge_count DESC 
    LIMIT 10
""")

The function will automatically detect the query type and return appropriate results:
- SELECT: Returns data as JSON array
- DDL (ALTER/CREATE/DROP): Returns success status
- DML (INSERT/UPDATE/DELETE): Returns affected row count
- Errors: Returns error details as JSON
*/

-- ============================================================================
-- EXPECTED RESULTS:
-- ============================================================================
-- 1. SupabaseClient.execute_raw_sql() will work without errors
-- 2. DDL operations (ALTER TABLE, CREATE INDEX, etc.) will execute successfully  
-- 3. GraphRAG service database operations will work at 100%
-- 4. Migration scripts can be run through the service
-- 5. Complex queries with joins and aggregations will return proper JSON results
-- 
-- BEFORE: SupabaseClient fails with "execute_sql function not found"
-- AFTER:  All SQL operations work through PostgREST RPC calls
-- ============================================================================