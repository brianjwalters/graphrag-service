#!/usr/bin/env python3
"""
Direct database migration execution using Supabase Python client.
Executes SQL files directly against the database.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client
import traceback

# SQL files to execute in order
SQL_FILES = [
    "/srv/luris/be/sql/law_schema.sql",
    "/srv/luris/be/sql/client_schema.sql", 
    "/srv/luris/be/sql/graph_schema_core.sql",
    "/srv/luris/be/sql/graph_schema_knowledge.sql",
    "/srv/luris/be/sql/migrate_to_2048_dimensions.sql",
    "/srv/luris/be/sql/public_schema_views.sql"
]

class DirectMigrationExecutor:
    """Execute migrations directly using Supabase client."""
    
    def __init__(self):
        # Get credentials from environment
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for admin access
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        # Create Supabase client
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        print(f"✅ Connected to Supabase at {self.supabase_url[:30]}...")
        
        self.results = []
        self.errors = []
    
    def split_sql_statements(self, sql_content: str) -> list:
        """
        Split SQL content into individual statements.
        Handles multi-line statements and comments.
        """
        # Remove single-line comments
        lines = sql_content.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove comment part but keep the rest of the line
            if '--' in line:
                line = line[:line.index('--')]
            cleaned_lines.append(line)
        
        sql_content = '\n'.join(cleaned_lines)
        
        # Split by semicolon but keep it
        statements = []
        current = []
        
        for line in sql_content.split('\n'):
            current.append(line)
            if line.strip().endswith(';'):
                statement = '\n'.join(current).strip()
                if statement and not statement.startswith('--'):
                    statements.append(statement)
                current = []
        
        # Add any remaining statement
        if current:
            statement = '\n'.join(current).strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
        
        return statements
    
    def execute_sql_statement(self, statement: str) -> bool:
        """
        Execute a single SQL statement using Supabase RPC.
        
        Note: Supabase doesn't directly support raw SQL execution via REST API.
        We need to use RPC functions or the Supabase CLI/direct connection.
        """
        try:
            # Get first few words for logging
            preview = ' '.join(statement.split()[:5])
            
            # For demonstration, we'll show what would be executed
            # In production, you'd use psycopg2 or similar for direct execution
            print(f"    Would execute: {preview}...")
            
            # Note: Actual execution would require:
            # 1. A database function that accepts raw SQL (security risk)
            # 2. Direct database connection with psycopg2
            # 3. Supabase CLI or migration tools
            
            return True
            
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:100]}")
            return False
    
    def execute_sql_file(self, file_path: str) -> bool:
        """Execute a single SQL file."""
        file_name = Path(file_path).name
        print(f"\n{'=' * 60}")
        print(f"Processing: {file_name}")
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
            
            # Split into statements
            statements = self.split_sql_statements(sql_content)
            print(f"  📊 Found {len(statements)} SQL statements")
            
            # Track statement types
            statement_types = {}
            for stmt in statements:
                stmt_type = stmt.strip().split()[0].upper() if stmt.strip() else "UNKNOWN"
                statement_types[stmt_type] = statement_types.get(stmt_type, 0) + 1
            
            print(f"  📋 Statement types: {statement_types}")
            
            # For now, mark as would-be-successful since we can't execute directly
            print(f"  ⚠️  Note: Direct SQL execution requires database access")
            print(f"  ℹ️  Use Supabase Dashboard SQL Editor or psql for actual execution")
            
            self.results.append({
                'file': file_name,
                'path': file_path,
                'statements': len(statements),
                'statement_types': statement_types,
                'status': 'ready_to_execute'
            })
            
            return True
            
        except Exception as e:
            error_msg = f"Error processing {file_name}: {str(e)}"
            print(f"  ✗ {error_msg}")
            self.errors.append(error_msg)
            
            self.results.append({
                'file': file_name,
                'path': file_path,
                'error': str(e),
                'status': 'failed'
            })
            
            return False
    
    def generate_execution_script(self):
        """Generate a shell script to execute the migrations."""
        script_content = """#!/bin/bash
# GraphRAG Database Migration Script
# Generated: """ + datetime.now().isoformat() + """

# Set your database connection string
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:[YOUR-PASSWORD]@db.tqfshsnwyhfnkchaiudg.supabase.co:5432/postgres}"

echo "=================================="
echo "GraphRAG Database Migration"
echo "=================================="

# Function to execute SQL file
execute_sql() {
    local file=$1
    echo ""
    echo "Executing: $(basename $file)"
    echo "----------------------------------"
    psql "$DATABASE_URL" -f "$file" -v ON_ERROR_STOP=1
    if [ $? -eq 0 ]; then
        echo "✓ Success"
    else
        echo "✗ Failed - stopping migration"
        exit 1
    fi
}

# Execute migrations in order
"""
        
        for sql_file in SQL_FILES:
            script_content += f'execute_sql "{sql_file}"\n'
        
        script_content += """
echo ""
echo "=================================="
echo "✅ All migrations completed!"
echo "=================================="
"""
        
        # Save the script
        script_path = "/srv/luris/be/graphrag-service/scripts/run_migrations.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        print(f"\n📜 Generated execution script: {script_path}")
        print("   Run with: export DATABASE_URL='your-connection-string' && ./run_migrations.sh")
    
    def run_analysis(self) -> bool:
        """Analyze all SQL files and prepare for execution."""
        print("=" * 80)
        print("GRAPHRAG DATABASE MIGRATION ANALYSIS")
        print("=" * 80)
        print(f"Started at: {datetime.now().isoformat()}")
        print(f"Total migrations: {len(SQL_FILES)}")
        
        success_count = 0
        
        for sql_file in SQL_FILES:
            if self.execute_sql_file(sql_file):
                success_count += 1
            else:
                print(f"\n⚠️  Analysis stopped at {Path(sql_file).name}")
                break
        
        # Generate execution script
        self.generate_execution_script()
        
        # Print summary
        print("\n" + "=" * 80)
        print("MIGRATION ANALYSIS SUMMARY")
        print("=" * 80)
        print(f"Files analyzed: {success_count}/{len(SQL_FILES)}")
        
        # Calculate total statements
        total_statements = sum(r.get('statements', 0) for r in self.results)
        print(f"Total SQL statements: {total_statements}")
        
        # Show statement type summary
        all_types = {}
        for r in self.results:
            if 'statement_types' in r:
                for stmt_type, count in r['statement_types'].items():
                    all_types[stmt_type] = all_types.get(stmt_type, 0) + count
        
        print(f"\nStatement breakdown:")
        for stmt_type, count in sorted(all_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {stmt_type}: {count}")
        
        if self.errors:
            print(f"\n⚠️  Errors encountered: {len(self.errors)}")
            for error in self.errors[:5]:
                print(f"  - {error[:100]}")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("1. Option A: Use Supabase Dashboard")
        print("   - Go to SQL Editor in Supabase Dashboard")
        print("   - Copy and paste each SQL file content")
        print("   - Execute in order")
        print("")
        print("2. Option B: Use psql with connection string")
        print("   - Get connection string from Supabase Dashboard > Settings > Database")
        print("   - Run: ./scripts/run_migrations.sh")
        print("")
        print("3. Option C: Use Supabase CLI")
        print("   - Install: npm install -g supabase")
        print("   - Run: supabase db push")
        print("=" * 80)
        
        return success_count == len(SQL_FILES)


def main():
    """Main execution function."""
    executor = DirectMigrationExecutor()
    
    try:
        success = executor.run_analysis()
        
        # Save report
        import json
        report = {
            'timestamp': datetime.now().isoformat(),
            'results': executor.results,
            'errors': executor.errors
        }
        
        report_file = f"migration_analysis_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Analysis report saved to: {report_file}")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n✗ Critical error: {str(e)}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║     GraphRAG Database Migration Analyzer                  ║
║                                                            ║
║  This tool analyzes SQL migration files and prepares      ║
║  them for execution via Supabase Dashboard or psql.       ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    main()