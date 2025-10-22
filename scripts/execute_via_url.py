#!/usr/bin/env python3
"""
Execute SQL migrations using PostgreSQL connection via URL format.
"""
import os
import sys
import time
from pathlib import Path
from datetime import datetime
import subprocess

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Installing psycopg2-binary...")
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
    """Execute migrations using connection string."""
    
    def __init__(self):
        # Use connection string format
        self.connection_string = "postgresql://postgres.tqfshsnwyhfnkchaiudg:ZFFQ5xj9vJh3hKCN@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        self.connection = None
        self.cursor = None
        self.results = []
        self.errors = []
    
    def connect(self):
        """Establish database connection."""
        try:
            print(f"Connecting to Supabase PostgreSQL...")
            self.connection = psycopg2.connect(
                self.connection_string,
                connect_timeout=10
            )
            self.connection.set_session(autocommit=False)
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            print("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {str(e)}")
            print("💡 You may need to get the correct database password from Supabase Dashboard")
            print("   Go to Settings > Database > Connection String")
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
                AND (table_name LIKE '%law_%' 
                OR table_name LIKE '%client_%'
                OR table_name LIKE '%graph_%');
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
    main()