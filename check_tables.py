#!/usr/bin/env python3
"""Check what's in the graph tables"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("/srv/luris/be/graphrag-service/.env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(url, key)

# Check nodes
result = supabase.from_("graph_nodes").select("*").limit(10).execute()
print(f"Nodes in database: {len(result.data)}")
if result.data:
    print(f"First node keys: {list(result.data[0].keys())}")
    for node in result.data:
        print(f"  - {node['node_id']}")
