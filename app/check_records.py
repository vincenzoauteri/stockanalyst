#!/usr/bin/env python3
"""
Quick script to check database record counts
Usage: python check_records.py
"""

import os
from datetime import datetime
from database import DatabaseManager
from sqlalchemy import text

def check_records():
    try:
        db_manager = DatabaseManager()
        
        with db_manager.engine.connect() as conn:
            print(f"📊 Database Record Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            # Main tables
            tables = {
                'sp500_constituents': 'S&P 500 Companies',
                'company_profiles': 'Company Profiles', 
                'historical_prices': 'Historical Prices',
                'undervaluation_scores': 'Undervaluation Scores'
            }
            
            for table, description in tables.items():
                try:
                    result = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.fetchone()[0]
                    print(f"{description:20}: {count:,} records")
                except Exception as e:
                    print(f"{description:20}: Error - {e}")
            
            print()
            
            # Historical prices details
            result = conn.execute(text('SELECT COUNT(DISTINCT symbol) FROM historical_prices'))
            unique_symbols = result.fetchone()[0]
            
            result = conn.execute(text('SELECT MIN(date), MAX(date) FROM historical_prices'))
            date_range = result.fetchone()
            
            # Use PostgreSQL compatible date function (CURRENT_DATE - INTERVAL '7 days')
            result = conn.execute(text("SELECT COUNT(*) FROM historical_prices WHERE date >= CURRENT_DATE - INTERVAL '7 days'"))
            recent_records = result.fetchone()[0]
            
            print("📈 Historical Data Summary:")
            print(f"   Symbols with data: {unique_symbols}")
            print(f"   Date range: {date_range[0]} to {date_range[1]}")
            print(f"   Recent records (7 days): {recent_records}")
            
            # Recently updated symbols
            result = conn.execute(text('''
                SELECT symbol, COUNT(*) as records, MAX(date) as latest_date
                FROM historical_prices 
                GROUP BY symbol 
                ORDER BY latest_date DESC 
                LIMIT 5
            '''))
            
            recent_updates = result.fetchall()
            print("\n🔄 Recently Updated Symbols:")
            for symbol, records, latest in recent_updates:
                print(f"   {symbol}: {records} records (latest: {latest})")
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")

if __name__ == "__main__":
    check_records()