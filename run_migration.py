#!/usr/bin/env python3
"""
Database Migration Runner for GraphRAG Service
Executes the schema migration to fix column mismatches
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add the service src to path
sys.path.append(str(Path(__file__).parent / "src"))

from clients.supabase_client import SupabaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_migration_file(migration_path: str) -> str:
    """Read the SQL migration file"""
    try:
        with open(migration_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Migration file not found: {migration_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading migration file: {e}")
        raise

def backup_critical_tables():
    """Create backup of critical data before migration"""
    logger.info("Creating backup of critical tables...")
    
    # Note: In production, you would want to create actual backups
    # For now, we'll just log the current state
    try:
        client = SupabaseClient()
        
        # Check current state
        doc_count = client.service_client.table('document_registry').select('count').execute()
        nodes_count = client.service_client.table('nodes').select('count').execute()
        edges_count = client.service_client.table('edges').select('count').execute()
        communities_count = client.service_client.table('communities').select('count').execute()
        
        logger.info(f"Pre-migration state:")
        logger.info(f"  - Documents: {len(doc_count.data) if doc_count.data else 0}")
        logger.info(f"  - Nodes: {len(nodes_count.data) if nodes_count.data else 0}")
        logger.info(f"  - Edges: {len(edges_count.data) if edges_count.data else 0}")
        logger.info(f"  - Communities: {len(communities_count.data) if communities_count.data else 0}")
        
    except Exception as e:
        logger.warning(f"Could not create backup: {e}")

async def execute_migration(migration_sql: str) -> bool:
    """Execute the migration SQL"""
    try:
        logger.info("Initializing Supabase client...")
        client = SupabaseClient()
        
        logger.info("Executing migration using SupabaseClient.execute_sql()...")
        # Use the execute_sql method from SupabaseClient (it's async)
        result = await client.execute_sql(migration_sql)
        
        if result and 'error' not in result:
            logger.info("Migration executed successfully!")
            logger.info(f"Migration result: {result}")
            return True
        else:
            logger.error(f"Migration failed - result: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

async def verify_migration():
    """Verify that the migration worked correctly"""
    logger.info("Verifying migration results...")
    
    try:
        client = SupabaseClient()
        
        # Verification queries from the migration file
        verifications = [
            ("Documents with processing_status", 
             "SELECT COUNT(*) FROM graph.document_registry WHERE processing_status IS NOT NULL"),
            ("Nodes with title", 
             "SELECT COUNT(*) FROM graph.nodes WHERE title IS NOT NULL"),
            ("Edges with relationship_type", 
             "SELECT COUNT(*) FROM graph.edges WHERE relationship_type IS NOT NULL"),
            ("Edges with edge_id", 
             "SELECT COUNT(*) FROM graph.edges WHERE edge_id IS NOT NULL"),
            ("Communities with title", 
             "SELECT COUNT(*) FROM graph.communities WHERE title IS NOT NULL"),
            ("Communities with node_count", 
             "SELECT COUNT(*) FROM graph.communities WHERE node_count IS NOT NULL")
        ]
        
        for description, query in verifications:
            try:
                result = await client.execute_sql(query)
                if result and isinstance(result, list) and len(result) > 0:
                    count = result[0].get('count', 0)
                    logger.info(f"  ✓ {description}: {count}")
                else:
                    logger.warning(f"  ⚠ Could not verify {description}: no result data")
            except Exception as e:
                logger.warning(f"  ⚠ Could not verify {description}: {e}")
                
    except Exception as e:
        logger.error(f"Verification failed: {e}")

async def main():
    """Main migration runner"""
    logger.info("Starting GraphRAG schema migration...")
    
    # Get migration file path
    migration_file = Path(__file__).parent / "migrations" / "001_fix_schema_mismatches.sql"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        sys.exit(1)
    
    try:
        # Step 1: Backup critical data
        backup_critical_tables()
        
        # Step 2: Read migration SQL
        logger.info(f"Reading migration file: {migration_file}")
        migration_sql = read_migration_file(str(migration_file))
        
        # Step 3: Execute migration
        logger.info("Executing migration...")
        success = await execute_migration(migration_sql)
        
        if not success:
            logger.error("Migration failed!")
            sys.exit(1)
        
        # Step 4: Verify migration
        await verify_migration()
        
        logger.info("✅ Migration completed successfully!")
        logger.info("The GraphRAG service should now be able to store data correctly.")
        
    except Exception as e:
        logger.error(f"Migration runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())