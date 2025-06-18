#!/usr/bin/env python3
"""
Check table structure
"""

from app.database.config import SessionLocal
from sqlalchemy import text

def check_table_structure():
    db = SessionLocal()
    try:
        # Check columns in lastmile_processing_results
        result = db.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'lastmile_processing_results'
            ORDER BY ordinal_position
        """))

        print("📋 Columns in lastmile_processing_results:")
        for row in result:
            print(f"  ✅ {row[0]}: {row[1]}")

        # Check if lastmile_request_details exists
        result2 = db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name = 'lastmile_request_details'
        """))

        tables = list(result2)
        if tables:
            print(f"\n⚠️ lastmile_request_details table still exists")
        else:
            print(f"\n✅ lastmile_request_details table has been removed")

        # Check alembic version
        result3 = db.execute(text("SELECT version_num FROM alembic_version"))
        version = result3.fetchone()
        print(f"\n🔄 Current migration version: {version[0] if version else 'None'}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_table_structure()