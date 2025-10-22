"""
Enhanced SupabaseClient for direct integration across Luris services.

This is the centralized Supabase client that all services should use directly
instead of going through the Supabase Service. This eliminates network overhead
and simplifies the architecture.
"""

import os
import time
from typing import Any, Dict, List, Optional, Union
from supabase import create_client, Client
# ClientOptions temporarily disabled for compatibility
# from supabase.lib.client_options import SyncClientOptions as ClientOptions
from pydantic_settings import BaseSettings
from datetime import datetime
import traceback
import asyncio
import backoff
from prometheus_client import Counter, Histogram

# Import LogClient with fallback
try:
    # Try absolute import first
    from services.log_service.src.client.log_client import LogClient
except ImportError:
    try:
        # Try relative import
        from ...services.log_service.src.client.log_client import LogClient
    except ImportError:
        # Fallback for dev/test if LogClient is not available
        class LogClient:
            async def info(self, message: str, **kwargs):
                print(f"[INFO] {message}", kwargs)
            async def error(self, message: str, **kwargs):
                print(f"[ERROR] {message}", kwargs)

# Prometheus metrics - safe creation to prevent duplicates
try:
    from prometheus_client import REGISTRY
    
    # Check if metrics already exist before creating them
    existing_metrics = set()
    for collector in REGISTRY._collector_to_names.keys():
        existing_metrics.update(REGISTRY._collector_to_names.get(collector, set()))
    
    # Only create metrics if they don't already exist
    if 'supabase_ops_total' not in existing_metrics:
        SUPABASE_OPS_TOTAL = Counter('supabase_ops_total', 'Total Supabase operations', ['operation', 'status'])
        SUPABASE_OPS_LATENCY = Histogram('supabase_ops_latency_seconds', 'Supabase operation latency', ['operation'])
        SUPABASE_OPS_RETRIES = Counter('supabase_ops_retries', 'Supabase operation retries', ['operation'])
        SUPABASE_OPS_TIMEOUTS = Counter('supabase_ops_timeouts', 'Supabase operation timeouts', ['operation'])
    else:
        # Metrics already exist - find and reuse them
        print("Reusing existing Supabase Prometheus metrics")
        # Create dummy objects that do nothing to avoid breaking the code
        class DummyMetric:
            def inc(self, *args, **kwargs): pass
            def observe(self, *args, **kwargs): pass
            def time(self): 
                class DummyTimer:
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                return DummyTimer()
            def labels(self, *args, **kwargs): return self
        
        SUPABASE_OPS_TOTAL = DummyMetric()
        SUPABASE_OPS_LATENCY = DummyMetric()
        SUPABASE_OPS_RETRIES = DummyMetric()
        SUPABASE_OPS_TIMEOUTS = DummyMetric()
        
except Exception as e:
    print(f"Warning: Could not initialize Prometheus metrics: {e}")
    # Create dummy metrics if Prometheus setup fails
    class DummyMetric:
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def time(self): 
            class DummyTimer:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return DummyTimer()
        def labels(self, *args, **kwargs): return self
    
    SUPABASE_OPS_TOTAL = DummyMetric()
    SUPABASE_OPS_LATENCY = DummyMetric()
    SUPABASE_OPS_RETRIES = DummyMetric()
    SUPABASE_OPS_TIMEOUTS = DummyMetric()

# MockSupabaseClient completely removed - no mock clients allowed
# All database operations must use real Supabase connections

class SupabaseSettings(BaseSettings):
    """
    Enhanced Supabase configuration with operation-specific timeout support.
    
    All settings are loaded from environment variables directly.
    No hard-coded credentials allowed.
    """
    # Core connection settings - MUST be provided via environment
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_api_key: str = os.getenv("SUPABASE_API_KEY", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # Operation-specific timeout settings (optimized for different operations)
    simple_op_timeout: int = int(os.getenv("SUPABASE_SIMPLE_OP_TIMEOUT", "8"))  # Simple CRUD ops
    complex_op_timeout: int = int(os.getenv("SUPABASE_COMPLEX_OP_TIMEOUT", "20"))  # Complex queries
    batch_op_timeout: int = int(os.getenv("SUPABASE_BATCH_OP_TIMEOUT", "30"))  # Batch operations
    vector_op_timeout: int = int(os.getenv("SUPABASE_VECTOR_OP_TIMEOUT", "25"))  # Vector operations
    
    # Legacy timeout (for backward compatibility)
    op_timeout: int = int(os.getenv("SUPABASE_OP_TIMEOUT", "20"))  # Default timeout
    
    # Enhanced retry and backoff settings
    max_retries: int = int(os.getenv("SUPABASE_MAX_RETRIES", "3"))
    backoff_max: int = int(os.getenv("SUPABASE_BACKOFF_MAX", "30"))  # seconds
    backoff_factor: float = float(os.getenv("SUPABASE_BACKOFF_FACTOR", "2.0"))
    
    # Connection pool settings (optimized for timeout scenarios)
    max_connections: int = int(os.getenv("SUPABASE_MAX_CONNECTIONS", "30"))  # Increased
    connection_timeout: int = int(os.getenv("SUPABASE_CONNECTION_TIMEOUT", "5"))  # Reduced
    pool_recycle: int = int(os.getenv("SUPABASE_POOL_RECYCLE", "300"))  # 5 minutes
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = os.getenv("SUPABASE_CIRCUIT_BREAKER", "true").lower() == "true"
    circuit_breaker_failure_threshold: int = int(os.getenv("SUPABASE_CB_FAILURE_THRESHOLD", "5"))
    circuit_breaker_recovery_timeout: int = int(os.getenv("SUPABASE_CB_RECOVERY_TIMEOUT", "60"))
    circuit_breaker_expected_exception: str = os.getenv("SUPABASE_CB_EXPECTED_EXCEPTION", "TimeoutError")
    
    # Performance settings
    batch_size: int = int(os.getenv("SUPABASE_BATCH_SIZE", "100"))
    enable_metrics: bool = os.getenv("SUPABASE_ENABLE_METRICS", "true").lower() == "true"
    enable_slow_query_log: bool = os.getenv("SUPABASE_SLOW_QUERY_LOG", "true").lower() == "true"
    slow_query_threshold: float = float(os.getenv("SUPABASE_SLOW_QUERY_THRESHOLD", "5.0"))  # seconds
    
    # Schema-specific timeout multipliers
    law_schema_timeout_multiplier: float = float(os.getenv("SUPABASE_LAW_TIMEOUT_MULT", "1.2"))  # 20% more time
    client_schema_timeout_multiplier: float = float(os.getenv("SUPABASE_CLIENT_TIMEOUT_MULT", "1.0"))
    graph_schema_timeout_multiplier: float = float(os.getenv("SUPABASE_GRAPH_TIMEOUT_MULT", "1.5"))  # 50% more time
    
    # Environment info
    environment: str = os.getenv("ENVIRONMENT", "development")
    service_name: str = os.getenv("SERVICE_NAME", "unknown")
    
    model_config = {
        "case_sensitive": False,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Validate required environment variables
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.supabase_api_key:
            raise ValueError("SUPABASE_API_KEY environment variable is required")
        if not self.supabase_service_key:
            raise ValueError("SUPABASE_SERVICE_KEY environment variable is required")
        
        print(f"✅ SupabaseSettings validated:")
        print(f"   URL: {self.supabase_url}")
        print(f"   API Key: {self.supabase_api_key[:20]}...")
        print(f"   Service Key: {self.supabase_service_key[:20]}...")
        print(f"   Environment: {self.environment}")

class SupabaseClient:
    """
    Modern centralized Supabase client with dual-key architecture.
    
    This client provides both anon and service_role access patterns:
    - anon key: Standard operations, respects RLS policies
    - service_role key: Admin operations, bypasses RLS
    
    IMPORTANT: This is the ONLY database client allowed in the system.
    All services must use this client for database access.
    
    Features:
    - Dual-client architecture (anon + service_role)
    - Modern create_client() API usage
    - Comprehensive error handling without mock fallbacks
    - Async operations with timeout and retry
    - Connection pooling and management
    - Prometheus metrics integration
    - Schema-aware table operations
    - Storage operations
    - Logging integration
    """
    
    def __init__(self, settings: Optional[SupabaseSettings] = None, log_client: Optional[LogClient] = None, service_name: Optional[str] = None, use_service_role: bool = False):
        """
        Initialize the modern SupabaseClient with dual-key architecture and circuit breaker.
        
        Args:
            settings: Optional SupabaseSettings instance
            log_client: Optional LogClient for structured logging
            service_name: Optional service name for logging context
            use_service_role: If True, use service_role key by default
        """
        self.settings = settings or SupabaseSettings()
        self.log_client = log_client
        self.service_name = service_name or self.settings.service_name
        self.use_service_role = use_service_role
        
        # Initialize dual clients
        self.anon_client = None
        self.service_client = None
        self.client = None  # Primary client reference
        
        # Create both clients with modern create_client() API
        self._create_clients()
        
        # Enhanced connection management with optimized pool
        self._connection_semaphore = asyncio.Semaphore(self.settings.max_connections)
        self._operation_count = 0
        self._error_count = 0
        
        # Circuit breaker state management
        self._circuit_breaker_state = {}
        self._circuit_breaker_failures = {}
        self._circuit_breaker_last_failure = {}
        
        # Performance monitoring
        self._slow_queries = []
        self._operation_latencies = {}
        
        # Connection pool health tracking
        self._pool_exhaustion_count = 0
        self._active_connections = 0
        
        print(f"✅ SupabaseClient initialized for {self.service_name}")
        print(f"   Anon client: {'OK' if self.anon_client else 'FAILED'}")
        print(f"   Service client: {'OK' if self.service_client else 'FAILED'}")
        print(f"   Primary: {'service_role' if use_service_role else 'anon'} key")
        
    def _create_clients(self):
        """
        Create both anon and service_role clients using modern create_client() API.
        """
        try:
            # ClientOptions temporarily disabled for compatibility
            # Using basic client creation without custom options
            options = None
            
            print(f"🔧 Creating anon client...")
            self.anon_client = create_client(
                self.settings.supabase_url,
                self.settings.supabase_api_key
            )
            print(f"✅ Anon client created successfully")
            
            print(f"🔧 Creating service_role client...")
            self.service_client = create_client(
                self.settings.supabase_url,
                self.settings.supabase_service_key
            )
            print(f"✅ Service client created successfully")
            
            # Set primary client
            self.client = self.service_client if self.use_service_role else self.anon_client
            
        except Exception as e:
            error_msg = f"❌ Failed to create Supabase clients: {e}"
            print(error_msg)
            print(f"❌ Error traceback: {traceback.format_exc()}")
            
            # NO MOCK FALLBACK - raise the error
            raise Exception(f"SupabaseClient initialization failed: {e}. Check environment variables and network connectivity.")
    
    def _get_schema_and_table(self, table: str) -> tuple[Optional[str], str]:
        """
        Extract schema and table name from table reference.

        Args:
            table: Table name (e.g., "graph.nodes", "law.documents", or "documents")

        Returns:
            Tuple of (schema_name, table_name)
            - ("graph", "nodes") for "graph.nodes"
            - ("law", "documents") for "law.documents"
            - (None, "documents") for "documents"
        """
        if '.' in table:
            parts = table.split('.', 1)
            return (parts[0], parts[1])
        else:
            return (None, table)

    def _convert_table_name(self, table: str) -> str:
        """
        DEPRECATED: Use _get_schema_and_table instead.

        This method is kept for backward compatibility but should not be used
        for new code. Use explicit schema routing with client.schema().from_()
        instead of client.table().

        Args:
            table: Table name in dot notation (e.g., "graph.nodes", "law.documents")

        Returns:
            Table name in underscore notation for Supabase REST API
        """
        # Convert dot notation to underscore notation for Supabase REST API
        if '.' in table:
            # Replace dot with underscore: graph.nodes → graph_nodes
            converted = table.replace('.', '_').lower()
            return converted

        # No schema prefix, return as-is (lowercase)
        return table.lower()
    
    def _extract_schema(self, table: str) -> Optional[str]:
        """
        Extract schema name from table reference.
        
        Args:
            table: Table name (e.g., "law.documents", "law_documents", or "documents")
            
        Returns:
            Schema name ("law", "client", "graph") or None if no schema specified
        """
        if '.' in table:
            # Dot notation: law.documents
            return table.split('.')[0]
        elif '_' in table:
            # Underscore notation: law_documents
            parts = table.split('_', 1)
            if parts[0] in ['law', 'client', 'graph']:
                return parts[0]
        return None

    async def _with_timeout(self, coro, operation: str, timeout_override: Optional[float] = None):
        """Enhanced timeout handling with operation-specific timeouts."""
        # Determine appropriate timeout based on operation type
        timeout = timeout_override or self._get_operation_timeout(operation)
        
        try:
            async with asyncio.timeout(timeout):
                return await coro
        except asyncio.TimeoutError as timeout_error:
            SUPABASE_OPS_TIMEOUTS.labels(operation=operation).inc()
            await self.log_error(
                f"Supabase {operation} timed out for {self.service_name}", 
                timeout=timeout,
                operation=operation,
                circuit_breaker_active=self._is_circuit_open(operation)
            )
            # Update circuit breaker state with error context
            self._record_failure(operation, timeout_error)
            raise
    
    def _get_operation_timeout(self, operation: str) -> float:
        """Get operation-specific timeout based on operation type."""
        # Simple operations (get, insert single, update single, delete single)
        if operation in ['get', 'fetch', 'select']:
            return self.settings.simple_op_timeout
        
        # Batch operations
        elif operation in ['batch_insert', 'batch_update', 'batch_delete', 'upsert']:
            return self.settings.batch_op_timeout
        
        # Vector operations
        elif operation in ['update_chunk_vector', 'vector_search', 'similarity_search']:
            return self.settings.vector_op_timeout
        
        # Complex operations (joins, aggregations, RPC)
        elif operation in ['rpc', 'complex_query', 'aggregate']:
            return self.settings.complex_op_timeout
        
        # Storage operations
        elif operation in ['upload_file', 'download_file', 'delete_file']:
            return self.settings.complex_op_timeout
        
        # Default to standard timeout
        else:
            return self.settings.op_timeout

    def _retry_backoff(self, operation: str):
        """Enhanced retry configuration with jitter."""
        def giveup(e):
            return isinstance(e, asyncio.TimeoutError)
        return backoff.on_exception(
            backoff.expo,
            Exception,
            max_tries=self.settings.max_retries,
            max_time=self.settings.backoff_max,
            giveup=giveup,
            jitter=backoff.full_jitter,
            on_backoff=self._on_backoff(operation),
            on_giveup=self._on_giveup(operation),
            on_success=self._on_success(operation),
        )

    def _on_backoff(self, operation):
        async def handler(details):
            SUPABASE_OPS_RETRIES.labels(operation=operation).inc()
            await self.log_info(
                f"Backoff: retrying {operation} for {self.service_name}", 
                details=details
            )
        return handler

    def _on_giveup(self, operation):
        async def handler(details):
            self._error_count += 1
            await self.log_error(
                f"Giveup: {operation} failed after retries for {self.service_name}", 
                details=details
            )
        return handler

    def _on_success(self, operation):
        async def handler(details):
            await self.log_info(
                f"Success: {operation} after retry for {self.service_name}", 
                details=details
            )
        return handler

    def _get_client(self, admin_operation: bool = False) -> 'Client':
        """
        Get the appropriate client based on operation type.
        
        Args:
            admin_operation: If True, returns service_role client for admin ops
            
        Returns:
            Appropriate Supabase client instance
        """
        if admin_operation and self.service_client:
            return self.service_client
        elif self.anon_client:
            return self.anon_client
        else:
            raise Exception(f"No Supabase client available for {self.service_name}")
    
    async def _execute(self, operation: str, func, admin_operation: bool = False, schema: Optional[str] = None, *args, **kwargs):
        """Enhanced execution with circuit breaker, connection pooling, and schema-aware timeouts."""
        import time
        
        # Check circuit breaker first
        if self._is_circuit_open(operation):
            self._error_count += 1
            raise Exception(f"Circuit breaker open for operation: {operation}")
        
        # Track connection pool usage
        if self._active_connections >= self.settings.max_connections * 0.8:
            await self.log_warning(
                f"Connection pool nearing exhaustion: {self._active_connections}/{self.settings.max_connections}",
                operation=operation
            )
        
        client = self._get_client(admin_operation)
        
        # Determine timeout with schema multiplier
        base_timeout = self._get_operation_timeout(operation)
        if schema:
            base_timeout = self._apply_schema_timeout_multiplier(base_timeout, schema)
        
        start_time = time.time()
        
        try:
            async with self._connection_semaphore:
                self._active_connections += 1
                self._operation_count += 1
                
                try:
                    with SUPABASE_OPS_LATENCY.labels(operation=operation).time():
                        # For sync Supabase operations, run in executor with timeout
                        loop = asyncio.get_event_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, func, client, *args, **kwargs),
                            timeout=base_timeout
                        )
                    
                    # Track operation latency
                    latency = time.time() - start_time
                    self._track_operation_latency(operation, latency)
                    
                    # Check for slow queries
                    if self.settings.enable_slow_query_log and latency > self.settings.slow_query_threshold:
                        await self._log_slow_query(operation, latency, schema)
                    
                    # Record success for circuit breaker
                    self._record_success(operation)
                    
                    SUPABASE_OPS_TOTAL.labels(operation=operation, status="success").inc()
                    return result
                    
                finally:
                    self._active_connections -= 1
                    
        except asyncio.TimeoutError as timeout_error:
            self._error_count += 1
            self._record_failure(operation, timeout_error)
            
            # Check for pool exhaustion
            if self._active_connections >= self.settings.max_connections:
                self._pool_exhaustion_count += 1
                await self.log_error(
                    f"Connection pool exhausted during timeout",
                    operation=operation,
                    pool_exhaustion_count=self._pool_exhaustion_count
                )
            
            SUPABASE_OPS_TOTAL.labels(operation=operation, status="timeout").inc()
            raise
            
        except Exception as e:
            self._error_count += 1
            self._record_failure(operation, e)  # Pass the error for intelligent filtering
            SUPABASE_OPS_TOTAL.labels(operation=operation, status="error").inc()
            
            if self.log_client and hasattr(self.log_client, 'error'):
                try:
                    await self.log_client.error(
                        f"Supabase {operation} failed for {self.service_name}", 
                        error=str(e), 
                        traceback=traceback.format_exc(),
                        service=self.service_name,
                        client_type="service_role" if admin_operation else "anon",
                        schema=schema,
                        latency=time.time() - start_time
                    )
                except:
                    print(f"[ERROR] {self.service_name}: Supabase {operation} failed: {e}")
            raise

    # Enhanced CRUD operations with dual-client support and schema awareness
    async def get(self, table: str, filters: Optional[Dict[str, Any]] = None, select: str = "*", limit: int = 100, offset: int = 0, admin_operation: bool = False) -> List[Dict[str, Any]]:
        """Enhanced async SELECT query with dual-client support and schema-aware timeouts."""
        # Extract schema from table name if present
        schema = self._extract_schema(table)
        
        def op(client):
            api_table = self._convert_table_name(table)
            query = client.table(api_table).select(select)
            if filters:
                for k, v in filters.items():
                    query = query.eq(k, v)
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.range(offset, offset + limit - 1)
            response = query.execute()
            return response.data
        return await self._execute("get", op, admin_operation, schema)

    async def insert(self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]], admin_operation: bool = False) -> List[Dict[str, Any]]:
        """Enhanced async INSERT with dual-client support and batch detection."""
        schema = self._extract_schema(table)
        
        # Detect batch operation
        operation = "batch_insert" if isinstance(data, list) and len(data) > 1 else "insert"
        
        def op(client):
            api_table = self._convert_table_name(table)
            response = client.table(api_table).insert(data).execute()
            return response.data
        return await self._execute(operation, op, admin_operation, schema)

    async def update(self, table: str, data: Dict[str, Any] = None, match: Dict[str, Any] = None, filters: Dict[str, Any] = None, admin_operation: bool = False) -> List[Dict[str, Any]]:
        """Enhanced async UPDATE with dual-client support and schema awareness."""
        schema = self._extract_schema(table)
        
        # Handle both call signatures
        if data is None and match is not None and isinstance(match, dict):
            # Called as update(table, match, data) - swap parameters
            data, match = filters or {}, data
        elif filters is not None:
            # Called as update(table, data, filters=...)
            match = filters
        elif match is None:
            match = {}
            
        def op(client):
            api_table = self._convert_table_name(table)
            query = client.table(api_table).update(data)
            for k, v in match.items():
                query = query.eq(k, v)
            response = query.execute()
            return response.data
        return await self._execute("update", op, admin_operation, schema)

    async def delete(self, table: str, match: Dict[str, Any], admin_operation: bool = False) -> List[Dict[str, Any]]:
        """Enhanced async DELETE with dual-client support and schema awareness."""
        schema = self._extract_schema(table)
        
        def op(client):
            api_table = self._convert_table_name(table)
            query = client.table(api_table).delete()
            for k, v in match.items():
                query = query.eq(k, v)
            response = query.execute()
            return response.data
        return await self._execute("delete", op, admin_operation, schema)

    async def upsert(self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]], on_conflict: Optional[str] = None, admin_operation: bool = False, **kwargs) -> List[Dict[str, Any]]:
        """
        Enhanced UPSERT query with dual-client support and batch detection.

        Args:
            table: Table name in dot notation (e.g., "graph.nodes")
            data: Single record or list of records to upsert
            on_conflict: Column name for conflict resolution (e.g., "node_id").
                         If provided, existing records with matching values will be updated.
                         If None, uses default upsert behavior.
            admin_operation: If True, use service_role client (bypasses RLS)
            **kwargs: Additional arguments passed to Supabase client

        Returns:
            List of upserted records

        Raises:
            ValueError: If on_conflict column(s) not found in records
            RuntimeError: If upsert operation fails

        Examples:
            # Upsert nodes with conflict resolution on node_id
            await client.upsert(
                "graph.nodes",
                [{"node_id": "node1", "data": "test"}],
                on_conflict="node_id",
                admin_operation=True
            )

            # Upsert without conflict resolution (default behavior)
            await client.upsert("graph.edges", edge_records)
        """
        schema = self._extract_schema(table)

        # Validate on_conflict parameter
        if on_conflict and data:
            # Get sample record for validation
            sample_record = data[0] if isinstance(data, list) else data

            # Handle both string and list of conflict columns
            conflict_cols = [on_conflict] if isinstance(on_conflict, str) else on_conflict

            # Validate columns exist in record
            missing_cols = [col for col in conflict_cols if col not in sample_record]
            if missing_cols:
                raise ValueError(
                    f"on_conflict columns {missing_cols} not found in record keys: "
                    f"{list(sample_record.keys())}"
                )

        # UPSERT is typically a batch operation
        operation = "upsert" if isinstance(data, list) else "insert"

        def op(client):
            api_table = self._convert_table_name(table)
            # Pass on_conflict parameter to underlying upsert call
            if on_conflict:
                query = client.table(api_table).upsert(data, on_conflict=on_conflict)
            else:
                query = client.table(api_table).upsert(data)
            response = query.execute()
            return response.data

        try:
            return await self._execute(operation, op, admin_operation, schema)
        except Exception as e:
            error_context = {
                "table": table,
                "on_conflict": on_conflict,
                "operation": operation,
                "record_count": len(data) if isinstance(data, list) else 1,
                "error_type": type(e).__name__
            }
            await self.log_error(
                f"UPSERT failed for {table} (on_conflict={on_conflict}): {str(e)}",
                **error_context
            )
            raise RuntimeError(
                f"Upsert operation failed for {table}: {str(e)}"
            ) from e

    # Enhanced storage operations with dual-client support
    async def upload_file(self, bucket: str, path: str, file_data: bytes, file_options: Optional[Dict[str, Any]] = None, admin_operation: bool = True) -> Dict[str, Any]:
        """Enhanced async file upload to Supabase Storage with dual-client support."""
        def op(client):
            # Convert bytes to file-like object for proper upload
            from io import BytesIO
            import tempfile
            import os
            
            # Set default options if not provided
            options = file_options or {}
            if "upsert" not in options:
                options["upsert"] = True  # Allow overwriting by default (boolean, not string)
            
            # The Supabase Python client expects a file path, not a BytesIO object
            # So we need to save to a temporary file first
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(path)[1]) as tmp_file:
                tmp_file.write(file_data)
                tmp_file_path = tmp_file.name
            
            try:
                # Check if we should upsert (overwrite existing files)
                should_upsert = options.get("upsert", True)
                
                if should_upsert:
                    # Try to remove existing file first
                    try:
                        client.storage.from_(bucket).remove([path])
                    except:
                        # File might not exist, that's ok
                        pass
                
                # Upload file using the file path
                # The Supabase Python client's upload method is simple
                result = client.storage.from_(bucket).upload(
                    path,
                    tmp_file_path
                )
                
                # Get public URL
                url = client.storage.from_(bucket).get_public_url(path)
                
                return {
                    "path": path,
                    "bucket": bucket,
                    "url": url,
                    "size": len(file_data),
                    "public_url": url
                }
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                    
        return await self._execute("upload_file", op, admin_operation)

    async def download_file(self, bucket: str, path: str, admin_operation: bool = False) -> bytes:
        """Enhanced async file download from Supabase Storage with dual-client support."""
        def op(client):
            return client.storage.from_(bucket).download(path)
        return await self._execute("download_file", op, admin_operation)
    
    async def delete_file(self, bucket: str, path: str, admin_operation: bool = True) -> Dict[str, Any]:
        """Enhanced delete file from Supabase Storage with dual-client support."""
        def op(client):
            result = client.storage.from_(bucket).remove([path])
            return {"success": True, "path": path, "bucket": bucket}
        return await self._execute("delete_file", op, admin_operation)

    # Compatibility aliases with dual-client support
    async def storage_delete(self, bucket: str, path: str, admin_operation: bool = True) -> Dict[str, Any]:
        """Delete file from storage (alias for delete_file)."""
        return await self.delete_file(bucket, path, admin_operation)
    
    async def storage_download(self, bucket: str, path: str, admin_operation: bool = False) -> bytes:
        """Download file from storage (alias for download_file)."""
        return await self.download_file(bucket, path, admin_operation)
    
    async def select(self, table: str, columns: str = "*", filters: Optional[Dict[str, Any]] = None, limit: int = 100, offset: int = 0, admin_operation: bool = False) -> Dict[str, Any]:
        """SELECT query with Supabase-style response."""
        data = await self.get(table, filters, columns, limit, offset, admin_operation)
        return {"data": data, "count": len(data)}
    
    async def fetch(self, table: str, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, admin_operation: bool = False) -> List[Dict[str, Any]]:
        """Fetch data from table (alias for get)."""
        return await self.get(table, filters, "*", limit or 100, 0, admin_operation)

    # FIX 2: Add execute_raw_sql method for direct SQL operations
    async def execute_raw_sql(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None,
        admin_operation: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query directly against the database.
        
        This method provides direct SQL execution capability for complex queries
        that cannot be easily expressed through the Supabase REST API.
        
        Args:
            query: SQL query string to execute
            params: Optional parameters for parameterized queries
            admin_operation: If True, use service_role client (bypasses RLS)
            
        Returns:
            Query results as list of dictionaries
            
        Example:
            results = await client.execute_raw_sql(
                "SELECT * FROM graph.entities WHERE entity_type = :type",
                {"type": "person"}
            )
        """
        def op(client):
            # Use RPC to execute raw SQL via a database function if available
            # Otherwise, use the Supabase client's direct query capability
            try:
                # Try to use RPC if a raw SQL execution function exists
                response = client.rpc('execute_sql', {
                    'query': query,
                    'params': params or {}
                }).execute()
                return response.data if response.data is not None else []
            except Exception as rpc_error:
                # Fallback: Use direct table query with raw SQL
                # This works for simple queries on known tables
                print(f"RPC execute_sql not available, attempting direct query: {rpc_error}")
                
                # For simple SELECT queries, try to parse and execute via REST API
                if query.strip().upper().startswith('SELECT'):
                    # This is a simplified approach - complex queries still need RPC
                    raise Exception(
                        "Complex SQL queries require an RPC function 'execute_sql' to be defined in the database. "
                        "Please create this function or use the standard CRUD methods (get, insert, update, delete)."
                    )
                else:
                    raise Exception(f"Non-SELECT queries require RPC support: {query}")
        
        return await self._execute("execute_raw_sql", op, admin_operation)
    
    # Alias for compatibility
    async def execute_sql(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        admin_operation: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Alias for execute_raw_sql for backward compatibility.
        
        Args:
            query: SQL query string to execute
            params: Optional parameters for parameterized queries
            admin_operation: If True, use service_role client
            
        Returns:
            Query results as list of dictionaries
        """
        return await self.execute_raw_sql(query, params, admin_operation)

    # Enhanced RPC operations with better error handling
    async def rpc(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None,
        admin_operation: bool = False
    ) -> Any:
        """
        Call a PostgreSQL function via RPC.
        
        This provides direct access to database functions for complex operations
        that cannot be expressed through the REST API.
        
        Args:
            function_name: Name of the PostgreSQL function to call
            params: Parameters to pass to the function
            admin_operation: If True, use service_role client
            
        Returns:
            Function result (type depends on the function)
            
        Example:
            result = await client.rpc('calculate_similarity', {
                'vector1': embedding1,
                'vector2': embedding2
            })
        """
        def op(client):
            response = client.rpc(function_name, params or {}).execute()
            return response.data
        
        return await self._execute("rpc", op, admin_operation)
    
    async def execute_function(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None,
        admin_operation: bool = False,
        timeout_override: Optional[float] = None
    ) -> Any:
        """
        Execute a PostgreSQL function via RPC (alias for rpc method).
        
        This method provides a more explicit interface for executing database functions.
        It's functionally identical to rpc() but with a clearer name and enhanced documentation.
        
        Args:
            function_name: Name of the PostgreSQL function to execute
            params: Parameters to pass to the function (optional)
            admin_operation: If True, use service_role client for admin privileges
            timeout_override: Optional timeout override for this specific operation
            
        Returns:
            The result from the PostgreSQL function. Return type depends on the function:
            - Scalar functions return single values (int, str, bool, etc.)
            - Set-returning functions return lists of records
            - JSON functions return dict or list
            
        Raises:
            Exception: If the function doesn't exist or execution fails
            
        Examples:
            # Function without parameters
            result = await client.execute_function('get_current_timestamp')
            
            # Function with simple parameters
            similar_chunks = await client.execute_function(
                'search_similar_chunks',
                {
                    'query_embedding': embedding_vector,
                    'match_threshold': 0.7,
                    'match_count': 10,
                    'filter_client_id': 'client_123'
                }
            )
            
            # Function returning table data
            search_results = await client.execute_function(
                'hybrid_search',
                {
                    'query_text': 'legal precedent',
                    'query_embedding': embedding,
                    'client_id': 'client_123',
                    'keyword_weight': 0.3,
                    'semantic_weight': 0.7,
                    'limit': 5
                }
            )
            
            # Admin operation for system functions
            stats = await client.execute_function(
                'analyze_graph_statistics',
                admin_operation=True
            )
            
            # Function with complex parameters
            graph_data = await client.execute_function(
                'build_subgraph',
                {
                    'start_node_id': 'node_123',
                    'max_depth': 3,
                    'relationship_types': ['cites', 'references', 'related_to'],
                    'include_metadata': True
                }
            )
        """
        # If timeout override is provided, we could potentially use it here
        # For now, we'll use the standard rpc method which handles timeouts internally
        return await self.rpc(function_name, params, admin_operation)

    # Enhanced RPC and specialized operations
    async def update_chunk_vector(
        self, 
        schema: str, 
        chunk_id: str, 
        vector: List[float],
        admin_operation: bool = True
    ) -> bool:
        """Enhanced update vector for a specific chunk using RPC with dual-client support."""
        def op(client):
            response = client.rpc('update_chunk_vector', {
                'p_schema': schema,
                'p_chunk_id': chunk_id,
                'p_vector': vector
            }).execute()
            # RPC returns boolean directly
            return response.data if response.data is not None else False
        
        try:
            result = await self._execute("update_chunk_vector", op, admin_operation)
            return result if isinstance(result, bool) else False
        except Exception as e:
            await self.log_error(
                f"Failed to update vector for chunk {chunk_id} in {schema}",
                error=str(e),
                service=self.service_name
            )
            return False

    # Enhanced logging methods
    async def log_info(self, message: str, **kwargs):
        """Enhanced log info message via LogClient."""
        if self.log_client and hasattr(self.log_client, 'info'):
            await self.log_client.info(
                message, 
                service=self.service_name,
                operation_count=self._operation_count,
                **kwargs
            )
        else:
            print(f"[INFO] {self.service_name}: {message}", kwargs)

    async def log_error(self, message: str, **kwargs):
        """Enhanced log error message via LogClient."""
        if self.log_client and hasattr(self.log_client, 'error'):
            await self.log_client.error(
                message, 
                service=self.service_name,
                error_count=self._error_count,
                **kwargs
            )
        else:
            print(f"[ERROR] {self.service_name}: {message}", kwargs)

    # Enhanced resource management
    # Circuit breaker helper methods
    def _is_circuit_open(self, operation: str) -> bool:
        """Check if circuit breaker is open for an operation."""
        if not self.settings.circuit_breaker_enabled:
            return False
        
        state = self._circuit_breaker_state.get(operation, 'closed')
        
        # Check if circuit should recover
        if state == 'open':
            last_failure = self._circuit_breaker_last_failure.get(operation, 0)
            if time.time() - last_failure > self.settings.circuit_breaker_recovery_timeout:
                self._circuit_breaker_state[operation] = 'half_open'
                return False
        
        return state == 'open'
    
    def _record_failure(self, operation: str, error: Optional[Exception] = None):
        """
        Record operation failure for circuit breaker.
        
        FIX 3: Enhanced circuit breaker logic that's more intelligent about errors.
        Not all errors should trigger the circuit breaker - only systematic failures.
        """
        if not self.settings.circuit_breaker_enabled:
            return
        
        # Check if this is a legitimate error that should trigger circuit breaker
        if error:
            error_msg = str(error).lower()
            
            # Don't trigger circuit breaker for these types of errors:
            # - Table not found (might be a schema issue, not a connection issue)
            # - Permission denied (RLS policy, not a system failure)
            # - Constraint violations (data issue, not system issue)
            # - Invalid query syntax (programming error, not system issue)
            non_circuit_errors = [
                'does not exist',
                'permission denied',
                'violates foreign key constraint',
                'violates unique constraint',
                'violates check constraint',
                'syntax error',
                'invalid input syntax',
                'column does not exist',
                'relation does not exist'
            ]
            
            # Check if this is a non-circuit error
            if any(err_pattern in error_msg for err_pattern in non_circuit_errors):
                # Log the error but don't trigger circuit breaker
                asyncio.create_task(self.log_info(
                    f"Non-circuit error in {operation}: {error_msg[:100]}",
                    operation=operation,
                    error_type="non_circuit"
                ))
                return
        
        # Record the failure
        self._circuit_breaker_failures[operation] = self._circuit_breaker_failures.get(operation, 0) + 1
        self._circuit_breaker_last_failure[operation] = time.time()
        
        # Open circuit if threshold exceeded
        if self._circuit_breaker_failures[operation] >= self.settings.circuit_breaker_failure_threshold:
            self._circuit_breaker_state[operation] = 'open'
            asyncio.create_task(self.log_warning(
                f"Circuit breaker opened for operation: {operation}",
                failures=self._circuit_breaker_failures[operation]
            ))
    
    def _record_success(self, operation: str):
        """Record operation success for circuit breaker."""
        if not self.settings.circuit_breaker_enabled:
            return
        
        state = self._circuit_breaker_state.get(operation, 'closed')
        
        if state == 'half_open':
            # Reset circuit on successful operation
            self._circuit_breaker_state[operation] = 'closed'
            self._circuit_breaker_failures[operation] = 0
            asyncio.create_task(self.log_info(
                f"Circuit breaker closed for operation: {operation}"
            ))
    
    def _apply_schema_timeout_multiplier(self, base_timeout: float, schema: str) -> float:
        """Apply schema-specific timeout multiplier."""
        if schema == 'law':
            return base_timeout * self.settings.law_schema_timeout_multiplier
        elif schema == 'graph':
            return base_timeout * self.settings.graph_schema_timeout_multiplier
        elif schema == 'client':
            return base_timeout * self.settings.client_schema_timeout_multiplier
        return base_timeout
    
    def _track_operation_latency(self, operation: str, latency: float):
        """Track operation latency for monitoring."""
        if operation not in self._operation_latencies:
            self._operation_latencies[operation] = []
        
        # Keep last 100 measurements per operation
        self._operation_latencies[operation].append(latency)
        if len(self._operation_latencies[operation]) > 100:
            self._operation_latencies[operation] = self._operation_latencies[operation][-100:]
    
    async def _log_slow_query(self, operation: str, latency: float, schema: Optional[str]):
        """Log slow query for analysis."""
        slow_query_info = {
            'operation': operation,
            'latency': latency,
            'schema': schema,
            'timestamp': datetime.utcnow().isoformat(),
            'service': self.service_name
        }
        
        self._slow_queries.append(slow_query_info)
        
        # Keep only last 50 slow queries
        if len(self._slow_queries) > 50:
            self._slow_queries = self._slow_queries[-50:]
        
        await self.log_warning(
            f"Slow query detected: {operation}",
            **slow_query_info
        )
    
    async def log_warning(self, message: str, **kwargs):
        """Log warning message via LogClient."""
        if self.log_client and hasattr(self.log_client, 'warning'):
            await self.log_client.warning(
                message,
                service=self.service_name,
                **kwargs
            )
        else:
            print(f"[WARNING] {self.service_name}: {message}", kwargs)
    
    async def close(self):
        """Enhanced close the LogClient and cleanup resources."""
        await self.log_info(f"Closing SupabaseClient for {self.service_name}")
        
        # Log final statistics
        health_info = self.get_health_info()
        await self.log_info(
            "SupabaseClient final statistics",
            **health_info
        )
        
        if hasattr(self.log_client, "close"):
            await self.log_client.close()

    def get_health_info(self) -> Dict[str, Any]:
        """Get comprehensive health information including circuit breaker and pool status."""
        # Calculate circuit breaker stats
        open_circuits = sum(1 for state in self._circuit_breaker_state.values() if state == 'open')
        
        # Calculate average latency
        avg_latency = 0
        if self._operation_latencies:
            total_latency = sum(sum(latencies) for latencies in self._operation_latencies.values())
            total_ops = sum(len(latencies) for latencies in self._operation_latencies.values())
            avg_latency = total_latency / total_ops if total_ops > 0 else 0
        
        return {
            "service_name": self.service_name,
            "environment": self.settings.environment,
            "operation_count": self._operation_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._operation_count, 1),
            "connection_pool": {
                "max_connections": self.settings.max_connections,
                "active_connections": self._active_connections,
                "pool_exhaustion_count": self._pool_exhaustion_count,
                "utilization": self._active_connections / self.settings.max_connections
            },
            "circuit_breaker": {
                "enabled": self.settings.circuit_breaker_enabled,
                "open_circuits": open_circuits,
                "total_circuits": len(self._circuit_breaker_state)
            },
            "performance": {
                "average_latency_seconds": round(avg_latency, 3),
                "slow_queries_count": len(self._slow_queries),
                "slow_query_threshold": self.settings.slow_query_threshold
            },
            "timeouts": {
                "simple_ops": self.settings.simple_op_timeout,
                "complex_ops": self.settings.complex_op_timeout,
                "batch_ops": self.settings.batch_op_timeout,
                "vector_ops": self.settings.vector_op_timeout
            },
            "clients": {
                "anon_client": str(type(self.anon_client)) if self.anon_client else "Not available",
                "service_client": str(type(self.service_client)) if self.service_client else "Not available",
                "primary_client": "service_role" if self.use_service_role else "anon"
            },
            "healthy": self._is_healthy()
        }
    
    def _is_healthy(self) -> bool:
        """Determine overall health status."""
        # Check basic client availability
        if not (self.anon_client or self.service_client):
            return False
        
        # Check error rate (< 10%)
        if self._error_count / max(self._operation_count, 1) >= 0.1:
            return False
        
        # Check if too many circuits are open
        if self.settings.circuit_breaker_enabled:
            open_circuits = sum(1 for state in self._circuit_breaker_state.values() if state == 'open')
            if open_circuits > len(self._circuit_breaker_state) * 0.5:  # More than 50% circuits open
                return False
        
        # Check connection pool health
        if self._pool_exhaustion_count > 10:  # Too many exhaustion events
            return False
        
        return True

    # Error handling and HTTP status mapping utility
    @staticmethod
    def map_exception_to_status(exc: Exception) -> int:
        """Enhanced exception to HTTP status mapping."""
        if isinstance(exc, asyncio.TimeoutError):
            return 504
        if hasattr(exc, 'status_code'):
            return getattr(exc, 'status_code')
        return 500

    def schema(self, schema_name: str, admin_operation: Optional[bool] = None) -> 'QueryBuilder':
        """
        Select schema for query operations (fluent API entry point).

        Args:
            schema_name: Schema name ('law', 'client', 'graph', 'public')
            admin_operation: If specified, overrides use_service_role for this query chain

        Returns:
            QueryBuilder instance for fluent chaining

        Examples:
            # Basic query
            nodes = await client.schema('graph').table('nodes') \
                .select('*') \
                .eq('client_id', 'abc') \
                .execute()

            # Count query
            result = await client.schema('client').table('entities') \
                .select('count', count='exact') \
                .eq('entity_type', 'STATUTE_CITATION') \
                .execute()
            total = result.count

            # NULL check (data quality)
            nulls = await client.schema('graph').table('nodes') \
                .select('count', count='exact') \
                .is_('client_id', 'null') \
                .execute()
        """
        # Use provided admin_operation or fall back to instance default
        use_admin = admin_operation if admin_operation is not None else self.use_service_role

        return QueryBuilder(
            client=self,
            schema=schema_name,
            admin_operation=use_admin
        )

    def storage(self, bucket_name: str, admin_operation: Optional[bool] = None) -> 'StorageQueryBuilder':
        """
        Select storage bucket for file operations (fluent API entry point).

        Args:
            bucket_name: Storage bucket name
            admin_operation: If specified, overrides use_service_role for this storage chain

        Returns:
            StorageQueryBuilder instance for fluent chaining

        Examples:
            # Upload file
            result = await client.storage('documents') \
                .upload('path/to/file.pdf', file_data) \
                .execute()

            # Download file
            data = await client.storage('documents') \
                .download('path/to/file.pdf') \
                .execute()

            # List files in directory
            files = await client.storage('documents') \
                .list('client-123/') \
                .execute()

            # Get public URL
            url = await client.storage('documents') \
                .get_public_url('path/to/file.pdf')

            # Remove file
            result = await client.storage('documents') \
                .remove(['path/to/file1.pdf', 'path/to/file2.pdf']) \
                .execute()
        """
        # Use provided admin_operation or fall back to instance default (True for storage)
        use_admin = admin_operation if admin_operation is not None else True

        return StorageQueryBuilder(
            client=self,
            bucket=bucket_name,
            admin_operation=use_admin
        )


# ============================================================
# QueryBuilder Classes - Fluent API Implementation
# ============================================================

class QueryBuilder:
    """
    Entry point for fluent Supabase API.
    Returned by SupabaseClient.schema() method.
    """

    def __init__(
        self,
        client: 'SupabaseClient',
        schema: str,
        admin_operation: bool = False
    ):
        """
        Initialize QueryBuilder with schema context.

        Args:
            client: Parent SupabaseClient instance
            schema: Schema name ('law', 'client', 'graph', 'public')
            admin_operation: If True, use service_role client
        """
        self._client = client
        self._schema = schema
        self._admin_operation = admin_operation

    def table(self, name: str) -> 'TableQueryBuilder':
        """
        Select table for query operations.

        Args:
            name: Table name (without schema prefix)

        Returns:
            TableQueryBuilder for method chaining

        Example:
            builder = client.schema('graph').table('nodes')
        """
        return TableQueryBuilder(
            self._client,
            self._schema,
            name,
            self._admin_operation
        )

    def from_(self, name: str) -> 'TableQueryBuilder':
        """Alias for table() method"""
        return self.table(name)


class TableQueryBuilder:
    """Query type selector for table operations"""

    def __init__(
        self,
        client: 'SupabaseClient',
        schema: str,
        table: str,
        admin_operation: bool
    ):
        self._client = client
        self._schema = schema
        self._table = table
        self._admin_operation = admin_operation

    def select(
        self,
        columns: str = '*',
        count: Optional[str] = None
    ) -> 'SelectQueryBuilder':
        """
        Start SELECT query.

        Args:
            columns: Columns to select (default '*')
            count: Count mode ('exact', 'planned', 'estimated')

        Returns:
            SelectQueryBuilder for filter/modifier chaining
        """
        return SelectQueryBuilder(
            self._client,
            self._schema,
            self._table,
            columns,
            count,
            self._admin_operation
        )

    def insert(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> 'InsertQueryBuilder':
        """Start INSERT query"""
        return InsertQueryBuilder(
            self._client,
            self._schema,
            self._table,
            data,
            self._admin_operation
        )

    def update(self, data: Dict[str, Any]) -> 'UpdateQueryBuilder':
        """Start UPDATE query"""
        return UpdateQueryBuilder(
            self._client,
            self._schema,
            self._table,
            data,
            self._admin_operation
        )

    def delete(self) -> 'DeleteQueryBuilder':
        """Start DELETE query"""
        return DeleteQueryBuilder(
            self._client,
            self._schema,
            self._table,
            self._admin_operation
        )

    def upsert(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None
    ) -> 'UpsertQueryBuilder':
        """Start UPSERT query"""
        return UpsertQueryBuilder(
            self._client,
            self._schema,
            self._table,
            data,
            on_conflict,
            self._admin_operation
        )


class SelectQueryBuilder:
    """
    SELECT query builder with full filter and modifier support.
    Implements complete supabase-py select API.
    """

    def __init__(
        self,
        client: 'SupabaseClient',
        schema: str,
        table: str,
        columns: str,
        count: Optional[str],
        admin_operation: bool
    ):
        self._client = client
        self._schema = schema
        self._table = table
        self._columns = columns
        self._count = count
        self._admin_operation = admin_operation
        self._filters = []  # List of (filter_type, column, value) tuples
        self._modifiers = []  # List of (modifier_type, *args) tuples

    # ========== FILTER METHODS (return self for chaining) ==========

    def eq(self, column: str, value: Any) -> 'SelectQueryBuilder':
        """Add equality filter: column = value"""
        self._filters.append(('eq', column, value))
        return self

    def neq(self, column: str, value: Any) -> 'SelectQueryBuilder':
        """Add not equal filter: column != value"""
        self._filters.append(('neq', column, value))
        return self

    def gt(self, column: str, value: Any) -> 'SelectQueryBuilder':
        """Add greater than filter: column > value"""
        self._filters.append(('gt', column, value))
        return self

    def gte(self, column: str, value: Any) -> 'SelectQueryBuilder':
        """Add greater than or equal filter: column >= value"""
        self._filters.append(('gte', column, value))
        return self

    def lt(self, column: str, value: Any) -> 'SelectQueryBuilder':
        """Add less than filter: column < value"""
        self._filters.append(('lt', column, value))
        return self

    def lte(self, column: str, value: Any) -> 'SelectQueryBuilder':
        """Add less than or equal filter: column <= value"""
        self._filters.append(('lte', column, value))
        return self

    def like(self, column: str, pattern: str) -> 'SelectQueryBuilder':
        """Add LIKE filter: column LIKE pattern"""
        self._filters.append(('like', column, pattern))
        return self

    def ilike(self, column: str, pattern: str) -> 'SelectQueryBuilder':
        """Add case-insensitive LIKE filter: column ILIKE pattern"""
        self._filters.append(('ilike', column, pattern))
        return self

    def is_(self, column: str, value: str) -> 'SelectQueryBuilder':
        """
        Add IS filter for NULL checks.

        Args:
            column: Column name
            value: 'null' or 'not.null'

        Example:
            .is_('client_id', 'null')  # WHERE client_id IS NULL
        """
        self._filters.append(('is', column, value))
        return self

    def in_(self, column: str, values: List[Any]) -> 'SelectQueryBuilder':
        """Add IN filter: column IN (values)"""
        self._filters.append(('in', column, values))
        return self

    def contains(self, column: str, value: Union[List, Dict]) -> 'SelectQueryBuilder':
        """Add CONTAINS filter for JSONB/array columns"""
        self._filters.append(('contains', column, value))
        return self

    def contained_by(self, column: str, value: Union[List, Dict]) -> 'SelectQueryBuilder':
        """Add CONTAINED BY filter for JSONB/array columns"""
        self._filters.append(('contained_by', column, value))
        return self

    def range_(self, column: str, start: Any, end: Any) -> 'SelectQueryBuilder':
        """Add range filter: column BETWEEN start AND end"""
        self._filters.append(('range', column, (start, end)))
        return self

    # ========== MODIFIER METHODS (return self for chaining) ==========

    def order(
        self,
        column: str,
        desc: bool = False,
        nullsfirst: bool = False
    ) -> 'SelectQueryBuilder':
        """
        Add ORDER BY clause.

        Args:
            column: Column to order by
            desc: If True, descending order
            nullsfirst: If True, nulls first
        """
        self._modifiers.append(('order', column, desc, nullsfirst))
        return self

    def limit(self, count: int) -> 'SelectQueryBuilder':
        """Add LIMIT clause"""
        self._modifiers.append(('limit', count))
        return self

    def offset(self, count: int) -> 'SelectQueryBuilder':
        """Add OFFSET clause"""
        self._modifiers.append(('offset', count))
        return self

    def range(self, start: int, end: int) -> 'SelectQueryBuilder':
        """
        Add range (LIMIT + OFFSET) clause.

        Args:
            start: Start index (0-based)
            end: End index (inclusive)
        """
        self._modifiers.append(('range', start, end))
        return self

    def single(self) -> 'SelectQueryBuilder':
        """Expect single result (will error if multiple)"""
        self._modifiers.append(('single',))
        return self

    def maybe_single(self) -> 'SelectQueryBuilder':
        """Return single result or None"""
        self._modifiers.append(('maybe_single',))
        return self

    # ========== EXECUTE METHOD (runs query through safety layer) ==========

    async def execute(self):
        """
        Execute SELECT query through SupabaseClient._execute().

        This method:
        1. Builds query using supabase-py Client fluent API
        2. Applies all accumulated filters
        3. Applies all accumulated modifiers
        4. Executes through SupabaseClient._execute() for safety

        Returns:
            Response object with .data and .count attributes
        """
        def query_fn(client):
            # Use explicit schema routing for custom schemas
            if self._schema and self._schema in ['law', 'client', 'graph']:
                # Use schema().from_() for explicit schema routing
                query = client.schema(self._schema).from_(self._table).select(
                    self._columns,
                    count=self._count
                )
            else:
                # Default to public schema (no schema specified)
                query = client.table(self._table).select(
                    self._columns,
                    count=self._count
                )

            # Apply all filters
            for filter_spec in self._filters:
                filter_type = filter_spec[0]
                column = filter_spec[1]

                if filter_type == 'eq':
                    query = query.eq(column, filter_spec[2])
                elif filter_type == 'neq':
                    query = query.neq(column, filter_spec[2])
                elif filter_type == 'gt':
                    query = query.gt(column, filter_spec[2])
                elif filter_type == 'gte':
                    query = query.gte(column, filter_spec[2])
                elif filter_type == 'lt':
                    query = query.lt(column, filter_spec[2])
                elif filter_type == 'lte':
                    query = query.lte(column, filter_spec[2])
                elif filter_type == 'like':
                    query = query.like(column, filter_spec[2])
                elif filter_type == 'ilike':
                    query = query.ilike(column, filter_spec[2])
                elif filter_type == 'is':
                    query = query.is_(column, filter_spec[2])
                elif filter_type == 'in':
                    query = query.in_(column, filter_spec[2])
                elif filter_type == 'contains':
                    query = query.contains(column, filter_spec[2])
                elif filter_type == 'contained_by':
                    query = query.contained_by(column, filter_spec[2])
                elif filter_type == 'range':
                    start, end = filter_spec[2]
                    query = query.range(column, start, end)

            # Apply all modifiers
            for modifier_spec in self._modifiers:
                modifier_type = modifier_spec[0]

                if modifier_type == 'order':
                    column, desc, nullsfirst = modifier_spec[1:4]
                    query = query.order(column, desc=desc, nullsfirst=nullsfirst)
                elif modifier_type == 'limit':
                    query = query.limit(modifier_spec[1])
                elif modifier_type == 'offset':
                    query = query.offset(modifier_spec[1])
                elif modifier_type == 'range':
                    start, end = modifier_spec[1:3]
                    query = query.range(start, end)
                elif modifier_type == 'single':
                    query = query.single()
                elif modifier_type == 'maybe_single':
                    query = query.maybe_single()

            # Execute query
            response = query.execute()

            # Return response with data and count
            result = type('Response', (), {
                'data': response.data,
                'count': getattr(response, 'count', None)
            })()
            return result

        # Execute through SupabaseClient._execute() for all safety features
        return await self._client._execute(
            operation='select',
            func=query_fn,
            admin_operation=self._admin_operation,
            schema=self._schema
        )


class InsertQueryBuilder:
    """INSERT query builder"""

    def __init__(
        self,
        client: 'SupabaseClient',
        schema: str,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        admin_operation: bool
    ):
        self._client = client
        self._schema = schema
        self._table = table
        self._data = data
        self._admin_operation = admin_operation
        self._returning = 'representation'

    def returning(self, columns: str = 'representation') -> 'InsertQueryBuilder':
        """Set what to return after insert"""
        self._returning = columns
        return self

    async def execute(self):
        """Execute INSERT query through SupabaseClient._execute()"""
        def query_fn(client):
            # Use explicit schema routing for custom schemas
            if self._schema and self._schema in ['law', 'client', 'graph']:
                query = client.schema(self._schema).from_(self._table).insert(self._data)
            else:
                query = client.table(self._table).insert(self._data)

            response = query.execute()

            result = type('Response', (), {
                'data': response.data,
                'count': getattr(response, 'count', None)
            })()
            return result

        return await self._client._execute(
            operation='insert',
            func=query_fn,
            admin_operation=self._admin_operation,
            schema=self._schema
        )


class UpdateQueryBuilder:
    """UPDATE query builder with filter support"""

    def __init__(
        self,
        client: 'SupabaseClient',
        schema: str,
        table: str,
        data: Dict[str, Any],
        admin_operation: bool
    ):
        self._client = client
        self._schema = schema
        self._table = table
        self._data = data
        self._admin_operation = admin_operation
        self._filters = []

    def eq(self, column: str, value: Any) -> 'UpdateQueryBuilder':
        """Add equality filter"""
        self._filters.append(('eq', column, value))
        return self

    def neq(self, column: str, value: Any) -> 'UpdateQueryBuilder':
        """Add not equal filter"""
        self._filters.append(('neq', column, value))
        return self

    def gt(self, column: str, value: Any) -> 'UpdateQueryBuilder':
        """Add greater than filter"""
        self._filters.append(('gt', column, value))
        return self

    def gte(self, column: str, value: Any) -> 'UpdateQueryBuilder':
        """Add greater than or equal filter"""
        self._filters.append(('gte', column, value))
        return self

    def in_(self, column: str, values: List[Any]) -> 'UpdateQueryBuilder':
        """Add IN filter"""
        self._filters.append(('in', column, values))
        return self

    def like(self, column: str, pattern: str) -> 'UpdateQueryBuilder':
        """Add LIKE filter"""
        self._filters.append(('like', column, pattern))
        return self

    async def execute(self):
        """Execute UPDATE query through SupabaseClient._execute()"""
        def query_fn(client):
            # Use explicit schema routing for custom schemas
            if self._schema and self._schema in ['law', 'client', 'graph']:
                query = client.schema(self._schema).from_(self._table).update(self._data)
            else:
                query = client.table(self._table).update(self._data)

            # Apply filters
            for filter_spec in self._filters:
                filter_type = filter_spec[0]
                column = filter_spec[1]
                value = filter_spec[2]

                if filter_type == 'eq':
                    query = query.eq(column, value)
                elif filter_type == 'neq':
                    query = query.neq(column, value)
                elif filter_type == 'gt':
                    query = query.gt(column, value)
                elif filter_type == 'gte':
                    query = query.gte(column, value)
                elif filter_type == 'in':
                    query = query.in_(column, value)
                elif filter_type == 'like':
                    query = query.like(column, value)

            response = query.execute()

            result = type('Response', (), {
                'data': response.data,
                'count': getattr(response, 'count', None)
            })()
            return result

        return await self._client._execute(
            operation='update',
            func=query_fn,
            admin_operation=self._admin_operation,
            schema=self._schema
        )


class DeleteQueryBuilder:
    """DELETE query builder with filter support"""

    def __init__(
        self,
        client: 'SupabaseClient',
        schema: str,
        table: str,
        admin_operation: bool
    ):
        self._client = client
        self._schema = schema
        self._table = table
        self._admin_operation = admin_operation
        self._filters = []

    def eq(self, column: str, value: Any) -> 'DeleteQueryBuilder':
        """Add equality filter"""
        self._filters.append(('eq', column, value))
        return self

    def neq(self, column: str, value: Any) -> 'DeleteQueryBuilder':
        """Add not equal filter"""
        self._filters.append(('neq', column, value))
        return self

    def in_(self, column: str, values: List[Any]) -> 'DeleteQueryBuilder':
        """Add IN filter"""
        self._filters.append(('in', column, values))
        return self

    def like(self, column: str, pattern: str) -> 'DeleteQueryBuilder':
        """Add LIKE filter"""
        self._filters.append(('like', column, pattern))
        return self

    async def execute(self):
        """Execute DELETE query through SupabaseClient._execute()"""
        def query_fn(client):
            # Use explicit schema routing for custom schemas
            if self._schema and self._schema in ['law', 'client', 'graph']:
                query = client.schema(self._schema).from_(self._table).delete()
            else:
                query = client.table(self._table).delete()

            # Apply filters
            for filter_spec in self._filters:
                filter_type = filter_spec[0]
                column = filter_spec[1]
                value = filter_spec[2]

                if filter_type == 'eq':
                    query = query.eq(column, value)
                elif filter_type == 'neq':
                    query = query.neq(column, value)
                elif filter_type == 'in':
                    query = query.in_(column, value)
                elif filter_type == 'like':
                    query = query.like(column, value)

            response = query.execute()

            result = type('Response', (), {
                'data': response.data,
                'count': getattr(response, 'count', None)
            })()
            return result

        return await self._client._execute(
            operation='delete',
            func=query_fn,
            admin_operation=self._admin_operation,
            schema=self._schema
        )


class UpsertQueryBuilder:
    """UPSERT query builder"""

    def __init__(
        self,
        client: 'SupabaseClient',
        schema: str,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str],
        admin_operation: bool
    ):
        self._client = client
        self._schema = schema
        self._table = table
        self._data = data
        self._on_conflict = on_conflict
        self._admin_operation = admin_operation
        self._ignore_duplicates = False

    def on_conflict(self, columns: str) -> 'UpsertQueryBuilder':
        """Set conflict columns"""
        self._on_conflict = columns
        return self

    def ignore_duplicates(self, ignore: bool = True) -> 'UpsertQueryBuilder':
        """Set whether to ignore duplicates"""
        self._ignore_duplicates = ignore
        return self

    async def execute(self):
        """Execute UPSERT query through SupabaseClient._execute()"""
        def query_fn(client):
            # Use explicit schema routing for custom schemas
            if self._schema and self._schema in ['law', 'client', 'graph']:
                query = client.schema(self._schema).from_(self._table).upsert(
                    self._data,
                    on_conflict=self._on_conflict,
                    ignore_duplicates=self._ignore_duplicates
                )
            else:
                query = client.table(self._table).upsert(
                    self._data,
                    on_conflict=self._on_conflict,
                    ignore_duplicates=self._ignore_duplicates
                )

            response = query.execute()

            result = type('Response', (), {
                'data': response.data,
                'count': getattr(response, 'count', None)
            })()
            return result

        return await self._client._execute(
            operation='upsert',
            func=query_fn,
            admin_operation=self._admin_operation,
            schema=self._schema
        )


class StorageQueryBuilder:
    """
    Storage operations builder for Supabase Storage.

    Provides fluent API for file upload, download, list, and removal operations.
    All operations route through SupabaseClient._execute() for safety features.
    """

    def __init__(
        self,
        client: 'SupabaseClient',
        bucket: str,
        admin_operation: bool
    ):
        """
        Initialize StorageQueryBuilder.

        Args:
            client: Parent SupabaseClient instance
            bucket: Storage bucket name
            admin_operation: If True, use service_role client
        """
        self._client = client
        self._bucket = bucket
        self._admin_operation = admin_operation
        self._operation = None  # 'upload', 'download', 'list', 'remove'
        self._path = None
        self._file_data = None
        self._file_options = {}
        self._paths = []  # For batch remove
        self._list_options = {}

    def upload(
        self,
        path: str,
        file_data: bytes,
        upsert: bool = True,
        content_type: Optional[str] = None
    ) -> 'StorageQueryBuilder':
        """
        Upload file to storage bucket.

        Args:
            path: File path in bucket (e.g., 'client-123/document.pdf')
            file_data: File content as bytes
            upsert: If True, overwrite existing files (default: True)
            content_type: Optional MIME type (e.g., 'application/pdf')

        Returns:
            Self for chaining (call .execute() to run)

        Example:
            result = await client.storage('documents') \\
                .upload('client-123/file.pdf', file_data, content_type='application/pdf') \\
                .execute()
        """
        self._operation = 'upload'
        self._path = path
        self._file_data = file_data
        self._file_options = {'upsert': upsert}
        if content_type:
            self._file_options['content_type'] = content_type
        return self

    def download(self, path: str) -> 'StorageQueryBuilder':
        """
        Download file from storage bucket.

        Args:
            path: File path in bucket

        Returns:
            Self for chaining (call .execute() to run)

        Example:
            file_data = await client.storage('documents') \\
                .download('client-123/file.pdf') \\
                .execute()
        """
        self._operation = 'download'
        self._path = path
        return self

    def list(
        self,
        path: str = '',
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None
    ) -> 'StorageQueryBuilder':
        """
        List files in storage bucket directory.

        Args:
            path: Directory path (default: root)
            limit: Maximum files to return
            offset: Number of files to skip
            sort_by: Sort by 'name', 'updated_at', 'created_at', 'last_accessed_at'

        Returns:
            Self for chaining (call .execute() to run)

        Example:
            files = await client.storage('documents') \\
                .list('client-123/', limit=50, sort_by='updated_at') \\
                .execute()
        """
        self._operation = 'list'
        self._path = path
        self._list_options = {
            'limit': limit,
            'offset': offset
        }
        if sort_by:
            self._list_options['sortBy'] = {'column': sort_by, 'order': 'desc'}
        return self

    def remove(self, paths: Union[str, List[str]]) -> 'StorageQueryBuilder':
        """
        Remove file(s) from storage bucket.

        Args:
            paths: Single path or list of paths to remove

        Returns:
            Self for chaining (call .execute() to run)

        Example:
            # Remove single file
            result = await client.storage('documents') \\
                .remove('client-123/file.pdf') \\
                .execute()

            # Remove multiple files
            result = await client.storage('documents') \\
                .remove(['file1.pdf', 'file2.pdf']) \\
                .execute()
        """
        self._operation = 'remove'
        self._paths = [paths] if isinstance(paths, str) else paths
        return self

    def get_public_url(self, path: str) -> str:
        """
        Get public URL for a file (synchronous, no execute() needed).

        Args:
            path: File path in bucket

        Returns:
            Public URL string

        Example:
            url = client.storage('documents').get_public_url('client-123/file.pdf')
        """
        supabase_client = self._client._get_client(self._admin_operation)
        return supabase_client.storage.from_(self._bucket).get_public_url(path)

    def create_signed_url(
        self,
        path: str,
        expires_in: int = 3600
    ) -> 'StorageQueryBuilder':
        """
        Create signed URL for private file access.

        Args:
            path: File path in bucket
            expires_in: URL expiration time in seconds (default: 3600 = 1 hour)

        Returns:
            Self for chaining (call .execute() to run)

        Example:
            signed_url = await client.storage('private-docs') \\
                .create_signed_url('client-123/confidential.pdf', expires_in=1800) \\
                .execute()
        """
        self._operation = 'create_signed_url'
        self._path = path
        self._file_options = {'expires_in': expires_in}
        return self

    async def execute(self):
        """
        Execute storage operation through SupabaseClient._execute().

        Returns:
            Operation result (type depends on operation):
            - upload: Dict with path, bucket, url, size
            - download: bytes (file content)
            - list: List of file metadata dicts
            - remove: Dict with success status
            - create_signed_url: Dict with signed_url

        Raises:
            ValueError: If no operation specified or invalid operation
        """
        if not self._operation:
            raise ValueError("No storage operation specified. Use upload(), download(), list(), or remove()")

        if self._operation == 'upload':
            return await self._execute_upload()
        elif self._operation == 'download':
            return await self._execute_download()
        elif self._operation == 'list':
            return await self._execute_list()
        elif self._operation == 'remove':
            return await self._execute_remove()
        elif self._operation == 'create_signed_url':
            return await self._execute_create_signed_url()
        else:
            raise ValueError(f"Unknown storage operation: {self._operation}")

    async def _execute_upload(self):
        """Execute upload operation"""
        def op(client):
            from io import BytesIO
            import tempfile
            import os

            # Set default options
            options = self._file_options or {}
            if "upsert" not in options:
                options["upsert"] = True

            # Save to temporary file (Supabase Python client expects file path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(self._path)[1]) as tmp_file:
                tmp_file.write(self._file_data)
                tmp_file_path = tmp_file.name

            try:
                # Remove existing file if upserting
                if options.get("upsert", True):
                    try:
                        client.storage.from_(self._bucket).remove([self._path])
                    except:
                        pass  # File might not exist

                # Upload file
                result = client.storage.from_(self._bucket).upload(
                    self._path,
                    tmp_file_path
                )

                # Get public URL
                url = client.storage.from_(self._bucket).get_public_url(self._path)

                return {
                    "path": self._path,
                    "bucket": self._bucket,
                    "url": url,
                    "size": len(self._file_data),
                    "public_url": url
                }
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)

        return await self._client._execute("upload_file", op, self._admin_operation)

    async def _execute_download(self):
        """Execute download operation"""
        def op(client):
            return client.storage.from_(self._bucket).download(self._path)

        return await self._client._execute("download_file", op, self._admin_operation)

    async def _execute_list(self):
        """Execute list operation"""
        def op(client):
            list_args = {
                'path': self._path,
                'limit': self._list_options.get('limit', 100),
                'offset': self._list_options.get('offset', 0)
            }

            # Add sort if specified
            if 'sortBy' in self._list_options:
                list_args['sortBy'] = self._list_options['sortBy']

            result = client.storage.from_(self._bucket).list(**list_args)
            return result

        return await self._client._execute("list_files", op, self._admin_operation)

    async def _execute_remove(self):
        """Execute remove operation"""
        def op(client):
            result = client.storage.from_(self._bucket).remove(self._paths)
            return {
                "success": True,
                "paths": self._paths,
                "bucket": self._bucket,
                "count": len(self._paths)
            }

        return await self._client._execute("delete_file", op, self._admin_operation)

    async def _execute_create_signed_url(self):
        """Execute create signed URL operation"""
        def op(client):
            expires_in = self._file_options.get('expires_in', 3600)
            result = client.storage.from_(self._bucket).create_signed_url(
                self._path,
                expires_in
            )
            return result

        return await self._client._execute("create_signed_url", op, self._admin_operation)


# Factory functions for easy client creation
def create_supabase_client(
    service_name: str,
    log_client: Optional[LogClient] = None,
    settings: Optional[SupabaseSettings] = None,
    use_service_role: bool = False
) -> SupabaseClient:
    """
    Factory function to create a configured SupabaseClient for a service.
    
    Args:
        service_name: Name of the service using the client
        log_client: Optional LogClient instance
        settings: Optional SupabaseSettings instance
        use_service_role: If True, use service_role key as primary client
        
    Returns:
        Configured SupabaseClient instance with dual-client architecture
    """
    if settings is None:
        settings = SupabaseSettings(service_name=service_name)
    
    return SupabaseClient(
        settings=settings,
        log_client=log_client,
        service_name=service_name,
        use_service_role=use_service_role
    )

def create_admin_supabase_client(
    service_name: str,
    log_client: Optional[LogClient] = None,
    settings: Optional[SupabaseSettings] = None
) -> SupabaseClient:
    """
    Factory function to create a SupabaseClient with service_role as primary.
    
    This is useful for services that primarily perform admin operations
    like data ingestion, migrations, or bulk operations.
    
    Args:
        service_name: Name of the service using the client
        log_client: Optional LogClient instance
        settings: Optional SupabaseSettings instance
        
    Returns:
        SupabaseClient configured with service_role as primary
    """
    return create_supabase_client(
        service_name=service_name,
        log_client=log_client,
        settings=settings,
        use_service_role=True
    )