#!/usr/bin/env python3
"""
Analyze vector performance and pgvector capabilities
"""
import os
import sys
import asyncio
import time

# Add the GraphRAG service to the path
sys.path.append('/srv/luris/be/graphrag-service/src')
sys.path.append('/srv/luris/be')

try:
    from clients.supabase_client import SupabaseClient, SupabaseSettings
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

async def analyze_vector_performance():
    """Analyze current vector performance situation."""
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = "https://tqfshsnwyhfnkchaiudg.supabase.co"
    os.environ['SUPABASE_API_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyMjE2OTEsImV4cCI6MjA1MTc5NzY5MX0.Xn33KBzBgQabFVHXoLX-htjWuiB3yQ_SYqsjyPTgIAE"
    os.environ['SUPABASE_SERVICE_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"
    
    print("🔍 VECTOR PERFORMANCE ANALYSIS")
    print("=" * 50)
    
    client = SupabaseClient(service_name="vector-analyzer", use_service_role=True)
    
    # Check pgvector version and capabilities
    print("1. pgvector Version & Capabilities")
    print("-" * 30)
    
    try:
        version_query = "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
        version_result = client.service_client.rpc('execute_sql', {'query': version_query}).execute()
        if version_result.data:
            version_info = version_result.data[0]
            print(f"   Extension: {version_info.get('extname', 'vector')}")
            print(f"   Version: {version_info.get('extversion', 'Unknown')}")
        else:
            print("   ❌ pgvector extension not found")
    except Exception as e:
        print(f"   ❌ Version check failed: {str(e)[:50]}...")
    
    # Check PostgreSQL version
    try:
        pg_query = "SELECT substring(version() from 'PostgreSQL ([0-9.]+)') as pg_version"
        pg_result = client.service_client.rpc('execute_sql', {'query': pg_query}).execute()
        if pg_result.data:
            pg_version = pg_result.data[0].get('pg_version', 'Unknown')
            print(f"   PostgreSQL: {pg_version}")
        else:
            print("   PostgreSQL: Unknown")
    except Exception as e:
        print(f"   PostgreSQL check failed: {str(e)[:50]}...")
    
    # Check current embeddings table status
    print("\n2. Current Embeddings Table Status")
    print("-" * 30)
    
    try:
        # Count vectors
        count_query = "SELECT COUNT(*) as vector_count FROM graph.embeddings"
        count_result = client.service_client.rpc('execute_sql', {'query': count_query}).execute()
        vector_count = count_result.data[0].get('vector_count', 0) if count_result.data else 0
        print(f"   Stored vectors: {vector_count}")
        
        # Check vector dimensions
        dim_query = """
        SELECT 
            column_name,
            data_type,
            CASE 
                WHEN data_type LIKE 'vector%' THEN 
                    CAST(REGEXP_REPLACE(data_type, 'vector\\((\\d+)\\)', '\\1') AS INTEGER)
                ELSE NULL 
            END as dimensions
        FROM information_schema.columns 
        WHERE table_schema = 'graph' 
        AND table_name = 'embeddings' 
        AND column_name = 'vector'
        """
        dim_result = client.service_client.rpc('execute_sql', {'query': dim_query}).execute()
        if dim_result.data:
            dimensions = dim_result.data[0].get('dimensions', 'Unknown')
            print(f"   Vector dimensions: {dimensions}")
        else:
            print("   Vector dimensions: Not found")
            
        # Check for vector indexes
        index_query = """
        SELECT 
            indexname, 
            indexdef 
        FROM pg_indexes 
        WHERE schemaname = 'graph' 
        AND tablename = 'embeddings'
        AND indexdef LIKE '%vector%'
        """
        index_result = client.service_client.rpc('execute_sql', {'query': index_query}).execute()
        if index_result.data and len(index_result.data) > 0:
            print("   Vector indexes:")
            for idx in index_result.data:
                print(f"     - {idx.get('indexname')}")
        else:
            print("   Vector indexes: ❌ None (brute-force search)")
            
    except Exception as e:
        print(f"   ❌ Table status check failed: {str(e)[:50]}...")
    
    # Performance implications
    print("\n3. Performance Implications")
    print("-" * 30)
    
    estimated_performance = {
        100: "~5ms",
        1000: "~50ms", 
        10000: "~500ms",
        100000: "~5s",
        1000000: "~50s"
    }
    
    print("   Brute-force search times (estimated):")
    for count, time_est in estimated_performance.items():
        status = "✅" if count <= 1000 else "⚠️" if count <= 10000 else "❌"
        print(f"     {status} {count:,} vectors: {time_est}")
    
    # Solutions analysis
    print("\n4. Available Solutions")
    print("-" * 30)
    
    print("   Option A: Dimension Reduction")
    print("     ✅ Create 1536-dim vectors alongside 2048-dim")
    print("     ✅ Use indexed search for fast retrieval")
    print("     ❌ Slight accuracy loss from dimensionality reduction")
    
    print("\n   Option B: pgvector Upgrade")
    print("     ✅ Native 2048-dim index support")
    print("     ✅ Best performance and accuracy")
    print("     ❌ Requires Supabase infrastructure upgrade")
    
    print("\n   Option C: Accept Brute-Force")
    print("     ✅ Works with current infrastructure")
    print("     ✅ Perfect accuracy maintained") 
    print("     ❌ Performance degrades with scale")
    
    # Current recommendation
    print("\n5. Current Recommendation")
    print("-" * 30)
    
    if vector_count < 1000:
        print("   ✅ CURRENT SETUP IS ADEQUATE")
        print("     - Dataset size supports brute-force search")
        print("     - Performance impact minimal (<100ms)")
        print("     - Continue with current implementation")
    elif vector_count < 10000:
        print("   ⚠️  MONITOR PERFORMANCE")
        print("     - May experience slower queries (100-500ms)")
        print("     - Consider optimization when performance becomes issue")
    else:
        print("   ❌ OPTIMIZATION RECOMMENDED")
        print("     - Large dataset will cause slow queries (>1s)")
        print("     - Implement dual-dimension strategy or upgrade pgvector")
    
    print("\n📊 Summary:")
    print(f"   Current vectors: {vector_count}")
    print(f"   Dimensions: 2048 (vLLM compatible)")
    print(f"   Index status: Brute-force only")
    print(f"   Performance: {'Adequate' if vector_count < 1000 else 'Monitor' if vector_count < 10000 else 'Needs optimization'}")

if __name__ == "__main__":
    try:
        asyncio.run(analyze_vector_performance())
    except Exception as e:
        print(f"Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)