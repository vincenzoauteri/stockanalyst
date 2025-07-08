#!/usr/bin/env python3
"""
Script to check for and report fake/test data in the production database
"""

from database import DatabaseManager
from sqlalchemy import text
import sys

def check_for_fake_data():
    """Check database for known fake test data patterns"""
    db = DatabaseManager()
    
    # Known test data patterns from conftest.py
    test_patterns = [
        {'symbol': 'AAPL', 'price': 170.0, 'mktcap': 2800000000000, 'name': 'Apple Inc.'},
        {'symbol': 'MSFT', 'price': 400.0, 'mktcap': 3000000000000, 'name': 'Microsoft Corp.'},
        {'symbol': 'GOOG', 'price': 2800.0, 'mktcap': 1800000000000, 'name': 'Alphabet Inc.'},
        {'symbol': 'AMZN', 'price': 3200.0, 'mktcap': 1600000000000, 'name': 'Amazon.com Inc.'},
        {'symbol': 'TSLA', 'price': 250.0, 'mktcap': 800000000000, 'name': 'Tesla Inc.'},
    ]
    
    found_fake_data = False
    
    print("🔍 Checking for fake/test data in production database...")
    
    with db.engine.connect() as conn:
        for pattern in test_patterns:
            result = conn.execute(text("""
                SELECT symbol, companyname, price, mktcap, created_at, updated_at
                FROM company_profiles 
                WHERE symbol = :symbol AND price = :price AND mktcap = :mktcap
            """), {
                'symbol': pattern['symbol'],
                'price': pattern['price'],
                'mktcap': pattern['mktcap']
            }).fetchone()
            
            if result:
                found_fake_data = True
                print(f"❌ FAKE DATA DETECTED: {pattern['symbol']}")
                print(f"   Price: ${result.price}, Market Cap: ${result.mktcap:,}")
                print(f"   Created: {result.created_at}, Updated: {result.updated_at}")
                print()
    
        if not found_fake_data:
            print("✅ No fake test data detected in production database")
            
            # Show current real data for verification
            print("\n📊 Current AAPL/MSFT data:")
            real_data = conn.execute(text("""
                SELECT symbol, companyname, price, mktcap 
                FROM company_profiles 
                WHERE symbol IN ('AAPL', 'MSFT')
                ORDER BY symbol
            """)).fetchall()
            
            for row in real_data:
                print(f"   {row.symbol}: ${row.price}, Market Cap: ${row.mktcap:,}")
    
    return found_fake_data

if __name__ == "__main__":
    has_fake_data = check_for_fake_data()
    sys.exit(1 if has_fake_data else 0)