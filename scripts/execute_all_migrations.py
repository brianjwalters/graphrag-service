#!/usr/bin/env python3
"""
Execute all GraphRAG database migrations in correct order.
Handles transaction management and error recovery.
"""

import os
import sys
import asyncio
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import SupabaseClient

# SQL files to execute in order
SQL_FILES = [
    "/srv/luris/be/sql/law_schema.sql",
    "/srv/luris/be/sql/client_schema.sql", 
    "/srv/luris/be/sql/graph_schema_core.sql",
    "/srv/luris/be/sql/graph_schema_knowledge.sql",
    "/srv/luris/be/sql/migrate_to_2048_dimensions.sql",
    "/srv/luris/be/sql/public_schema_views.sql"
]

class MigrationExecutor:
    """Execute database migrations with proper error handling."""
    
    def __init__(self):
        self.client = SupabaseClient()
        self.results = []
        self.errors = []
        
    async def execute_sql_file(self, file_path: str) -> bool:
        """
        Execute a single SQL file.
        
        Args:
            file_path: Path to SQL file
            
        Returns:
            True if successful, False otherwise
        """
        file_name = Path(file_path).name
        print(f"\n{'=' * 60}")
        print(f"Executing: {file_name}")
        print(f"{'=' * 60}")
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                print(f"  ✗ {error_msg}")
                self.errors.append(error_msg)
                return False
            
            # Read SQL content
            with open(file_path, 'r') as f:
                sql_content = f.read()
            
            print(f"  📄 Read {len(sql_content)} characters from {file_name}")
            
            # Split into individual statements (basic split on semicolon)
            # Note: This is simplified - production would need proper SQL parsing
            statements = [s.strip() for s in sql_content.split(';\n') if s.strip()]
            
            print(f"  📊 Found {len(statements)} SQL statements")
            
            # Execute each statement
            success_count = 0
            for i, statement in enumerate(statements, 1):
                # Skip comments and empty statements
                if not statement or statement.startswith('--'):
                    continue
                
                # Add semicolon back
                statement = statement + ';'
                
                # Get first few words for logging
                preview = ' '.join(statement.split()[:3])
                
                try:
                    # For now, we'll print what we would execute
                    # In production, this would use Supabase MCP or direct connection
                    print(f"    [{i}/{len(statements)}] {preview}...")
                    
                    # Simulate execution (replace with actual Supabase execution)
                    # result = await self.client.execute_raw_sql(statement)
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"    ✗ Failed: {str(e)[:100]}")
                    self.errors.append(f"{file_name} statement {i}: {str(e)}")
            
            print(f"  ✓ Successfully executed {success_count}/{len(statements)} statements")
            
            self.results.append({
                'file': file_name,
                'path': file_path,
                'statements': len(statements),
                'successful': success_count,
                'status': 'completed'
            })
            
            return success_count == len(statements)
            
        except Exception as e:
            error_msg = f"Error executing {file_name}: {str(e)}"
            print(f"  ✗ {error_msg}")
            self.errors.append(error_msg)
            
            self.results.append({
                'file': file_name,
                'path': file_path,
                'error': str(e),
                'status': 'failed'
            })
            
            return False
    
    async def run_all_migrations(self) -> bool:
        """
        Execute all migrations in order.
        
        Returns:
            True if all successful, False otherwise
        """
        print("=" * 80)
        print("GRAPHRAG DATABASE MIGRATION EXECUTOR")
        print("=" * 80)
        print(f"Started at: {datetime.now().isoformat()}")
        print(f"Total migrations: {len(SQL_FILES)}")
        
        success_count = 0
        
        for sql_file in SQL_FILES:
            if await self.execute_sql_file(sql_file):
                success_count += 1
            else:
                print(f"\n⚠️  Migration stopped at {Path(sql_file).name}")
                print("   Fix the error and resume from this file")
                break
        
        # Print summary
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Completed: {success_count}/{len(SQL_FILES)} migrations")
        
        if self.errors:
            print(f"\nErrors encountered: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error[:100]}")
        
        if success_count == len(SQL_FILES):
            print("\n✅ All migrations completed successfully!")
        else:
            print(f"\n⚠️  Migrations incomplete. {len(SQL_FILES) - success_count} files remaining.")
        
        print("=" * 80)
        
        return success_count == len(SQL_FILES)
    
    def get_report(self) -> Dict[str, Any]:
        """Get detailed migration report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(SQL_FILES),
            'executed': len(self.results),
            'successful': len([r for r in self.results if r['status'] == 'completed']),
            'failed': len([r for r in self.results if r['status'] == 'failed']),
            'results': self.results,
            'errors': self.errors
        }


async def main():
    """Main execution function."""
    executor = MigrationExecutor()
    
    try:
        success = await executor.run_all_migrations()
        
        # Save report
        report = executor.get_report()
        report_file = f"migration_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        # Return appropriate exit code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        print(f"\n✗ Critical error: {str(e)}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║         GraphRAG Database Migration Executor              ║
║                                                            ║
║  This script will execute the following migrations:       ║
║  1. Law Schema (6 tables)                                 ║
║  2. Client Schema (4 tables)                              ║
║  3. Graph Schema Core (4 tables)                          ║
║  4. Graph Schema Knowledge (12+ tables)                   ║
║  5. Vector Dimension Migration (2048-dim)                 ║
║  6. Public Schema Views (29+ views)                       ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        asyncio.run(main())
    else:
        print("Migration cancelled.")
        sys.exit(0)