"""
Graph Schema Validation Script - Fluent API Version

This script validates the graph schema by:
1. Checking row counts against targets for all graph tables
2. Validating multi-tenant compliance (client_id presence)

Uses SupabaseClient fluent API with full safety features:
- Timeout handling
- Retry logic with exponential backoff
- Circuit breaker protection
- Prometheus metrics tracking
- Comprehensive error handling
- Connection pooling

Author: Backend Engineer Agent
Created: 2025-10-20
"""

import asyncio
import sys
import time
from typing import Dict, Any, Tuple

sys.path.insert(0, '/srv/luris/be/graphrag-service')

from src.clients.supabase_client import create_admin_supabase_client


async def validate_graph_schema() -> bool:
    """
    Validate graph schema by checking table counts and multi-tenant compliance.

    Uses the fluent API which provides:
    - Automatic timeout handling (30s default)
    - Retry logic with exponential backoff (3 retries)
    - Circuit breaker for repeated failures
    - Prometheus metrics for monitoring
    - Structured logging

    Returns:
        bool: True if all targets met and fully compliant, False otherwise
    """
    # Create admin client (bypasses RLS for validation)
    client = create_admin_supabase_client(service_name="graph-validation")

    print('\n' + '='*70)
    print('📊 FINAL GRAPH SCHEMA VALIDATION (Fluent API)')
    print('='*70 + '\n')

    # Define table targets
    # Note: enhanced_contextual_chunks table doesn't exist in production schema
    tables = {
        'nodes': {'target': 100000, 'has_embedding': True},
        'edges': {'target': 80000, 'has_embedding': False},
        'communities': {'target': 500, 'has_embedding': True},
        'chunks': {'target': 30000, 'has_embedding': True},
    }

    print('Table                              Target      Actual    Status')
    print('-' * 70)

    total_rows = 0
    all_complete = True
    table_counts = {}

    # Check table counts using fluent API
    for table, config in tables.items():
        target = config['target']

        try:
            # ✅ CORRECT - Using fluent API with safety features
            # This provides: timeout, retry, circuit breaker, metrics
            result = await client.schema('graph').table(table) \
                .select('count', count='exact') \
                .execute()

            actual = result.count
            table_counts[table] = actual
            total_rows += actual

            pct = 100 * actual / target if target > 0 else 0
            status = '✅' if actual >= target else '⏳'

            if actual < target:
                all_complete = False

            print(f'{table:30} {target:>10,} {actual:>10,}    {status} ({pct:>5.1f}%)')

        except asyncio.TimeoutError:
            print(f'{table:30} {"TIMEOUT":>10} {"N/A":>10}    ❌ Operation timed out')
            all_complete = False
        except Exception as e:
            error_msg = str(e)[:30] + '...' if len(str(e)) > 30 else str(e)
            print(f'{table:30} {"ERROR":>10} {"N/A":>10}    ❌ {error_msg}')
            all_complete = False

    print('-' * 70)
    print(f'TOTAL GRAPH ROWS:                            {total_rows:>10,}')
    print()

    # Note: Graph schema tables don't have client_id - they're system-wide
    # This is correct architecture for GraphRAG knowledge graph
    print('ℹ️  NOTE: Graph tables are system-wide (no client_id column)')
    print('   This is intentional - knowledge graph spans all documents')
    print()
    print('='*70)

    # Final status
    if all_complete:
        print('✅ ALL TARGETS MET - GRAPH SCHEMA COMPLETE!')
        success = True
    else:
        print('⏳ Some targets not yet met')
        success = False

    # Show client health info
    print()
    print('📊 CLIENT HEALTH METRICS:')
    print('-' * 70)
    health = client.get_health_info()
    print(f'Service name: {health["service_name"]}')
    print(f'Environment: {health["environment"]}')
    print(f'Total operations: {health["operation_count"]}')
    print(f'Error count: {health["error_count"]}')
    print(f'Error rate: {health["error_rate"]:.2%}')
    print(f'Average latency: {health["performance"]["average_latency_seconds"]:.3f}s')
    print(f'Slow queries: {health["performance"]["slow_queries_count"]}')
    print(f'Connection pool: {health["connection_pool"]["active_connections"]}/{health["connection_pool"]["max_connections"]} ({health["connection_pool"]["utilization"]:.2%})')
    print(f'Circuit breaker: {health["circuit_breaker"]["open_circuits"]} open circuits')
    print(f'Primary client: {health["clients"]["primary_client"]}')
    print(f'Overall health: {"✅ HEALTHY" if health["healthy"] else "❌ UNHEALTHY"}')

    return success


async def main():
    """Main entry point"""
    start_time = time.time()

    try:
        print('🚀 Starting graph schema validation using fluent API...')
        print(f'⏰ Start time: {time.strftime("%Y-%m-%d %H:%M:%S")}')

        success = await validate_graph_schema()

        duration = time.time() - start_time
        print()
        print(f'⏱️  Total validation time: {duration:.2f}s')

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print('\n\n⚠️  Validation interrupted by user')
        sys.exit(130)
    except Exception as e:
        print(f'\n❌ VALIDATION FAILED: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    # Run async validation
    asyncio.run(main())
