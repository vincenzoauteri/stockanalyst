#!/usr/bin/env python3
"""
Debug API Tests - See what's actually happening
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Set environment variables before importing
os.environ.update({
    'SECRET_KEY': 'test-secret-key',
    'DATABASE_PATH': ':memory:',
    'FMP_API_KEY': 'test_fmp_key'
})

# Add the app directory to the path
sys.path.insert(0, '/app')

def debug_api_stocks_endpoint():
    """Debug the stocks endpoint"""
    from app import app
    
    with app.test_client() as client:
        response = client.get('/api/v2/stocks')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data.decode()}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"Success: {data.get('success')}")
            print(f"Data length: {len(data.get('data', []))}")
            if data.get('data'):
                print(f"First item: {data['data'][0]}")

def debug_api_stock_detail_endpoint():
    """Debug the stock detail endpoint"""
    from app import app
    
    with app.test_client() as client:
        response = client.get('/api/v2/stocks/AAPL')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data.decode()}")

def debug_api_health_endpoint():
    """Debug the health endpoint"""
    from app import app
    
    with app.test_client() as client:
        response = client.get('/api/v2/health')
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data.decode()}")

if __name__ == "__main__":
    print("🔍 Debugging API Endpoints")
    print("=" * 50)
    
    print("\n📊 Testing /api/v2/stocks")
    debug_api_stocks_endpoint()
    
    print("\n📈 Testing /api/v2/stocks/AAPL")
    debug_api_stock_detail_endpoint()
    
    print("\n🏥 Testing /api/v2/health")
    debug_api_health_endpoint()