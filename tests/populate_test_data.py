#!/usr/bin/env python3
"""
Populate Test Database with Sample Data
Copies a subset of production data to test database for testing purposes
"""

import os
import sys
from database import DatabaseManager
from sqlalchemy import text

def populate_test_database():
    """Populate test database with sample S&P 500 data"""
    
    # Set environment for test database
    os.environ['POSTGRES_HOST'] = 'test-postgres'
    os.environ['POSTGRES_DB'] = 'stockanalyst_test' 
    os.environ['POSTGRES_USER'] = 'stockanalyst'
    os.environ['POSTGRES_PASSWORD'] = 'testpassword'
    
    try:
        # Initialize test database connection
        test_db = DatabaseManager()
        
        print("🔄 Populating test database with sample data...")
        
        # Import test fixtures  
        from tests.fixtures.sample_companies import SAMPLE_SP500_COMPANIES, SAMPLE_COMPANY_PROFILES, SAMPLE_UNDERVALUATION_SCORES
        
        # Insert sample companies
        with test_db.engine.begin() as conn:
            # Clear existing data
            conn.execute(text("DELETE FROM sp500_constituents"))
            
            # Insert sample companies
            for company in SAMPLE_SP500_COMPANIES:
                conn.execute(text("""
                    INSERT INTO sp500_constituents (symbol, name, sector)
                    VALUES (:symbol, :name, :sector)
                    ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    sector = EXCLUDED.sector
                """), company)
            
            # Add sample company profiles
            for profile in SAMPLE_COMPANY_PROFILES:
                conn.execute(text("""
                    INSERT INTO company_profiles (symbol, companyname, price, mktcap, industry)
                    VALUES (:symbol, :companyname, :price, :mktcap, :industry)
                    ON CONFLICT (symbol) DO UPDATE SET
                    companyname = EXCLUDED.companyname,
                    price = EXCLUDED.price,
                    mktcap = EXCLUDED.mktcap,
                    industry = EXCLUDED.industry
                """), profile)
            
            conn.commit()
            
        print("✅ Test database populated successfully!")
        
        # Verify data was inserted
        with test_db.engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM sp500_constituents")).fetchone()
            companies_count = result[0]
            
            result = conn.execute(text("SELECT COUNT(*) FROM company_profiles")).fetchone() 
            profiles_count = result[0]
            
        print(f"📊 Inserted {companies_count} companies and {profiles_count} profiles")
        
        return True
        
    except Exception as e:
        print(f"❌ Error populating test database: {e}")
        return False

if __name__ == "__main__":
    success = populate_test_database()
    sys.exit(0 if success else 1)