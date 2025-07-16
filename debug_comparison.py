#!/usr/bin/env python3
"""Debug script to test stock comparison functionality"""

import os
import sys
sys.path.append('/app')

from database import DatabaseManager
from data_access_layer import StockDataService

def test_symbols_endpoint():
    """Test the symbols endpoint"""
    print("Testing symbols endpoint...")
    try:
        db = DatabaseManager()
        symbols = db.get_sp500_symbols()
        print(f"✓ Found {len(symbols)} symbols in database")
        
        # Check if test symbols exist
        test_symbols = ['AAPL', 'MSFT', 'ABNB', 'GOOGL', 'AMZN']
        for symbol in test_symbols:
            exists = symbol in symbols
            print(f"{'✓' if exists else '✗'} {symbol} exists in database: {exists}")
        
        return symbols
    except Exception as e:
        print(f"✗ Error getting symbols: {e}")
        return []

def test_stock_comparison():
    """Test stock comparison functionality"""
    print("\nTesting stock comparison...")
    try:
        service = StockDataService()
        test_symbols = ['AAPL', 'MSFT']
        
        print(f"Testing comparison for symbols: {test_symbols}")
        comparison_data = service.get_stock_comparison(test_symbols)
        
        print(f"✓ Got {len(comparison_data)} results from comparison")
        
        for stock in comparison_data:
            print(f"  - {stock.get('symbol', 'Unknown')}: {stock.get('company_name', 'No name')}")
        
        return comparison_data
    except Exception as e:
        print(f"✗ Error in stock comparison: {e}")
        import traceback
        traceback.print_exc()
        return []

def check_database_tables():
    """Check if required tables exist"""
    print("\nChecking database tables...")
    try:
        db = DatabaseManager()
        with db.engine.connect() as conn:
            from sqlalchemy import text
            
            tables = [
                'sp500_constituents',
                'company_profiles', 
                'undervaluation_scores',
                'income_statements',
                'balance_sheets',
                'cash_flow_statements'
            ]
            
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                print(f"  {table}: {count} records")
                
    except Exception as e:
        print(f"✗ Error checking tables: {e}")

if __name__ == "__main__":
    print("=== Stock Comparison Debug Script ===")
    
    # Test database connection
    try:
        db = DatabaseManager()
        with db.engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT version()"))
            print(f"✓ Connected to database: PostgreSQL")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)
    
    # Run tests
    symbols = test_symbols_endpoint()
    check_database_tables()
    comparison_data = test_stock_comparison()
    
    print(f"\n=== Summary ===")
    print(f"Symbols found: {len(symbols)}")
    print(f"Comparison results: {len(comparison_data)}")