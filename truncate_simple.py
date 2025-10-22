#!/usr/bin/env python3
"""Simple truncate using direct Supabase client"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment
load_dotenv("/srv/luris/be/graphrag-service/.env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")  # Service role key for admin operations

print(f"URL: {url}")
print(f"Key: {'***' + key[-10:] if key else 'None'}")

if not url or not key:
    print("❌ Missing credentials")
    exit(1)

supabase = create_client(url, key)

# Tables in dependency order
tables = [
    "graph_node_communities",
    "graph_edges",
    "graph_communities",
    "graph_nodes",
    "graph_document_registry"
]

for table in tables:
    try:
        print(f"\n🗑️  Clearing {table}...")
        # Delete all rows where id is not null (which is all rows)
        result = supabase.from_(table).delete().neq('created_at', '1900-01-01').execute()
        print(f"   ✅ Cleared {table}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n✅ Done!")
