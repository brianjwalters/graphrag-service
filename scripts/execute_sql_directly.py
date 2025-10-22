#!/usr/bin/env python3
"""
Execute SQL directly using psycopg2 for PostgreSQL connection.
This bypasses the Supabase REST API limitations.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2.extras import RealDictCursor

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
    """Execute migrations directly via PostgreSQL connection."""
    
    def __init__(self):
        # Build connection string from Supabase URL
        self.supabase_url = "https://tqfshsnwyhfnkchaiudg.supabase.co"
        # Extract project ref from URL
        self.project_ref = "tqfshsnwyhfnkchaiudg"
        
        # PostgreSQL connection parameters
        self.db_host = f"db.{self.project_ref}.supabase.co"
        self.db_port = 5432
        self.db_name = "postgres"
        self.db_user = "postgres"
        
        # You need to get the database password from Supabase Dashboard
        # Go to Settings > Database > Connection String
        self.db_password = os.getenv("SUPABASE_DB_PASSWORD", "")
        
        if not self.db_password:
            print("=" * 60)
            print("⚠️  DATABASE PASSWORD REQUIRED")
            print("=" * 60)
            print("To execute migrations directly, you need the database password.")
            print("")
            print("Steps to get it:")
            print("1. Go to Supabase Dashboard: https://supabase.com/dashboard")
            print("2. Select your project")
            print("3. Go to Settings > Database")
            print("4. Copy the password from Connection String")
            print("5. Run this script with:")
            print("   SUPABASE_DB_PASSWORD='your-password' python3 execute_sql_directly.py")
            print("=" * 60)
            sys.exit(1)
        
        self.connection = None
        self.cursor = None
        self.results = []
        self.errors = []
    
    def connect(self):
        """Establish database connection."""
        try:
            print(f"Connecting to {self.db_host}...")
            self.connection = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                connect_timeout=10
            )
            self.connection.set_session(autocommit=False)
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            print("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {str(e)}")
            return False
    
    def execute_sql_file(self, file_path: str) -> bool:
        """Execute a single SQL file."""
        file_name = Path(file_path).name
        print(f"\n{'=' * 60}")
        print(f"Executing: {file_name}")
        print(f"{'=' * 60}")
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"  ✗ File not found: {file_path}")
                self.errors.append(f"File not found: {file_path}")
                return False
            
            # Read SQL content
            with open(file_path, 'r') as f:
                sql_content = f.read()
            
            print(f"  📄 Read {len(sql_content)} characters")
            
            # Execute the entire file as one transaction
            try:
                print(f"  ⏳ Executing SQL...")
                start_time = time.time()
                
                self.cursor.execute(sql_content)
                self.connection.commit()
                
                execution_time = time.time() - start_time
                print(f"  ✅ Executed successfully in {execution_time:.2f} seconds")
                
                self.results.append({
                    'file': file_name,
                    'status': 'success',
                    'execution_time': execution_time
                })
                
                return True
                
            except Exception as e:
                # Rollback on error
                self.connection.rollback()
                error_msg = str(e)[:500]
                print(f"  ✗ Execution failed: {error_msg}")
                self.errors.append(f"{file_name}: {error_msg}")
                
                self.results.append({
                    'file': file_name,
                    'status': 'failed',
                    'error': error_msg
                })
                
                return False
                
        except Exception as e:
            error_msg = f"Error processing {file_name}: {str(e)}"
            print(f"  ✗ {error_msg}")
            self.errors.append(error_msg)
            return False
    
    def verify_tables(self):
        """Verify that tables were created."""
        print("\n" + "=" * 60)
        print("VERIFYING CREATED TABLES")
        print("=" * 60)
        
        try:
            # Query to get all tables in our schemas
            query = """
                SELECT 
                    schemaname,
                    tablename,
                    (SELECT COUNT(*) FROM information_schema.columns 
                     WHERE table_schema = schemaname AND table_name = tablename) as column_count
                FROM pg_tables 
                WHERE schemaname IN ('law', 'client', 'graph')
                ORDER BY schemaname, tablename;
            """
            
            self.cursor.execute(query)
            tables = self.cursor.fetchall()
            
            schema_counts = {}
            for table in tables:
                schema = table['schemaname']
                if schema not in schema_counts:
                    schema_counts[schema] = []
                schema_counts[schema].append(table['tablename'])
            
            for schema, table_list in sorted(schema_counts.items()):
                print(f"\n{schema.upper()} Schema: {len(table_list)} tables")
                for table_name in table_list[:5]:  # Show first 5
                    print(f"  ✓ {schema}.{table_name}")
                if len(table_list) > 5:
                    print(f"  ... and {len(table_list) - 5} more")
            
            # Check public views
            query = """
                SELECT COUNT(*) as view_count
                FROM information_schema.views
                WHERE table_schema = 'public'
                AND table_name LIKE '%law_%' 
                OR table_name LIKE '%client_%'
                OR table_name LIKE '%graph_%';
            """
            
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            view_count = result['view_count'] if result else 0
            
            print(f"\nPublic Views: {view_count} created")
            
            return True
            
        except Exception as e:
            print(f"✗ Verification failed: {str(e)}")
            return False
    
    def run_migrations(self):
        """Execute all migrations."""
        print("=" * 80)
        print("POSTGRESQL DIRECT MIGRATION EXECUTOR")
        print("=" * 80)
        print(f"Started at: {datetime.now().isoformat()}")
        
        if not self.connect():
            return False
        
        success_count = 0
        
        for sql_file in SQL_FILES:
            if self.execute_sql_file(sql_file):
                success_count += 1
            else:
                print(f"\n⚠️  Migration stopped at {Path(sql_file).name}")
                print("   Fix the error and resume from this file")
                break
        
        # Verify tables if any migrations succeeded
        if success_count > 0:
            self.verify_tables()
        
        # Close connection
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        
        # Print summary
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Completed: {success_count}/{len(SQL_FILES)} migrations")
        
        if self.errors:
            print(f"\n⚠️  Errors encountered: {len(self.errors)}")
            for error in self.errors[:3]:
                print(f"  - {error[:100]}")
        
        if success_count == len(SQL_FILES):
            print("\n✅ All migrations completed successfully!")
        else:
            print(f"\n⚠️  Migrations incomplete. {len(SQL_FILES) - success_count} files remaining.")
        
        print("=" * 80)
        
        return success_count == len(SQL_FILES)


def main():
    """Main execution function."""
    executor = PostgreSQLMigrationExecutor()
    
    try:
        success = executor.run_migrations()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        print(f"\n✗ Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║        PostgreSQL Direct Migration Executor               ║
║                                                            ║
║  This script connects directly to PostgreSQL to execute   ║
║  the GraphRAG database migrations.                        ║
║                                                            ║
║  Requirements:                                             ║
║  - Database password from Supabase Dashboard              ║
║  - Network access to Supabase PostgreSQL server          ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    main()