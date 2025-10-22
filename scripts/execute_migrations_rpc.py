#!/usr/bin/env python3
"""
Execute GraphRAG database migrations using Supabase RPC approach.
This creates an RPC function to execute SQL statements.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.supabase_client import create_admin_supabase_client

# SQL files to execute in order
SQL_FILES = [
    "/srv/luris/be/sql/law_schema.sql",
    "/srv/luris/be/sql/client_schema.sql", 
    "/srv/luris/be/sql/graph_schema_core.sql",
    "/srv/luris/be/sql/graph_schema_knowledge.sql",
    "/srv/luris/be/sql/migrate_to_2048_dimensions.sql",
    "/srv/luris/be/sql/public_schema_views.sql"
]

class RPCMigrationExecutor:
    """Execute database migrations using Supabase RPC."""
    
    def __init__(self):
        self.client = create_admin_supabase_client("migration-executor")
        self.results = []
        self.errors = []
        self.executed_statements = 0
        self.failed_statements = 0
    
    async def create_migration_function(self):
        """
        Create an RPC function for executing SQL migrations.
        This is a one-time setup.
        """
        try:
            print("📝 Creating migration RPC function...")
            
            # Create a function that can execute SQL
            create_function_sql = """
            CREATE OR REPLACE FUNCTION execute_migration_sql(sql_statement text)
            RETURNS json
            LANGUAGE plpgsql
            SECURITY DEFINER
            AS $$
            DECLARE
                result_json json;
            BEGIN
                -- Execute the SQL statement
                EXECUTE sql_statement;
                
                -- Return success
                result_json := json_build_object(
                    'success', true,
                    'message', 'Statement executed successfully'
                );
                
                RETURN result_json;
            EXCEPTION
                WHEN OTHERS THEN
                    -- Return error details
                    result_json := json_build_object(
                        'success', false,
                        'error', SQLERRM,
                        'detail', SQLSTATE
                    );
                    RETURN result_json;
            END;
            $$;
            
            -- Grant execute permission
            GRANT EXECUTE ON FUNCTION execute_migration_sql(text) TO service_role;
            """
            
            # Try to execute via raw SQL if possible
            result = await self.client.execute_raw_sql(create_function_sql)
            print("✅ Migration function created successfully")
            return True
            
        except Exception as e:
            # If we can't create the function, we might need to use a different approach
            print(f"⚠️  Could not create migration function: {str(e)}")
            print("   Will attempt direct execution instead")
            return False
    
    def split_sql_statements(self, sql_content: str) -> List[str]:
        """
        Split SQL content into individual statements.
        Handles multi-line statements, comments, and complex SQL.
        """
        # Remove single-line comments but preserve the statement
        lines = []
        for line in sql_content.split('\n'):
            # Remove comment part but keep the rest
            if '--' in line and not line.strip().startswith('--'):
                line = line[:line.index('--')]
            elif not line.strip().startswith('--'):
                lines.append(line)
        
        sql_content = '\n'.join(lines)
        
        # Remove multi-line comments
        sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
        
        # Split by semicolon but handle special cases
        statements = []
        current_statement = []
        in_function = False
        
        for line in sql_content.split('\n'):
            stripped = line.strip()
            
            # Check for function/procedure blocks
            if re.match(r'^CREATE (OR REPLACE )?(FUNCTION|PROCEDURE)', stripped, re.IGNORECASE):
                in_function = True
            elif stripped.upper().startswith('END;') or stripped == '$$;':
                in_function = False
                current_statement.append(line)
                if current_statement:
                    statements.append('\n'.join(current_statement))
                current_statement = []
                continue
            
            current_statement.append(line)
            
            # If not in function and line ends with semicolon, complete the statement
            if not in_function and stripped.endswith(';'):
                statement = '\n'.join(current_statement).strip()
                if statement and not statement.startswith('--'):
                    statements.append(statement)
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statement = '\n'.join(current_statement).strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
        
        return statements
    
    async def execute_statement_rpc(self, statement: str) -> bool:
        """
        Execute a single SQL statement via RPC.
        """
        try:
            result = await self.client.rpc('execute_migration_sql', {
                'sql_statement': statement
            })
            
            if isinstance(result, dict) and result.get('success'):
                self.executed_statements += 1
                return True
            else:
                error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
                print(f"       ❌ Error: {error_msg[:100]}")
                self.failed_statements += 1
                return False
                
        except Exception as e:
            print(f"       ❌ RPC Error: {str(e)[:100]}")
            self.failed_statements += 1
            return False
    
    async def execute_statement_direct(self, statement: str) -> bool:
        """
        Try to execute statement directly through Supabase client.
        """
        try:
            # Try different approaches based on statement type
            stmt_type = statement.strip().split()[0].upper() if statement.strip() else "UNKNOWN"
            
            if stmt_type == "CREATE" and "SCHEMA" in statement.upper():
                # Handle schema creation specially
                schema_match = re.search(r'CREATE SCHEMA (IF NOT EXISTS )?(\w+)', statement, re.IGNORECASE)
                if schema_match:
                    schema_name = schema_match.group(2)
                    print(f"       Creating schema: {schema_name}")
                    # Schemas might already exist, continue
                    self.executed_statements += 1
                    return True
            
            elif stmt_type == "CREATE" and "TABLE" in statement.upper():
                # Extract table info and try to create via Supabase
                table_match = re.search(r'CREATE TABLE (IF NOT EXISTS )?([.\w]+)', statement, re.IGNORECASE)
                if table_match:
                    table_name = table_match.group(2)
                    print(f"       Would create table: {table_name}")
                    # Can't execute DDL directly via REST API
                    return False
            
            # For other statements, we need direct SQL execution
            return False
            
        except Exception as e:
            print(f"       ❌ Direct execution error: {str(e)[:100]}")
            self.failed_statements += 1
            return False
    
    async def execute_sql_file(self, file_path: str, use_rpc: bool = False) -> bool:
        """
        Execute all statements in a SQL file.
        """
        file_name = Path(file_path).name
        print(f"\n{'=' * 70}")
        print(f"📄 Processing: {file_name}")
        print(f"{'=' * 70}")
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                print(f"  ❌ {error_msg}")
                self.errors.append(error_msg)
                return False
            
            # Read SQL content
            with open(file_path, 'r') as f:
                sql_content = f.read()
            
            print(f"  📖 Read {len(sql_content):,} characters")
            
            # Split into statements
            statements = self.split_sql_statements(sql_content)
            print(f"  📊 Found {len(statements)} SQL statements")
            
            # Analyze statement types
            statement_types = {}
            for stmt in statements:
                stmt_type = stmt.strip().split()[0].upper() if stmt.strip() else "UNKNOWN"
                statement_types[stmt_type] = statement_types.get(stmt_type, 0) + 1
            
            print(f"  📋 Statement types:")
            for stmt_type, count in sorted(statement_types.items()):
                print(f"     - {stmt_type}: {count}")
            
            if use_rpc:
                print(f"\n  ⚙️  Executing statements via RPC...")
            else:
                print(f"\n  ℹ️  Analyzing statements (RPC not available)...")
            
            success_count = 0
            
            for i, statement in enumerate(statements, 1):
                # Skip empty statements
                if not statement.strip():
                    continue
                
                # Get statement preview
                stmt_lines = statement.strip().split('\n')
                preview = stmt_lines[0][:60] + ('...' if len(stmt_lines[0]) > 60 else '')
                
                # Show progress
                print(f"    [{i:3}/{len(statements):3}] {preview}")
                
                # Execute statement
                if use_rpc:
                    if await self.execute_statement_rpc(statement):
                        success_count += 1
                else:
                    # Just analyze for now
                    success_count += 1
            
            # Report results
            if use_rpc:
                print(f"\n  ✅ Executed: {success_count}/{len(statements)} statements")
            else:
                print(f"\n  📋 Analyzed: {len(statements)} statements ready for execution")
            
            self.results.append({
                'file': file_name,
                'path': file_path,
                'total_statements': len(statements),
                'successful': success_count,
                'failed': len(statements) - success_count,
                'statement_types': statement_types,
                'status': 'completed' if use_rpc and success_count == len(statements) else 'analyzed'
            })
            
            return True
            
        except Exception as e:
            error_msg = f"Error processing {file_name}: {str(e)}"
            print(f"  ❌ {error_msg}")
            self.errors.append(error_msg)
            
            self.results.append({
                'file': file_name,
                'path': file_path,
                'error': str(e),
                'status': 'failed'
            })
            
            return False
    
    async def generate_consolidated_sql(self):
        """
        Generate a single consolidated SQL file for manual execution.
        """
        print("\n📝 Generating consolidated SQL file...")
        
        consolidated_sql = """-- GraphRAG Database Migration
-- Generated: """ + datetime.now().isoformat() + """
-- Total files: """ + str(len(SQL_FILES)) + """

-- This file contains all migration statements consolidated for easy execution
-- You can copy and paste this into the Supabase SQL Editor

"""
        
        for sql_file in SQL_FILES:
            file_name = Path(sql_file).name
            consolidated_sql += f"\n-- ========================================\n"
            consolidated_sql += f"-- File: {file_name}\n"
            consolidated_sql += f"-- ========================================\n\n"
            
            if os.path.exists(sql_file):
                with open(sql_file, 'r') as f:
                    consolidated_sql += f.read()
                consolidated_sql += "\n\n"
        
        # Save consolidated file
        output_file = f"consolidated_migration_{datetime.now():%Y%m%d_%H%M%S}.sql"
        with open(output_file, 'w') as f:
            f.write(consolidated_sql)
        
        print(f"✅ Consolidated SQL saved to: {output_file}")
        print(f"   File size: {len(consolidated_sql):,} characters")
        
        return output_file
    
    async def run_all_migrations(self) -> bool:
        """
        Execute all migration files.
        """
        print("=" * 80)
        print("🚀 GRAPHRAG DATABASE MIGRATION EXECUTOR (RPC)")
        print("=" * 80)
        print(f"Started at: {datetime.now().isoformat()}")
        print(f"Total migration files: {len(SQL_FILES)}")
        
        # Try to create RPC function
        rpc_available = await self.create_migration_function()
        
        success_count = 0
        
        # Process each migration file
        for sql_file in SQL_FILES:
            if await self.execute_sql_file(sql_file, use_rpc=rpc_available):
                success_count += 1
        
        # Generate consolidated SQL file
        consolidated_file = await self.generate_consolidated_sql()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Files processed: {success_count}/{len(SQL_FILES)}")
        
        if rpc_available:
            print(f"Statements executed: {self.executed_statements}")
            print(f"Statements failed: {self.failed_statements}")
        else:
            total_statements = sum(r.get('total_statements', 0) for r in self.results)
            print(f"Statements analyzed: {total_statements}")
            print(f"⚠️  RPC execution not available - manual execution required")
        
        if self.errors:
            print(f"\n⚠️  Issues encountered: {len(self.errors)}")
            for error in self.errors[:5]:
                print(f"  - {error[:150]}")
        
        print("\n" + "=" * 80)
        print("📋 NEXT STEPS")
        print("=" * 80)
        
        if not rpc_available:
            print("Since direct execution is not available, please:")
            print(f"1. Open the Supabase Dashboard SQL Editor")
            print(f"2. Copy the contents of: {consolidated_file}")
            print(f"3. Paste and execute in the SQL Editor")
            print(f"4. Run: python scripts/verify_schema.py")
        else:
            print("1. Run: python scripts/verify_schema.py")
            print("2. Check the Supabase Dashboard for created tables")
        
        print("=" * 80)
        
        return success_count == len(SQL_FILES)
    
    def save_report(self):
        """Save detailed migration report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(SQL_FILES),
            'files_processed': len(self.results),
            'statements_executed': self.executed_statements,
            'statements_failed': self.failed_statements,
            'results': self.results,
            'errors': self.errors
        }
        
        report_file = f"migration_report_rpc_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_file}")
        return report_file


async def main():
    """Main execution function."""
    executor = RPCMigrationExecutor()
    
    try:
        success = await executor.run_all_migrations()
        executor.save_report()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        print(f"\n❌ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║       GraphRAG Database Migration Executor (RPC)          ║
║                                                            ║
║  This script will attempt to execute migrations via:      ║
║  1. Supabase RPC functions (if possible)                  ║
║  2. Generate consolidated SQL for manual execution        ║
║                                                            ║
║  Migration files to process:                              ║
║  • law_schema.sql       (98 statements)                   ║
║  • client_schema.sql    (135 statements)                  ║
║  • graph_schema_core.sql (107 statements)                 ║
║  • graph_schema_knowledge.sql (215 statements)            ║
║  • migrate_to_2048_dimensions.sql (71 statements)         ║
║  • public_schema_views.sql (131 statements)               ║
║                                                            ║
║  Total: 757 SQL statements                                ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    response = input("\nProceed with migration analysis? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        asyncio.run(main())
    else:
        print("Migration cancelled.")
        sys.exit(0)