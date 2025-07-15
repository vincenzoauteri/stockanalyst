#!/usr/bin/env python3
"""Debug script to test table creation in isolation"""

import os
import sys
sys.path.append('/app')

from sqlalchemy import create_engine, text

def test_table_creation():
    # Set test environment
    os.environ['TESTING'] = 'true'
    os.environ['POSTGRES_HOST'] = 'test-postgres'
    os.environ['POSTGRES_DB'] = 'stockanalyst_test'
    os.environ['POSTGRES_PASSWORD'] = 'testpassword'
    
    # Create engine
    db_url = 'postgresql://stockanalyst:testpassword@test-postgres:5432/stockanalyst_test'
    engine = create_engine(db_url)
    
    print("Testing basic connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            print(f"✓ Connected to PostgreSQL: {result.fetchone()[0]}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    print("\nTesting table creation...")
    try:
        with engine.connect() as conn:
            # Start explicit transaction
            trans = conn.begin()
            try:
                # Create one simple table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS test_table (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                """))
                trans.commit()
                print("✓ Created test_table successfully")
                
                # Check if table exists
                result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'test_table'"))
                count = result.fetchone()[0]
                print(f"✓ Table exists check: {count} table(s) found")
                
            except Exception as e:
                trans.rollback()
                print(f"✗ Table creation failed: {e}")
                
    except Exception as e:
        print(f"✗ Transaction failed: {e}")
        
    print("\nTesting sp500_constituents table...")
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS sp500_constituents (
                        id SERIAL PRIMARY KEY,
                        symbol TEXT UNIQUE NOT NULL,
                        name TEXT,
                        sector TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                trans.commit()
                print("✓ Created sp500_constituents successfully")
            except Exception as e:
                trans.rollback()
                print(f"✗ sp500_constituents creation failed: {e}")
    except Exception as e:
        print(f"✗ sp500_constituents transaction failed: {e}")
        
    print("\nFinal table count:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
            tables = result.fetchall()
            print(f"Tables in database: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
    except Exception as e:
        print(f"✗ Failed to list tables: {e}")

if __name__ == "__main__":
    test_table_creation()