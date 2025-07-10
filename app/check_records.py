#!/usr/bin/env python3
"""
Quick script to check database record counts
Usage: python check_records.py
"""

import sqlite3
import os
from datetime import datetime

def check_records():
    db_path = os.getenv('DATABASE_PATH', 'stock_analysis.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
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
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f"{description:20}: {count:,} records")
            except Exception as e:
                print(f"{description:20}: Error - {e}")
        
        print()
        
        # Historical prices details
        cursor.execute('SELECT COUNT(DISTINCT symbol) FROM historical_prices')
        unique_symbols = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(date), MAX(date) FROM historical_prices')
        date_range = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(*) FROM historical_prices WHERE date >= date("now", "-7 days")')
        recent_records = cursor.fetchone()[0]
        
        print("📈 Historical Data Summary:")
        print(f"   Symbols with data: {unique_symbols}")
        print(f"   Date range: {date_range[0]} to {date_range[1]}")
        print(f"   Recent records (7 days): {recent_records}")
        
        # Recently updated symbols
        cursor.execute('''
            SELECT symbol, COUNT(*) as records, MAX(date) as latest_date
            FROM historical_prices 
            GROUP BY symbol 
            ORDER BY latest_date DESC 
            LIMIT 5
        ''')
        
        recent_updates = cursor.fetchall()
        print("\n🔄 Recently Updated Symbols:")
        for symbol, records, latest in recent_updates:
            print(f"   {symbol}: {records} records (latest: {latest})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")

if __name__ == "__main__":
    check_records()