#!/bin/bash
# Script to run table access tests with proper environment setup

# Check if .env file exists in parent directory
ENV_FILE="/srv/luris/be/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file not found at $ENV_FILE"
    echo "Please ensure Supabase credentials are configured"
    exit 1
fi

# Export environment variables
export $(grep -v '^#' $ENV_FILE | xargs)

# Run the test
cd /srv/luris/be/graphrag-service
venv/bin/python3 tests/test_all_tables_access.py