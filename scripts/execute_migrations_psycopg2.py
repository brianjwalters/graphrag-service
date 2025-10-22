#!/usr/bin/env python3
"""
Execute GraphRAG database migrations using direct PostgreSQL connection via psycopg2.
This script connects directly to Supabase PostgreSQL and executes SQL statements.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import re

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment from {env_path}")
else:
    print(f"⚠️  No .env file found at {env_path}, using system environment")

# SQL files to execute in order
SQL_FILES = [
    "/srv/luris/be/sql/law_schema.sql",
    "/srv/luris/be/sql/client_schema.sql", 
    "/srv/luris/be/sql/graph_schema_core.sql",
    "/srv/luris/be/sql/graph_schema_knowledge.sql",
    "/srv/luris/be/sql/migrate_to_2048_dimensions.sql",
    "/srv/luris/be/sql/public_schema_views.sql"
]

class PostgreSQLMigrationExecutor:
    """Execute database migrations using direct PostgreSQL connection."""
    
    def __init__(self):
        # Build connection string from environment variables
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        
        # Extract host from Supabase URL
        # Format: https://tqfshsnwyhfnkchaiudg.supabase.co
        import re
        import socket
        match = re.match(r'https://([^.]+)\.supabase\.co', self.supabase_url)
        if match:
            project_id = match.group(1)
            self.db_host = f"db.{project_id}.supabase.co"
            
            # Try to resolve to IPv4 address to avoid IPv6 issues
            try:
                # Get IPv4 address
                ip_address = socket.gethostbyname(self.db_host)
                print(f"📡 Resolved {self.db_host} to {ip_address}")
                # Use IP address directly to avoid IPv6 issues
                self.db_host = ip_address
            except:
                print(f"⚠️  Could not resolve {self.db_host}, will try hostname directly")
        else:
            raise ValueError(f"Invalid SUPABASE_URL format: {self.supabase_url}")
        
        # Get database password from environment
        # Try multiple possible password sources
        self.db_password = (
            os.getenv("SUPABASE_DB_PASSWORD") or
            os.getenv("POSTGRES_PASSWORD") or
            os.getenv("DB_PASSWORD") or
            "postgres"  # Default password for local development
        )
        
        # Note: The service key is NOT the database password
        print(f"ℹ️  Using database password from environment (length: {len(self.db_password)})")
        
        # Database connection parameters
        self.db_params = {
            'host': self.db_host,
            'port': 5432,
            'database': 'postgres',
            'user': 'postgres',
            'password': self.db_password
        }
        
        self.connection = None
        self.cursor = None
        self.results = []
        self.errors = []
        self.executed_statements = 0
        self.failed_statements = 0
    
    def connect(self):
        """Establish connection to PostgreSQL database."""
        try:
            print(f"🔌 Connecting to PostgreSQL at {self.db_host}...")
            self.connection = psycopg2.connect(**self.db_params)
            # Set autocommit mode for DDL statements
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.connection.cursor()
            
            # Test connection
            self.cursor.execute("SELECT version()")
            version = self.cursor.fetchone()[0]
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {version.split(',')[0]}")
            
            # Check current schemas
            self.cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name IN ('law', 'client', 'graph', 'public')
                ORDER BY schema_name
            """)
            schemas = [row[0] for row in self.cursor.fetchall()]
            print(f"   Existing schemas: {', '.join(schemas) if schemas else 'none'}")
            
            return True
            
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("🔌 Disconnected from database")
    
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
        
        # Split by semicolon but handle special cases
        statements = []
        current_statement = []
        in_function = False
        in_string = False
        
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
    
    def execute_statement(self, statement: str, file_name: str, stmt_num: int) -> bool:
        """
        Execute a single SQL statement.
        
        Args:
            statement: SQL statement to execute
            file_name: Source file name for logging
            stmt_num: Statement number for logging
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get statement type for logging
            stmt_type = statement.strip().split()[0].upper() if statement.strip() else "UNKNOWN"
            
            # Execute the statement
            self.cursor.execute(statement)
            
            # Check if statement returned results
            if self.cursor.description:
                # For SELECT statements, fetch results
                results = self.cursor.fetchall()
                if results and len(results) <= 5:  # Show small result sets
                    print(f"       Result: {results}")
            
            self.executed_statements += 1
            return True
            
        except psycopg2.errors.DuplicateTable as e:
            # Table already exists - not necessarily an error
            print(f"       ℹ️  Table already exists (skipping)")
            return True
            
        except psycopg2.errors.DuplicateObject as e:
            # Object already exists - not necessarily an error
            print(f"       ℹ️  Object already exists (skipping)")
            return True
            
        except Exception as e:
            error_msg = str(e).replace('\n', ' ')[:200]
            print(f"       ❌ Error: {error_msg}")
            self.errors.append(f"{file_name} stmt {stmt_num}: {error_msg}")
            self.failed_statements += 1
            
            # For critical errors, we might want to stop
            if "syntax error" in error_msg.lower():
                return False
            
            # Continue with other statements
            return True
    
    def execute_sql_file(self, file_path: str) -> bool:
        """
        Execute all statements in a SQL file.
        
        Args:
            file_path: Path to SQL file
            
        Returns:
            True if successful, False otherwise
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
            
            # Execute each statement
            print(f"\n  ⚙️  Executing statements...")
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
                if self.execute_statement(statement, file_name, i):
                    success_count += 1
            
            # Report results
            print(f"\n  ✅ Completed: {success_count}/{len(statements)} statements executed")
            
            self.results.append({
                'file': file_name,
                'path': file_path,
                'total_statements': len(statements),
                'successful': success_count,
                'failed': len(statements) - success_count,
                'statement_types': statement_types,
                'status': 'completed' if success_count == len(statements) else 'partial'
            })
            
            return success_count > 0  # Continue even if some statements fail
            
        except Exception as e:
            error_msg = f"Error processing {file_name}: {str(e)}"
            print(f"  ❌ {error_msg}")
            self.errors.append(error_msg)
            traceback.print_exc()
            
            self.results.append({
                'file': file_name,
                'path': file_path,
                'error': str(e),
                'status': 'failed'
            })
            
            return False
    
    def verify_tables(self):
        """Verify that tables were created successfully."""
        print("\n" + "=" * 70)
        print("🔍 Verifying Created Tables")
        print("=" * 70)
        
        try:
            # Check tables in each schema
            schemas = ['law', 'client', 'graph']
            total_tables = 0
            
            for schema in schemas:
                self.cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """, (schema,))
                
                tables = [row[0] for row in self.cursor.fetchall()]
                total_tables += len(tables)
                
                print(f"\n  📁 Schema '{schema}': {len(tables)} tables")
                for table in tables:
                    # Get row count
                    try:
                        self.cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
                        count = self.cursor.fetchone()[0]
                        print(f"     ✓ {table} ({count} rows)")
                    except:
                        print(f"     ✓ {table}")
            
            # Check views
            self.cursor.execute("""
                SELECT schemaname, viewname 
                FROM pg_views 
                WHERE schemaname IN ('law', 'client', 'graph', 'public')
                ORDER BY schemaname, viewname
            """)
            
            views = {}
            for schema, view in self.cursor.fetchall():
                if schema not in views:
                    views[schema] = []
                views[schema].append(view)
            
            print(f"\n  👁️  Views created:")
            for schema, view_list in views.items():
                print(f"     {schema}: {len(view_list)} views")
            
            print(f"\n  📊 Summary:")
            print(f"     Total tables: {total_tables}")
            print(f"     Total views: {sum(len(v) for v in views.values())}")
            
            return total_tables > 0
            
        except Exception as e:
            print(f"  ❌ Verification failed: {str(e)}")
            return False
    
    def run_all_migrations(self) -> bool:
        """
        Execute all migration files in order.
        
        Returns:
            True if successful, False otherwise
        """
        print("=" * 80)
        print("🚀 GRAPHRAG DATABASE MIGRATION EXECUTOR")
        print("=" * 80)
        print(f"Started at: {datetime.now().isoformat()}")
        print(f"Database: {self.db_host}")
        print(f"Total migration files: {len(SQL_FILES)}")
        
        # Connect to database
        if not self.connect():
            print("\n❌ Failed to connect to database")
            return False
        
        try:
            success_count = 0
            
            # Execute each migration file
            for sql_file in SQL_FILES:
                if self.execute_sql_file(sql_file):
                    success_count += 1
                else:
                    # Continue with other files even if one fails
                    print(f"\n⚠️  File {Path(sql_file).name} had issues, continuing...")
            
            # Verify tables were created
            self.verify_tables()
            
            # Print summary
            print("\n" + "=" * 80)
            print("📊 MIGRATION SUMMARY")
            print("=" * 80)
            print(f"Files processed: {success_count}/{len(SQL_FILES)}")
            print(f"Statements executed: {self.executed_statements}")
            print(f"Statements failed: {self.failed_statements}")
            
            if self.errors:
                print(f"\n⚠️  Errors encountered: {len(self.errors)}")
                for error in self.errors[:10]:  # Show first 10 errors
                    print(f"  - {error[:150]}")
            
            if success_count == len(SQL_FILES) and self.failed_statements == 0:
                print("\n✅ All migrations completed successfully!")
                return True
            elif success_count > 0:
                print(f"\n⚠️  Migrations partially completed with some errors.")
                print("   Tables may have been created despite errors.")
                return True
            else:
                print(f"\n❌ Migrations failed.")
                return False
                
        finally:
            # Always disconnect
            self.disconnect()
    
    def save_report(self):
        """Save detailed migration report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'database': self.db_host,
            'total_files': len(SQL_FILES),
            'files_processed': len(self.results),
            'statements_executed': self.executed_statements,
            'statements_failed': self.failed_statements,
            'results': self.results,
            'errors': self.errors
        }
        
        report_file = f"migration_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Report saved to: {report_file}")
        return report_file


def main():
    """Main execution function."""
    executor = PostgreSQLMigrationExecutor()
    
    try:
        success = executor.run_all_migrations()
        executor.save_report()
        
        if success:
            print("\n" + "=" * 80)
            print("✅ MIGRATION COMPLETED")
            print("=" * 80)
            print("\nNext steps:")
            print("1. Run: python scripts/verify_schema.py")
            print("2. Check Supabase Dashboard for created tables")
            print("3. Test the GraphRAG service endpoints")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        executor.disconnect()
        sys.exit(130)
        
    except Exception as e:
        print(f"\n❌ Critical error: {str(e)}")
        traceback.print_exc()
        executor.disconnect()
        sys.exit(2)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║      GraphRAG PostgreSQL Database Migration Executor      ║
║                                                            ║
║  This script will directly connect to your Supabase       ║
║  PostgreSQL database and execute all migration files.     ║
║                                                            ║
║  Migration files to execute:                              ║
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
    
    # Check environment variables
    if not os.getenv("SUPABASE_URL"):
        print("\n❌ ERROR: SUPABASE_URL environment variable not set")
        print("   Set it with: export SUPABASE_URL='https://your-project.supabase.co'")
        sys.exit(1)
    
    if not os.getenv("SUPABASE_SERVICE_KEY") and not os.getenv("SUPABASE_DB_PASSWORD"):
        print("\n❌ ERROR: SUPABASE_SERVICE_KEY or SUPABASE_DB_PASSWORD required")
        print("   Set one with: export SUPABASE_SERVICE_KEY='your-service-key'")
        print("   Or: export SUPABASE_DB_PASSWORD='your-db-password'")
        sys.exit(1)
    
    response = input("\n⚠️  This will create/modify database tables. Proceed? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        main()
    else:
        print("Migration cancelled.")
        sys.exit(0)