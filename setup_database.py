#!/usr/bin/env python3
"""
Database Setup Script for LastMile Processing
Usage: python setup_database.py [--init|--migrate|--reset]
"""

import sys
import os
import argparse
from sqlalchemy import text

# Add the app directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.config import engine, Base, create_tables, drop_tables
from app.database.models import LastMileProcessingResult


def init_database():
    """Initialize database with tables"""
    print("🔄 Initializing database...")
    try:
        # Create all tables
        create_tables()
        print("✅ Database tables created successfully!")

        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name LIKE 'lastmile%'
            """))
            tables = [row[0] for row in result.fetchall()]

        print(f"📋 Created tables: {', '.join(tables)}")
        return True

    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        return False


def run_migrations():
    """Run Alembic migrations"""
    print("🔄 Running database migrations...")
    try:
        import subprocess

        # Run alembic upgrade
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )

        if result.returncode == 0:
            print("✅ Migrations completed successfully!")
            print(result.stdout)
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error running migrations: {str(e)}")
        return False


def reset_database():
    """Reset database (drop and recreate all tables)"""
    print("⚠️  RESETTING DATABASE - This will delete all data!")

    confirm = input("Are you sure you want to continue? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Database reset cancelled.")
        return False

    try:
        # Drop all tables
        print("🔄 Dropping existing tables...")
        drop_tables()
        print("✅ Tables dropped successfully!")

        # Recreate tables
        print("🔄 Creating new tables...")
        create_tables()
        print("✅ Tables created successfully!")

        return True

    except Exception as e:
        print(f"❌ Error resetting database: {str(e)}")
        return False


def check_database_connection():
    """Check if database connection is working"""
    print("🔄 Checking database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version[:50]}...")
            return True

    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print("\n🔧 Check your database connection settings:")
        print("   - Is PostgreSQL running?")
        print("   - Is the database 'db-cablo' created?")
        print("   - Are the credentials correct?")
        print("   - Is the database accessible on localhost:5433?")
        return False


def show_table_info():
    """Show information about created tables"""
    print("\n📊 Table Information:")
    try:
        with engine.connect() as conn:
            # Get table info
            result = conn.execute(text("""
                SELECT
                    schemaname,
                    tablename,
                    tableowner,
                    hasindexes,
                    hasrules,
                    hastriggers
                FROM pg_tables
                WHERE schemaname = 'public' AND tablename LIKE 'lastmile%'
                ORDER BY tablename
            """))

            tables = result.fetchall()
            for table in tables:
                print(f"  📋 {table[1]} (owner: {table[2]}, indexes: {table[3]}, triggers: {table[5]})")

            # Get column count for each table
            for table in tables:
                result = conn.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_name = '{table[1]}' AND table_schema = 'public'
                """))
                col_count = result.fetchone()[0]
                print(f"     └─ {col_count} columns")

    except Exception as e:
        print(f"❌ Error getting table info: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description='Database Setup for LastMile Processing')
    parser.add_argument('--init', action='store_true', help='Initialize database with tables')
    parser.add_argument('--migrate', action='store_true', help='Run Alembic migrations')
    parser.add_argument('--reset', action='store_true', help='Reset database (drop and recreate)')
    parser.add_argument('--check', action='store_true', help='Check database connection')
    parser.add_argument('--info', action='store_true', help='Show table information')

    args = parser.parse_args()

    print("🚀 LastMile Processing Database Setup")
    print("=" * 50)

    # Always check connection first
    if not check_database_connection():
        sys.exit(1)

    success = True

    if args.reset:
        success = reset_database()
    elif args.migrate:
        success = run_migrations()
    elif args.init:
        success = init_database()
    elif args.check:
        print("✅ Database connection check passed!")
    elif args.info:
        show_table_info()
    else:
        # Default: initialize database
        print("\nNo specific action specified. Running database initialization...")
        success = init_database()

    if success and not args.check and not args.info:
        show_table_info()

        print("\n🎉 Database setup completed!")
        print("\n📝 Next steps:")
        print("   1. Install dependencies: pip install -r requirements-database.txt")
        print("   2. Set DATABASE_URL environment variable if needed")
        print("   3. Start using the database in your LastMile processing!")

        print(f"\n🔗 Database URL: postgresql://postgres:adminbvt@localhost:5433/db-cablo")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()