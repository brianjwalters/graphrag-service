#!/bin/bash
# GraphRAG Database Migration Script
# Generated: 2025-08-29T16:22:11.868083

# Set your database connection string
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:[YOUR-PASSWORD]@db.tqfshsnwyhfnkchaiudg.supabase.co:5432/postgres}"

echo "=================================="
echo "GraphRAG Database Migration"
echo "=================================="

# Function to execute SQL file
execute_sql() {
    local file=$1
    echo ""
    echo "Executing: $(basename $file)"
    echo "----------------------------------"
    psql "$DATABASE_URL" -f "$file" -v ON_ERROR_STOP=1
    if [ $? -eq 0 ]; then
        echo "✓ Success"
    else
        echo "✗ Failed - stopping migration"
        exit 1
    fi
}

# Execute migrations in order
execute_sql "/srv/luris/be/sql/law_schema.sql"
execute_sql "/srv/luris/be/sql/client_schema.sql"
execute_sql "/srv/luris/be/sql/graph_schema_core.sql"
execute_sql "/srv/luris/be/sql/graph_schema_knowledge.sql"
execute_sql "/srv/luris/be/sql/migrate_to_2048_dimensions.sql"
execute_sql "/srv/luris/be/sql/public_schema_views.sql"

echo ""
echo "=================================="
echo "✅ All migrations completed!"
echo "=================================="
