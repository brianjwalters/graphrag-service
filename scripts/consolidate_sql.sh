#!/bin/bash
#
# Consolidate SQL batch files by table
# Combines all batches for each table into a single SQL file for easier execution
#

SQL_DIR="/srv/luris/be/graphrag-service/sql_inserts"
OUTPUT_DIR="/srv/luris/be/graphrag-service/sql_consolidated"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "==================================================================="
echo "Consolidating SQL Files by Table"
echo "==================================================================="
echo "Input directory: $SQL_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Table names (in foreign key dependency order)
tables=(
    "document_registry"
    "nodes"
    "communities"
    "edges"
    "node_communities"
    "chunks"
    "enhanced_contextual_chunks"
    "text_units"
    "reports"
)

total_size=0

for table in "${tables[@]}"; do
    echo "Processing: $table"

    output_file="$OUTPUT_DIR/${table}.sql"

    # Add header
    echo "-- Consolidated SQL for graph.$table" > "$output_file"
    echo "-- Generated: $(date --iso-8601=seconds)" >> "$output_file"
    echo "-- " >> "$output_file"
    echo "" >> "$output_file"

    # Start transaction
    echo "BEGIN;" >> "$output_file"
    echo "" >> "$output_file"

    # Concatenate all batch files for this table (sorted numerically)
    batch_count=0
    for batch_file in $(ls "$SQL_DIR/${table}_batch_"*.sql 2>/dev/null | sort -V); do
        if [ -f "$batch_file" ]; then
            # Skip header comments, just get the INSERT statements
            grep "^INSERT" "$batch_file" >> "$output_file"
            ((batch_count++))
        fi
    done

    # End transaction
    echo "" >> "$output_file"
    echo "COMMIT;" >> "$output_file"

    # Get file size
    file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
    file_size_mb=$(echo "scale=2; $file_size / 1024 / 1024" | bc)
    total_size=$((total_size + file_size))

    echo "  ✓ Consolidated $batch_count batches → $output_file ($file_size_mb MB)"
done

total_size_mb=$(echo "scale=2; $total_size / 1024 / 1024" | bc)

echo ""
echo "==================================================================="
echo "Consolidation Complete"
echo "==================================================================="
echo "Total files created: ${#tables[@]}"
echo "Total size: $total_size_mb MB"
echo ""
echo "Files ready for execution in foreign key order:"
for i in "${!tables[@]}"; do
    echo "  $((i+1)). ${tables[$i]}.sql"
done
echo ""
echo "Next step: Execute SQL files via MCP execute_sql tool"
