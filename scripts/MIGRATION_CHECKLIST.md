# Migration Checklist: From Direct Client to Fluent API

**Purpose**: Step-by-step guide for migrating scripts from direct client access to fluent API

---

## 🎯 Migration Goals

1. ✅ Use fluent API instead of `client.service_client.schema().table()`
2. ✅ Gain timeout protection (30s default)
3. ✅ Gain retry logic (3 retries with exponential backoff)
4. ✅ Gain circuit breaker protection
5. ✅ Gain Prometheus metrics tracking
6. ✅ Gain comprehensive error handling

---

## 📋 Step-by-Step Migration

### Step 1: Replace Imports

**Before**:
```python
from src.clients.supabase_client import SupabaseClient
```

**After**:
```python
from src.clients.supabase_client import create_admin_supabase_client
import asyncio
```

**Why**:
- Factory functions provide cleaner initialization
- Async support requires `asyncio` import

---

### Step 2: Replace Client Initialization

**Before**:
```python
client = SupabaseClient()
```

**After**:
```python
client = create_admin_supabase_client(service_name="my-service-name")
```

**Options**:
- `create_supabase_client()` - Uses anon key (RLS enforced)
- `create_admin_supabase_client()` - Uses service_role key (bypasses RLS)

**Why**:
- Factory functions handle dual-client setup
- Service name enables better logging/metrics

---

### Step 3: Replace Direct Client Access

**Before** (❌ UNSAFE):
```python
result = client.service_client.schema('graph').table('nodes') \
    .select('count', count='exact') \
    .execute()
```

**After** (✅ SAFE):
```python
result = await client.schema('graph').table('nodes') \
    .select('count', count='exact') \
    .execute()
```

**Changes**:
- Remove `.service_client.` or `.anon_client.`
- Add `await` keyword
- Keep everything else the same!

**Why**:
- Fluent API automatically selects correct client
- Timeout, retry, circuit breaker all automatic
- Metrics tracked automatically

---

### Step 4: Make Function Async

**Before**:
```python
def validate_schema():
    result = client.service_client.schema(...).execute()
    return result.count
```

**After**:
```python
async def validate_schema() -> int:
    result = await client.schema(...).execute()
    return result.count
```

**Changes**:
- Add `async` before `def`
- Add `await` before `client.schema(...).execute()`
- Add return type hint (optional but recommended)

---

### Step 5: Add Error Handling

**Before** (no error handling):
```python
result = client.service_client.schema(...).execute()
```

**After** (comprehensive error handling):
```python
try:
    result = await client.schema(...).execute()
except asyncio.TimeoutError:
    print('Operation timed out after 30s')
    # Handle timeout
except Exception as e:
    print(f'Error: {e}')
    # Handle other errors
```

**Why**:
- Timeout errors are now detectable
- Proper error recovery possible
- Better user feedback

---

### Step 6: Update Main Entry Point

**Before**:
```python
if __name__ == '__main__':
    validate_schema()
```

**After**:
```python
if __name__ == '__main__':
    asyncio.run(validate_schema())
```

**Why**:
- `asyncio.run()` creates event loop
- Proper async execution
- Automatic cleanup

---

### Step 7: Add Health Monitoring (Optional)

**New Feature**:
```python
# Get comprehensive health info
health = client.get_health_info()

print(f'Total operations: {health["operation_count"]}')
print(f'Error rate: {health["error_rate"]:.2%}')
print(f'Average latency: {health["performance"]["average_latency_seconds"]:.3f}s')
print(f'Healthy: {"✅" if health["healthy"] else "❌"}')
```

**Why**:
- Monitor client performance
- Detect issues early
- Production-ready monitoring

---

## 🔍 Common Patterns

### Pattern 1: SELECT with Filters

**Before**:
```python
result = client.service_client.schema('graph').table('nodes') \
    .select('id,title,content') \
    .eq('status', 'active') \
    .gte('created_at', '2024-01-01') \
    .execute()
```

**After**:
```python
result = await client.schema('graph').table('nodes') \
    .select('id,title,content') \
    .eq('status', 'active') \
    .gte('created_at', '2024-01-01') \
    .execute()
```

**Changes**: Just add `await` and remove `.service_client.`

---

### Pattern 2: INSERT

**Before**:
```python
result = client.service_client.schema('graph').table('nodes') \
    .insert({'title': 'Test', 'content': 'Data'}) \
    .execute()
```

**After**:
```python
result = await client.schema('graph').table('nodes') \
    .insert({'title': 'Test', 'content': 'Data'}) \
    .execute()
```

**Changes**: Just add `await` and remove `.service_client.`

---

### Pattern 3: UPDATE

**Before**:
```python
result = client.service_client.schema('graph').table('nodes') \
    .update({'status': 'processed'}) \
    .eq('id', node_id) \
    .execute()
```

**After**:
```python
result = await client.schema('graph').table('nodes') \
    .update({'status': 'processed'}) \
    .eq('id', node_id) \
    .execute()
```

**Changes**: Just add `await` and remove `.service_client.`

---

### Pattern 4: DELETE

**Before**:
```python
result = client.service_client.schema('graph').table('nodes') \
    .delete() \
    .eq('id', node_id) \
    .execute()
```

**After**:
```python
result = await client.schema('graph').table('nodes') \
    .delete() \
    .eq('id', node_id) \
    .execute()
```

**Changes**: Just add `await` and remove `.service_client.`

---

### Pattern 5: COUNT Queries

**Before**:
```python
result = client.service_client.schema('graph').table('nodes') \
    .select('count', count='exact') \
    .execute()
count = result.count
```

**After**:
```python
result = await client.schema('graph').table('nodes') \
    .select('count', count='exact') \
    .execute()
count = result.count
```

**Changes**: Just add `await` and remove `.service_client.`

---

## 📊 Complete Example

### Original Script (Direct Client Access)

```python
from src.clients.supabase_client import SupabaseClient

client = SupabaseClient()

def validate_tables():
    tables = ['nodes', 'edges', 'communities']

    for table in tables:
        # ❌ Direct client access - UNSAFE
        result = client.service_client.schema('graph').table(table) \
            .select('count', count='exact') \
            .execute()

        print(f'{table}: {result.count}')

if __name__ == '__main__':
    validate_tables()
```

### Refactored Script (Fluent API)

```python
from src.clients.supabase_client import create_admin_supabase_client
import asyncio

async def validate_tables():
    # ✅ Factory function
    client = create_admin_supabase_client(service_name="validator")

    tables = ['nodes', 'edges', 'communities']

    for table in tables:
        try:
            # ✅ Fluent API with full safety
            result = await client.schema('graph').table(table) \
                .select('count', count='exact') \
                .execute()

            print(f'{table}: {result.count}')

        except asyncio.TimeoutError:
            print(f'{table}: TIMEOUT')
        except Exception as e:
            print(f'{table}: ERROR - {e}')

    # ✅ Show health metrics
    health = client.get_health_info()
    print(f'\nTotal operations: {health["operation_count"]}')
    print(f'Error rate: {health["error_rate"]:.2%}')

if __name__ == '__main__':
    asyncio.run(validate_tables())
```

---

## ✅ Migration Checklist

Use this checklist for each script migration:

- [ ] Replace `SupabaseClient()` with factory function
- [ ] Add `import asyncio` if not present
- [ ] Make functions `async`
- [ ] Add `await` before `.execute()`
- [ ] Remove `.service_client.` or `.anon_client.`
- [ ] Add error handling (timeout + general)
- [ ] Update main entry point with `asyncio.run()`
- [ ] Test the refactored script
- [ ] Verify health metrics work
- [ ] Document any schema discoveries

---

## 🚨 Common Mistakes

### Mistake 1: Forgetting `await`
```python
# ❌ WRONG - Missing await
result = client.schema('graph').table('nodes').execute()

# ✅ CORRECT - With await
result = await client.schema('graph').table('nodes').execute()
```

### Mistake 2: Not Making Function Async
```python
# ❌ WRONG - Not async
def validate():
    result = await client.schema(...).execute()  # SyntaxError!

# ✅ CORRECT - Async function
async def validate():
    result = await client.schema(...).execute()
```

### Mistake 3: Still Using Direct Client
```python
# ❌ WRONG - Still direct access
result = await client.service_client.schema(...).execute()

# ✅ CORRECT - Fluent API
result = await client.schema(...).execute()
```

### Mistake 4: No Error Handling
```python
# ❌ WRONG - No error handling
result = await client.schema(...).execute()

# ✅ CORRECT - With error handling
try:
    result = await client.schema(...).execute()
except asyncio.TimeoutError:
    # Handle timeout
    pass
except Exception as e:
    # Handle other errors
    pass
```

---

## 🎯 Benefits Summary

After migration, you gain:

1. **Timeout Protection**: 30s default, configurable
2. **Retry Logic**: 3 retries with exponential backoff + jitter
3. **Circuit Breaker**: Automatic failure protection
4. **Metrics**: Prometheus tracking of all operations
5. **Error Handling**: Proper async exception handling
6. **Connection Pooling**: 30 connections by default
7. **Health Monitoring**: Real-time client health status
8. **Logging**: Structured logging with request IDs

**All of this with minimal code changes!**

---

## 📖 Reference

- **SupabaseClient Documentation**: `/srv/luris/be/shared/clients/SUPABASE_CLIENT_TROUBLESHOOTING.md`
- **Example Refactored Script**: `/srv/luris/be/graphrag-service/scripts/validate_graph_schema_fluent.py`
- **Comparison Document**: `/srv/luris/be/graphrag-service/scripts/FLUENT_API_REFACTOR_COMPARISON.md`
