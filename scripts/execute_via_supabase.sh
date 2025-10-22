#!/bin/bash
# Execute GraphRAG migrations using Supabase tools
# This script executes SQL files in the correct order

echo "=================================================="
echo "GraphRAG Database Migration Execution"
echo "=================================================="
echo "Started at: $(date)"
echo ""

# Supabase connection details
SUPABASE_URL="https://tqfshsnwyhfnkchaiudg.supabase.co"
SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxZnNoc253eWhmbmtjaGFpdWRnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjIyMTY5MSwiZXhwIjoyMDUxNzk3NjkxfQ.IkU-6kLwNyGffui58B1ku5EPLHaI-XePXQodKOKFEu8"

# SQL files to execute
SQL_DIR="/srv/luris/be/sql"
SQL_FILES=(
    "law_schema.sql"
    "client_schema.sql"
    "graph_schema_core.sql"
    "graph_schema_knowledge.sql"
    "migrate_to_2048_dimensions.sql"
    "public_schema_views.sql"
)

# Function to execute SQL via curl to Supabase
execute_sql_file() {
    local file=$1
    local filename=$(basename $file)
    
    echo ""
    echo "--------------------------------------------------"
    echo "Executing: $filename"
    echo "--------------------------------------------------"
    
    # Check if file exists
    if [ ! -f "$file" ]; then
        echo "✗ File not found: $file"
        return 1
    fi
    
    # For now, we'll prepare the content
    # Actual execution would require the Supabase CLI or direct psql
    echo "  File size: $(wc -c < $file) bytes"
    echo "  Lines: $(wc -l < $file)"
    
    # Count statement types
    echo "  Statement types:"
    grep -E "^(CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|GRANT|COMMENT)" "$file" | \
        awk '{print $1}' | sort | uniq -c | while read count type; do
        echo "    $type: $count"
    done
    
    echo "  ✓ Ready for execution"
    return 0
}

# Main execution
echo "Preparing to execute ${#SQL_FILES[@]} migration files..."
echo ""

SUCCESS_COUNT=0
for sql_file in "${SQL_FILES[@]}"; do
    full_path="$SQL_DIR/$sql_file"
    if execute_sql_file "$full_path"; then
        ((SUCCESS_COUNT++))
    else
        echo "✗ Migration stopped at $sql_file"
        break
    fi
done

echo ""
echo "=================================================="
echo "MIGRATION SUMMARY"
echo "=================================================="
echo "Completed: $SUCCESS_COUNT/${#SQL_FILES[@]} files"

if [ $SUCCESS_COUNT -eq ${#SQL_FILES[@]} ]; then
    echo "✅ All migrations prepared successfully!"
    echo ""
    echo "To execute the migrations, use one of these methods:"
    echo ""
    echo "1. Supabase Dashboard SQL Editor:"
    echo "   - Go to: $SUPABASE_URL"
    echo "   - Navigate to SQL Editor"
    echo "   - Copy and paste each SQL file"
    echo ""
    echo "2. Using psql directly:"
    echo "   DATABASE_URL='postgresql://postgres:[password]@db.tqfshsnwyhfnkchaiudg.supabase.co:5432/postgres'"
    echo "   for file in ${SQL_FILES[@]}; do"
    echo "     psql \$DATABASE_URL -f $SQL_DIR/\$file"
    echo "   done"
    echo ""
    echo "3. Using Supabase CLI:"
    echo "   supabase db push --db-url \$DATABASE_URL"
else
    echo "⚠️ Migration preparation incomplete"
fi

echo "=================================================="
echo "Completed at: $(date)"
echo "=================================================="