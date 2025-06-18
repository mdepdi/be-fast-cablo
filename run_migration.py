#!/usr/bin/env python3
"""
Run Database Migration Script
"""

import subprocess
import sys
import os

def run_migration():
    """Run the database migration"""
    print("🔄 Running database migration...")
    print("=" * 50)

    try:
        # Change to the correct directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Run alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            print("\nMigration output:")
            print(result.stdout)

            if result.stderr:
                print("\nWarnings:")
                print(result.stderr)

        else:
            print("❌ Migration failed!")
            print(f"Error: {result.stderr}")
            print(f"Output: {result.stdout}")
            return False

    except FileNotFoundError:
        print("❌ Alembic not found. Please install it:")
        print("pip install alembic")
        return False
    except Exception as e:
        print(f"❌ Error running migration: {str(e)}")
        return False

    return True

def check_migration_status():
    """Check current migration status"""
    print("\n🔍 Checking migration status...")

    try:
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("Current migration:")
            print(result.stdout)
        else:
            print("Could not check migration status")
            print(result.stderr)

    except Exception as e:
        print(f"Error checking migration status: {str(e)}")

def show_migration_history():
    """Show migration history"""
    print("\n📜 Migration history:")

    try:
        result = subprocess.run(
            ["alembic", "history"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Could not get migration history")
            print(result.stderr)

    except Exception as e:
        print(f"Error getting migration history: {str(e)}")

if __name__ == "__main__":
    print("🗃️ Database Migration Tool")
    print("=" * 50)

    # Check current status first
    check_migration_status()

    # Show migration history
    show_migration_history()

    # Ask user if they want to proceed
    print("\n" + "=" * 50)
    print("This migration will:")
    print("1. ✅ Add 'download_links' column to lastmile_processing_results")
    print("2. ❌ DROP 'lastmile_request_details' table (unused)")
    print("3. 🔄 Update database schema to version 002")

    response = input("\nDo you want to proceed? (y/N): ").lower().strip()

    if response in ['y', 'yes']:
        success = run_migration()

        if success:
            print("\n✨ Migration completed successfully!")
            print("\nChanges made:")
            print("- Added download_links JSONB column")
            print("- Removed unused lastmile_request_details table")
            print("- Database schema updated to version 002")

            # Check final status
            check_migration_status()
        else:
            print("\n❌ Migration failed. Please check the errors above.")
            sys.exit(1)
    else:
        print("Migration cancelled.")
        sys.exit(0)